"""
leverage_manager.py — K430 Leverage Management Module
======================================================
Provides leverage-aware position sizing for all production sleeves.

Design:
  - Reads/writes data/leverage_config.json (single source of truth)
  - Default PAPER_TRADE phase → LEVERAGE=1.0 (additive: no behaviour change at default)
  - Rollout: PAPER_TRADE → LIVE_1.5X → LIVE_3X (user advances manually)
  - Per-exchange caps enforced (HL 3x, Bybit 3x, PAXG 10x, SPX 5x, sUSDe 1x)
  - Circuit breaker integration: check_margin_health() → refuse_trade() if > 80% margin used

K426 finding: 3x leverage → +$2.2M/yr @ $10M AUM
K430 implementation: safe-default PAPER_TRADE=1x, user advances to 1.5x then 3x

Usage:
  from leverage_manager import get_current_leverage, compute_position_size, check_margin_health

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# ── K339: REPO_ROOT from __file__ ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LEVERAGE_CONFIG_PATH = DATA_DIR / "leverage_config.json"

# ── Rollout phase constants ────────────────────────────────────────────────────
PHASE_PAPER_TRADE = "PAPER_TRADE"
PHASE_LIVE_1_5X   = "LIVE_1.5X"
PHASE_LIVE_3X     = "LIVE_3X"
ROLLOUT_SEQUENCE  = [PHASE_PAPER_TRADE, PHASE_LIVE_1_5X, PHASE_LIVE_3X]
PHASE_LEVERAGE_MAP = {
    PHASE_PAPER_TRADE: 1.0,
    PHASE_LIVE_1_5X:   1.5,
    PHASE_LIVE_3X:     3.0,
}

# ── Exchange-side leverage caps (HL min margin = notional / leverage) ──────────
DEFAULT_EXCHANGE_CAPS: Dict[str, float] = {
    "K280_K208_HL":    3.0,
    "K280_K208_Bybit": 3.0,
    "K280_K208_OKX":   3.0,   # K456: OKX 3rd venue (conservative 3x, OKX supports 100x for BTC)
    "K280_K208_Aevo":  3.0,   # K460: Aevo 4th venue (conservative 3x, Aevo max ~10x, 1h cycle)
    "K280_K208_dYdX":  3.0,   # K460: dYdX v4 5th venue (conservative 3x, Cosmos chain, TODO Cosmos signing)
    "K280_K276b":      3.0,
    "K297_PAXG":       10.0,
    "K297_SPX":        5.0,
    "sUSDe":           1.0,
    "K449_ETH_BTC":   4.0,   # K450: ETH-BTC paired-trade (v6.16 sleeve, HL-only)
    "K476_SOL_BTC":   4.0,   # K478: SOL-BTC paired-trade (v6.21 candidate, HL-only)
    "K484_AVAX_BTC":  4.0,   # K489: AVAX-BTC paired-trade (v6.23 candidate, HL-only, OOS Sh 43.89)
    "K493_ATOM_BTC":  4.0,   # K499: ATOM-BTC paired-trade (v6.24 candidate, HL-only, OOS Sh 50.79 #1 family)
    "K495_DEX_CEX_FLOW": 3.0,  # K502: DEX-CEX flow divergence (v6.25 candidate, HL-only, bear-conditional, $323K/yr)
    "K500_INJ_BTC":   4.0,   # K506: INJ-BTC paired-trade (v6.25 candidate, HL-only, OOS Sh 11.23, Cosmos 2nd, $124K/yr)
    "K507_SEI_BTC":   4.0,   # K514: SEI-BTC paired-trade (v6.27 candidate, HL+Bybit split, OOS Sh 48.10, Cosmos 3rd, $179K/yr)
    "K507_TIA_BTC":   4.0,   # K524: TIA-BTC paired-trade (v6.28 candidate, HL-only 1%, OOS Sh 14.44, Celestia modular DA #6, $51K/yr)
    "K512_APT_BTC":   4.0,   # K520: APT-BTC paired-trade (v6.28 candidate, HL+Bybit split, OOS Sh 51.10, Move-VM #1 family, $302K/yr)
    "K541_STABLECOIN_SUPPLY": 2.0,  # K550: stablecoin supply growth (v6.29 candidate, HL-only, 3% sleeve, 2x leverage, OOS Sh 1.498, $294K/yr)
    "K521_OPTIONS_SKEW": 2.0,       # K565: options 25d skew DVOL+skew V4 (v6.30 candidate, HL-only, 3% sleeve, 2x leverage, OOS Sh 1.019, $494K/yr)
    "K628_JTO_ORTHOG": 4.0,         # K637: JTO-BTC orthogonalized (v6.31 candidate, Bybit-only, 2-3% sleeve, 4x leverage, OOS Sh 18.30 residual, $17.85M/yr potential, Solana LST/MEV #24)
    "K631_WLD_ORTHOG": 4.0,         # K639: WLD-BTC orthogonalized (v6.32 candidate, Bybit-only, 2% sleeve, 4x leverage, OOS Sh 18.04 residual W=72h, $2.9M/yr @$10M, Biometric ID cluster, beta_JUP=0.458795)
    "K633_OP_ORTHOG":  4.0,         # K640: OP-BTC orthogonalized (v6.33 candidate, Bybit-only, 2% sleeve, 4x leverage, OOS Sh 12.68 residual W=72h, $2.32M/yr @$10M @4x, L2 Superchain cluster unlock, beta_FIL=0.542224)
    "K635_IMX_ORTHOG": 4.0,         # K641: IMX-BTC orthogonalized (v6.34 candidate, Bybit-only, 2% sleeve, 4x leverage, OOS Sh 24.81 residual MF W=168h, $4.78M/yr @$10M @4x, Gaming L2 Infra cluster, beta_SHIB=0.254 beta_TIA=0.068 beta_SEI=0.158)
    "K638_STX_ORTHOG": 4.0,         # K642: STX-BTC orthogonalized (v6.35 candidate, Bybit-only, 1.5% sleeve, 4x leverage, OOS Sh 12.38 residual MF W=504h, $65,018/yr net @$10M @4x, BTC-L2 cluster, beta_APT=0.203339 beta_SEI=0.125164 beta_DOGE=0.306518)
    "K645_BNB_ORTHOG":  4.0,        # K650: BNB-BTC orthogonalized (v6.36 candidate, Bybit-only, 3% sleeve, 4x leverage, OOS Sh 7.07 residual SF W=168h, $17,694/yr net @$10M @4x, Binance-ecosystem cluster, beta_ETH=0.539, ETH-cluster unlock 6th orthog, 45th daemon)
    "K646_ALGO_ORTHOG": 4.0,       # K651: ALGO-BTC orthogonalized (v6.37 candidate, Bybit-only, 2% sleeve, 4x leverage, OOS Sh 8.11 residual SF W=72h, ~$20,325/yr net @$10M @4x, Enterprise/Utility L1 Algorand PoS VRF cluster, beta_FIL=0.411, FIL-cluster unlock 7th orthog, 46th daemon)
    "K648_POL_ORTHOG": 4.0,       # K652: POL-BTC orthogonalized (v6.37 candidate, Bybit-only, 2% sleeve, 4x leverage, OOS Sh 23.41 residual MF W=168h, $4,293,200/yr @$10M @4x, Polygon L2/PoS/zkEVM cluster unlock, beta_OP=0.337443 beta_SEI=0.075509 beta_APT=-0.016480 beta_TIA=0.059789 beta_FIL=0.042751 beta_SAND=0.200488, 6-factor unlock 7th orthog confirmed, 47th daemon)
    "K647_DOT_ORTHOG":  4.0,      # K653: DOT-BTC orthogonalized (v6.38 candidate, Bybit-only, 3% sleeve, 4x leverage, OOS Sh 23.25 residual SF W=168h, ~$103,586/yr net @$10M @4x, Governance/Staking Polkadot relay chain cluster, beta_INJ=0.642, INJ-cluster unlock 8th orthog, 48th daemon, OOS R²=-4.11 STRUCTURAL BREAK caution, IS beta re-OLS every 30d mandatory)
    "K629_WLD_ETH":   4.0,       # K654: WLD-ETH FR Differential (v6.38 candidate, HL-primary, 3% sleeve, 4x leverage, OOS Sh 19.90 W=168h direct diff, $94,210/yr @$10M @4x, Biometric ID cluster Cluster 24, ETH-base fix JUP-BTC corr=0.3437 PASS, 9/9 §6 gates, 49th daemon)
    "K656_GALA_ORTHOG": 4.0,    # K659: GALA-BTC dual-factor orthogonalized (v6.40 candidate, Bybit-only, 2% sleeve, 4x leverage, OOS Sh 8.3211 residual DF W=504h, $48,143/yr net @$10M @4x, Gaming Publisher Gala Games P2E GalaChain L1, beta_JUP=0.22738 beta_FIL=0.405439, JUP+FIL dual-factor unlock 9th orthog MILESTONE, 50th daemon MILESTONE, gaming cluster COMPLETE)
    "K663_TIA_ETH":  4.0,     # K668: TIA-ETH FR Differential (v6.41 candidate, HL-primary, 1.5% sleeve, 4x leverage, OOS Sh 17.13 W=168h direct diff, $63,060/yr net @$10M @4x, Modular DA Celestia cluster, ETH-base K660 SURPRISE G5b corr=0.2309 PASS, dual with K507 TIA-BTC 1.5%, 9/9 §6 gates, 51st daemon)
    "K658_SOL_ETH":  4.0,     # K669: SOL-ETH FR Differential (v6.40 candidate, HL-primary, 1.5% sleeve, 4x leverage, OOS Sh 29.66 W=168h direct diff, $42,332/yr @$10M @4x (1.5% sleeve), SOL L1 Monolithic SVM DePIN-Retail cluster, ETH-base wins Sh 16.30->29.66 +13.36 vs K476, SOL-BTC corr=0.2131 PASS dual sleeve, 9/9 §6 gates, 52nd daemon)
    "K661_AVAX_ETH": 4.0,   # K677: AVAX-ETH FR Differential (v6.43 candidate, HL-primary, 1.5% sleeve, 4x leverage, OOS Sh 28.26 W=168h direct diff, $63,416/yr net @$10M @4x (1.5% sleeve), AVAX Subnet/RWA Avalanche9000 cluster, ETH-base ACCEPT CONDITIONAL PnL corr=0.3731 PASS dual-sleeve K484, G5a K449 corr=-0.008 CRITICAL PASS, 6/7 §6 gates G6 structural 18.6/yr, 53rd daemon 6th ETH-base scaffold)
    "K587_ICP_BTC":  4.0,   # K678: ICP-BTC FR Differential (BTC-base Compute/Cloud cluster, HL 0.5%+Bybit 0.5% split, 4x leverage, OOS Sh 12.53 W=168h, $21K/yr net @$10M @4x (1% sleeve), ICP vol 8.40x highest in BTC-base family, HL maxLev=5x limit uses 4x margin of safety, 60d paper-trade gate, v6.43 candidate, 54th daemon)
    "K457_basket":    4.0,   # K459: BTC+ETH+SOL multi-asset basket carry (matches K449 4x cap)
}

# ── v6.13d sleeve weights (K348) ──────────────────────────────────────────────
# v6.16 candidate: K280 72% + K297' 20% + sUSDe 5% + K449 3% = 100%
SLEEVE_WEIGHTS: Dict[str, float] = {
    "K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72
    "K297":   0.20,   # K302a satellite (PAXG 60% + SPX 40%)
    "sUSDe":  0.05,   # sUSDe OC sleeve
    "K449":   0.03,   # K449 ETH-BTC FR differential paired-trade (K450 scaffold)
    "K457":   0.00,   # K457 BTC+ETH+SOL basket (K459 scaffold, 5% target at v6.20 activation)
    "K476":   0.00,   # K476 SOL-BTC FR differential paired-trade (K478 scaffold, 3% target at v6.21 activation)
    "K484":   0.00,   # K484 AVAX-BTC FR differential paired-trade (K489 scaffold, 3% target at v6.23 activation)
    "K493":   0.00,   # K493 ATOM-BTC FR differential paired-trade (K499 scaffold, 3% target at v6.24 activation)
    "K495":   0.00,   # K495 DEX-CEX flow divergence bear-conditional (K502 scaffold, 3% target at v6.25 activation)
}

# v6.21 candidate weights (proposed in K478 — not yet active)
SLEEVE_WEIGHTS_V621: Dict[str, float] = {
    "K280":  0.69,   # reduced 3pp to fund K476 sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.03,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 activation)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, K478 scaffold)
}

# v6.23 candidate weights (proposed in K489 — not yet active)
# K449 5% + K476 3% + K484 3% = 11% combined paired-trade sleeve, ~$276K/yr @ $10M
SLEEVE_WEIGHTS_V623: Dict[str, float] = {
    "K280":  0.63,   # reduced 6pp vs v6.13d to fund combined paired-trade sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.05,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, bumped to 5%)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition)
    "K484":  0.03,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, K489 scaffold)
    "K457":  0.01,   # BTC+ETH+SOL basket (placeholder, reduced from v6.20 5% pending paper gate)
}

# v6.24 candidate weights (proposed in K499 — not yet active)
# K449 5% + K476 3% + K484 3% + K493 3% = 14% combined paired-trade sleeve, ~$507K/yr @ $10M
SLEEVE_WEIGHTS_V624: Dict[str, float] = {
    "K280":  0.60,   # reduced 3pp vs v6.23 to fund K493 ATOM-BTC sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.05,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition)
    "K484":  0.03,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition)
    "K493":  0.03,   # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, K499 scaffold)
    "K457":  0.01,   # BTC+ETH+SOL basket (placeholder, pending paper gate)
}

# v6.25 candidate weights (proposed in K502/K506 — not yet active)
# K449 5% + K476 3% + K484 3% + K493 3% + K500 3% = 17% combined paired-trade sleeve, ~$631K/yr @ $10M
# K495 (DEX-CEX bear-conditional) is orthogonal axis — included in v6.25 total portfolio
# v6.25 activation: K500 INJ-BTC (34th daemon) + K495 DEX-CEX (33rd daemon, bear-conditional)
# Note: K495 sleeve adjusts K280 allocation when bear regime active; K500 is always-on carry
SLEEVE_WEIGHTS_V625: Dict[str, float] = {
    "K280":  0.57,   # reduced 3pp vs v6.24 to fund K495 DEX-CEX bear-conditional sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.05,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition)
    "K484":  0.03,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition)
    "K493":  0.03,   # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, K499 scaffold)
    "K500":  0.03,   # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, K506 scaffold, $124K/yr)
    "K495":  0.03,   # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
    "K457":  0.01,   # BTC+ETH+SOL basket (placeholder, pending paper gate)
}

# v6.27 candidate weights (proposed in K514 — not yet active)
# K449 5% + K476 3% + K484 3% + K493 3% + K500 3% + K507 3% = 20% combined paired-trade sleeve
# ~$810K/yr @ $10M (K449 $187K + K476 $187K + K484 $75.7K + K493 $231K + K500 $124K + K507 $179K)
# HL+Bybit split: K507 uses HL 1.5% + Bybit 1.5% → HL 63.5% (1.5pp headroom vs 65% cap)
# K507 Cosmos 3rd CONFIRMED: SEI EVM-compat + Cosmos SDK distinct from ATOM IBC + INJ DeFi-perp
SLEEVE_WEIGHTS_V627: Dict[str, float] = {
    "K280":  0.54,   # reduced 3pp vs v6.25 to fund K507 SEI-BTC sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.05,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":  0.03,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition)
    "K484":  0.03,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition)
    "K493":  0.03,   # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition)
    "K500":  0.03,   # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, $124K/yr)
    "K507":  0.03,   # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, K514 scaffold, $179K/yr)
    "K495":  0.03,   # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
    "K457":  0.01,   # BTC+ETH+SOL basket (placeholder, pending paper gate)
}

# v6.28 candidate weights (proposed in K520/K524 — not yet active)
# K449 5% + K476 4% + K484 5% + K493 5% + K500 4% + K507 SEI 2% + K507 TIA 1% + K512 APT 2% = 28% combined
# ~$1.162M/yr @ $10M (K449 $187K + K476 $187K + K484 $75.7K + K493 $231K + K500 $124K + K507 SEI $179K + K512 APT $302K + K507 TIA $51K)
# HL concentration: K512 HL+Bybit 1%+1% (HL 64%) + K507 TIA HL-only 1% = HL 65% (exactly at cap)
# K512 Move-VM #1 CONFIRMED: APT Block-STM parallel execution + Move resource model — family rank #1 OOS Sh 51.10
# K507 TIA Celestia DA CONFIRMED: modular DA layer, rollup adoption drives FR dynamics, G5d 0.05 vs ATOM LOWEST in family
SLEEVE_WEIGHTS_V628: Dict[str, float] = {
    "K280":  0.51,   # reduced 1pp vs K520 draft to fund K507 TIA-BTC sleeve (K524)
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.05,   # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":  0.04,   # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, bumped to 4%)
    "K484":  0.05,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, bumped to 5%)
    "K493":  0.05,   # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, bumped to 5%)
    "K500":  0.04,   # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, bumped to 4%)
    "K507":  0.02,   # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, reduced to 2%)
    "K507_TIA": 0.01, # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr, Celestia DA #6)
    "K512":  0.02,   # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, K520 scaffold, $302K/yr)
    "K495":  0.03,   # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.29 candidate weights (proposed in K550 — not yet active)
# K541 Stablecoin Supply Growth 3% sleeve added to v6.28 combined portfolio
# OOS Sh 1.498, $294K/yr @$10M, 7-axis Sh 6.872 +0.165 lift, G5 max corr 0.074 orthogonal
# 90d paper-trade gate (longer than 60d for lower Sharpe)
# DefiLlama free API: USDT+USDC supply z-score 2nd derivative (V3 acceleration spike)
# Total combined v6.29: ~$1.456M/yr @$10M (v6.28 $1.162M + K541 $294K)
SLEEVE_WEIGHTS_V629: Dict[str, float] = {
    "K280":    0.48,    # reduced 3pp vs v6.28 to fund K541 stablecoin sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr, 90d gate)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.30 candidate weights (proposed in K565 — not yet active)
# K521 Options 25d Skew 3% sleeve added to v6.29 combined portfolio
# OOS Sh 1.019, $494K/yr @$10M, 5-axis Sh 6.386 +0.082 lift, Max corr 0.199 orthogonal
# 90d paper-trade gate (G3 DSR CONDITIONAL — longer gate for conservative DSR)
# Deribit free API: DVOL index + 25d skew (no auth) — BTC LONG directional
# Total combined v6.30: ~$1.950M/yr @$10M (v6.29 $1.456M + K521 $494K)
# HL concentration: K521 BTC LONG = HL-only +3% → watch vs 65% cap (v6.29 HL at ~65%+)
# v6.30 activation: K521 90d gate pass + HL concentration review (may require K280 reduction)
SLEEVE_WEIGHTS_V630: Dict[str, float] = {
    "K280":    0.45,    # reduced 3pp vs v6.29 to fund K521 options skew sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.31 candidate weights (proposed in K637 — not yet active)
# K628 JTO orthogonalized 2% Bybit sleeve added to v6.30 combined portfolio
# OOS Sh 18.30 (residual), $17,851,320/yr potential @$10M @4x (largest single-token)
# 2% sleeve = $7,140,528/yr | 3% sleeve = $10,710,792/yr
# Bybit-only: HL concentration UNCHANGED at 65% (K628 uses Bybit for JTO+BTC)
# Orthog β HARDCODED: β_SEI=0.164, β_DOGE=0.302 (K628 OLS, IS R²=0.075)
# 60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<20%
# Total combined v6.31: ~$1.950M/yr @$10M (v6.30 $1.950M) + K628 $7.14M/yr = $9.09M/yr potential
# Note: v6.31 profit is 2% sleeve activation scenario; 3% = higher (K280 further reduced)
SLEEVE_WEIGHTS_V631: Dict[str, float] = {
    "K280":    0.43,    # reduced 2pp vs v6.30 to fund K628 JTO orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, 2% sleeve)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.32 candidate weights (proposed in K639 — not yet active)
# K631 WLD-BTC orthogonalized 2% Bybit sleeve added to v6.31 combined portfolio
# OOS Sh 18.04 (residual W=72h), $2,900,000/yr @$10M @4x (2% sleeve)
# Bybit-only: HL concentration UNCHANGED at 65% (K631 uses Bybit for WLD+BTC)
# Orthog β HARDCODED: β_JUP=0.458795 (K631 OLS, W=72h optimal)
# 60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<20%
# Total combined v6.32: v6.31 portfolio + K631 $2.9M/yr = incremental Biometric ID alpha
SLEEVE_WEIGHTS_V632: Dict[str, float] = {
    "K280":    0.41,    # reduced 2pp vs v6.31 to fund K631 WLD orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr, Biometric ID)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.33 candidate weights (proposed in K640 — not yet active)
# K633 OP-BTC orthogonalized 2% Bybit sleeve added to v6.32 combined portfolio
# OOS Sh 12.68 (residual W=72h), $2,318,640/yr @$10M @4x (full potential)
# 2% sleeve = $46,373/yr | L2 Superchain cluster unlock
# Bybit-only: HL concentration UNCHANGED at 65% (K633 uses Bybit for OP+BTC)
# Orthog β HARDCODED: β_FIL=0.542224 (K633 OLS, IS R²=0.3283, W=72h optimal)
# 60d paper-trade gate: Realized Sh>=5 + fill>=60% + maxDD<20%
# L2 cluster unlock: OP orthog validates L2 Rollup / Optimism Superchain as new alpha cluster
SLEEVE_WEIGHTS_V633: Dict[str, float] = {
    "K280":    0.39,    # reduced 2pp vs v6.32 to fund K633 OP orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr @4x, L2 cluster unlock)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.34 candidate weights (proposed in K641 — not yet active)
# K635 IMX-BTC orthogonalized 2% Bybit sleeve added to v6.33 combined portfolio
# OOS Sh 24.81 (residual MF SHIB+TIA+SEI W=168h), $4,775,120/yr @$10M @4x (2% sleeve)
# Bybit-only: HL concentration UNCHANGED at 65% (K635 uses Bybit for IMX+BTC)
# Orthog beta HARDCODED: beta_SHIB=0.254, beta_TIA=0.068, beta_SEI=0.158 (K635 OLS MF)
# 60d paper-trade gate: Realized Sh>=12 + fill>=60% + maxDD<20%
# Gaming L2 Infra cluster: ImmutableX StarkEx ZK rollup for NFT/gaming
# Total combined v6.34: v6.33 portfolio + K635 $4.78M/yr = incremental Gaming L2 alpha
SLEEVE_WEIGHTS_V634: Dict[str, float] = {
    "K280":    0.37,    # reduced 2pp vs v6.33 to fund K635 IMX orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.35 candidate weights (proposed in K642 — not yet active)
# K638 STX-BTC orthogonalized 1.5% Bybit sleeve added to v6.34 combined portfolio
# OOS Sh 12.38 (residual MF APT+SEI+DOGE W=504h), $65,018/yr net @$10M @4x (1.5% sleeve)
# Bybit-only: HL concentration UNCHANGED at 65% (K638 uses Bybit for STX+BTC)
# Orthog beta HARDCODED: beta_APT=0.203339, beta_SEI=0.125164, beta_DOGE=0.306518 (K638 OLS MF)
# 60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<20%
# BTC-L2 cluster: STX PoX Proof-of-Transfer Bitcoin Layer-2
# Total combined v6.35: v6.34 portfolio + K638 $65K/yr = incremental BTC-L2 alpha
SLEEVE_WEIGHTS_V635: Dict[str, float] = {
    "K280":    0.355,   # reduced 1.5pp vs v6.34 to fund K638 STX orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.36 candidate weights (proposed in K650 — not yet active)
# K645 BNB-BTC orthogonalized 3% Bybit sleeve added to v6.35 combined portfolio
# OOS Sh 7.07 (residual SF ETH W=168h), $17,694/yr net @$10M @4x (3% sleeve)
# Bybit-only: HL concentration UNCHANGED at 65% (K645 uses Bybit for BNB+BTC)
# Orthog beta HARDCODED: beta_ETH=0.539 (K645 OLS SF)
# 60d paper-trade gate: Realized Sh>=3.5 + fill>=60% + maxDD<20%
# ETH-cluster unlock: K480 BLOCKED (ETH corr=0.435) -> K645 post-orth=0.1757 PASS
# Binance-ecosystem cluster: BSC DEX cycles / BNB burn / Launchpad IDO / opBNB L2
# Total combined v6.36: v6.35 portfolio + K645 $17,694/yr = incremental Binance-ecosystem alpha
SLEEVE_WEIGHTS_V636: Dict[str, float] = {
    "K280":    0.325,   # reduced 3pp vs v6.35 to fund K645 BNB orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.37 candidate weights (proposed in K651 — not yet active)
# K646 ALGO-BTC orthogonalized 2% Bybit sleeve added to v6.36 combined portfolio
# OOS Sh 8.11 (residual SF FIL W=72h), ~$20,325/yr net @$10M @4x (2% sleeve)
# Bybit-only: HL concentration UNCHANGED at 65% (K646 uses Bybit for ALGO+BTC)
# Orthog beta HARDCODED: beta_FIL=0.411 (K646 OLS SF)
# 60d paper-trade gate: Realized Sh>=4 + fill>=60% + maxDD<20%
# FIL-cluster unlock: K522 BLOCKED (FIL corr=0.6052) -> K646 post-orth=0.2546 PASS
# Enterprise/Utility L1 cluster: Algorand VRF cycles / CBDC pilots / DeFi-lite adoption
# Total combined v6.37: v6.36 portfolio + K646 $20,325/yr = incremental Algorand PoS alpha
SLEEVE_WEIGHTS_V637: Dict[str, float] = {
    "K280":    0.305,   # reduced 2pp vs v6.36 to fund K646 ALGO orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.37 candidate weights (proposed in K652 — not yet active)
# K648 POL-BTC orthogonalized 2% Bybit sleeve added to v6.36 combined portfolio
# OOS Sh=23.41 (residual MF 6-factor W=168h), $4,293,200/yr @$10M @4x (2% sleeve)
# Bybit-only: HL concentration UNCHANGED at 65% (K648 uses Bybit for POL+BTC)
# betas HARDCODED: OP=0.337443 SEI=0.075509 APT=-0.016480 TIA=0.059789 FIL=0.042751 SAND=0.200488 (K648 OLS MF 6-factor)
# 60d paper-trade gate: Realized Sh>=12 + fill>=60% + maxDD<20%
# Polygon L2 cluster unlock: K611 BLOCKED-ROLLUP-SIBLING (6 factors) -> K648 all post-orth < 0.40 (max |OP|=0.096 PASS)
# AggLayer/zkEVM alpha: Polygon-specific FR dynamics orthogonal to OP+SEI+APT+TIA+FIL+SAND
# Total combined v6.37: v6.36 portfolio + K648 $4.29M/yr = largest single orthog addition in series
SLEEVE_WEIGHTS_V637: Dict[str, float] = {
    "K280":    0.305,   # reduced 2pp vs v6.36 to fund K648 POL orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.38 candidate weights (proposed in K653 — not yet active)
# K647 DOT-BTC orthogonalized 3% Bybit sleeve added to v6.37 combined portfolio
# OOS Sh 23.25 (residual SF INJ W=168h), ~$103,586/yr net @$10M @4x (3% sleeve)
# Bybit-only: HL concentration 65%->64% (3% split: HL 1.5%+Bybit 1.5%) — 1pp headroom
# Orthog beta HARDCODED: beta_INJ=0.642 (K647 OLS SF)
# 60d paper-trade gate STRICT: Realized Sh>=12 + fill>=60% + maxDD<15% (OOS R²=-4.11 caution)
# IS beta re-OLS every 30d mandatory (structural break monitoring)
# INJ-cluster unlock: K513 BLOCKED (INJ corr=0.4229) -> K647 post-orth=0.037 PASS
# Governance/Staking cluster: Polkadot relay chain 28d unbonding / OpenGov / parachain auctions
# Total combined v6.38: v6.37 portfolio + K647 $103,586/yr = incremental Polkadot relay-chain alpha
SLEEVE_WEIGHTS_V638: Dict[str, float] = {
    "K280":    0.275,   # reduced 3pp vs v6.37 to fund K647 DOT orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Governance/Staking Polkadot relay chain, OOS R²=-4.11 caution)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# K629 WLD-ETH FR Differential 3% HL sleeve added to v6.38 combined portfolio
# OOS Sh 19.90 (W=168h direct diff, 9/9 §6 PASS), $94,210/yr @$10M @4x (3% sleeve)
# HL-primary: WLD-PERP + ETH-PERP both on HL — HL concentration 57.5% -> ~59.5% (+2pp, within 65% limit)
# Signal: diff = WLD_FR - ETH_FR (direct, no OLS orthogonalization — ETH base is the mechanism fix)
# ETH-base fix: JUP-BTC cross-base corr=0.3437 PASS (K621 WLD-BTC blocked at 0.4612)
# Anti-corr with K449 ETH-BTC (corr=-0.2052): portfolio diversification benefit
# 60d paper-trade gate: Realized Sh>=10 + fill>=60% + maxDD<15%
# Biometric ID cluster: WLD = Worldcoin/World ID biometric proof-of-humanhood + AI-bot resistance
# Total combined v6.39: v6.38 portfolio + K629 $94,210/yr = Cluster 24 ETH-base unlock
SLEEVE_WEIGHTS_V639: Dict[str, float] = {
    "K280":    0.245,   # reduced 3pp vs v6.38 to fund K629 WLD-ETH sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Governance/Staking Polkadot relay chain, OOS R²=-4.11 caution)
    "K629":    0.03,    # WLD-ETH FR Differential, 4x leverage, HL-primary (v6.39 K654 addition, $94,210/yr, Biometric ID Cluster 24, ETH-base fix)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# K656 GALA-BTC Dual-Factor Orthogonalized FR Differential 2% Bybit sleeve added to v6.39
# OOS Sh 8.3211 (DF W=504h dual-factor, ACCEPT CONDITIONAL), $48,143/yr net @$10M @4x (2% sleeve)
# Bybit-only: GALAUSDT perp + BTC-USDT-SWAP — HL cap breached (66.5% > 65%); HL concentration unchanged
# Signal: residual = GALA_diff - 0.22738*JUP_diff - 0.405439*FIL_diff; rolling_mean_504h > 1.5sigma
# K620 dual blockers cleared: JUP 0.4308->0.0495 (-87%), FIL 0.4114->0.0184 (-96%)
# IS R²=0.4731: LARGEST in K6xx orthog series (FIRST dual-factor JUP+FIL)
# Gaming cluster COMPLETE: SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) all ACCEPT CONDITIONAL
# 60d paper-trade gate: Realized Sh>=4 + fill>=60% + maxDD<20% (50% of OOS Sh=8.32)
# 50th daemon MILESTONE — 9th orthog scaffold — gaming cluster completion
# Total combined v6.40: v6.39 portfolio + K656 $48K/yr = gaming cluster complete
SLEEVE_WEIGHTS_V640: Dict[str, float] = {
    "K280":    0.225,   # reduced 2pp vs v6.39 to fund K656 GALA orthog sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.01,  # TIA-BTC delta-neutral, 4x leverage, HL-only 1% (v6.28 K524 addition, $51K/yr)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Governance/Staking Polkadot relay chain, OOS R²=-4.11 caution)
    "K629":    0.03,    # WLD-ETH FR Differential, 4x leverage, HL-primary (v6.39 K654 addition, $94,210/yr, Biometric ID Cluster 24, ETH-base fix)
    "K656":    0.02,    # GALA-BTC dual-factor orthogonalized, 4x leverage, Bybit-only (v6.40 K659 MILESTONE, $48,143/yr net, Gaming Publisher GalaChain, JUP+FIL dual-factor, 50th daemon)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# K663 TIA-ETH FR Differential 1.5% HL sleeve added to v6.40
# OOS Sh 17.13 (W=168h direct diff, zero threshold, 9/9 §6 PASS), $63,060/yr net @$10M @4x (1.5% sleeve)
# HL-only: TIA-PERP and ETH-PERP on Hyperliquid; HL concentration +1.5pp to ~61.0% (within 65%)
# Signal: sign(rolling_mean_168h(TIA_FR - ETH_FR)) — zero threshold, 55.3 trades/yr
# G5b TIA-BTC K507 corr=0.2309 PASS (K660 predicted BLOCKED-APT-style; ACTUAL: PASS K660 SURPRISE)
# TIA vol_ratio=2.12x + periodic Celestia DA narrative spikes above ETH = signal divergence from K507
# Dual-sleeve: K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = $114,598/yr net @$10M
# 60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<15%
# 51st daemon
SLEEVE_WEIGHTS_V641: Dict[str, float] = {
    "K280":    0.21,   # reduced 1.5pp vs v6.40 to fund K663 TIA-ETH HL sleeve
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.04,    # SOL-BTC delta-neutral, 4x leverage, HL-only (v6.21 addition, 4%)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.015, # TIA-BTC delta-neutral, 4x leverage, HL-only 1.5% (dual with K663 TIA-ETH; was 1%)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Polkadot relay chain, OOS R²=-4.11 caution)
    "K629":    0.03,    # WLD-ETH FR Differential, 4x leverage, HL-primary (v6.39 K654 addition, $94,210/yr, Biometric ID Cluster 24, ETH-base fix)
    "K656":    0.02,    # GALA-BTC dual-factor orthogonalized, 4x leverage, Bybit-only (v6.40 K659 MILESTONE, $48,143/yr net, Gaming Publisher GalaChain)
    "K663":    0.015,   # TIA-ETH FR Differential, 4x leverage, HL-primary (v6.41 K668 addition, $63,060/yr net, Modular DA Celestia, ETH-base K660 SURPRISE, dual with K507_TIA 1.5%, 51st daemon)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# K658 SOL-ETH FR Differential 1.5% HL sleeve added to v6.41
# OOS Sh 29.66 (W=168h direct diff, sign threshold, ETH-base wins vs K476 SOL-BTC Sh=16.30)
# HL-only: SOL-PERP and ETH-PERP on Hyperliquid; HL concentration: neutral (K476 reduced 4%->1.5%)
# Signal: sign(rolling_mean_168h(SOL_FR - ETH_FR)) — zero threshold, 20.3 trades/yr (G6 structural)
# Dual-sleeve: K476 SOL-BTC 1.5% + K658 SOL-ETH 1.5% = 3% combined ($85K/yr est); PnL corr=0.2131
# ETH-base wins: SOL FR = DePIN/retail momentum; ETH FR = DeFi/staking yields → distinct drivers
# 60d paper-trade gate: Realized Sh>=15 + fill>=60% + maxDD<15%
# 52nd daemon — K669 scaffold
SLEEVE_WEIGHTS_V642: Dict[str, float] = {
    "K280":    0.21,    # unchanged vs v6.41 (K658 at 1.5% uses K476 reduction space — net neutral)
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.015,   # SOL-BTC delta-neutral, 4x leverage, HL-only (reduced 4%->1.5% to pair with K658)
    "K484":    0.05,    # AVAX-BTC delta-neutral, 4x leverage, HL-only (v6.23 addition, 5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.015, # TIA-BTC delta-neutral, 4x leverage, HL-only 1.5% (dual with K663 TIA-ETH)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Polkadot relay chain, OOS R²=-4.11 caution)
    "K629":    0.03,    # WLD-ETH FR Differential, 4x leverage, HL-primary (v6.39 K654 addition, $94,210/yr, Biometric ID Cluster 24, ETH-base fix)
    "K656":    0.02,    # GALA-BTC dual-factor orthogonalized, 4x leverage, Bybit-only (v6.40 K659 MILESTONE, $48,143/yr net, Gaming Publisher GalaChain)
    "K663":    0.015,   # TIA-ETH FR Differential, 4x leverage, HL-primary (v6.41 K668 addition, $63,060/yr net, Modular DA Celestia, dual with K507_TIA, 51st daemon)
    "K658":    0.015,   # SOL-ETH FR Differential, 4x leverage, HL-primary (v6.42 K669 addition, $42,332/yr @1.5%, SOL L1 SVM DePIN-Retail, ETH-base wins Sh 16.30->29.66, dual K476 1.5%, 52nd daemon)
    "K661":    0.015,   # AVAX-ETH FR Differential, 4x leverage, HL-primary (v6.43 K677 addition, $63,416/yr net @1.5%, AVAX Subnet/RWA Avalanche9000, ETH-base ACCEPT CONDITIONAL PnL corr=0.3731 dual K484 1.5%, 53rd daemon 6th ETH-base scaffold)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# K661 AVAX-ETH FR Differential 1.5% HL sleeve added to v6.42
# OOS Sh 28.26 (W=168h direct diff, zero threshold, 6/7 §6 gates, G6 structural 18.6/yr)
# HL-only: AVAX-PERP and ETH-PERP on Hyperliquid; HL concentration +~1.5pp to ~64.0% (within 65%)
# Signal: sign(rolling_mean_168h(AVAX_FR - ETH_FR)) — zero threshold, 18.6 trades/yr
# ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base marginally better)
# PnL corr=0.3731 < 0.40 -> dual-sleeve eligible: K484 1.5% + K661 1.5% = $139K/yr est
# G5a ETH-BTC K449 corr=-0.008 (CRITICAL: shared ETH leg minimal risk — near-zero)
# G5b AVAX-BTC K484 corr=0.3731 PASS (family orthogonality — dual-sleeve eligible)
# 60d paper-trade gate: Realized Sh>=14 + fill>=60% + maxDD<15%
# 53rd daemon — K677 scaffold — 6th ETH-base mechanism scaffold
SLEEVE_WEIGHTS_V643: Dict[str, float] = {
    "K280":    0.21,    # unchanged vs v6.42 (K661 at 1.5% uses K484 headroom — net neutral vs HL cap)
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.015,   # SOL-BTC delta-neutral, 4x leverage, HL-only (reduced 4%->1.5% per K669 dual-sleeve)
    "K484":    0.015,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (reduced from 5% to 1.5% for K661 dual-sleeve; K484 AVAX-BTC primary)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.015, # TIA-BTC delta-neutral, 4x leverage, HL-only 1.5% (dual with K663 TIA-ETH)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Polkadot relay chain, OOS R²=-4.11 caution)
    "K629":    0.03,    # WLD-ETH FR Differential, 4x leverage, HL-primary (v6.39 K654 addition, $94,210/yr, Biometric ID Cluster 24, ETH-base fix)
    "K656":    0.02,    # GALA-BTC dual-factor orthogonalized, 4x leverage, Bybit-only (v6.40 K659 MILESTONE, $48,143/yr net, Gaming Publisher GalaChain)
    "K663":    0.015,   # TIA-ETH FR Differential, 4x leverage, HL-primary (v6.41 K668 addition, $63,060/yr net, Modular DA Celestia, dual with K507_TIA, 51st daemon)
    "K658":    0.015,   # SOL-ETH FR Differential, 4x leverage, HL-primary (v6.42 K669 addition, $42,332/yr @1.5%, SOL L1 SVM DePIN-Retail, dual K476 1.5%, 52nd daemon)
    "K661":    0.015,   # AVAX-ETH FR Differential, 4x leverage, HL-primary (v6.43 K677 addition, $63,416/yr net @1.5%, AVAX Subnet/RWA, ETH-base ACCEPT CONDITIONAL dual K484 1.5%, 53rd daemon)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# K587 ICP-BTC FR Differential 1% split sleeve added to v6.43
# OOS Sh 12.53 (W=168h EMA, ICP FR - BTC FR, sign threshold ±0.00001)
# HL+Bybit split: ICP leg HL 0.5%, BTC leg Bybit 0.5% (high-vol — ICP vol 8.40x vs BTC = highest in family)
# HL maxLev ICP = 5x; strategy uses 4x (margin of safety; conservative below HL hard limit)
# Compute/Cloud cluster: Internet Computer Protocol (Dfinity) — decentralised cloud compute
# Neuron staking unlock cycles, SNS DAO launches, canister demand waves → orthogonal FR dynamics
# $21K/yr net @$10M @4x @1% total sleeve (HL 0.5% + Bybit 0.5%)
# 60d paper-trade gate: Realized Sh>=6 (50% of OOS 12.53) + fill>=60% + maxDD<20%
# 54th daemon — K678 scaffold
SLEEVE_WEIGHTS_V644: Dict[str, float] = {
    "K280":    0.21,    # unchanged vs v6.43 (K587 ICP HL+Bybit split — HL 0.5% net vs cap)
    "K297":    0.20,
    "sUSDe":   0.05,
    "K449":    0.05,    # ETH-BTC delta-neutral, 4x leverage, HL-only (v6.16 base, 5%)
    "K476":    0.015,   # SOL-BTC delta-neutral, 4x leverage, HL-only (dual K658 1.5%)
    "K484":    0.015,   # AVAX-BTC delta-neutral, 4x leverage, HL-only (dual K661 1.5%)
    "K493":    0.05,    # ATOM-BTC delta-neutral, 4x leverage, HL-only (v6.24 addition, 5%)
    "K500":    0.04,    # INJ-BTC delta-neutral, 4x leverage, HL-only (v6.25 addition, 4%)
    "K507":    0.02,    # SEI-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.27 addition, 2%)
    "K507_TIA": 0.015, # TIA-BTC delta-neutral, 4x leverage, HL-only 1.5% (dual with K663 TIA-ETH)
    "K512":    0.02,    # APT-BTC delta-neutral, 4x leverage, HL+Bybit split (v6.28 addition, $302K/yr)
    "K541":    0.03,    # Stablecoin supply growth, 2x leverage, HL-only (v6.29 K550 addition, $294K/yr)
    "K521":    0.03,    # Options 25d skew DVOL+skew V4, 2x leverage, HL-only (v6.30 K565 addition, $494K/yr)
    "K628":    0.02,    # JTO-BTC orthogonalized, 4x leverage, Bybit-only (v6.31 K637 addition, $7.14M/yr)
    "K631":    0.02,    # WLD-BTC orthogonalized, 4x leverage, Bybit-only (v6.32 K639 addition, $2.9M/yr)
    "K633":    0.02,    # OP-BTC orthogonalized, 4x leverage, Bybit-only (v6.33 K640 addition, $2.32M/yr)
    "K635":    0.02,    # IMX-BTC orthogonalized, 4x leverage, Bybit-only (v6.34 K641 addition, $4.78M/yr, Gaming L2 Infra)
    "K638":    0.015,   # STX-BTC orthogonalized, 4x leverage, Bybit-only (v6.35 K642 addition, $65K/yr net, BTC-L2 cluster)
    "K645":    0.03,    # BNB-BTC orthogonalized, 4x leverage, Bybit-only (v6.36 K650 addition, $17,694/yr net, Binance-ecosystem)
    "K646":    0.02,    # ALGO-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K651 addition, ~$20,325/yr net, Enterprise/Utility L1)
    "K648":    0.02,    # POL-BTC orthogonalized, 4x leverage, Bybit-only (v6.37 K652 addition, $4,293,200/yr, Polygon L2/zkEVM cluster)
    "K647":    0.03,    # DOT-BTC orthogonalized, 4x leverage, Bybit-only (v6.38 K653 addition, ~$103,586/yr net, Polkadot relay chain, OOS R²=-4.11 caution)
    "K629":    0.03,    # WLD-ETH FR Differential, 4x leverage, HL-primary (v6.39 K654 addition, $94,210/yr, Biometric ID Cluster 24, ETH-base fix)
    "K656":    0.02,    # GALA-BTC dual-factor orthogonalized, 4x leverage, Bybit-only (v6.40 K659 MILESTONE, $48,143/yr net, Gaming Publisher GalaChain)
    "K663":    0.015,   # TIA-ETH FR Differential, 4x leverage, HL-primary (v6.41 K668 addition, $63,060/yr net, Modular DA Celestia, dual with K507_TIA, 51st daemon)
    "K658":    0.015,   # SOL-ETH FR Differential, 4x leverage, HL-primary (v6.42 K669 addition, $42,332/yr @1.5%, SOL L1 SVM DePIN-Retail, dual K476 1.5%, 52nd daemon)
    "K661":    0.015,   # AVAX-ETH FR Differential, 4x leverage, HL-primary (v6.43 K677 addition, $63,416/yr net @1.5%, AVAX Subnet/RWA, ETH-base ACCEPT CONDITIONAL dual K484 1.5%, 53rd daemon)
    "K587":    0.01,    # ICP-BTC FR Differential, 4x leverage, HL 0.5%+Bybit 0.5% split (v6.43 K678 addition, $21K/yr net @1%, Compute/Cloud cluster, ICP vol 8.40x highest in family, HL maxLev=5x uses 4x, 54th daemon)
    "K495":    0.03,    # DEX-CEX flow divergence, 3x leverage, bear-conditional (v6.25 addition, K502 scaffold)
}

# v6.16 candidate weights (proposed in K450 — not yet active)
SLEEVE_WEIGHTS_V616: Dict[str, float] = {
    "K280":  0.72,   # reduced 3pp to fund K449 sleeve
    "K297":  0.20,
    "sUSDe": 0.05,
    "K449":  0.03,   # ETH-BTC delta-neutral, 4x leverage, HL-only
}


# ─────────────────────────────────────────────────────────────────────────────
# Config I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> Dict:
    """Load leverage_config.json; return defaults if missing."""
    if LEVERAGE_CONFIG_PATH.exists():
        try:
            with open(LEVERAGE_CONFIG_PATH) as f:
                return json.load(f)
        except Exception as e:
            print(f"  [leverage_manager] Config load error: {e} — using defaults")
    # Return safe defaults (PAPER_TRADE, 1x)
    return {
        "rollout_phase":    PHASE_PAPER_TRADE,
        "current_leverage": 1.0,
        "target_leverage":  3.0,
        "exchange_caps":    DEFAULT_EXCHANGE_CAPS.copy(),
        "deployment_pct":   0.80,
        "cash_buffer_pct":  0.20,
        "circuit_breaker": {
            "max_margin_pct":     0.80,
            "warning_margin_pct": 0.70,
            "deactivated":        False,
        },
        "rollout_history": [],
    }


def _save_config(cfg: Dict) -> None:
    """Persist leverage config atomically."""
    tmp = LEVERAGE_CONFIG_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(LEVERAGE_CONFIG_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Core API
# ─────────────────────────────────────────────────────────────────────────────

def get_current_leverage() -> float:
    """
    Return current operational leverage from config.

    At PAPER_TRADE (default): returns 1.0 — no change to position sizing.
    At LIVE_1.5X: returns 1.5.
    At LIVE_3X: returns 3.0.
    If circuit_breaker.deactivated is True: returns 1.0 regardless (emergency).
    """
    cfg = _load_config()
    # Circuit breaker override: emergency reduce to 1x
    cb = cfg.get("circuit_breaker", {})
    if cb.get("deactivated", False):
        return 1.0
    lev = float(cfg.get("current_leverage", 1.0))
    return max(1.0, lev)


def get_rollout_phase() -> str:
    """Return current rollout phase string."""
    return _load_config().get("rollout_phase", PHASE_PAPER_TRADE)


def compute_position_size(
    sleeve_name: str,
    current_aum: float,
    deployment_pct: Optional[float] = None,
) -> float:
    """
    Compute leveraged notional position size for a sleeve.

    Formula:
        notional = current_aum × deployment_pct × sleeve_weight × leverage

    Args:
        sleeve_name:    One of 'K280', 'K297', 'sUSDe'
        current_aum:    Total portfolio AUM in USD
        deployment_pct: Fraction of AUM deployed (reads from config if None)

    Returns:
        Notional position size in USD.

    Example at 3x (K280, $10M AUM, 80% deployment):
        notional = $10M × 0.80 × 0.75 × 3.0 = $18M

    K448: Apply per-sleeve exchange caps (e.g. sUSDe capped at 1x).
    """
    cfg = _load_config()
    raw_leverage = get_current_leverage()

    # K448/K450: cap leverage by exchange limit per sleeve
    cap_key_map = {
        "K280":   "K280_K208_HL",
        "K297":   "K297_PAXG",
        "sUSDe":  "sUSDe",
        "K449":   "K449_ETH_BTC",   # K450: 4x cap for ETH-BTC paired-trade sleeve
        "K457":   "K457_basket",    # K459: 4x cap for BTC+ETH+SOL basket
        "K476":   "K476_SOL_BTC",   # K478: 4x cap for SOL-BTC paired-trade sleeve
        "K484":   "K484_AVAX_BTC",  # K489: 4x cap for AVAX-BTC paired-trade sleeve
        "K493":   "K493_ATOM_BTC",  # K499: 4x cap for ATOM-BTC paired-trade sleeve
        "K495":   "K495_DEX_CEX_FLOW",  # K502: 3x cap for DEX-CEX flow divergence (bear-conditional)
        "K500":   "K500_INJ_BTC",   # K506: 4x cap for INJ-BTC paired-trade sleeve
        "K507":     "K507_SEI_BTC",   # K514: 4x cap for SEI-BTC paired-trade sleeve (HL+Bybit split)
        "K507_TIA": "K507_TIA_BTC",  # K524: 4x cap for TIA-BTC paired-trade sleeve (HL-only 1%, Celestia DA #6)
        "K512":     "K512_APT_BTC",  # K520: 4x cap for APT-BTC paired-trade sleeve (HL+Bybit split, Move-VM #1)
        "K587":     "K587_ICP_BTC",  # K678: 4x cap for ICP-BTC paired-trade sleeve (HL+Bybit split, Compute/Cloud, ICP HL maxLev=5x)
    }
    cap_key = cap_key_map.get(sleeve_name, sleeve_name)
    exchange_caps = cfg.get("exchange_caps", DEFAULT_EXCHANGE_CAPS)
    sleeve_cap = float(exchange_caps.get(cap_key, raw_leverage))
    effective_leverage = min(raw_leverage, sleeve_cap)

    sleeve_weight = SLEEVE_WEIGHTS.get(sleeve_name, 0.0)
    if deployment_pct is None:
        deployment_pct = float(cfg.get("deployment_pct", 0.80))

    return current_aum * deployment_pct * sleeve_weight * effective_leverage


def compute_margin_required(
    sleeve_name: str,
    leverage: Optional[float] = None,
    current_aum: float = 0.0,
    deployment_pct: Optional[float] = None,
) -> float:
    """
    Compute margin required for a sleeve at given leverage.

    HL exchange margin model: margin = notional / exchange_leverage_cap
    (Exchange provides leverage; margin = collateral posted.)

    For sUSDe (spot, no leverage): margin = notional (leverage = 1x always).

    Args:
        sleeve_name:    One of 'K280', 'K297', 'sUSDe'
        leverage:       Operational leverage to use (reads from config if None)
        current_aum:    AUM for absolute margin computation (0 = ratio only)
        deployment_pct: Deployment fraction (reads from config if None)

    Returns:
        Margin required in USD (0.0 if current_aum=0, i.e. fractional mode).
    """
    cfg = _load_config()
    if leverage is None:
        leverage = get_current_leverage()
    if deployment_pct is None:
        deployment_pct = float(cfg.get("deployment_pct", 0.80))

    # Exchange cap lookup (sleeve → exchange cap key)
    cap_key_map = {
        "K280":   "K280_K208_HL",   # use HL cap as conservative reference
        "K297":   "K297_PAXG",      # PAXG dominates margin (60% weight)
        "sUSDe":  "sUSDe",
        "K449":   "K449_ETH_BTC",   # K450: 4x cap ETH-BTC paired-trade
        "K457":   "K457_basket",    # K459: 4x cap BTC+ETH+SOL basket
        "K476":   "K476_SOL_BTC",   # K478: 4x cap SOL-BTC paired-trade
        "K484":   "K484_AVAX_BTC",  # K489: 4x cap AVAX-BTC paired-trade
        "K495":   "K495_DEX_CEX_FLOW",  # K502: 3x cap DEX-CEX flow divergence
        "K500":   "K500_INJ_BTC",   # K506: 4x cap INJ-BTC paired-trade
        "K507":     "K507_SEI_BTC",   # K514: 4x cap SEI-BTC paired-trade (HL+Bybit split)
        "K507_TIA": "K507_TIA_BTC",  # K524: 4x cap TIA-BTC paired-trade (HL-only 1%, Celestia DA #6)
        "K512":     "K512_APT_BTC",  # K520: 4x cap APT-BTC paired-trade (HL+Bybit split, Move-VM #1)
        "K587":     "K587_ICP_BTC",  # K678: 4x cap ICP-BTC paired-trade (HL+Bybit split, Compute/Cloud, ICP HL maxLev=5x)
    }
    cap_key = cap_key_map.get(sleeve_name, sleeve_name)
    exchange_caps = cfg.get("exchange_caps", DEFAULT_EXCHANGE_CAPS)
    exchange_cap  = float(exchange_caps.get(cap_key, 1.0))

    # Cap operational leverage at exchange cap
    eff_leverage = min(leverage, exchange_cap)

    if current_aum <= 0:
        # Return margin fraction of notional (useful for ratio checks)
        return 1.0 / eff_leverage if eff_leverage > 0 else 1.0

    notional = compute_position_size(sleeve_name, current_aum, deployment_pct)
    # At 1x: no exchange leverage benefit → margin = notional
    margin = notional / eff_leverage
    return margin


def check_margin_health(
    current_aum: float,
    deployment_pct: Optional[float] = None,
    verbose: bool = False,
) -> Dict:
    """
    Compute portfolio-wide margin health snapshot.

    Returns:
        {
            "margin_used_pct":       float,   # 0–1 fraction of AUM used as margin
            "cash_buffer_remaining": float,   # USD remaining as cash buffer
            "warning":               bool,    # True if > warning_margin_pct (70%)
            "circuit_breaker_fire":  bool,    # True if > max_margin_pct (80%)
            "sleeves":               dict,    # per-sleeve margin breakdown
            "leverage":              float,
            "phase":                 str,
        }

    Circuit breaker logic:
        margin_used_pct > 80% → fire (emergency reduce to 1x)
        margin_used_pct > 70% → warning (dashboard alert)
    """
    cfg            = _load_config()
    leverage       = get_current_leverage()
    phase          = get_rollout_phase()
    cb             = cfg.get("circuit_breaker", {})
    max_pct        = float(cb.get("max_margin_pct", 0.80))
    warn_pct       = float(cb.get("warning_margin_pct", 0.70))
    if deployment_pct is None:
        deployment_pct = float(cfg.get("deployment_pct", 0.80))

    sleeves_margin: Dict[str, float] = {}
    total_margin   = 0.0

    for sleeve in ["K280", "K297", "sUSDe", "K449", "K457", "K476", "K484", "K493", "K495", "K500", "K507"]:
        m = compute_margin_required(sleeve, leverage, current_aum, deployment_pct)
        sleeves_margin[sleeve] = round(m, 2)
        total_margin += m

    margin_used_pct  = total_margin / current_aum if current_aum > 0 else 0.0
    cash_buffer      = current_aum - total_margin

    # In PAPER_TRADE at 1x: margin = notional (no exchange leverage benefit yet).
    # At 1x with 80% deployment, computed margin_used_pct = 80% which is benign.
    # Suppress CB fire/warning in PAPER_TRADE — only meaningful when leverage > 1x.
    _phase = cfg.get("rollout_phase", PHASE_PAPER_TRADE)
    if _phase == PHASE_PAPER_TRADE or leverage <= 1.0:
        cb_fire = False
        warning = False
    else:
        cb_fire = margin_used_pct > max_pct
        warning = margin_used_pct > warn_pct

    if verbose:
        print(f"  [margin_health] phase={phase}, leverage={leverage}x, "
              f"margin_used={margin_used_pct*100:.1f}%, cash_buffer=${cash_buffer:,.0f}")
        for s, m in sleeves_margin.items():
            print(f"    {s}: ${m:,.0f}")
        if cb_fire:
            print("  [margin_health] *** CIRCUIT BREAKER FIRE ***")
        elif warning:
            print("  [margin_health] WARNING: margin usage approaching limit")

    return {
        "margin_used_pct":       round(margin_used_pct, 4),
        "cash_buffer_remaining": round(cash_buffer, 2),
        "total_margin_usd":      round(total_margin, 2),
        "warning":               warning,
        "circuit_breaker_fire":  cb_fire,
        "sleeves":               sleeves_margin,
        "leverage":              leverage,
        "phase":                 phase,
        "aum":                   current_aum,
        "max_margin_pct":        max_pct,
        "warn_margin_pct":       warn_pct,
        "checked_at_utc":        datetime.now(timezone.utc).isoformat(),
    }


def refuse_trade(sleeve_name: str, margin_check: Dict) -> None:
    """
    Log and raise when margin health check blocks a trade.
    Called by production scripts when compute_margin_required > MAX_ALLOWED.
    """
    msg = (
        f"[leverage_manager] TRADE REFUSED — {sleeve_name}: "
        f"margin_used_pct={margin_check.get('margin_used_pct',0)*100:.1f}% "
        f"exceeds max {margin_check.get('max_margin_pct',0.80)*100:.0f}%. "
        f"phase={margin_check.get('phase','?')}, leverage={margin_check.get('leverage',1)}x. "
        f"Emergency: reduce leverage or increase cash buffer."
    )
    print(msg)
    # Write alert to data/leverage_alert.json for dashboard pickup
    alert_path = DATA_DIR / "leverage_alert.json"
    with open(alert_path, "w") as f:
        json.dump({"alert": msg, "ts_utc": datetime.now(timezone.utc).isoformat(),
                   "margin_check": margin_check}, f, indent=2)
    raise RuntimeError(msg)


def apply_rollout_step() -> Dict:
    """
    Advance rollout phase one step: PAPER_TRADE → LIVE_1.5X → LIVE_3X.
    Idempotent at LIVE_3X (already at target).

    Returns updated config dict.
    This is a USER-TRIGGERED action; NOT called automatically.
    """
    cfg   = _load_config()
    phase = cfg.get("rollout_phase", PHASE_PAPER_TRADE)
    idx   = ROLLOUT_SEQUENCE.index(phase) if phase in ROLLOUT_SEQUENCE else 0

    if idx >= len(ROLLOUT_SEQUENCE) - 1:
        print(f"  [leverage_manager] Already at max rollout phase: {phase}")
        return cfg

    next_phase = ROLLOUT_SEQUENCE[idx + 1]
    next_lev   = PHASE_LEVERAGE_MAP[next_phase]

    # Record history entry
    history_entry = {
        "ts_utc":      datetime.now(timezone.utc).isoformat(),
        "from_phase":  phase,
        "to_phase":    next_phase,
        "from_lev":    cfg.get("current_leverage", 1.0),
        "to_lev":      next_lev,
    }
    cfg.setdefault("rollout_history", []).append(history_entry)

    cfg["rollout_phase"]    = next_phase
    cfg["current_leverage"] = next_lev
    _save_config(cfg)

    print(f"  [leverage_manager] Rollout advanced: {phase} → {next_phase} "
          f"(leverage {history_entry['from_lev']}x → {next_lev}x)")
    return cfg


def emergency_reduce_leverage() -> None:
    """
    Emergency leverage reduction: set circuit_breaker.deactivated = True.
    get_current_leverage() returns 1.0 when deactivated=True.
    All scripts automatically use 1x leverage after this call.
    """
    cfg = _load_config()
    cfg.setdefault("circuit_breaker", {})["deactivated"] = True
    cfg["rollout_phase"]    = PHASE_PAPER_TRADE  # record phase regression
    cfg["current_leverage"] = 1.0
    cfg.setdefault("rollout_history", []).append({
        "ts_utc":      datetime.now(timezone.utc).isoformat(),
        "event":       "EMERGENCY_REDUCE",
        "from_phase":  get_rollout_phase(),
        "to_phase":    PHASE_PAPER_TRADE,
        "from_lev":    cfg.get("current_leverage", 1.0),
        "to_lev":      1.0,
    })
    _save_config(cfg)
    print("  [leverage_manager] EMERGENCY LEVERAGE REDUCE: circuit_breaker.deactivated=True, leverage=1x")


def restore_leverage_after_emergency(target_phase: str = PHASE_PAPER_TRADE) -> None:
    """
    Restore leverage after emergency. Sets deactivated=False and resets to target_phase.
    User calls this manually after resolving the margin crisis.
    """
    if target_phase not in ROLLOUT_SEQUENCE:
        raise ValueError(f"Unknown phase: {target_phase}. Must be one of {ROLLOUT_SEQUENCE}")
    cfg = _load_config()
    cfg.setdefault("circuit_breaker", {})["deactivated"] = False
    cfg["rollout_phase"]    = target_phase
    cfg["current_leverage"] = PHASE_LEVERAGE_MAP[target_phase]
    cfg.setdefault("rollout_history", []).append({
        "ts_utc":   datetime.now(timezone.utc).isoformat(),
        "event":    "EMERGENCY_RESTORE",
        "to_phase": target_phase,
        "to_lev":   PHASE_LEVERAGE_MAP[target_phase],
    })
    _save_config(cfg)
    print(f"  [leverage_manager] Leverage restored: phase={target_phase}, "
          f"leverage={PHASE_LEVERAGE_MAP[target_phase]}x, deactivated=False")


# ─────────────────────────────────────────────────────────────────────────────
# CLI (quick sanity check)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]

    if "--advance" in args:
        updated = apply_rollout_step()
        print(f"Phase: {updated['rollout_phase']}, Leverage: {updated['current_leverage']}x")
        sys.exit(0)

    if "--emergency-reduce" in args:
        emergency_reduce_leverage()
        sys.exit(0)

    if "--restore" in args:
        target = args[args.index("--restore") + 1] if len(args) > args.index("--restore") + 1 else PHASE_PAPER_TRADE
        restore_leverage_after_emergency(target)
        sys.exit(0)

    # Default: print current status
    cfg = _load_config()
    lev = get_current_leverage()
    phase = get_rollout_phase()
    print(f"\n=== K430 Leverage Manager Status ===")
    print(f"  Rollout phase:    {phase}")
    print(f"  Current leverage: {lev}x")
    print(f"  Target leverage:  {cfg.get('target_leverage', 3.0)}x")
    print(f"  Circuit breaker:  {'DEACTIVATED (emergency 1x)' if cfg.get('circuit_breaker',{}).get('deactivated') else 'OK'}")
    print(f"  Deployment pct:   {cfg.get('deployment_pct', 0.80)*100:.0f}%")

    # Show position sizes at $10M for reference
    aum = 10_000_000
    print(f"\n  Position sizes @ ${aum/1e6:.0f}M AUM ({lev}x leverage):")
    for sleeve in ["K280", "K297", "sUSDe", "K449", "K457"]:
        notional = compute_position_size(sleeve, aum)
        margin   = compute_margin_required(sleeve, lev, aum)
        print(f"    {sleeve:8s}: notional=${notional:>12,.0f}  margin=${margin:>12,.0f}")

    health = check_margin_health(aum, verbose=True)
    print(f"\n  Margin used: {health['margin_used_pct']*100:.1f}%  "
          f"Cash buffer: ${health['cash_buffer_remaining']:,.0f}")
    print(f"  CB fire: {health['circuit_breaker_fire']}  Warning: {health['warning']}")

#!/usr/bin/env python3
"""Ground-truth deployment status verifier (K311).

Runs after each wave that touches daemons/plists, to confirm what HTML
claims matches actual launchctl/filesystem state. Output is JSON for
HTML consumption and a stderr summary for the operator.

Status levels (least to most committed):
    SCAFFOLD-READY      script files exist, no plist
    PENDING ACTIVATION  plist exists, not loaded
    LOADED              launchctl knows about it but no PID
    ACTIVE              launchctl reports a PID
    DEPRECATED          previously active, plist removed or unload'd
    UNKNOWN             cannot decide

Usage:
    python scripts/verify_deployment_status.py
    python scripts/verify_deployment_status.py --json-only > status.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOGS_DIR = REPO_ROOT / "logs"

JST = timezone(timedelta(hours=9))


@dataclass
class DaemonSpec:
    label: str
    purpose: str
    scripts: list[str] = field(default_factory=list)
    log_basename: Optional[str] = None
    expected_html_status: Optional[str] = None  # what HTML currently claims


REGISTRY: list[DaemonSpec] = [
    DaemonSpec(
        label="com.cryptolab.k280-live",
        purpose="K280 main 80% (K198+K208+K276b_top20 on Bybit+HL)",
        scripts=["scripts/k280_live_fetch.py", "scripts/k280_daily_run.py"],
        log_basename="k280_live",
        expected_html_status="PENDING ACTIVATION",  # K310 plist staged, awaiting manual load
    ),
    DaemonSpec(
        label="com.cryptolab.k302a-satellite",
        purpose="K302a v6.12 satellite 20% (PAXG/SPX HL-only)",
        scripts=[
            "scripts/k302a_satellite_fetch.py",
            "scripts/k302a_satellite_run.py",
        ],
        log_basename="k302a_satellite",
        expected_html_status="PENDING ACTIVATION",
    ),
    DaemonSpec(
        label="com.cryptolab.hl-predicted-monitor",
        purpose="K304 HL predictedFundings 5min poll (230 coins × 3 venues)",
        scripts=["scripts/hl_predicted_fr_monitor.py"],
        log_basename="hl_predicted_monitor",
        expected_html_status="PENDING ACTIVATION",
    ),
    DaemonSpec(
        label="com.cryptolab.hlp-monitor",
        purpose="K200 HLP balance monitor — NO BACKING SCRIPT (K310 audit finding)",
        scripts=["scripts/hlp_balance_monitor.py"],
        log_basename="hlp_monitor",
        expected_html_status="UNKNOWN",  # K310 corrected from ACTIVE; no script exists
    ),
    DaemonSpec(
        label="com.cryptolab.k287-satellite",
        purpose="K287d satellite (DEPRECATED — K289, 60d rollback until 2026-07-25)",
        scripts=["scripts/k287_satellite_fetch.py", "scripts/k287_satellite_run.py"],
        log_basename="k287_satellite",
        expected_html_status="SCAFFOLD-READY",  # K310 acknowledged plist never created
    ),
    DaemonSpec(
        label="com.cryptolab.susde-oc",
        purpose="K344 sUSDe Optimal Control sleeve (v6.13d 5%)",
        scripts=["scripts/k344_susde_oc_daily_run.py"],
        log_basename="k344_susde_oc",
        expected_html_status="SCAFFOLD-READY",  # K348: plist in repo root (gitignored); cp to LaunchAgents then launchctl load to activate
    ),
    DaemonSpec(
        label="com.cryptolab.hl-hip4-monitor",
        purpose="K353/K356 HIP-4 prediction market polling (2-week calibration to K368)",
        scripts=["scripts/hl_hip4_monitor.py"],
        log_basename="hl_hip4_monitor",
        expected_html_status="SCAFFOLD-READY",  # plist in repo root (gitignored), cp to LaunchAgents to activate
    ),
    DaemonSpec(
        label="com.cryptolab.variational-fr-monitor",
        purpose="K363/K365 Variational RWA FR data accumulation (trading API target Q3-Q4 2026)",
        scripts=["scripts/variational_fr_monitor.py"],
        log_basename="variational_fr_monitor",
        expected_html_status="SCAFFOLD-READY",
    ),
    DaemonSpec(
        label="com.cryptolab.k376-momentum",
        purpose="K376 volume momentum paper-trade (v6.14 candidate, ETH/LINK/AVAX, BTC regime filter)",
        scripts=["scripts/k376_momentum_run.py"],
        log_basename="k376_momentum",
        expected_html_status="SCAFFOLD-READY",
    ),
    DaemonSpec(
        label="com.cryptolab.k386-v613e-fallback",
        purpose="K386 v6.13e BEAR_1 fallback (K385 conditional: CFTC/HL, K280 85%+BTC/ETH spot 10%+sUSDe 5%, HL 52.5%)",
        scripts=["scripts/k386_v613e_fallback_run.py"],
        log_basename="k386_v613e_fallback",
        expected_html_status="SCAFFOLD-READY",  # plist in repo root (gitignored); activate only on BEAR_1 trigger
    ),
    DaemonSpec(
        label="com.cryptolab.regulatory-rss",
        purpose="K387 SEC/CFTC RSS monitor (30min polling, HyperLiquid/HIP-3/manipulation keyword alerts, manual review only)",
        scripts=["scripts/regulatory_rss_monitor.py"],
        log_basename="regulatory_rss_monitor",
        expected_html_status="SCAFFOLD-READY",  # plist in repo root (gitignored); 30min StartInterval via launchd
    ),
    DaemonSpec(
        label="com.cryptolab.protocol-tvl-monitor",
        purpose="K407 Generic TVL trajectory monitor (HypurrFi + Variational + future protocols, weekly polling, DefiLlama API)",
        scripts=["scripts/protocol_tvl_trajectory_monitor.py"],
        log_basename="protocol_tvl_monitor",
        expected_html_status="SCAFFOLD-READY",  # plist in repo root (gitignored); weekly StartInterval (604800) via launchd
    ),
    DaemonSpec(
        label="com.cryptolab.susde-apy-monitor",
        purpose="K412 sUSDe APY weekly monitor (K344 sleeve re-eval automation, K361 baseline tracking, DefiLlama yields API)",
        scripts=["scripts/susde_apy_monitor.py"],
        log_basename="k412_susde_apy",
        expected_html_status="SCAFFOLD-READY",  # plist in repo root (gitignored); weekly StartInterval (604800) via launchd
    ),
    DaemonSpec(
        label="com.cryptolab.k415-usdy",
        purpose="K415 USDY sleeve paper-trade scaffold (v6.15a/b activation pathway, 4.5% APY T-bill yield, 40-day lock monitor, DefiLlama+Ondo API, daily 06:00 JST)",
        scripts=["scripts/k415_usdy_sleeve_run.py"],
        log_basename="k415_usdy_sleeve",
        expected_html_status="SCAFFOLD-READY",  # K415: plist in repo root (gitignored); activate only after user non-US confirm + USDY purchase
    ),
    DaemonSpec(
        label="com.cryptolab.leverage-circuit-breaker",
        purpose="K430 3x leverage circuit breaker (5-min margin health monitor, margin>80% fires emergency 1x reduce, margin>70% warning, 15th daemon)",
        scripts=["scripts/leverage_circuit_breaker.py", "scripts/leverage_manager.py"],
        log_basename="leverage_circuit_breaker",
        expected_html_status="SCAFFOLD-READY",  # K430: plist in repo root (gitignored); activate when advancing to LIVE_1.5X/LIVE_3X rollout phase
    ),
    DaemonSpec(
        label="com.cryptolab.smart-router",
        purpose="K434 Smart Router daemon (cross-venue HL/Bybit/OKX FR scoring, 1h polling, K208 route optimization, +$175K/yr @ $10M, 16th daemon)",
        scripts=["scripts/smart_router.py"],
        log_basename="smart_router",
        expected_html_status="SCAFFOLD-READY",  # K434: plist in repo root (gitignored); activate after live testing
    ),
    DaemonSpec(
        label="com.cryptolab.k443-variational-paper",
        purpose="K443 K297'' Variational paper-trade scaffold (XAU 50%+XAG 30%+CL 20%, 4h funding, 8% AUM, capacity expansion $25M+, trading API trigger Q3-Q4 2026, 17th daemon)",
        scripts=["scripts/k297_variational_run.py"],
        log_basename="k443_variational_paper",
        expected_html_status="SCAFFOLD-READY",  # K443: plist in repo root (gitignored); activate when Variational trading API released
    ),
    DaemonSpec(
        label="com.cryptolab.loss-harvester",
        purpose="K444 Loss harvesting annual cron (Dec 28 06:00 JST, tax-aware tracking, $2-41K/yr tax savings INFORMATIONAL ONLY, 18th daemon)",
        scripts=["scripts/loss_harvester.py"],
        log_basename="loss_harvester",
        expected_html_status="SCAFFOLD-READY",  # K444: plist in repo root (gitignored); fires annually Dec 28; user activates after setting TAX_RATE_PCT
    ),
    DaemonSpec(
        label="com.cryptolab.k449-eth-btc",
        purpose="K449 ETH-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL-only, v6.16 candidate 3% sleeve, 19th daemon)",
        scripts=["scripts/k449_eth_btc_run.py"],
        log_basename="k449_eth_btc",
        expected_html_status="SCAFFOLD-READY",  # K450: plist in repo root (gitignored); activate after 60d paper-trade gate + fill_rate>=65%
    ),
    DaemonSpec(
        label="com.cryptolab.okx-fr-monitor",
        purpose="K456 OKX FR Monitor (K454 v6.20 wave 1/7, 3rd K208 venue, 18-symbol FR poll, 8h cycle, triangle arb HL/Bybit/OKX, 20th daemon)",
        scripts=["scripts/okx_fr_fetcher.py"],
        log_basename="okx_fr_monitor",
        expected_html_status="SCAFFOLD-READY",  # K456: plist in repo root (gitignored); activate after OKX API keys configured + v6.20 go-live
    ),
    DaemonSpec(
        label="com.cryptolab.depth-allocator",
        purpose="K458 Depth-Aware Allocator (K454 phase 5 HIGH priority, v6.20 capacity rescue, 5% OI cap per venue, HL/Bybit/OKX greedy distribution, $100M+ slippage guard, 21st daemon)",
        scripts=["scripts/depth_aware_allocator.py"],
        log_basename="depth_allocator",
        expected_html_status="SCAFFOLD-READY",  # K458: plist in repo root (gitignored); activate after v6.20 go-live + AUM >$10M
    ),
    DaemonSpec(
        label="com.cryptolab.k457-basket",
        purpose="K457 BTC+ETH+SOL Multi-Asset Basket FR Carry (K459 scaffold, inv-vol weights, DAR(2,1) gate, 6 legs, HL+Bybit, 4x leverage, 5% sleeve v6.20, 60d paper-trade gate, 22nd daemon)",
        scripts=["scripts/k457_basket_run.py"],
        log_basename="k457_basket",
        expected_html_status="SCAFFOLD-READY",  # K459: plist in repo root (gitignored); activate after 60d paper-trade gate + OOS Sharpe >=15 + fill_rate >=65%
    ),
    DaemonSpec(
        label="com.cryptolab.aevo-fr-monitor",
        purpose="K460 Aevo FR Monitor (K454 v6.20 wave 5/7, 4th K208 venue, 14-symbol FR poll, 1h cycle, cross-venue arb HL/Bybit/OKX/Aevo, api.aevo.xyz, 23rd daemon)",
        scripts=["scripts/aevo_fr_fetcher.py"],
        log_basename="aevo_fr_monitor",
        expected_html_status="SCAFFOLD-READY",  # K460: plist in repo root (gitignored); activate after Aevo API keys configured + v6.20 go-live
    ),
    DaemonSpec(
        label="com.cryptolab.dydx-v4-fr-monitor",
        purpose="K460 dYdX v4 FR Monitor (K454 v6.20 wave 6/7, 5th K208 venue, Cosmos chain, 18-symbol FR poll, 1h cycle, indexer.dydx.trade, 24th daemon)",
        scripts=["scripts/dydx_v4_fr_fetcher.py"],
        log_basename="dydx_v4_fr_monitor",
        expected_html_status="SCAFFOLD-READY",  # K460: plist in repo root (gitignored); activate after Cosmos signing impl + v6.20 go-live
    ),
    DaemonSpec(
        label="com.cryptolab.lighter-fr-monitor",
        purpose="K465 Lighter FR Monitor (K454 v6.20 6th K208 venue, zkEVM perps, 14-symbol FR poll, 8h cycle, mainnet.zklighter.elliot.ai, conservative tier, 25th daemon)",
        scripts=["scripts/lighter_fr_fetcher.py"],
        log_basename="lighter_fr_monitor",
        expected_html_status="SCAFFOLD-READY",  # K465: plist in repo root (gitignored); activate after Lighter trading keys configured + v6.20 go-live
    ),
    DaemonSpec(
        label="com.cryptolab.vertex-fr-monitor",
        purpose="K465 Vertex FR Monitor (K454 v6.20 7th K208 venue, spot+perp AMM, USDC margin, 14-symbol FR poll, 8h cycle, gateway.prod.vertexprotocol.com/v1, conservative tier, 26th daemon — 7-venue K208 mesh COMPLETE)",
        scripts=["scripts/vertex_fr_fetcher.py"],
        log_basename="vertex_fr_monitor",
        expected_html_status="SCAFFOLD-READY",  # K465: plist in repo root (gitignored); activate after Vertex trading keys configured + v6.20 go-live
    ),
    DaemonSpec(
        label="com.cryptolab.jlp-apy-monitor",
        purpose="K468 JLP APY trigger monitor (K467 CONDITIONAL trigger-based, Jupiter Perpetuals LP, break-even 21%, entry trigger >=25%, weekly DefiLlama poll, 27th daemon)",
        scripts=["scripts/jlp_apy_monitor.py"],
        log_basename="jlp_apy_monitor",
        expected_html_status="SCAFFOLD-READY",  # K468: plist in repo root (gitignored); weekly StartInterval (604800) via launchd; activate when JLP entry trigger fires (>=25% APY)
    ),
    DaemonSpec(
        label="com.cryptolab.spark-usds-monitor",
        purpose="K473 Spark sUSDS APY weekly monitor (K471 fast-track, 50/50 sUSDe+sUSDS sleeve, v6.21 candidate, combined APY 4-5%, +$40K/yr at $10M, weekly DefiLlama poll, 28th daemon)",
        scripts=["scripts/spark_usds_monitor.py"],
        log_basename="k473_spark_usds",
        expected_html_status="SCAFFOLD-READY",  # K473: plist in repo root (gitignored); weekly StartInterval (604800) via launchd; activate after K266 gate review + sUSDS position funded
    ),
    DaemonSpec(
        label="com.cryptolab.k476-sol-btc",
        purpose="K476 SOL-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL-only, OOS Sh 16.30, $187K/yr @$10M, v6.21 candidate K449+K476 6% combined sleeve, 29th daemon)",
        scripts=["scripts/k476_sol_btc_run.py"],
        log_basename="k476_sol_btc",
        expected_html_status="SCAFFOLD-READY",  # K478: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=5.0 paper + fill_rate >=60%)
    ),
    DaemonSpec(
        label="com.cryptolab.k484-avax-btc",
        purpose="K484 AVAX-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL-only, OOS Sh 43.89 #1 family, $75.7K/yr net @$10M, G5a 0.300 PASS, v6.23 candidate K449+K476+K484 11% combined sleeve ~$276K/yr, 30th daemon)",
        scripts=["scripts/k484_avax_btc_run.py"],
        log_basename="k484_avax_btc",
        expected_html_status="SCAFFOLD-READY",  # K489: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=5.0 paper + fill_rate >=60% + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k376-regime-monitor",
        purpose="K497 K376 bull regime trigger monitor (daily BTC 20d SMA slope check, BULL_CONFIRMED alert when slope>0 for ≥7d, NO live switch — user gate, +$247K/yr unlock at $10M when triggered, 31st daemon)",
        scripts=["scripts/k376_regime_trigger_monitor.py"],
        log_basename="k376_regime_monitor",
        expected_html_status="SCAFFOLD-READY",  # K497: plist in scripts/ (gitignored); daily StartCalendarInterval 22:00 UTC (07:00 JST); activate to enable daily regime polling
    ),
    DaemonSpec(
        label="com.cryptolab.k493-atom-btc",
        purpose="K493 ATOM-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL-only, OOS Sh 50.79 #1 family, $231K/yr net @$10M, G5a 0.1763 Cosmos hypothesis CONFIRMED, v6.24 candidate K449+K476+K484+K493 14% combined sleeve ~$507K/yr, 32nd daemon)",
        scripts=["scripts/k493_atom_btc_run.py"],
        log_basename="k493_atom_btc",
        expected_html_status="SCAFFOLD-READY",  # K499: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=5.0 paper + fill_rate >=60% + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k495-dex-cex-flow",
        purpose="K495 DEX-CEX flow divergence bear-conditional (LONG BTC+ETH+SOL, 3x leverage, daily cron 86400s, HL-only, bear-regime gate 90d BTC<0, OOS Sh bear-cond 4.59, $323K/yr @$10M, corr K208=-0.017 K280=0.008 fully orthogonal to FR-carry family, v6.25 candidate 3% sleeve, 33rd daemon)",
        scripts=["scripts/k495_dex_cex_flow_run.py"],
        log_basename="k495_dex_cex_flow",
        expected_html_status="SCAFFOLD-READY",  # K502: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=3.0 + >=2 bear-regime hits + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k500-inj-btc",
        purpose="K500 INJ-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL-only, OOS Sh 11.23 #4 family, $124K/yr net @$10M, G5a 0.1409 Cosmos 2nd CONFIRMED, G5d 0.2893 PASS, v6.25 candidate K449+K476+K484+K493+K500 17% combined sleeve ~$631K/yr, 34th daemon)",
        scripts=["scripts/k500_inj_btc_run.py"],
        log_basename="k500_inj_btc",
        expected_html_status="SCAFFOLD-READY",  # K506: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=3.5 + fill_rate >=60% + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k507-sei-btc",
        purpose="K507 SEI-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL+Bybit split 1.5%+1.5%, OOS Sh 48.10 #2 family, $179K/yr net @$10M, Cosmos 3rd CONFIRMED: SEI EVM-compat + Cosmos SDK, HL 63.5% post-K507 (1.5pp headroom), v6.27 candidate K449+K476+K484+K493+K500+K507 20% combined sleeve ~$810K/yr, 35th daemon)",
        scripts=["scripts/k507_sei_btc_run.py"],
        log_basename="k507_sei_btc",
        expected_html_status="SCAFFOLD-READY",  # K514: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=5.0 + fill_rate >=60% + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k512-apt-btc",
        purpose="K512 APT-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL+Bybit split 1%+1%, OOS Sh 51.10 #1 family, $302K/yr net @$10M, Move-VM CONFIRMED: Aptos Block-STM + Move resource model creates orthogonal FR dynamics, OU half-life 0.27d, HL 64% post-K512 (1pp headroom), v6.28 candidate K449+K476+K484+K493+K500+K507+K512 combined sleeve, 36th daemon)",
        scripts=["scripts/k512_apt_btc_run.py"],
        log_basename="k512_apt_btc",
        expected_html_status="SCAFFOLD-READY",  # K520: plist in repo root (gitignored); activate after 60d paper-trade gate (OOS Sh >=5.0 + fill_rate >=60% + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k507-tia-btc",
        purpose="K507 TIA-BTC FR differential paired-trade (delta-neutral, 4x leverage, 8h cycle, HL-only 1% sleeve, OOS Sh 14.44 #6 family, $51K/yr net @$10M, Celestia modular DA CONFIRMED: rollup adoption + blob fee market creates orthogonal FR dynamics, G5d 0.05 vs ATOM=LOWEST in family, HL 65% post-K507-TIA (exactly at cap), v6.28 candidate K449+K476+K484+K493+K500+K507+K507-TIA+K512 combined sleeve ~$1.162M/yr, 37th daemon)",
        scripts=["scripts/k507_tia_btc_run.py"],
        log_basename="k507_tia_btc",
        expected_html_status="SCAFFOLD-READY",  # K524: plist in scripts/ (gitignored); activate after 60d paper-trade gate (OOS Sh >=3.5 + fill_rate >=60% + maxDD <15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k541-stablecoin-supply",
        purpose="K541 Stablecoin Supply Growth directional signal (LONG BTC+ETH+SOL, V3 z-score 2nd derivative acceleration, 2x leverage, daily cron 86400s, HL-only, OOS Sh 1.498, $294K/yr @$10M, 7-axis Sh 6.872 +0.165 lift, G5 max corr 0.074 orthogonal, 90d paper-trade gate, DefiLlama free API, v6.29 candidate 3% sleeve, 38th daemon)",
        scripts=["scripts/k541_stablecoin_supply_run.py"],
        log_basename="k541_stablecoin_supply",
        expected_html_status="SCAFFOLD-READY",  # K550: plist in scripts/ (gitignored); activate after 90d paper-trade gate (OOS Sh >=1.2 + fill_rate >=60% + maxDD <25% + >=50 trades)
    ),
    DaemonSpec(
        label="com.cryptolab.k521-options-skew",
        purpose="K521 Options 25d Skew directional signal (LONG BTC, V4 DVOL z-score + ETH-BTC 25d skew spread composite, 2x leverage, daily cron 86400s, HL-only, OOS Sh 1.019, $494K/yr @$10M, 5-axis Sh 6.386 +0.082 lift, Max corr 0.199 orthogonal, 90d paper-trade gate, Deribit free public API, v6.30 candidate 3% sleeve, 39th daemon)",
        scripts=["scripts/k521_options_skew_run.py"],
        log_basename="k521_options_skew",
        expected_html_status="SCAFFOLD-READY",  # K565: plist in scripts/ (gitignored); activate after 90d paper-trade gate (OOS Sh >=0.8 + fill_rate >=60% + maxDD <20% + >=100 trades in 90d)
    ),
    DaemonSpec(
        label="com.cryptolab.k628-jto-orthog",
        purpose="K628 JTO-BTC Orthogonalized FR Differential (Solana LST/MEV, Bybit-only JTO+BTC paired, 4x leverage, 8h cycle, OOS Sh 18.30 residual, $17.85M/yr potential @$10M @4x, β_SEI=0.164 β_DOGE=0.302 hardcoded, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.31 candidate 2-3% sleeve, 40th daemon)",
        scripts=["scripts/k628_jto_orthog_run.py"],
        log_basename="k628_jto_orthog",
        expected_html_status="SCAFFOLD-READY",  # K637: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=8 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k631-wld-orthog",
        purpose="K631 WLD-BTC Orthogonalized FR Differential (Biometric ID cluster, Bybit-only WLD+BTC paired, 4x leverage, 8h cycle, OOS Sh 18.04 residual W=72h, $2.9M/yr @$10M @4x, β_JUP=0.458795 hardcoded, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.32 candidate 2% sleeve, 41st daemon)",
        scripts=["scripts/k631_wld_orthog_run.py"],
        log_basename="k631_wld_orthog",
        expected_html_status="SCAFFOLD-READY",  # K639: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=8 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k633-op-orthog",
        purpose="K633 OP-BTC Orthogonalized FR Differential (L2 Superchain cluster unlock, Bybit-only OP+BTC paired, 4x leverage, 8h cycle, OOS Sh 12.68 residual W=72h, $2.32M/yr @$10M @4x full potential, beta_FIL=0.542224 hardcoded, IS R2=0.3283, FIL corr 0.43 to 0.07 post-orth, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.33 candidate 2% sleeve, 42nd daemon)",
        scripts=["scripts/k633_op_orthog_run.py"],
        log_basename="k633_op_orthog",
        expected_html_status="SCAFFOLD-READY",  # K640: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=5 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k635-imx-orthog",
        purpose="K635 IMX-BTC Orthogonalized FR Differential (Gaming L2 Infra cluster, Bybit-only IMX+BTC paired, 4x leverage, 8h cycle, OOS Sh 24.81 residual MF W=168h, $4.78M/yr @$10M @4x, beta_SHIB=0.254 beta_TIA=0.068 beta_SEI=0.158 hardcoded, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.34 candidate 2% sleeve, 43rd daemon)",
        scripts=["scripts/k635_imx_orthog_run.py"],
        log_basename="k635_imx_orthog",
        expected_html_status="SCAFFOLD-READY",  # K641: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=12 + fill_rate>=60% + maxDD<20%)
    ),
]


def list_launchctl() -> dict[str, dict]:
    """Map label -> {pid: int|None, exit: int|None}."""
    try:
        out = subprocess.check_output(
            ["launchctl", "list"], text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    result: dict[str, dict] = {}
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid_s, exit_s, label = parts[0], parts[1], parts[2]
        if not label.startswith("com.cryptolab."):
            continue
        result[label] = {
            "pid": int(pid_s) if pid_s.strip().lstrip("-").isdigit() and pid_s != "-" else None,
            "exit": int(exit_s) if exit_s.strip().lstrip("-").isdigit() else None,
        }
    return result


def classify(spec: DaemonSpec, launchctl_state: dict) -> dict:
    plist_path = LAUNCH_AGENTS / f"{spec.label}.plist"
    plist_exists = plist_path.is_file()
    scripts_present = [s for s in spec.scripts if (REPO_ROOT / s).is_file()]
    scripts_missing = [s for s in spec.scripts if s not in scripts_present]
    state = launchctl_state.get(spec.label)

    if state and state.get("pid"):
        status = "ACTIVE"
    elif state is not None:
        status = "LOADED"
    elif plist_exists:
        status = "PENDING ACTIVATION"
    elif scripts_present and not plist_exists:
        status = "SCAFFOLD-READY"
    elif not scripts_present and not plist_exists:
        status = "UNKNOWN"
    else:
        status = "UNKNOWN"

    log_file = (
        LOGS_DIR / f"{spec.log_basename}.log" if spec.log_basename else None
    )
    err_file = (
        LOGS_DIR / f"{spec.log_basename}.err" if spec.log_basename else None
    )

    mismatch = (
        spec.expected_html_status is not None
        and spec.expected_html_status != status
    )

    return {
        "label": spec.label,
        "purpose": spec.purpose,
        "actual_status": status,
        "expected_html_status": spec.expected_html_status,
        "mismatch_with_html": mismatch,
        "pid": state.get("pid") if state else None,
        "last_exit_code": state.get("exit") if state else None,
        "plist_exists": plist_exists,
        "plist_path": str(plist_path),
        "scripts_present": scripts_present,
        "scripts_missing": scripts_missing,
        "log_file": str(log_file) if log_file else None,
        "log_exists": bool(log_file and log_file.is_file()),
        "log_size_bytes": log_file.stat().st_size if log_file and log_file.is_file() else 0,
        "err_size_bytes": err_file.stat().st_size if err_file and err_file.is_file() else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-only", action="store_true", help="suppress stderr summary")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "deployment_status.json"),
        help="JSON output path",
    )
    args = parser.parse_args()

    launchctl_state = list_launchctl()
    daemons = [classify(spec, launchctl_state) for spec in REGISTRY]
    payload = {
        "generated_at_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "daemons": daemons,
        "summary": {
            "active": sum(1 for d in daemons if d["actual_status"] == "ACTIVE"),
            "loaded": sum(1 for d in daemons if d["actual_status"] == "LOADED"),
            "pending_activation": sum(
                1 for d in daemons if d["actual_status"] == "PENDING ACTIVATION"
            ),
            "scaffold_ready": sum(
                1 for d in daemons if d["actual_status"] == "SCAFFOLD-READY"
            ),
            "unknown": sum(1 for d in daemons if d["actual_status"] == "UNKNOWN"),
            "mismatches_with_html": sum(1 for d in daemons if d["mismatch_with_html"]),
        },
    }

    Path(args.output).write_text(json.dumps(payload, indent=2))

    if not args.json_only:
        print(f"=== Deployment status ({payload['generated_at_jst']}) ===", file=sys.stderr)
        for d in daemons:
            flag = "!!" if d["mismatch_with_html"] else "  "
            print(
                f"{flag} {d['label']:40s} {d['actual_status']:20s} "
                f"(html claims: {d['expected_html_status']}) "
                f"pid={d['pid']} plist={'Y' if d['plist_exists'] else 'N'}",
                file=sys.stderr,
            )
        print(f"--- summary: {payload['summary']} ---", file=sys.stderr)
        print(f"--- json saved: {args.output} ---", file=sys.stderr)
        return 1 if payload["summary"]["mismatches_with_html"] > 0 else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

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
    DaemonSpec(
        label="com.cryptolab.k638-stx-orthog",
        purpose="K638 STX-BTC Orthogonalized FR Differential (BTC-L2 cluster, Bybit-only STX+BTC paired, 4x leverage, 8h cycle, OOS Sh 12.38 residual MF W=504h, $65,018/yr net @$10M @4x, beta_APT=0.203339 beta_SEI=0.125164 beta_DOGE=0.306518 hardcoded, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.35 candidate 1.5% sleeve, 44th daemon)",
        scripts=["scripts/k638_stx_orthog_run.py"],
        log_basename="k638_stx_orthog",
        expected_html_status="SCAFFOLD-READY",  # K642: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=6 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k645-bnb-orthog",
        purpose="K645 BNB-BTC Orthogonalized FR Differential (Binance-ecosystem cluster, ETH-cluster unlock, Bybit-only BNB+BTC paired, 4x leverage, 8h cycle, OOS Sh 7.07 residual SF W=168h, $17,694/yr net @$10M @4x, beta_ETH=0.539 hardcoded, ETH corr 0.435->0.1757 post-orth PASS, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.36 candidate 3% sleeve, 45th daemon, K650 milestone)",
        scripts=["scripts/k645_bnb_orthog_run.py"],
        log_basename="k645_bnb_orthog",
        expected_html_status="SCAFFOLD-READY",  # K650: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=3.5 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k646-algo-orthog",
        purpose="K646 ALGO-BTC Orthogonalized FR Differential (Enterprise/Utility L1 cluster, FIL-cluster unlock, Bybit-only ALGO+BTC paired, 4x leverage, 8h cycle, OOS Sh 8.11 residual SF W=72h, ~$20,325/yr net @$10M @4x, beta_FIL=0.411 hardcoded, FIL corr 0.6052->0.2546 post-orth PASS, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.37 candidate 2% sleeve, 46th daemon, K651 scaffold)",
        scripts=["scripts/k646_algo_orthog_run.py"],
        log_basename="k646_algo_orthog",
        expected_html_status="SCAFFOLD-READY",  # K651: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=4 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k648-pol-orthog",
        purpose="K648 POL-BTC 6-Factor Orthogonalized FR Differential (Polygon L2/PoS/zkEVM cluster unlock, Bybit-only POL+BTC paired, 4x leverage, 8h cycle, OOS Sh 23.41 residual MF W=168h, $4,293,200/yr @$10M @4x, beta_OP=0.337443 beta_SEI=0.075509 beta_APT=-0.016480 beta_TIA=0.059789 beta_FIL=0.042751 beta_SAND=0.200488 hardcoded, IS R2=0.3788 OOS R2=0.0114 ADF p=0.0, post-orth all < 0.40 PASS, HL concentration UNCHANGED 65%, 60d paper-trade gate, v6.37 candidate 2% sleeve, 47th daemon, K652 scaffold)",
        scripts=["scripts/k648_pol_orthog_run.py"],
        log_basename="k648_pol_orthog",
        expected_html_status="SCAFFOLD-READY",  # K652: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=12 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k647-dot-orthog",
        purpose="K647 DOT-BTC Orthogonalized FR Differential (Governance/Staking cluster, INJ-cluster unlock, Bybit-only DOT+BTC paired, 4x leverage, 8h cycle, OOS Sh 23.25 residual SF W=168h, ~$103,586/yr net @$10M @4x, beta_INJ=0.642 hardcoded, INJ corr 0.4229->0.037 post-orth PASS, HL 65%->64% 1pp headroom, 60d paper-trade gate STRICT OOS R2=-4.11, v6.38 candidate 3% sleeve, 48th daemon, K653 scaffold)",
        scripts=["scripts/k647_dot_orthog_run.py"],
        log_basename="k647_dot_orthog",
        expected_html_status="SCAFFOLD-READY",  # K653: plist in scripts/ (gitignored); activate after 60d gate STRICT (Realized Sh>=12 + fill_rate>=60% + maxDD<15%, OOS R²=-4.11 caution)
    ),
    DaemonSpec(
        label="com.cryptolab.k629-wld-eth",
        purpose="K629 WLD-ETH FR Differential (Biometric ID / World ID Cluster 24, ETH-base mechanism fix, HL-primary WLD+ETH both legs, 4x leverage, 8h cycle, OOS Sh 19.90 W=168h direct diff 9/9 gates PASS, $94,210/yr @$10M @4x, JUP-BTC cross-base corr=0.3437 PASS (K621 WLD-BTC 0.4612 BLOCKED), ETH-BTC same-base corr=-0.2052 anti-corr K449, HL ~59.5% +2pp within 65% limit, 60d paper-trade gate, v6.39 candidate 3% sleeve, 49th daemon, K654 scaffold)",
        scripts=["scripts/k629_wld_eth_run.py"],
        log_basename="k629_wld_eth",
        expected_html_status="SCAFFOLD-READY",  # K654: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=10 + fill_rate>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k656-gala-orthog",
        purpose="K656 GALA-BTC Dual-Factor Orthogonalized FR Differential (Gaming Publisher Gala Games P2E GalaChain L1, Bybit-only GALA+BTC paired, 4x leverage, 8h cycle, OOS Sh 8.3211 residual DF W=504h, $48,143/yr net @$10M @4x, beta_JUP=0.22738 beta_FIL=0.405439 hardcoded, JUP 0.4308->0.0495 FIL 0.4114->0.0184 CLEARED, IS R2=0.4731 LARGEST in series (dual-factor first), HL concentration UNCHANGED 64.5% (Bybit-only; HL cap 66.5%>65%), 60d paper-trade gate, v6.40 candidate 2% sleeve, 50th daemon MILESTONE, K659 scaffold, gaming cluster COMPLETE: SAND+AXS+IMX+GALA)",
        scripts=["scripts/k656_gala_orthog_run.py"],
        log_basename="k656_gala_orthog",
        expected_html_status="SCAFFOLD-READY",  # K659: plist in scripts/ (gitignored); activate after 60d gate (Realized Sh>=4 + fill_rate>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k663-tia-eth",
        purpose="K663 TIA-ETH FR Differential (Modular DA Celestia, ETH-base K660 SURPRISE, HL-primary TIA+ETH both legs, 4x leverage, 8h cycle, OOS Sh 17.13 W=168h direct diff 9/9 gates PASS, $63,060/yr net @$10M @4x (1.5% sleeve), G5b TIA-BTC K507 corr=0.2309 PASS (K660 predicted BLOCKED-APT-style; TIA vol_ratio=2.12x DA spikes), HL ~61.0% +1.5pp within 65% limit, dual with K507 TIA-BTC 1.5% = $114,598/yr net, 60d paper-trade gate, v6.41 candidate, 51st daemon, K668 scaffold)",
        scripts=["scripts/k663_tia_eth_run.py"],
        log_basename="k663_tia_eth",
        expected_html_status="SCAFFOLD-READY",  # K668: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=8 + fill_rate>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k658-sol-eth",
        purpose="K658 SOL-ETH FR Differential (SOL L1 Monolithic SVM DePIN-Retail, ETH-base wins vs K476 SOL-BTC, HL-primary SOL+ETH both legs, 4x leverage, 8h cycle, OOS Sh 29.66 W=168h direct diff ETH-base +13.36 vs K476 Sh=16.30, $42,332/yr @$10M @4x @1.5% sleeve, K476 PnL corr=0.2131 PASS dual-sleeve, K449 ETH-BTC critical corr=0.0488, OU halflife=2.4h vol_ratio=1.63x, HL neutral: K476 reduced 4%->1.5% net unchanged within 65% limit, dual K476 1.5%+K658 1.5%=$85K/yr est, 60d paper-trade gate, v6.42 candidate 1.5% sleeve, 52nd daemon, K669 scaffold)",
        scripts=["scripts/k658_sol_eth_run.py"],
        log_basename="k658_sol_eth",
        expected_html_status="SCAFFOLD-READY",  # K669: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=15 + fill_rate>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k661-avax-eth",
        purpose="K661 AVAX-ETH FR Differential (AVAX Subnet/RWA Avalanche9000 cluster, ETH-base ACCEPT CONDITIONAL vs K484 AVAX-BTC, HL-primary AVAX+ETH both legs, 4x leverage, 8h cycle, OOS Sh 28.26 W=168h direct diff vs K484 Sh=43.89 BTC-base marginally better, $63,416/yr net @$10M @4x @1.5% sleeve, K484 PnL corr=0.3731 PASS dual-sleeve, G5a K449 ETH-BTC critical corr=-0.008 PASS, G5b K484 AVAX-BTC corr=0.3731 PASS, OU halflife=3.7h vol_ratio=1.38x, HL +~1.5pp ~64.0% within 65% limit, dual K484 1.5%+K661 1.5%=$139K/yr net est, 6/7 §6 gates G6 structural 18.6/yr, 60d paper-trade gate, v6.43 candidate 1.5% sleeve, 53rd daemon 6th ETH-base scaffold, K677 scaffold)",
        scripts=["scripts/k661_avax_eth_run.py"],
        log_basename="k661_avax_eth",
        expected_html_status="SCAFFOLD-READY",  # K677: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=14 + fill_rate>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k587-icp-btc",
        purpose="K587 ICP-BTC FR Differential (Compute/Cloud cluster Internet Computer Protocol Dfinity, BTC-base paired-trade, HL+Bybit split 0.5%+0.5%, 4x leverage, 8h cycle, OOS Sh 12.53 W=168h EMA ICP FR-BTC FR, $21K/yr net @$10M @4x @1% sleeve, ICP vol 8.40x highest in BTC-base family, HL maxLev=5x uses 4x margin of safety, neuron staking unlock cycles SNS DAO launches canister compute demand waves orthogonal FR dynamics, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<20%, v6.43 candidate 1% sleeve, 54th daemon, K678 scaffold)",
        scripts=["scripts/k587_icp_btc_run.py"],
        log_basename="k587_icp_btc",
        expected_html_status="SCAFFOLD-READY",  # K678: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=6 + fill>=60% + maxDD<20%)
    ),
    DaemonSpec(
        label="com.cryptolab.k679-apt-sol",
        purpose="K679 APT-SOL FR Differential (FIRST ALT-ALT pair Move-VM vs SVM DePIN-Retail, Bybit-only APT-PERP+SOL-PERP both legs, 4x leverage, 8h cycle, OOS Sh 39.29 W=168h direct alt-alt diff, $234,700/yr net @$10M @4x @3% standalone sleeve, HL 65.5% OVER cap Bybit-only mandatory, K512+K476 algebraic overlap — standalone, APT FR=Move-VM Block-STM adoption Aptos Foundation grants, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer validator economics, 60d paper-trade gate Realized Sh>=20 fill>=60% maxDD<15%, v6.44 candidate 3% sleeve, 55th daemon, K683 scaffold)",
        scripts=["scripts/k679_apt_sol_run.py"],
        log_basename="k679_apt_sol",
        expected_html_status="SCAFFOLD-READY",  # K683: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=20 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k682-atom-sol",
        purpose="K682 ATOM-SOL FR Differential (SECOND ALT-ALT pair Cosmos IBC vs SVM DePIN-Retail, Bybit-only ATOM-PERP+SOL-PERP both legs, 4x leverage, 8h cycle, OOS Sh 43.43 W=168h direct alt-alt diff, $214,638/yr net @$10M @4x @2% standalone sleeve, HL 62.5% Bybit-only preferred, K493+K476 algebraic overlap anti-corr=-0.5195 HEDGES K493 — standalone, ATOM FR=Cosmos IBC governance-driven episodics staking -3.27%/ann validator inflation, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer +7.73%/ann, 60d paper-trade gate Realized Sh>=22 fill>=60% maxDD<15%, v6.45 candidate 2% sleeve, 55th daemon 2nd alt-alt, K685 scaffold)",
        scripts=["scripts/k682_atom_sol_run.py"],
        log_basename="k682_atom_sol",
        expected_html_status="SCAFFOLD-READY",  # K685: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=22 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k684-sol-inj",
        purpose="K684 SOL-INJ FR Differential (THIRD ALT-ALT pair SVM DePIN-Retail vs Cosmos-DeFi-Perp, Bybit-only SOL-PERP+INJ-PERP both legs, 4x leverage, 8h cycle, OOS Sh 9.65 W=168h direct alt-alt diff, $114,316/yr net @$10M @4x @3% standalone sleeve, HL 62.5% Bybit-only preferred headroom preserved, K476+K500 algebraic overlap — standalone, K679+K684 SOL double-exposure monitor, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer ETF speculation +7.7%ann persistent, INJ FR=Cosmos DeFi perp DEX liquidations INJ burn IBC bridge +3.6%ann episodic mean-reverting, 60d paper-trade gate Realized Sh>=5 fill>=60% maxDD<15%, v6.46 candidate 3% sleeve, 56th daemon, K687 scaffold)",
        scripts=["scripts/k684_sol_inj_run.py"],
        log_basename="k684_sol_inj",
        expected_html_status="SCAFFOLD-READY",  # K687: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=5 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k686-avax-sol",
        purpose="K686 AVAX-SOL FR Differential (FOURTH ALT-ALT pair Avalanche Subnet institutional vs Solana SVM retail, Bybit-only AVAX-PERP+SOL-PERP both legs, 4x leverage, 8h cycle, OOS Sh 50.27 W=168h direct alt-alt diff, $102,153/yr net @$10M @4x @3% standalone sleeve, HL 62.5% Bybit-only preferred headroom preserved, K484+K476 algebraic overlap anti-corr=-0.6295 HEDGES K484 — standalone, K682/K679 SOL triple-exposure monitor, AVAX FR=Subnet launches Avalanche9000 RWA institutional HFT colocation +6.39%ann episodic, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer ETF speculation +7.73%ann persistent, same-tier L1 AVAX/SOL vol=0.85x ADF -13.99 OU 3.6h FASTEST, 60d paper-trade gate Realized Sh>=25 fill>=60% maxDD<15%, v6.47 candidate 3% sleeve, 57th daemon 4th alt-alt HIGHEST Sh in family, K689 scaffold)",
        scripts=["scripts/k686_avax_sol_run.py"],
        log_basename="k686_avax_sol",
        expected_html_status="SCAFFOLD-READY",  # K689: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=25 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k690-sei-sol",
        purpose="K690 SEI-SOL FR Differential (FIFTH ALT-ALT pair Cosmos EVM parallel vs Solana SVM retail, Bybit-only SEI-PERP+SOL-PERP both legs, 4x leverage, 8h cycle, OOS Sh 25.11 W=168h direct alt-alt diff, $104,174/yr net @$10M @4x @3% standalone sleeve, HL 62.5% Bybit-only preferred headroom preserved, K507+K476 algebraic overlap anti-corr=-0.5109 HEDGES K507 — standalone, K682/K686 SOL triple-exposure monitor, SEI FR=Cosmos EVM DeFi/CosmWasm launches NEGATIVE mean -3.65%ann short-sellers dominate, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer ETF speculation +7.70%ann persistent, mid-cap alt-alt SEI/SOL vol=1.32x ADF p=1.01e-23 OU 4.41h STRONG, carry-dominant BEAR_SEI LONG SOL/SHORT SEI carry-positive both legs, 60d paper-trade gate Realized Sh>=12 fill>=60% maxDD<15%, v6.48 candidate 3% sleeve, 58th daemon 5th alt-alt WF 12/12 UNPRECEDENTED, K693 scaffold)",
        scripts=["scripts/k690_sei_sol_run.py"],
        log_basename="k690_sei_sol",
        expected_html_status="SCAFFOLD-READY",  # K693: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=12 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k694-tia-sol",
        purpose="K694 TIA-SOL FR Differential (SIXTH ALT-ALT pair 8th-evaluated Celestia DA infra vs Solana SVM retail cross-architecture, Bybit-only TIA-PERP+SOL-PERP both legs, 4x leverage, 8h cycle, OOS Sh 19.09 W=168h direct alt-alt diff, $58,354/yr net @$10M @4x @3% standalone sleeve, HL 62.5% Bybit-only mandatory HL-only would breach 65% cap, TIA new vertex K476 signed-corr=0.2275 SOL-saturation PASS, K691 TIA-APT lesson applied APT-shared-REJECT avoided, natural SOL-short hedge to K679+K682+K686+K690, TIA FR=Celestia DA demand rollup blob-fees OP-Stack episodic +1.08%ann, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer ETF +7.70%ann persistent, cross-tier TIA~$1-3B vs SOL~$60-80B vol=1.296x ADF -9.2282 OU 3.46h FASTEST, 60d paper-trade gate Realized Sh>=9 fill>=60% maxDD<15%, v6.49 candidate 3% sleeve, 59th daemon 6th alt-alt CONDITIONAL G4 11/12, K697 scaffold)",
        scripts=["scripts/k694_tia_sol_run.py"],
        log_basename="k694_tia_sol",
        expected_html_status="SCAFFOLD-READY",  # K697: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=9 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k696-ena-sol",
        purpose="K696 ENA-SOL FR Differential (SEVENTH ALT-ALT MILESTONE FIRST CROSS-CLUSTER 9th-evaluated, Ethena synth stable infra vs Solana SVM retail, Bybit-only ENA-PERP+SOL-PERP both legs, 4x leverage, 8h cycle, OOS Sh 26.93 W=168h direct alt-alt cross-cluster diff, $93,187/yr net @$10M @4x @3% standalone sleeve, HL 62.5% Bybit-only mandatory HL-only would breach 65% cap, ENA new vertex MR8/MR9 PASS ENA-SOL=K616-K476 K616perp K476 corr=0.0094 independent, G5b K476 corr=0.1765 PASS SOL saturation CRITICAL G5c K616 corr=-0.7427 signed PASS MR6 ENA cap<6%AUM PnL-corr=0.6723 complementary, double carry ENA FR<0 37.2% time SOL_FR+|ENA_FR| both-legs-positive, ADF stat=-13.0808 p=0 strongest-stationary OU hl=3.75h STRONG, regime-dist 61.5% BEAR_ENA 38.5% BULL_ENA, 60d paper-trade gate Realized Sh>=13 fill>=60% maxDD<15%, v6.51 candidate 3% sleeve, 60th daemon MILESTONE 7th alt-alt ACCEPT 15/17 G4 11/12 G6 20.8/yr, K699 scaffold)",
        scripts=["scripts/k696_ena_sol_run.py"],
        log_basename="k696_ena_sol",
        expected_html_status="SCAFFOLD-READY",  # K699: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=13 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k698-link-eth",
        purpose="K698 LINK-ETH FR Differential (oracle middleware vs Ethereum L1, Bybit-only LINK-PERP+ETH-PERP both legs, 4x leverage, 8h cycle, OOS Sh 12.07 W=120h direct diff, $28,997/yr net @$10M @4x @2.5% sleeve, HL 64.5% UNCHANGED Bybit-only mandatory HL-only would push 67%>65% cap, G5a K557 LINK-BTC corr=0.0578 PASS CRITICAL G5b K449 ETH-BTC corr=-0.0036 PASS CRITICAL all 11/11 G5 PASS, MR9 FR identity max_err=5.42e-20 position-level corr=0.1254 de-correlated, K695 LINK-SOL REJECTED G5c=0.497 K698 avoids SOL clean oracle expansion, K557 coord LINK-BTC 1.5%+K698 LINK-ETH 2.5%=4% max combined LINK AUM, LINK FR=Chainlink oracle integrations CCIP feed-launches MM floor ~1.25e-5/hr anchor ETH FR=DeFi staking LST demand Pectra upgrades, ADF stat=-18.82 p=0.0 OU hl=1.45h ultra-fast MR LINK>ETH 74.5% time, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15%, v6.50 candidate 2.5% sleeve, 61st daemon 4th ETH-base scaffold 1st oracle-ETH pair, K701 scaffold)",
        scripts=["scripts/k698_link_eth_run.py"],
        log_basename="k698_link_eth",
        expected_html_status="SCAFFOLD-READY",  # K701: plist in scripts/ (gitignored); activate after 60d paper-trade gate (Realized Sh>=6 + fill>=60% + maxDD<15%)
    ),
    DaemonSpec(
        label="com.cryptolab.k747-tao-sol",
        purpose="K747 TAO-SOL FR Differential (FIFTEENTH ALT-ALT pair 13th-vertex TAO Bittensor AI L1 compute marketplace vs Solana SVM retail, HL-only TAO-PERP+SOL-PERP both legs maxLeverage=5 index=116, 4x leverage, 8h cycle, OOS Sh 12.233 W=168h direct alt-alt diff, central $17,210/yr net @$10M @4x @2.5% sleeve K523 3-point $12,907-$45,289/yr, HL 65.0% AT CAP paper-gate-strict HL-only mandatory Bybit-TAO 84.6% floor-capped G8-FAIL-structural, G4 WF 12/12 ALL-POSITIVE UNPRECEDENTED best-WF-in-family, G5b K476 corr=0.2229 SOL-saturation PASS G5c AVAX-BTC=0.0126 PASS G5k AVAX-SOL=0.1286 PASS AVAX-cluster-bypass confirmed, K746 ONDO-SOL BLOCKED G5c=-0.4148 G5k=-0.5842 TAO AI-compute-marketplace != AVAX-subnet-appchain DISTINCT, G8-FAIL K735-HBAR-SOL precedent-applies same-structural-pattern HL-only-viable, TAO-vertex 13th V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO} MR9-L002-all-future-TAO-X-blocked, TAO FR=GPU-scarcity-NVDA/H100 Bittensor-subnet-launches institutional-AI-adoption +16.34%/ann TAO-dominant-100%-quarters, SOL FR=DePIN/Retail meme-coin BONK/WIF Firedancer ETF +7.706%/ann persistent, ADF stat=-12.2254 p=0.0 OU hl=2.0h FAST vol-ratio=1.5734x above-1.5x-threshold, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15% + K498-OKX-activation-required, live-trigger=K498-OKX-reduces-HL%<65%+60d-gate, 69th daemon 15th alt-alt CONDITIONAL G8-FAIL, K750 scaffold)",
        scripts=["scripts/k747_tao_sol_run.py"],
        log_basename="k747_tao_sol",
        expected_html_status="SCAFFOLD-READY",  # K750: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498 OKX reduces HL% below 65%
    ),
    DaemonSpec(
        label="com.cryptolab.k545-tax-harvester",
        purpose="K545 Tax Loss Harvester (K753 full scaffold: daily 03:00 UTC, paper-mode default, scan_open_positions+identify_loss_candidates+execute_harvest+reentry_after_window, min_loss $500, max_harvest $50K/run, wash-sale 30d conservative, regime-stress cancel max_dd>15%, K523 3-point shield: conservative $74K / central $185K / optimistic $370K @$10M 37%, multi-venue reentry HL/Bybit/OKX, LIVE requires explicit --live + PAPER_TRADE=False, NOT TAX ADVICE, 70th daemon, K753 scaffold)",
        scripts=["scripts/k545_tax_harvester.py"],
        log_basename="k545_tax_harvester",
        expected_html_status="SCAFFOLD-READY",  # K753: plist in scripts/ (gitignored); 1-step activation: sed CRYPTO_LAB_PATH + cp plist + launchctl load; LIVE requires CPA review + explicit --live flag
    ),
    DaemonSpec(
        label="com.cryptolab.k754-pepe-sol",
        purpose="K754 PEPE-SOL FR Differential (SIXTEENTH ALT-ALT pair 14th-vertex PEPE Ethereum ERC-20 meme leader × Solana SVM, HL primary PEPE-PERP+SOL-PERP Bybit fallback 1000PEPE OKX confirmed, 4x leverage, 8h cycle, OOS Sh 44.43 W=84h G6-safe direct alt-alt diff, central $62,000/yr net @$10M @4x @2.5% sleeve K523 3-point $34.8K-$85.7K/yr, HL 66.8% AT CAP paper-gate-strict K751-audit K498/v6.52-activation-required, G4 WF 12/12-positive min_sh=5.56 strong-WF-validation, G5 22/22 PASS max_corr=0.247-G5l-SEI-SOL well-below-0.40, G6 64.2/yr PASS W=84h-chosen-over-168h-for-G6 168h-would-give-29.5/yr-FAIL, G8 HL+Bybit+OKX-all-venues-confirmed Bybit=1000PEPE-denomination, L003 AVAX-corr=0.4125-PASS proximity-warning-monthly-recheck, L010 HBAR-corr=0.4272-PASS proximity-warning-monthly-recheck, L004 OOS-carry=73.7%-PASS, L007 FIL-SOL-pre=0.2517-PASS, PEPE-vertex 14th V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE} MR9-L002-all-future-PEPE-X-blocked, PEPE FR=ERC-20-meme-bull-rotations social-virality CEX-listing-catalysts frog-narrative P99=1.66bps Max=6.66bps Q4-2024-peak+0.54bps, SOL FR=DePIN/Retail BONK/WIF Firedancer ETF +7.706%/ann Min=-20.51bps cascade, MaxDD-OOS=-0.107% very-contained diff-mean-reversion, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15% + K498/v6.52-OKX-activation-required, live-trigger=K498/v6.52-reduces-HL%<65%+60d-gate, 71st daemon 16th alt-alt CONDITIONAL HL-cap-66.8%, K756 scaffold)",
        scripts=["scripts/k754_pepe_sol_run.py"],
        log_basename="k754_pepe_sol",
        expected_html_status="SCAFFOLD-READY",  # K756: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%
    ),
    DaemonSpec(
        label="com.cryptolab.k759-wif-sol",
        purpose="K759 WIF-SOL FR Differential (SEVENTEENTH ALT-ALT pair 15th-vertex WIF Solana-native meme × Solana SVM, HL primary WIF-PERP+SOL-PERP Bybit fallback WIFUSDT OKX confirmed, 4x leverage, 8h cycle, OOS Sh 24.45 W=168h G6-safe direct alt-alt diff, central $54,245/yr net @$10M @4x @2.0% sleeve K523 3-point $20.7K-$76.8K/yr, HL 66.8% AT CAP paper-gate-strict K751-audit K498/v6.52-activation-required, G4 WF 12/12-positive min_sh=9.895 strong-WF-validation, G5 all-PASS max_corr=0.3819-G5w-PEPE-SOL 0.018-margin-below-0.40, G5w PEPE-SOL=0.382 proximity-0.018-margin-reduced-sleeve-2.0pct, G6 31.2/yr PASS W=168h-family-standard G6-compliant, G8 HL+Bybit+OKX-all-venues-confirmed WIF-standard-denomination, L011 raw_corr(WIF,SOL)=0.487-PASS-borderline SOL-ecosystem-threshold-0.50 OOS=0.054-near-zero monthly-recheck, L003 AVAX-corr=0.3823-PASS, L004 OOS-carry=77.5%-PASS full-87.2%-warn-meme-artifact, L007 FIL-corr=0.3318-PASS, L010 HBAR-corr=0.4011-PASS, WIF-vertex 15th V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF} MR9-L002-all-future-WIF-X-blocked, WIF FR=SOL-native-meme BONK/WIF/POPCAT-rotation CEX-listings Coinbase-Apr2024 SVM-DEX-Raydium/Jupiter vol_ratio=1.347x P99=1.416bps Max=3.164bps Q2-2024-peak+0.13bps-diff, SOL FR=DePIN/Retail Phantom Firedancer ETF +8.82%/ann Min=-20.51bps cascade, MaxDD-OOS=-0.216% very-contained diff-mean-reversion, cross-sleeve WIF-SOL+PEPE-SOL=4.0%-combined-meme-vs-SOL, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15% + K498/v6.52-OKX-activation-required, live-trigger=K498/v6.52-reduces-HL%<65%+60d-gate, 72nd daemon 17th alt-alt CONDITIONAL HL-cap-66.8%, K761 scaffold)",
        scripts=["scripts/k759_wif_sol_run.py"],
        log_basename="k759_wif_sol",
        expected_html_status="SCAFFOLD-READY",  # K761: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%
    ),
    DaemonSpec(
        label="com.cryptolab.k769-axs-sol",
        purpose="K769 AXS-SOL FR Differential (EIGHTEENTH ALT-ALT pair 16th-vertex AXS Gaming-P2E Axie-Infinity × Solana SVM, HL primary AXS-PERP+SOL-PERP Bybit fallback AXSUSDT, 4x leverage, 8h cycle, OOS Sh 16.05 W=168h G6-safe direct alt-alt diff, central $123,689/yr net @$10M @4x @1.5% sleeve K523 3-point $78.3K-$175.2K/yr, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, G4 WF 12/12-positive min_sh=5.9193 mean=16.8423 strong-WF-validation, G5 all-PASS max_corr=-0.2796-G5n-ENA-SOL all-23-gates-well-below-0.40 no-proximity-warnings, G6 31.1/yr PASS W=168h-family-standard G6-long-tail-compliant, G8 HL+Bybit-confirmed OKX-pending 2-venue-confirmed, L003 AVAX-corr=0.149-PASS, L004 AXS-carry=41pct-full-32pct-OOS-L004-PASS gaming-bear-net-negative, L007 FIL-corr=0.1711-PASS, L010 HBAR-corr=-0.0355-PASS, L011 SOL-direct=0.1916-PASS OOS=0.1182-near-zero, AXS-vertex 16th V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,AXS} MR9-L002-all-future-AXS-X-blocked, AXS FR=Gaming-P2E-Axie-Origins-seasonal SLP-burn-mint AXS-staking-APR NFT-breeding SEA-retail-speculation P2E-tournaments-Axie-World-Championship Ronin-sidechain-upgrades vol_ratio=5.24x-full-8.88x-OOS-16.23x-HL, SOL FR=DePIN/Retail Phantom Firedancer ETF +8.82%/ann Min=-20.51bps cascade, MaxDD-OOS=-0.5311%, raw_corr(AXS,SOL)=0.19-full-0.1182-OOS-orthogonal, Bybit-730d-primary-backtest HL-from-2026-01-18-3040rows-OOS, sleeve-1.5pct-long-tail-AXS-HIP3-listing max-2.0pct, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15% + K498/v6.52-OKX-activation-required, live-trigger=K498/v6.52-reduces-HL%<65%+60d-gate, 76th daemon 18th alt-alt CLEAN ACCEPT HL-cap-66.8%, K771 scaffold)",
        scripts=["scripts/k769_axs_sol_run.py"],
        log_basename="k769_axs_sol",
        expected_html_status="SCAFFOLD-READY",  # K771: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%
    ),
    DaemonSpec(
        label="com.cryptolab.k774-io-sol",
        purpose="K774 IO-SOL FR Differential (NINETEENTH ALT-ALT pair 18th-vertex IO GPU-DePIN io.net-compute-marketplace × Solana SVM, HL-only IO-PERP+SOL-PERP Bybit-N/A-HIP3-fresh, 4x leverage, 8h cycle, OOS Sh 19.884 W=168h G6-safe direct alt-alt diff, central $28,009/yr net @$10M @4x @1.5% sleeve K523 3-point $21K-$74K/yr, HIP3-HL-only-asset IO-NOT-on-Bybit G8=STRUCTURAL_NA K735/K747-precedent, G9-marginal OOS=150.2d<180d-threshold 60d-gate-compensates monitor-for-180d, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, G4 WF 12/12-positive min_sh=5.866 strong-WF-validation, G5 26/26-PASS max_corr=0.2778-G5s-HBAR-SOL all-well-below-0.40, G5v IO-SOL-vs-TAO-SOL-corr=0.047-PASS GPU-DePIN-distinct-from-AI-L1, G5s HBAR-SOL-borderline IS=0.352-full=0.278 monthly-recheck, G6 48.6/yr PASS W=168h-family-standard G6-compliant, L003 AVAX-corr=0.2402-PASS, L004 IO-carry=0.519-full-0.566-OOS-PASS, L007 FIL-signal-corr=-0.0831-PASS, L010 HBAR-corr=0.2212-PASS, L011 SOL-direct=0.1516-PASS, AI-cluster IO-SOL-vs-TAO-SOL=0.047-PASS GPU-DePIN-compute-supply-distinct-from-AI-L1-substrate, IO-vertex 18th-GPU-DePIN-cluster V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR,AXS,IO} MR9-L002-all-future-IO-X-blocked, IO FR=GPU-compute-supply/demand H100-supply-constraint AI-hyperscaler-demand io.net-network-utilization DePIN-narrative-rotation FR-structural-negative=-17.9%/yr kurtosis=493.47 vol_ratio=1.96x-full-5.83x-90d-13.11x-30d, SOL FR=DePIN/Retail Phantom Firedancer ETF +2.59%/yr Min=-20.51bps-cascade, Double-carry=BEAR_IO-structural SHORT-IO-collect-17.9%/yr+LONG-SOL-collect-2.59%/yr both-legs-favorable, MaxDD-OOS=-0.389955% very-contained, HL-only IO-PERP+SOL-PERP $1.42M/day-IO-volume, sleeve-1.5pct-HIP3-liquidity-constraint max-1.5pct-absolute, 60d gate: Realized Sh>=10 fill>=60% maxDD<15% + K498/v6.52-OKX-activation-required, live-trigger=K498/v6.52-reduces-HL%<65%+60d-gate+G9-180d-full+G5s-stable, 77th daemon 19th alt-alt ACCEPT CONDITIONAL HL-cap-66.8%, K776 scaffold)",
        scripts=["scripts/k774_io_sol_run.py"],
        log_basename="k774_io_sol",
        expected_html_status="SCAFFOLD-READY",  # K776: plist in scripts/ (gitignored); activate after 60d gate (Sh>=10 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65% AND G9 full 180d OOS
    ),
    DaemonSpec(
        label="com.cryptolab.k777-eigen-sol",
        purpose="K777 EIGEN-SOL FR Differential (TWENTIETH ALT-ALT pair 19th-vertex EIGEN ETH-restaking-AVS-economy EigenLayer × Solana SVM, HL primary EIGEN-PERP+SOL-PERP Bybit fallback EIGENUSDT-confirmed, 4x leverage, 8h cycle, OOS Sh 35.90 W=84h G6-safe direct alt-alt diff, central $84,307/yr net @$10M @4x @1.5% sleeve K523 3-point $63K-$296K/yr, G8 PASS HL+Bybit EIGENUSDT-from-2024-09-18 HL-from-2025-10-12, G9-marginal OOS=118.6d<120d-1.4d-short-operational-limit monitor-for-180d, G5z BLUR-SOL OOS=0.441-borderline W=84 window-artifact W=48=0.345-PASS monthly-recheck, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, G4 WF 4/4-positive fold-Sh=64.1/32.3/36.7/35.4-all-strong, G5 24/25-PASS G5z-borderline-only G5q-LDO-SOL=0.147-PASS restaking-distinct-from-LSD, G6 33.9/yr PASS W=84h-primary G6-compliant, L003 AVAX-corr=0.0656-PASS, L004 carry=0.514-full-0.436-OOS-PASS-bidirectional, L007 FIL-corr=0.0546-PASS, L010 HBAR-corr=0.1835-PASS, L011 SOL-direct=0.1276-PASS, EIGEN-vertex 19th-ETH-restaking-cluster V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR,AXS,IO,EIGEN} MR9-L002-all-future-EIGEN-X-blocked, EIGEN FR=AVS-launches EigenLayer-milestones restaking-yield-vs-ETH-staking operator-registration-cycles institutional-adoption slashing-risk-events FR-structural-negative=-12%/yr vol_ratio=1.868x-full-3.97x-30d, SOL FR=DePIN/Retail Phantom Firedancer ETF persistent-positive Min=-20.51bps-cascade, restaking-vs-LSD-distinction LDO=liquid-staking-stETH EIGEN=restaking-AVS-security mechanistically-distinct G5q-confirmed, MaxDD-OOS=-0.5541% W=84h very-contained, Bybit-EIGENUSDT-730d-backtest HL-from-2025-10-12, live-gate=Sh>=15+fill>=60%+maxDD<15%+K498/v6.52+G9-180d+G5z<0.40, 78th daemon 20th alt-alt ACCEPT CONDITIONAL HL-cap-66.8%, K779 scaffold)",
        scripts=["scripts/k777_eigen_sol_run.py"],
        log_basename="k777_eigen_sol",
        expected_html_status="SCAFFOLD-READY",  # K779: plist in scripts/ (gitignored); activate after live gate (Sh>=15 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65% AND G9 full 180d OOS AND G5z BLUR-SOL W=84 OOS < 0.40
    ),
    DaemonSpec(
        label="com.cryptolab.k778-comp-sol",
        purpose="K778 COMP-SOL FR Differential (TWENTY-SECOND ALT-ALT scaffold 20th-vertex COMP DeFi-governance-token Compound-Finance × Solana SVM, HL primary COMP-PERP+SOL-PERP Bybit fallback COMPUSDT OKX secondary COMP-confirmed, 4x leverage, 8h cycle, OOS Sh 25.05 IS Sh 14.91 OOS>IS CLEAN-ACCEPT W=48h G6-87.5/yr-OOS, central $207,345/yr net @$10M @4x @2.5% sleeve K523 3-point $79K-$276K/yr, CLEAN ACCEPT 30/30 no-conditional-caveats, G4 WF 12/12-ALL-POSITIVE min_fold_sh=14.79-perfect-WF-validation, G5 22/22-ALL-PASS max_corr=0.3906-G5j-SOL-INJ-negative all-below-0.40, G5q LDO-SOL=0.2926-PASS DeFi-protocol-overlap-clear, G5v AAVE-SOL=0.2359-PASS DeFi-lending-cluster-clear, G6 87.5/yr PASS W=48h-highest-frequency-alt-alt-family, G7 OOS-ann-ret-4x=130.1%-PASS, G8 OKX-COMP-FR-vs-HL-COMP-FR-corr=0.8548-PASS-proxy-n=284, G9 OOS-216d-PASS>=180d-NO-marginal-caveat, L004 PASS COMP-bidirectional-pos_frac_full=68.1%-pos_frac_oos=50.1%-both-below-80% unlike-AAVE-K748-BLOCKED-86%-or-PENDLE-K758-BLOCKED-90%, L004-surprise COMP-is-governance-not-lending-bidirectional-FR-reward-cycle-speculation, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, vol_ratio=3.62x-full-6.0x-30d raw_corr=0.0765 OU-half-life=1.94h cycle_independence=0.9235, COMP-vertex 20th-DeFi-governance-cluster V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR,AXS,IO,EIGEN,COMP} MR9-L002-all-future-COMP-X-blocked, COMP FR=governance-reward-distribution emissions-schedule protocol-competition-Aave-vs-Compound governance-votes-rate-models COMP-liquidation-cascades fee-switch-treasury TVL-migration, MaxDD-OOS=-0.0834%-W=48h-extremely-contained, 60d-gate=Sh>=12+fill>=60%+maxDD<15%+K498/v6.52, live-trigger=K498/v6.52-reduces-HL%<65%+60d-gate, 79th daemon 22nd alt-alt scaffold CLEAN ACCEPT 30/30 HL-cap-66.8%, K780 scaffold)",
        scripts=["scripts/k778_comp_sol_run.py"],
        log_basename="k778_comp_sol",
        expected_html_status="SCAFFOLD-READY",  # K780: plist in scripts/ (gitignored); activate after 60d gate (Sh>=12 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%
    ),
    DaemonSpec(
        label="com.cryptolab.k786-bio-sol",
        purpose="K786 BIO-SOL FR Differential (TWENTY-THIRD ALT-ALT scaffold 21st-vertex BIO DeSci-Biotech-DAO-coordination Bio-Protocol × Solana SVM, HL ONLY BIO-PERP+SOL-PERP G8-FAIL-HL-only-HIP-3-no-Bybit-no-OKX, 4x leverage 0.4%-sleeve-liquidity-limited, 8h cycle, OOS Sh 23.10 IS Sh 23.24 IS~OOS-consistent-no-directional-overfit W=84h G6-7479/yr-OOS, central $63,652/yr net @$10M @4x @0.4% sleeve K523 3-point $54K-$168K/yr, ACCEPT 8/9 G8-FAIL-cross-venue-unconfirmed, G4 WF 5/5-ALL-POSITIVE min_fold_sh=20.95-all-folds-strong, G5 24/24-ALL-PASS max_corr=0.3308-G5u-FIL-SOL all-below-0.40, G6 7479/yr PASS W=84h-ultra-high-frequency, G7 OOS-ann-ret-4x=558.4%-PASS, G8 FAIL BIO-HL-only-HIP-3-no-cross-venue-perp-confirmed, G9 OOS-204.8d-PASS>=180d, L004 PASS BIO-bidirectional-pos_frac_full=0.5590-pos_frac_oos=0.5983-both-below-80%, L004_DIFF BORDERLINE full=0.303-0.003-above-floor OOS=0.461-PASS monthly-recheck-required, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, vol_ratio=9.833x-full raw_corr=0.0028 OU-half-life=7.16h cycle_independence=0.9972, BIO-vertex 21st-DeSci-cluster-1st V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR,AXS,IO,EIGEN,COMP,BIO} MR9-L002-all-future-BIO-X-blocked, BIO FR=DeSci-narrative-cycles BioDAO-deal-flow IP-NFT-acquisitions VitaDAO-longevity-milestones AthenaDAO-HairDAO-GenomesDAO biotech-bull-bear regulatory-DeSci-news decentralized-patient-capital, SOL FR=DePIN/Retail Phantom Firedancer ETF persistent-positive Min=-20.51bps-cascade, live-gate=Sh>=15+fill>=60%+maxDD<15%+K498/v6.52+cross-venue-Bybit-BIO-verify, 80th daemon 23rd alt-alt scaffold ACCEPT 8/9 HL-cap-66.8%, K787 scaffold)",
        scripts=["scripts/k786_bio_sol_run.py"],
        log_basename="k786_bio_sol",
        expected_html_status="SCAFFOLD-READY",  # K787: plist in scripts/ (gitignored); activate after 60d gate (Sh>=15 + fill>=60% + maxDD<15%) AND K498/v6.52 AND cross-venue Bybit BIO verified (G8 resolution)
    ),
    DaemonSpec(
        label="com.cryptolab.k789-resolv-sol",
        purpose="K789 RESOLV-SOL FR Differential (TWENTY-FOURTH ALT-ALT scaffold 22nd-vertex-candidate RESOLV RWA-Synthetic-Dollar-yield-bearing-stablecoin Resolv-Protocol × Solana SVM, HL ONLY RESOLV-PERP+SOL-PERP G8-FAIL-HL-only-HIP-3-no-Bybit-no-OKX G9-FAIL-OOS=141d-re-gate-Aug-2026, 4x leverage 0.4%-sleeve-liquidity-limited, 8h cycle, OOS Sh 23.91 IS Sh 26.05 IS>OOS-typical W=84h G6-1228/yr-OOS, central $41,539/yr net @$10M @4x @0.4% sleeve K523 3-point $26K-$109K/yr, CONDITIONAL ACCEPT 7/9 G8-G9-FAIL, G4 WF 8/8-ALL-POSITIVE min_fold_sh=27.72-all-folds-strong, G5 25/25-ALL-PASS max_corr=0.1269-G5k-AVAX-SOL all-below-0.40, G5n ENA-SOL=0.0497-PASS-2nd-synth-dollar-distinct G5y BIO-SOL=-0.0119-PASS, G6 1228/yr PASS W=84h, G7 OOS-ann-ret-4x=273.3%-PASS, G8 FAIL RESOLV-HL-only-HIP-3-no-cross-venue-perp-confirmed-precedent-K786-BIO-SOL-same-pattern, G9 FAIL OOS=141d<180d-re-gate-Aug-18-2026-39-more-days, L004 PASS RESOLV-bidirectional-carry_full=0.5867-carry_oos=0.6955-both-below-80%, L004_DIFF BORDERLINE-PASS full=0.3159-0.016-above-floor IS=0.1597-WARN-not-gated OOS=0.5502-governs IS-failure-structural-RESOLV-FR-negative-2025Q3Q4-delta-hedge-bear-regime-recovered-2026Q1+, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, vol_ratio=13.9458x-full raw_corr=0.0461 OU-half-life=6.68h cycle_independence=0.9539, RESOLV-vertex 22nd-candidate-2nd-RWA-synth-dollar-cluster-after-ENA V-candidate={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR,AXS,IO,EIGEN,COMP,BIO,RESOLV} MR9-L002-all-future-RESOLV-X-blocked-if-confirmed, RESOLV FR=delta-hedge-rebalancing-cycles ETH-BTC-perp-funding-regime stablecoin-adoption-flow RWA-yield-competition-vs-sUSDe-USDS-USDC DAO-governance-events stablecoin-regulatory-news-SEC-MiCA, SOL FR=DePIN/Retail Phantom Firedancer ETF persistent-positive Min=-20.51bps-cascade, live-gate=Sh>=15+fill>=60%+maxDD<15%+K498/v6.52+G9-re-gate-Aug-2026+cross-venue-RESOLV-verify, 81st daemon 24th alt-alt scaffold CONDITIONAL ACCEPT 7/9 HL-cap-66.8%, K790 scaffold)",
        scripts=["scripts/k789_resolv_sol_run.py"],
        log_basename="k789_resolv_sol",
        expected_html_status="SCAFFOLD-READY",  # K790: plist in scripts/ (gitignored); activate after 60d gate (Sh>=15 + fill>=60% + maxDD<15%) AND K498/v6.52 AND G9 re-gate Aug 2026 AND cross-venue RESOLV perp verify (G8 resolution)
    ),
    DaemonSpec(
        label="com.cryptolab.k788-meme-sol",
        purpose="K788 MEME-SOL FR Differential (TWENTY-FIFTH ALT-ALT scaffold 22nd-vertex MEME ERC-20-meme-index memecoin.org-basket-weighted-cross-chain-ETH × Solana SVM, HL primary MEME-PERP+SOL-PERP G8-PASS-HL+OKX+Bybit-confirmed, 3x leverage 0.4%-sleeve-liquidity-limited-MEME-OI=480K-daily-vol=447K, 8h cycle, OOS Sh 15.97 IS Sh 13.12 OOS>IS-no-directional-overfit W=84h G6-84.3/yr-OOS, central $14,518/yr net @$10M @3x @0.4% sleeve K523 3-point $9.2K-$20.6K/yr, CONDITIONAL_ACCEPT 9/9 G8-PASS-cross-venue-verified, G4 WF 12/12-ALL-POSITIVE min_fold_sh=4.3534-all-folds-positive, G5 27/27-ALL-PASS max_corr=0.1973-G5b-SOL-BTC all-below-0.40, G5w PEPE-SOL=0.1339-PASS-meme-cluster-orthogonal G5y WIF-SOL=0.0825-PASS-cross-chain-meme-distinct, G6 84.3/yr PASS W=84h, G7 OOS-ann-ret-3x=60.5%-PASS, G8 PASS MEME-HL+OKX+Bybit-confirmed Bybit=MEMEUSDT-Nov2023-50x OKX=corr0.843, G9 OOS-212d-PASS>=180d, L004 PASS MEME-bidirectional-pos_frac_full=0.7940-pos_frac_oos=0.5743-both-below-80%, L004_DIFF BORDERLINE full=0.289-0.011-BELOW-floor OOS=0.440-PASS G2-p=0.000-timing-alpha-5.13Sh-vs-pure-carry IS-Sh=7.99 monthly-recheck-required reduce-sleeve-if-OOS<0.28-2mo, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, vol_ratio=3.34x-full raw_corr=0.1177 MEME-vertex 22nd-ERC-20-meme-index-cluster-1st V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR,AXS,IO,EIGEN,COMP,BIO,MEME} MR9-L002-all-future-MEME-X-blocked, MEME FR=ERC-20-meme-market-sentiment ETH-meme-bull/bear-cycles ETH-ecosystem-meme-rotation HL-HIP-3-speculative-demand meme-crash-kurtosis-Max=-48.37bps memecoin.org-basket, SOL FR=DePIN/Retail Phantom Firedancer ETF persistent-positive Min=-20.51bps-cascade, live-gate=Sh>=10+fill>=60%+maxDD<15%+K498/v6.52+L004_DIFF-stable-OOS>=0.30, 82nd daemon 25th alt-alt scaffold CONDITIONAL_ACCEPT 9/9 HL-cap-66.8%, K791 scaffold)",
        scripts=["scripts/k788_meme_sol_run.py"],
        log_basename="k788_meme_sol",
        expected_html_status="SCAFFOLD-READY",  # K791: plist in scripts/ (gitignored); activate after 60d gate (Sh>=10 + fill>=60% + maxDD<15%) AND K498/v6.52 AND L004_DIFF stable (OOS diff_pos >= 0.30 for 2+ months)
    ),
    DaemonSpec(
        label="com.cryptolab.k763-compound-scheduler",
        purpose="K763 Compounding Schedule Optimizer (profit-max axis #3 compounding, daily 03:00 UTC Kelly-optimal rebalance recommendation, PAPER_TRADE=True default LIVE 自動変更禁止, half-Kelly 0.5x cash-buffer 8%, COMPOUND_FREQUENCY=daily|weekly|monthly env-configurable, K523 3-point uplift: conservative $3.5K/weekly-vs-monthly @r=10% | central $3.28M/daily-vs-weekly @r=218% v6.52-mid | optimistic $13.6M/Kelly+continuous @r=273%, K518 38% haircut applied realized: $1.3K/$1.25M/$5.2M, net-benefit daily $13.68M vs monthly baseline (cost $118K/yr), Kelly f*=10.77x full / 5.39x half / 0.92 capped, v6.52 K724 $21.81M mid confirmed, reversibility=COMPOUND_FREQUENCY=monthly, 73rd daemon K763 scaffold)",
        scripts=["scripts/k763_compound_scheduler.py"],
        log_basename="k763_compound_scheduler",
        expected_html_status="SCAFFOLD-READY",  # K763: plist in scripts/ (gitignored); activate: sed REPO_ROOT_PLACEHOLDER + cp + launchctl load; COMPOUND_FREQUENCY=monthly to revert
    ),
    DaemonSpec(
        label="com.cryptolab.k768-blur-sol",
        purpose="K768 BLUR-SOL FR Differential (EIGHTEENTH ALT-ALT pair 16th-vertex BLUR Ethereum-L1-NFT-marketplace × Solana SVM, HL primary BLUR-PERP+SOL-PERP Bybit fallback BLURUSDT, 4x leverage, 8h cycle, OOS Sh 14.98 W=168h G6-safe direct alt-alt diff, central $61,000/yr net @$10M @4x @0.6% sleeve K523 3-point $37K-$153K/yr, liquidity-limited HL BLUR $0.6M/day 10%-daily-vol-rule $60K-pos-max 0.6%-sleeve-cap, HL 66.8% AT CAP paper-gate-strict K751-audit, G4 WF 20/21-positive positive_frac=0.952 strong-WF-validation, G5 FIL-SOL-full=0.4398-FAIL OOS=0.2805-PASS SOL-anchor-contamination-exception documented, G6 38.2/yr PASS W=168h-family-standard G6-compliant, G8 HL+Bybit-confirmed BLUR-HL-2024-05 BLURUSDT-4594rows-2023-02, L003 AVAX-corr=0.0445-PASS, L004 IS=0.836-OOS=0.482-PASS, L007 FIL-corr=0.0478-PASS raw-FR-independence-confirmed, L010 HBAR-corr=0.0784-PASS, L011 SOL-corr=0.0603-PASS, BLUR-vertex 16th V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,BLUR} MR9-L002-all-future-BLUR-X-blocked, BLUR FR=NFT-marketplace Blur.io Eth-L1 NFT-bull-cycles BAYC/Pudgy royalty-battles Blur-Blend-lending airdrop-seasons kurtosis=575.70 Max-spike=0.008065 64-events>0.0001 vol_ratio=6.77x-full, SOL FR=DePIN/Retail Firedancer ETF +8.79%/ann Min=-20.51bps-cascade, MaxDD-OOS=-0.68% very-contained, 4-live-conditions: G5-FIL-SOL-90d-OOS<0.40 + HL-BLUR-vol>$1M/day + HL%<65% + NFT-governance-review, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15% + 4-conditions, live-trigger=all-4-conditions+60d-gate, 75th daemon 18th alt-alt CONDITIONAL HL-cap-66.8%, K770 scaffold)",
        scripts=["scripts/k768_blur_sol_run.py"],
        log_basename="k768_blur_sol",
        expected_html_status="SCAFFOLD-READY",  # K770: plist in scripts/ (gitignored); activate after 60d gate + all 4 live-elevation conditions (K770 governance)
    ),
    DaemonSpec(
        label="com.cryptolab.k767-rwa-diversified",
        purpose="K767 K297' RWA 4-Provider Diversified Yield Sleeve (sUSDe 35%+Spark sUSDS 25%+USDY 25%+Mountain USDM 15%, weekly rebalance Sunday 03:00 JST, 20% of AUM=$2M sleeve, blended APY ~4.0%, K523 3-point: conservative $56K/$21K | central $79K/$30K | optimistic $103K/$39K gross/realized @$10M K518 38%, +$69K/yr central uplift vs sUSDe-only baseline, HHI 1.0→0.26 diversification, DeFiLlama free API all providers, BEAR_1 sUSDe-50%, geo-strategy US/non-US USDY gating, PAPER_TRADE=True default LIVE 自動変更禁止, data/rwa_allocation.json allocation source-of-truth, 74th daemon K767 scaffold)",
        scripts=["scripts/k767_rwa_diversified.py"],
        log_basename="k767_rwa_diversified",
        expected_html_status="SCAFFOLD-READY",  # K767: plist in scripts/ (gitignored); activate: cp plist to LaunchAgents + launchctl load; fund providers first; USDY non-US only
    ),
    DaemonSpec(
        label="com.cryptolab.k795-basket-rotation",
        purpose="K795 Multi-Asset Basket Rotation Strategy (83rd daemon, regime-aware rotation across 36 accepted alt-alt+base strategies, daily 09:00 JST rotation check, Variant B regime-conditional BTC+SOL 30d trend filter PASS, Variant A top-5 rolling Sh PASS_WITH_OVERFIT_CAVEAT, PAPER_TRADE=True default LIVE 自動変更禁止, K523 3-point: conservative $21K | mid $112K | optimistic $285K @$10M, data/k795_rotation_dashboard.json allocation source-of-truth, regime: BULL_ALT alt-alt-cross 1.8x / BEAR_ALT BTC-base 1.5x / MIXED equal-weight, 36-strategy universe total static central $3.93M/yr, turnover cost 5bps pessimistic $46K/yr, net uplift Variant B $112K/yr central, 83rd daemon K795 scaffold)",
        scripts=["scripts/k795_basket_rotation.py"],
        log_basename="k795_basket_rotation",
        expected_html_status="SCAFFOLD-READY",  # K795: plist in scripts/ (gitignored); activate after 60d paper observation + regime accuracy >= 70% + K498/v6.52 OKX activation
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

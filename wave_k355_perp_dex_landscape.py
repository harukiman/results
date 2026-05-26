"""
wave_k355_perp_dex_landscape.py
K355 — Perp DEX Competitive Landscape + v6.13d Concentration Risk Assessment
Synthesizes R12-11 (Paradex $8T endgame), R12-15 (Variational $50M), R12-16 (CME/ICE CFTC).

REPO_ROOT pattern (K339 security rule):
  REPO_ROOT = Path(__file__).resolve().parent   (this script lives at repo root)

NO new packages — stdlib + json + datetime only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent
OUTPUT_JSON = REPO_ROOT / "wave_k355_perp_dex_landscape.json"
OUTPUT_MD   = REPO_ROOT / "wave_k355_perp_dex_landscape.md"

# ── Phase 1: Venue Catalog (data from WebFetch, R12-11, R12-15 synthesis) ──
VENUE_CATALOG = [
    {
        "venue": "Hyperliquid",
        "chain": "HL L1 (custom)",
        "tvl_usd_m": 845,          # HLP cumulative P&L proxy; HLP TVL ~$845M cumulative (R12-19)
        "vol_30d_usd_b": 248.0,    # R12-11 Paradex report 30d vol
        "vol_24h_usd_b": None,     # not directly available from fetch
        "oi_usd_b": 5.63,          # R12-11
        "oi_vol_ratio": 0.021,     # R12-11 (highest in cohort)
        "market_share_pct": 31.7,  # R12-11 (was 80% peak mid-2025, compressed to 31%)
        "listed_assets_count": 230, # K297 discovery: 230 HL perp markets
        "rwa_markets": ["PAXG", "SPX"],  # HIP-3 confirmed (K297)
        "rwa_volume_flag": True,
        "funding_mechanism": "Hourly discrete (8h computed, 1h intervals, 4% cap)",
        "regulatory_status": "Permissionless / no formal license; CME/ICE CFTC pressure (R12-16)",
        "risk_level": "HIGH",
        "notes": "Builder ecosystem 40% DAU via 3rd-party; HIP-4 pipeline; CFTC scrutiny active",
        "source": "R12-11 Paradex report + R12-16 CoinDesk + R12-19 kkdemian"
    },
    {
        "venue": "Variational",
        "chain": "Arbitrum (L2)",
        "tvl_usd_m": None,
        "vol_30d_usd_b": 71.8,
        "vol_24h_usd_b": None,
        "oi_usd_b": 0.932,
        "oi_vol_ratio": 0.014,
        "market_share_pct": 9.2,
        "listed_assets_count": 500,   # R12-11: "500+ markets"; RFQ model
        "rwa_markets": ["Gold", "Silver", "Copper", "WTI", "100+ planned"],
        "rwa_volume_flag": True,
        "funding_mechanism": "OLP-embedded cost of carry (no separate FR accrual)",
        "regulatory_status": "Cayman Islands incorporated; permissionless; $50M Dragonfly-led Series A (May 2026)",
        "risk_level": "MEDIUM",
        "notes": "RFQ aggregates CEX+DEX liquidity; $200B cumulative since 2025; primary HL HIP-3 competitor",
        "source": "R12-15 CoinDesk + R12-11 Paradex report"
    },
    {
        "venue": "Paradex",
        "chain": "Starknet appchain",
        "tvl_usd_m": None,
        "vol_30d_usd_b": 43.52,
        "vol_24h_usd_b": None,
        "oi_usd_b": 0.608,
        "oi_vol_ratio": 0.014,
        "market_share_pct": 0.99,
        "listed_assets_count": 250,
        "rwa_markets": [],
        "rwa_volume_flag": False,
        "funding_mechanism": "Continuous accrual as unrealized PnL",
        "regulatory_status": "Permissionless; FATF/MiCA exposure; position confidentiality unique feature",
        "risk_level": "LOW-MEDIUM",
        "notes": "Only venue with full position confidentiality (dark pool analogue); institutional focus; -78% 7d vol during incentive transition",
        "source": "R12-11 Paradex report (self-published; flag potential bias)"
    },
    {
        "venue": "Lighter",
        "chain": "Ethereum ZK-Rollup",
        "tvl_usd_m": None,
        "vol_30d_usd_b": 145.9,
        "vol_24h_usd_b": None,
        "oi_usd_b": 1.02,
        "oi_vol_ratio": 0.007,
        "market_share_pct": 18.6,
        "listed_assets_count": 500,
        "rwa_markets": ["US Equities (Chainlink 24/5)", "Forex", "Commodities"],
        "rwa_volume_flag": True,
        "funding_mechanism": "8-hour standard formula",
        "regulatory_status": "Permissionless; Founders Fund + Ribbit + Haun + Robinhood Ventures backed; launched Jan 2026",
        "risk_level": "MEDIUM",
        "notes": "Chainlink real data feeds for equities/forex; zero retail fees; ZK proof of all matching; 4.5h outage Oct 2025 stress test",
        "source": "R12-11 Paradex report + Lighter.xyz WebFetch"
    },
    {
        "venue": "dYdX v4",
        "chain": "dYdX chain (Cosmos)",
        "tvl_usd_m": 12,           # MegaVault TVL from dydx.xyz fetch
        "vol_30d_usd_b": None,
        "vol_24h_usd_b": None,
        "oi_usd_b": 0.200,         # dydx.xyz: $200M OI
        "oi_vol_ratio": None,
        "market_share_pct": None,
        "listed_assets_count": 220,  # dydx.xyz: "220+ markets"
        "rwa_markets": [],
        "rwa_volume_flag": False,
        "funding_mechanism": "8-hour standard",
        "regulatory_status": "Explicitly excludes US persons; dYdX International Ltd; lifetime vol $1.5T",
        "risk_level": "LOW",
        "notes": "US-excluded; lifetime vol $1.5T; Solana spot trading added; zero-fee promotions active; declining relative share",
        "source": "dydx.xyz WebFetch"
    },
    {
        "venue": "Aevo",
        "chain": "Ethereum L2 (OP Stack)",
        "tvl_usd_m": 350,           # ATH TVL from aevo.xyz fetch
        "vol_30d_usd_b": None,
        "vol_24h_usd_b": None,
        "oi_usd_b": None,
        "oi_vol_ratio": None,
        "market_share_pct": None,
        "listed_assets_count": None,
        "rwa_markets": [],
        "rwa_volume_flag": False,
        "funding_mechanism": "Hybrid off-chain matching + on-chain settlement",
        "regulatory_status": "Paradigm/Coinbase Ventures/Dragonfly backed; AEVO token governance",
        "risk_level": "LOW-MEDIUM",
        "notes": "Focus: options + perps; $10B+ options vol lifetime; >$50M premiums; <10ms latency; declining from ATH",
        "source": "aevo.xyz WebFetch"
    },
    {
        "venue": "Drift (Solana)",
        "chain": "Solana",
        "tvl_usd_m": 826,           # drift.trade: $826B total deposits (LIKELY $826M — unit confusion)
        "vol_30d_usd_b": None,
        "vol_24h_usd_b": None,
        "oi_usd_b": None,
        "oi_vol_ratio": None,
        "market_share_pct": None,
        "listed_assets_count": 100,  # "100+" tradeable markets
        "rwa_markets": [],
        "rwa_volume_flag": False,
        "funding_mechanism": "Solana-native; 8h standard",
        "regulatory_status": "Trail of Bits + OtterSec audited; 50B+ cumulative vol; 19.2M trades",
        "risk_level": "LOW-MEDIUM",
        "notes": "Up to 101x leverage on SOL/BTC/ETH; use any token as collateral; $50B cumulative vol",
        "source": "drift.trade WebFetch"
    },
    {
        "venue": "GMX v2",
        "chain": "Arbitrum + Avalanche",
        "tvl_usd_m": None,
        "vol_30d_usd_b": None,
        "vol_24h_usd_b": None,
        "oi_usd_b": None,
        "oi_vol_ratio": None,
        "market_share_pct": None,
        "listed_assets_count": None,
        "rwa_markets": [],
        "rwa_volume_flag": False,
        "funding_mechanism": "Borrowing rate model (not traditional FR)",
        "regulatory_status": "Permissionless; GLP/GM pool model",
        "risk_level": "LOW",
        "notes": "Site blocked WebFetch; pool-based model distinct from CLOB; declining relative share",
        "source": "Known prior data (WebFetch blocked)"
    },
    {
        "venue": "Vertex",
        "chain": "Arbitrum",
        "tvl_usd_m": None,
        "vol_30d_usd_b": None,
        "vol_24h_usd_b": None,
        "oi_usd_b": None,
        "oi_vol_ratio": None,
        "market_share_pct": None,
        "listed_assets_count": None,
        "rwa_markets": [],
        "rwa_volume_flag": False,
        "funding_mechanism": "Hybrid off-chain sequencer + on-chain clearing",
        "regulatory_status": "Permissionless; Arbitrum-native",
        "risk_level": "LOW",
        "notes": "Sequencer-based CLOB; known for tight spreads on majors; data not fetched this wave",
        "source": "Prior knowledge (no WebFetch this wave)"
    },
]

# ── Phase 2: HL Competitive Position ──────────────────────────────────────

HL_POSITION = {
    "hip3_rwa_markets": {
        "SPX": {
            "asset_class": "S&P 500 Equity Index",
            "data_start": "2025-01-07",
            "max_leverage": 5,
            "always_on_carry_sharpe": 5.87,
            "always_on_carry_ann_return_pct": 6.80,
            "max_dd_pct": -1.74,
        },
        "PAXG": {
            "asset_class": "Gold-backed token",
            "data_start": "2025-04-06",
            "max_leverage": 10,
            "always_on_carry_sharpe": 16.91,
            "always_on_carry_ann_return_pct": 8.03,
            "max_dd_pct": -0.36,
        },
        "portfolio_sharpe": 10.17,
        "portfolio_ann_return_pct": 7.3,
        "correlation_SPX_PAXG": 0.18,
    },
    "market_share_trend": {
        "peak_mid_2025_pct": 80,
        "feb_2026_pct": 31.7,
        "interpretation": "Compressed from 80% peak to 31.7% — healthy fragmentation, not decline. Absolute volume still growing.",
    },
    "dominance_window_assessment": {
        "months_remaining_estimate": 12,
        "rationale": [
            "Variational: $50M raise, 500+ markets, $200B cumulative vol ALREADY LIVE since 2025",
            "Lighter: ZK rollup with Chainlink 24/5 equities/forex feed (launched Jan 2026)",
            "HL HIP-3 advantage: permissionless listing speed (24-48h vs Variational RFQ onboarding)",
            "HL HIP-3 disadvantage: FR carry visible on-chain = arbitrageable; Variational OLP embeds carry (no extractable FR signal)",
            "Variational RFQ model = DIRECT SUBSTITUTE for HL HIP-3 gold/silver/commodities",
            "Lighter Chainlink equities feed = DIRECT SUBSTITUTE for HL SPX",
            "HL moat: existing user base, builder ecosystem, HLP liquidity depth",
            "Fragmentation already underway (31.7% share vs 80% peak)",
        ],
        "confidence": "MEDIUM — window 6-18 months before meaningful RWA carry fragmentation",
    },
    "variational_threat_timeline": {
        "current_status": "LIVE since 2025, $200B cumulative vol, $50M Series A May 2026",
        "rwa_assets_live": ["Gold", "Silver", "Copper", "WTI"],
        "equity_index_status": "Not confirmed yet (SPX/equity indices unclear)",
        "key_differentiator": "RFQ aggregates CEX+DEX liquidity → tighter spreads on RWA than HL HIP-3 CLOB",
        "carry_fragmentation_impact": "If Variational offers PAXG/Gold RFQ with tighter spread → HL HIP-3 FR premium will compress as arbitrageurs route via Variational",
        "estimated_impact_on_k297_carry": "10-25% carry compression over 12 months if Variational scales gold volume",
    },
}

# ── Phase 3: Cross-Venue Arb Opportunities ────────────────────────────────

CROSS_VENUE_ARB = {
    "same_asset_multi_venue": [
        {
            "asset": "BTC-PERP",
            "venues": ["Hyperliquid", "dYdX v4", "Drift", "Aevo", "Lighter"],
            "api_access": ["HL: public", "dYdX: public", "Drift: public", "Aevo: public", "Lighter: public"],
            "fr_spread_opportunity": "Moderate — BTC FR typically tight across venues; spread ~0.5-2 bps",
            "arb_feasibility": "MODERATE — requires low-latency execution; K208 bilateral HL-Bybit already captures some",
        },
        {
            "asset": "ETH-PERP",
            "venues": ["Hyperliquid", "dYdX v4", "Drift", "Aevo", "Lighter"],
            "api_access": ["HL: public", "dYdX: public", "Drift: public"],
            "fr_spread_opportunity": "Moderate — typically 1-3 bps spread",
            "arb_feasibility": "MODERATE — same as BTC",
        },
        {
            "asset": "SOL-PERP",
            "venues": ["Hyperliquid", "Drift", "dYdX v4"],
            "api_access": ["HL: public", "Drift: public", "dYdX: public"],
            "fr_spread_opportunity": "Higher — SOL FR more volatile; 2-8 bps spread common",
            "arb_feasibility": "HIGH — Drift (Solana native) vs HL historically shows larger FR spreads",
        },
        {
            "asset": "PAXG-PERP",
            "venues": ["Hyperliquid HIP-3"],
            "api_access": ["HL: public"],
            "fr_spread_opportunity": "N/A — no comparable venue yet for PAXG perp",
            "arb_feasibility": "NOT YET FEASIBLE — HL monopoly on PAXG perp",
        },
        {
            "asset": "Gold-PERP",
            "venues": ["Hyperliquid HIP-3 (PAXG proxy)", "Variational (Gold RFQ)", "Lighter (Chainlink 24/5)"],
            "api_access": ["HL: public", "Variational: API available", "Lighter: public"],
            "fr_spread_opportunity": "HIGH POTENTIAL — different mechanisms (FR vs OLP carry vs ZK) create pricing gaps",
            "arb_feasibility": "MEDIUM-HIGH — Variational OLP model vs HL HIP-3 FR: if Variational Gold spot+perp pricing diverges from HL PAXG, arb opportunity emerges",
        },
    ],
    "recommended_next_pairs": [
        {
            "priority": 1,
            "pair": "HL SOL-PERP vs Drift SOL-PERP",
            "rationale": "Both have public APIs, same asset, documented FR spread. K208 pattern directly extensible.",
            "api_urls": {
                "HL": "https://api.hyperliquid.xyz/info",
                "Drift": "https://mainnet-beta.drift.trade/",
            },
            "estimated_edge": "1-5 bps FR spread captured with 8h execution cycle",
        },
        {
            "priority": 2,
            "pair": "HL PAXG-PERP vs Variational Gold-RFQ",
            "rationale": "Direct RWA substitute; different carry mechanisms may create persistent pricing gap",
            "api_urls": {
                "HL": "https://api.hyperliquid.xyz/info",
                "Variational": "https://api.variational.fi/ (to verify)",
            },
            "estimated_edge": "Unknown — requires data collection; high potential if mechanisms diverge",
        },
        {
            "priority": 3,
            "pair": "HL BTC-PERP vs dYdX v4 BTC-PERP",
            "rationale": "Both US-user-excluded venues; K270 already tracks dYdX FR data (alt_exchange_fr_daily)",
            "api_urls": {
                "HL": "https://api.hyperliquid.xyz/info",
                "dYdX": "https://indexer.dydx.trade/v4/",
            },
            "estimated_edge": "0.5-2 bps; existing K270 data already partial",
        },
    ],
    "k208_extension_notes": "K208 is currently HL-Bybit bilateral DAR reverse carry. Extension to multi-venue requires: (1) normalized FR format across venues, (2) latency matching (HL 1s vs Bybit ~100ms), (3) settlement timing alignment (HL hourly vs 8h standard). Feasibility: HIGH for HL-Drift SOL pair within 1-2 waves.",
}

# ── Phase 4: Concentration Risk Assessment ────────────────────────────────

CONCENTRATION_RISK = {
    "v613d_allocation": {
        "K280_weight_pct": 75,
        "K297_prime_weight_pct": 20,
        "sUSDe_weight_pct": 5,
        "total_pct": 100,
    },
    "venue_exposure": {
        "K280_bybit_split": 0.50,   # K280 = Bybit + HL ~50/50 split
        "K280_hl_split": 0.50,
        "K297_prime_venue": "HL_only",
        "sUSDe_venue": "Ethena_DeFi",
    },
    "hl_capital_exposure_calc": {
        "from_K280": 0.75 * 0.50,        # = 0.375
        "from_K297_prime": 0.20,         # = 0.200
        "from_sUSDe": 0.0,               # Ethena, not HL
        "total_hl_exposure_pct": (0.75 * 0.50 + 0.20) * 100,  # = 57.5%
    },
    "bybit_exposure_pct": 0.75 * 0.50 * 100,   # = 37.5%
    "ethena_exposure_pct": 5.0,

    "scenario_analysis": {
        "scenario_A_cftc_hip3_enforcement": {
            "description": "CFTC formally restricts HL HIP-3 listings — SPX, PAXG delisted or volume halted",
            "probability_12m": "15-25%",
            "K297_prime_impact": "TOTAL LOSS OF ALPHA — strategy collapses to near-zero (carry source eliminated)",
            "K280_impact": "PARTIAL — K280 uses HL for execution but not HIP-3; likely 5-15% degradation from HL instability",
            "sUSDe_impact": "NONE — Ethena is independent",
            "combined_portfolio_impact": {
                "K297_prime_pnl_loss_pct": 100,
                "K280_pnl_degradation_pct": 10,
                "portfolio_ann_return_impact_pp": -(0.20 * 10.0 + 0.75 * 10 * 0.10),
                "note": "Approximate: lose ~2.0pp from K297' + 0.75pp from K280 degradation = ~2.75pp return loss",
            },
            "capital_at_risk_pct": 20.0,   # K297' full weight
        },
        "scenario_B_hl_venue_shutdown": {
            "description": "HL platform goes offline (regulatory shutdown, hack, insolvency)",
            "probability_12m": "3-7%",
            "K297_prime_impact": "TOTAL LOSS",
            "K280_impact": "SEVERE — ~50% of K280 exposure on HL; positions stranded",
            "sUSDe_impact": "NONE",
            "combined_portfolio_impact": {
                "capital_loss_pct": 57.5,
                "note": "Full HL exposure = 57.5% of capital at risk",
            },
            "capital_at_risk_pct": 57.5,
        },
        "scenario_C_variational_captures_rwa_carry": {
            "description": "Variational scales Gold/Silver RFQ volume → HL HIP-3 FR premium compresses",
            "probability_12m": "40-60%",
            "K297_prime_impact": "GRADUAL DEGRADATION — carry compressed 10-25% over 12 months",
            "K280_impact": "NONE",
            "sUSDe_impact": "NONE",
            "combined_portfolio_impact": {
                "K297_prime_ann_return_compression_pct": 15,
                "portfolio_ann_return_impact_pp": -(0.20 * 7.3 * 0.15),
                "note": "~0.22pp return loss — manageable but monitor",
            },
            "capital_at_risk_pct": 0,  # Capital not at risk, just carry compressed
        },
        "scenario_D_hl_market_share_decline": {
            "description": "HL share falls from 31.7% to 15% — liquidity dries, slippage increases",
            "probability_12m": "25-35%",
            "K297_prime_impact": "MODERATE — wider spreads increase round-trip cost",
            "K280_impact": "MODERATE — K208 (ML allocator) partly depends on HL liquidity",
            "combined_portfolio_impact": {
                "note": "Cost degradation ~5-10%; not catastrophic but Sharpe degrades",
            },
            "capital_at_risk_pct": 0,
        },
    },

    "risk_severity_matrix": {
        "CRITICAL": ["scenario_B_hl_venue_shutdown"],
        "HIGH": ["scenario_A_cftc_hip3_enforcement"],
        "MEDIUM": ["scenario_C_variational_captures_rwa_carry", "scenario_D_hl_market_share_decline"],
        "overall_assessment": "REAL AND NON-TRIVIAL. 57.5% HL exposure is NOT acceptable long-term for a strategy targeting capital preservation. Scenario B (HL shutdown) has only 3-7% probability but 57.5% capital-at-risk = ~2-4% expected loss from this tail alone. Scenario A (CFTC HIP-3) has active trigger (CME/ICE lobbying as of May 2026).",
    },

    "mitigation_strategies": {
        "A_diversify_k297_to_variational": {
            "description": "Add Variational Gold RFQ as K297 parallel sleeve once API confirmed",
            "hl_exposure_reduction_pp": 5,
            "feasibility": "MEDIUM — Variational API needs validation; K356 candidate",
            "estimated_timeline_waves": 5,
        },
        "B_reduce_k297_to_fallback": {
            "description": "v6.13e fallback: K280 85% + K297' 10% + sUSDe 5% (HL exposure drops to 52.5%)",
            "hl_exposure_after_pct": 0.85 * 0.50 * 100 + 10,  # = 52.5%
            "sharpe_cost": -2.58,  # v6.13e Sharpe 22.89 vs v6.13d 25.47
            "trigger": "If CFTC formally opens HL investigation OR HL HYPE token drops >40% in 7d",
        },
        "C_emergency_exit_script": {
            "description": "Pre-build script to close all HL positions within 2h if trigger fires",
            "status": "NOT YET BUILT — K356 must-do",
            "priority": "HIGH",
        },
        "D_add_drift_solana_sleeve": {
            "description": "Add Drift (Solana) as 3rd execution venue for non-RWA carry positions",
            "hl_exposure_reduction_pp": 10,
            "feasibility": "HIGH — Drift API public, K208 pattern extensible",
            "estimated_timeline_waves": 3,
        },
    },
}

# ── Phase 5: Decision Matrix ───────────────────────────────────────────────

DECISION_MATRIX = {
    "immediate_this_wave": [
        {
            "action": "Document concentration risk formally",
            "status": "DONE (this wave)",
            "concern_level": "HIGH",
        },
        {
            "action": "Confirm v6.13e fallback parameters are recorded",
            "status": "DONE — v6.13e: K280 85% + K297' 10% + sUSDe 5%, Sharpe 22.89",
            "concern_level": "HIGH",
        },
    ],
    "monitor_next_30d": [
        {
            "item": "Variational Gold/Silver volume growth",
            "signal": "If Variational 30d RWA vol > $20B → carry compression imminent",
            "source": "Variational public dashboard or API",
        },
        {
            "item": "CFTC formal action on HL",
            "signal": "If CFTC opens formal investigation or issues subpoena → trigger v6.13e fallback",
            "source": "Bloomberg/CoinDesk alert monitoring",
        },
        {
            "item": "HL HYPE token price",
            "signal": "If HYPE drops >40% in 7d → heightened platform risk",
            "source": "HL price feed",
        },
        {
            "item": "HL HIP-3 FR carry levels (PAXG/SPX)",
            "signal": "If 30d rolling APR < 4% on both → carry edge degrading",
            "source": "K302 monitoring daemon (existing)",
        },
    ],
    "defer_until_concrete_action": [
        "Architecture change to Variational integration (K356+)",
        "Emergency exit script build (K356 must-do)",
        "Drift Solana sleeve addition (K357+)",
    ],
    "trigger_v613e_fallback_conditions": [
        "CFTC formally opens HL investigation (any public filing)",
        "HL halts HIP-3 listings voluntarily or under pressure",
        "HYPE token -40% in 7d from current ~$44 level",
        "K297' rolling 30d MaxDD exceeds -0.5% (existing K346 monitor trigger)",
    ],
}

# ── Phase 6: Forward Strategy / Memory Recommendations ────────────────────

FORWARD_STRATEGY = {
    "memory_recommendation": {
        "file": "feedback_concentration_risk_HL.md",
        "verdict": "CREATE — concern level is NON-TRIVIAL",
        "content_summary": (
            "v6.13d has 57.5% HL exposure. Scenarios: CFTC HIP-3 enforcement (15-25% prob, ~2.75pp return loss), "
            "HL shutdown (3-7% prob, 57.5% capital at risk). Variational (already live) is primary RWA carry competitor. "
            "v6.13e fallback pre-approved (Sharpe 22.89 vs 25.47). Emergency exit script is unbuilt (K356 priority)."
        ),
    },
    "k356_candidates": [
        "Emergency HL exit script (HIGH PRIORITY)",
        "Variational API integration research",
        "Drift Solana SOL-PERP arb vs HL (K208 extension)",
    ],
    "k357_candidates": [
        "Lighter Chainlink equity feed vs HL SPX: data collection",
        "Multi-venue FR normalization schema",
    ],
    "v613e_trigger_protocol": (
        "On CFTC formal action OR HL HIP-3 halt: "
        "1. Reduce K297' from 20%→10% within 24h. "
        "2. Increase K280 from 75%→85%. "
        "3. sUSDe unchanged at 5%. "
        "4. Log to deployment_status.json with timestamp."
    ),
}

# ── Output ─────────────────────────────────────────────────────────────────

def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "wave": "K355",
        "generated_at": now,
        "phase1_venue_catalog": VENUE_CATALOG,
        "phase2_hl_competitive_position": HL_POSITION,
        "phase3_cross_venue_arb": CROSS_VENUE_ARB,
        "phase4_concentration_risk": CONCENTRATION_RISK,
        "phase5_decision_matrix": DECISION_MATRIX,
        "phase6_forward_strategy": FORWARD_STRATEGY,
        "sources": [
            "R12-11: Paradex blog Perp DEX Wars $8T (self-published; flag potential bias)",
            "R12-15: CoinDesk Variational $50M Series A (May 2026)",
            "R12-16: CoinDesk CME/ICE CFTC pressure on HL (May 2026)",
            "K297: wave_k297_hip3_weekend.md — HL HIP-3 PAXG/SPX carry",
            "K346: wave_k346_v6_13_weighting.md — v6.13d architecture",
            "WebFetch: dydx.xyz, aevo.xyz, drift.trade, lighter.xyz, paradex.trade/blog",
        ],
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"[K355] JSON written → {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

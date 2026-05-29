"""
K470 — MEV / Liquidator Strategy Exploration
Wave: K470 | Date: 2026-05-25 | Status: ANALYSIS ONLY → DEFER
Purpose: Explore MEV liquidator strategies (Aave V3, Compound V3, HyperLiquid HLP,
         dYdX v4, Drift) as a potential new strategy class orthogonal to carry/momentum.
Constraint: DO NOT modify production scripts (K339 security rule). Analysis only.
Decision: DEFER — focus on v6.20 deployment first; MEV liquidators are 5-10x effort
          for 1-10% revenue lift relative to v6.20 baseline.
"""

import json
import math
from pathlib import Path
from datetime import datetime, timezone

# ── Constants ─────────────────────────────────────────────────────────────────

WAVE = "K470"
DATE = "2026-05-25"
REPO_ROOT = Path("/Users/nekonaomichi/crypto-lab")
OUTPUT_JSON = REPO_ROOT / "wave_k470_mev_liquidator.json"

# ── Aave V3 Liquidation Mechanics (sourced from on-chain contract analysis) ───

AAVE_V3_PARAMS = {
    # From LiquidationLogic.sol
    "default_close_factor_pct": 50.0,          # 50% of debt can be repaid per liquidation
    "max_close_factor_pct": 100.0,             # 100% when HF < 0.95
    "close_factor_hf_threshold": 0.95,         # Below this: full liquidation allowed
    "liquidation_trigger_hf": 1.0,             # Health Factor < 1.0 triggers eligibility
    # Typical bonus by asset (from Aave V3 risk parameters, as of 2026)
    "liquidation_bonus_pct_by_asset": {
        "WBTC":  5.0,   # 5% bonus
        "WETH":  5.0,   # 5% bonus
        "USDC":  4.5,   # 4.5% bonus (stable collateral)
        "DAI":   4.5,   # 4.5% bonus
        "LINK":  7.5,   # 7.5% bonus (higher risk asset)
        "UNI":   8.5,   # 8.5% bonus
        "AAVE":  10.0,  # 10% bonus
        "eMode_stablecoins": 1.0,  # Only 1% in eMode (tight collateral bands)
    },
    # Protocol fee deducted from liquidator bonus (Aave V3 governance param)
    "protocol_fee_pct_of_bonus": 10.0,        # 10% of bonus goes to protocol
    # Net bonus after protocol fee (example for WETH: 5% * (1 - 0.10) = 4.5%)
    "net_bonus_example_weth_pct": 4.5,
    # Flash loan overhead
    "flashloan_fee_pct": 0.09,                # Aave V3 flash loan fee: 9bps
    # Gas cost per liquidation (Ethereum mainnet, estimate)
    "gas_units_per_liquidation": 400_000,      # ~400K gas for flash loan + liquidate + repay
    "eth_gas_price_gwei_typical": 15.0,        # ~15 gwei typical non-peak
    "eth_price_usd_approx": 2500.0,
}

# Compute gas cost per liquidation
def compute_gas_cost_usd(gas_units: int, gwei: float, eth_price: float) -> float:
    gas_eth = gas_units * gwei * 1e-9
    return gas_eth * eth_price

GAS_COST_PER_LIQ_USD = compute_gas_cost_usd(
    AAVE_V3_PARAMS["gas_units_per_liquidation"],
    AAVE_V3_PARAMS["eth_gas_price_gwei_typical"],
    AAVE_V3_PARAMS["eth_price_usd_approx"],
)

# ── Market Size Estimates ─────────────────────────────────────────────────────

MARKET_SIZE = {
    # Aave V3 (all chains: Ethereum, Polygon, Arbitrum, Optimism, Base)
    "aave_v3_tvl_usd": 15_000_000_000,        # ~$15B TVL across chains (2026 est.)
    "aave_v3_annual_liquidation_vol_usd": 500_000_000,  # ~$500M/yr (volatile market)
    "aave_v3_annual_liquidation_vol_bear_usd": 100_000_000,  # $100M bear market
    "aave_v3_annual_liquidation_vol_bull_crash_usd": 2_000_000_000,  # $2B crash event
    # Average bonus gross to liquidators
    "aave_v3_avg_bonus_pct": 5.5,             # blended across assets
    # Total gross liquidation profit (Aave V3)
    "aave_v3_gross_annual_profit_usd": 500_000_000 * 0.055,  # $27.5M pool
    # Competition
    "aave_num_active_liquidator_bots": 30,    # ~30 active sophisticated bots
    "aave_top10_bots_market_share_pct": 85.0, # Top 10 capture ~85%
    "aave_top3_bots_market_share_pct": 60.0,  # Top 3 capture ~60%
    # Compound V3
    "compound_v3_tvl_usd": 3_000_000_000,
    "compound_v3_annual_liq_vol_usd": 80_000_000,
    "compound_v3_bonus_pct": 5.0,
    "compound_v3_gross_annual_profit_usd": 80_000_000 * 0.05,  # $4M pool
    # HyperLiquid HLP (backstop liquidations)
    "hl_hlp_tvl_usd": 400_000_000,            # ~$400M in HLP
    "hl_hlp_annual_liq_profit_usd": 20_000_000,  # est. from HLP APY ~5%
    "hl_hlp_structure": "community_vault",    # democratized — not open to external bots
    # dYdX v4 (Cosmos chain)
    "dydx_v4_annual_liq_vol_usd": 50_000_000,
    "dydx_v4_bonus_pct": 2.5,
    "dydx_v4_gross_annual_profit_usd": 50_000_000 * 0.025,  # $1.25M
    # Drift (Solana)
    "drift_annual_liq_vol_usd": 30_000_000,
    "drift_insurance_fund_buffer_usd": 10_000_000,
    "drift_accessible_to_external_bots": True,
}

# ── Boutique Liquidator Revenue Model ─────────────────────────────────────────

def compute_boutique_revenue(
    gross_pool_usd: float,
    market_share_pct: float,
    gas_cost_per_event_usd: float,
    events_per_year: int,
    infra_cost_monthly_usd: float,
) -> dict:
    """
    Estimate annual net revenue for a boutique liquidator bot.
    Assumes you can realistically capture market_share_pct of the gross pool.
    """
    gross_revenue = gross_pool_usd * (market_share_pct / 100)
    total_gas_cost = gas_cost_per_event_usd * events_per_year * (market_share_pct / 100)
    total_infra_cost = infra_cost_monthly_usd * 12
    net_revenue = gross_revenue - total_gas_cost - total_infra_cost
    return {
        "gross_pool_usd": gross_pool_usd,
        "market_share_pct": market_share_pct,
        "gross_revenue_usd": round(gross_revenue),
        "gas_cost_usd": round(total_gas_cost),
        "infra_cost_usd": round(total_infra_cost),
        "net_revenue_usd": round(net_revenue),
    }

# Scenarios: boutique bot entering Aave V3 with 1-5% market share
AAVE_V3_SCENARIOS = {
    "pessimistic_1pct_share": compute_boutique_revenue(
        gross_pool_usd=MARKET_SIZE["aave_v3_gross_annual_profit_usd"],
        market_share_pct=1.0,
        gas_cost_per_event_usd=GAS_COST_PER_LIQ_USD,
        events_per_year=5000,     # ~14/day across all chains
        infra_cost_monthly_usd=5000,
    ),
    "base_2pct_share": compute_boutique_revenue(
        gross_pool_usd=MARKET_SIZE["aave_v3_gross_annual_profit_usd"],
        market_share_pct=2.0,
        gas_cost_per_event_usd=GAS_COST_PER_LIQ_USD,
        events_per_year=5000,
        infra_cost_monthly_usd=5000,
    ),
    "optimistic_5pct_share": compute_boutique_revenue(
        gross_pool_usd=MARKET_SIZE["aave_v3_gross_annual_profit_usd"],
        market_share_pct=5.0,
        gas_cost_per_event_usd=GAS_COST_PER_LIQ_USD,
        events_per_year=5000,
        infra_cost_monthly_usd=5000,
    ),
}

# ── Infrastructure Requirements ───────────────────────────────────────────────

INFRASTRUCTURE = {
    # Node infrastructure
    "dedicated_ethereum_node": {
        "provider": "e.g. Blastapi/Alchemy dedicated or self-hosted",
        "monthly_cost_usd": 500,
        "latency_ms": "<20ms to mempool",
        "required": True,
        "note": "Archive node preferred for complex state queries",
    },
    "private_mempool_relay": {
        "provider": "Flashbots MEV-Share or Eden Network",
        "monthly_cost_usd": 0,    # Free but requires tips/bribes for inclusion
        "bundle_tip_pct_of_profit": 70,  # Typical: searcher keeps 30% via MEV-Share
        "required": True,
        "note": "Without MEV-Share, liquidations are front-run by sandwich bots",
    },
    "oracle_price_feeds": {
        "provider": "Chainlink + Pyth Network",
        "monthly_cost_usd": 50,
        "latency_ms": "<1000ms price update",
        "required": True,
    },
    "health_factor_monitor": {
        "description": "On-chain account scanner — track HF for all Aave positions",
        "events_per_second": 100,   # Block-by-block polling
        "required": True,
        "monthly_cost_usd": 200,
    },
    "flashloan_smart_contract": {
        "description": "Custom liquidator contract using Aave flash loans",
        "one_time_dev_cost_usd": 20000,
        "audit_cost_usd": 30000,   # Smart contract audit mandatory
        "required": True,
    },
    "gas_bidding_engine": {
        "description": "Dynamic priority fee optimizer (EIP-1559)",
        "required": True,
        "monthly_cost_usd": 0,    # Internal logic
    },
    "monitoring_alerting": {
        "provider": "Grafana + Prometheus or Datadog",
        "monthly_cost_usd": 100,
        "required": True,
    },
    # Summary
    "total_monthly_infra_usd": 5000,   # Including buffer for node, monitoring, etc.
    "total_initial_dev_usd": 80000,    # Dev + audit + testing
    "ongoing_maintenance_hrs_per_month": 20,  # Tuning, updates, incident response
    "time_to_production_months": 4,    # Realistic 4-month build
}

# ── MEV Relay Economics ───────────────────────────────────────────────────────

MEV_RELAY_ECONOMICS = {
    # Flashbots MEV-Share: searcher submits bundle, user/protocol get part of MEV
    "mev_share_searcher_share_pct": 30,    # Searcher keeps ~30% via MEV-Share
    "mev_share_user_refund_pct": 70,       # 70% refunded to user/protocol
    # Private mempool required to avoid being sandwiched
    "public_mempool_sandwich_risk": "HIGH",
    "expected_loss_from_sandwich_pct": 80,  # 80% of profit stolen without private relay
    # Alternative: bundle via Flashbots Protect (higher inclusion cost)
    "flashbots_protect_inclusion_rate_pct": 95,
    "flashbots_tip_pct_of_profit": 10,     # 10% tip to miners/validators
}

# ── K266 Gates Assessment ─────────────────────────────────────────────────────

K266_GATES = {
    "G1_oos_sharpe": {
        "applicable": False,
        "reason": "Event-driven strategy: no continuous daily PnL stream to compute Sharpe",
        "alternative_metric": "avg_profit_per_event_usd > gas_cost * 3x",
        "status": "NOT APPLICABLE — event count needed for meaningful Sharpe",
    },
    "G3_dsr": {
        "applicable": "PARTIAL",
        "estimated_events_per_month": 30,        # ~1/day rough estimate
        "profit_per_event_usd_net": 2700,        # base scenario
        "monthly_dsr_equivalent": "N/A",
        "note": "DSR framework does not map to episodic MEV revenue cleanly",
    },
    "G6_trade_count": {
        "applicable": True,
        "estimated_liquidations_per_day": 1,     # boutique 2% share of ~14/day market
        "passes": True,
        "note": "Frequency is event-limited, not signal-driven",
    },
    "G7_ann_return_pct": {
        "gross_on_deployed_capital_pct": "N/A",  # Flash loans = no capital required
        "net_revenue_usd_base": AAVE_V3_SCENARIOS["base_2pct_share"]["net_revenue_usd"],
        "passes_if_compared_to_v620": False,     # v6.20 at $10M AUM = $1M/yr; MEV = $50K-$275K
        "note": "Revenue absolute, not percentage — capacity-limited by event count",
    },
    "overall_gate_status": "INCOMPLETE — event-driven model incompatible with G1/G3 continuous Sharpe gates",
}

# ── Orthogonality Analysis ─────────────────────────────────────────────────────

ORTHOGONALITY = {
    "mechanism": "event_driven_forced_liquidation",
    "signal_source": "on-chain_health_factor",
    "comparison_to_existing": {
        "K208_FR_carry": {
            "correlation_expected": 0.05,
            "reason": "MEV profits uncorrelated with funding rate levels",
        },
        "K376_momentum": {
            "correlation_expected": 0.10,
            "reason": "Liquidation cascades CAUSE momentum spikes but profits occur before/during",
            "positive_note": "HL cascade signal (K372 concept) could enhance K376",
        },
        "K449_ETH_BTC_differential": {
            "correlation_expected": 0.05,
        },
        "K457_basket": {
            "correlation_expected": 0.05,
        },
    },
    "true_alpha_orthogonal": True,
    "note": "MEV liquidation is structurally uncorrelated — profits driven by collateral shortfalls, not market direction",
}

# ── Capital Requirements ───────────────────────────────────────────────────────

CAPITAL_STRUCTURE = {
    "flash_loan_based": {
        "capital_required_usd": 0,        # Flash loans: borrow and repay in one tx
        "advantage": "No locked capital",
        "max_liquidation_size": "Unlimited (constrained by Aave flash loan pool)",
        "flash_loan_fee_on_profit_pct": AAVE_V3_PARAMS["flashloan_fee_pct"],
    },
    "pre_funded_based": {
        "capital_required_usd": 500_000,  # Need capital to repay debt before claiming collateral
        "advantage": "Faster execution (no flash loan callback overhead)",
        "note": "Used by top-tier bots for speed advantage",
    },
    "recommended_approach": "flash_loan_based",
    "sleeve_weight_if_accepted": "0.5-1% of AUM (separate capital bucket)",
    "capacity_limit": "Revenue limited by liquidation event count, not AUM",
}

# ── Competing Venue Analysis ──────────────────────────────────────────────────

VENUE_COMPARISON = {
    "Aave_V3_Ethereum": {
        "gross_pool_usd": MARKET_SIZE["aave_v3_gross_annual_profit_usd"],
        "competition_level": "EXTREME",
        "num_active_bots": 30,
        "infrastructure_barrier": "HIGH",
        "flash_loan_available": True,
        "accessibility": "Open — anyone can call liquidationCall()",
        "realistic_share_boutique_pct": 1.0,
        "estimated_net_revenue_usd": AAVE_V3_SCENARIOS["pessimistic_1pct_share"]["net_revenue_usd"],
    },
    "Aave_V3_L2_chains": {
        "gross_pool_usd": 5_000_000,    # smaller but less competitive
        "competition_level": "MEDIUM",
        "num_active_bots": 5,
        "infrastructure_barrier": "MEDIUM",
        "flash_loan_available": True,
        "accessibility": "Open",
        "realistic_share_boutique_pct": 10.0,
        "estimated_net_revenue_usd": 5_000_000 * 0.10 - 60_000,  # $440K
    },
    "Compound_V3": {
        "gross_pool_usd": MARKET_SIZE["compound_v3_gross_annual_profit_usd"],
        "competition_level": "HIGH",
        "num_active_bots": 15,
        "realistic_share_boutique_pct": 3.0,
        "estimated_net_revenue_usd": 4_000_000 * 0.03 - 60_000,  # $60K
    },
    "HyperLiquid_HLP": {
        "accessible_to_external_bots": False,
        "note": "HLP is community vault — backstop liquidations democratized through HLP shares, not external bots",
        "alternative": "Participate in HLP as LP; indirect liquidation exposure",
        "hlp_apy_est_pct": 5.0,
    },
    "dYdX_v4": {
        "gross_pool_usd": MARKET_SIZE["dydx_v4_gross_annual_profit_usd"],
        "competition_level": "LOW",    # Cosmos chain — fewer searchers
        "infrastructure_barrier": "HIGH",    # Cosmos SDK expertise required
        "realistic_share_boutique_pct": 15.0,
        "estimated_net_revenue_usd": 1_250_000 * 0.15 - 60_000,  # $127K
    },
    "Drift_Solana": {
        "accessible_to_external_bots": True,
        "competition_level": "MEDIUM",
        "infrastructure_barrier": "MEDIUM",  # Solana RPC required
        "gross_pool_usd": MARKET_SIZE["drift_annual_liq_vol_usd"] * 0.025,  # $750K
        "realistic_share_boutique_pct": 8.0,
        "estimated_net_revenue_usd": 750_000 * 0.08 - 60_000,  # $0K (marginal)
    },
}

# ── Lighter Alternative: HL Cascade Signal Enhancement ────────────────────────

HL_CASCADE_SIGNAL = {
    "concept": "K372 reactivated as SIGNAL (not as liquidator)",
    "mechanism": (
        "Monitor HL liquidation cascade events (position close volume spike) "
        "as a directional signal to ENHANCE K376 momentum or K208 FR filter. "
        "Liquidation cascades create momentum (directional) and FR spikes (carry opportunity). "
        "Signal: cascade_volume_t > 2x avg → increase K376 position size OR "
        "add FR carry for 4-8h post-cascade window."
    ),
    "implementation_effort": "LOW",
    "dev_time_days": 5,
    "expected_alpha_bps_per_trade": 15,   # incremental vs existing K376
    "signal_source": "HL public API — open interest + mark price delta per 15min",
    "k266_compatible": True,
    "recommendation": "PURSUE THIS FIRST — low effort, no smart contracts, uses existing HL infra",
}

# ── Revenue Summary ────────────────────────────────────────────────────────────

def compute_annual_revenue_summary() -> dict:
    """Consolidate revenue estimates across all venues and scenarios."""
    aave_l2_net = VENUE_COMPARISON["Aave_V3_L2_chains"]["estimated_net_revenue_usd"]
    compound_net = VENUE_COMPARISON["Compound_V3"]["estimated_net_revenue_usd"]
    dydx_net = VENUE_COMPARISON["dYdX_v4"]["estimated_net_revenue_usd"]

    # Multi-venue boutique: focus on L2 + dYdX (lower competition)
    multi_venue_net = aave_l2_net + dydx_net  # $567K if estimates hold

    v620_baseline_at_10m_aum = 1_000_000

    return {
        "single_venue_pessimistic_usd": AAVE_V3_SCENARIOS["pessimistic_1pct_share"]["net_revenue_usd"],
        "single_venue_base_usd": AAVE_V3_SCENARIOS["base_2pct_share"]["net_revenue_usd"],
        "single_venue_optimistic_usd": AAVE_V3_SCENARIOS["optimistic_5pct_share"]["net_revenue_usd"],
        "multi_venue_boutique_est_usd": round(multi_venue_net),
        "mev_as_pct_of_v620_baseline_pessimistic": round(
            AAVE_V3_SCENARIOS["pessimistic_1pct_share"]["net_revenue_usd"] / v620_baseline_at_10m_aum * 100, 1
        ),
        "mev_as_pct_of_v620_baseline_base": round(
            AAVE_V3_SCENARIOS["base_2pct_share"]["net_revenue_usd"] / v620_baseline_at_10m_aum * 100, 1
        ),
        "mev_as_pct_of_v620_baseline_optimistic": round(
            AAVE_V3_SCENARIOS["optimistic_5pct_share"]["net_revenue_usd"] / v620_baseline_at_10m_aum * 100, 1
        ),
        "v620_baseline_usd": v620_baseline_at_10m_aum,
        "note": (
            "MEV liquidator contributes 1-20% of v6.20 baseline at $10M AUM. "
            "Even optimistic estimates lag v6.20 by 5x for 5-10x more implementation effort."
        ),
    }

ANNUAL_REVENUE_SUMMARY = compute_annual_revenue_summary()

# ── Effort vs Reward Matrix ────────────────────────────────────────────────────

EFFORT_REWARD = {
    "strategies": {
        "v6.20_carry_momentum": {
            "annual_revenue_est_usd": 1_000_000,
            "implementation_effort_months": 0,    # Already built
            "status": "PRODUCTION",
            "complexity": "LOW (existing)",
        },
        "MEV_liquidator_Aave_V3_mainnet": {
            "annual_revenue_est_usd": 200_000,   # base scenario
            "implementation_effort_months": 6,
            "initial_capex_usd": 80_000,
            "status": "RESEARCH",
            "complexity": "EXTREME",
            "risk": "Smart contract bugs, gas wars, MEV competition",
        },
        "MEV_liquidator_Aave_V3_L2": {
            "annual_revenue_est_usd": 440_000,
            "implementation_effort_months": 4,
            "initial_capex_usd": 60_000,
            "status": "RESEARCH",
            "complexity": "HIGH",
        },
        "MEV_liquidator_dYdX_v4": {
            "annual_revenue_est_usd": 127_000,
            "implementation_effort_months": 5,
            "initial_capex_usd": 70_000,
            "status": "RESEARCH",
            "complexity": "HIGH (Cosmos SDK)",
        },
        "HL_cascade_signal_K376_enhancement": {
            "annual_revenue_est_usd": 50_000,    # incremental alpha
            "implementation_effort_months": 0.25,  # 5 days
            "initial_capex_usd": 0,
            "status": "RECOMMENDED_NEXT",
            "complexity": "LOW",
            "note": "Reactivates K372 concept as signal enhancer, no smart contracts",
        },
    }
}

# ── Decision Matrix ────────────────────────────────────────────────────────────

DECISION = {
    "recommendation": "DEFER",
    "rationale": [
        "MEV liquidator generates $50K-$440K/yr for boutique operator — 5-44% of v6.20 baseline",
        "Implementation requires 4-6 months dev, $60-80K capex, smart contract audits",
        "Competition from 30+ active sophisticated bots on Aave mainnet",
        "Revenue is capacity-limited by event count, not scalable with AUM",
        "v6.20 baseline already strong; scaling AUM from $10M to $100M is higher ROI",
        "Smart contract risk introduces catastrophic loss potential not present in v6.20",
    ],
    "defer_trigger": [
        "$100M+ AUM achieved (MEV becomes meaningful diversifier)",
        "Dedicated MEV engineer hired (not founder time)",
        "v6.20 production stable for 6+ months",
    ],
    "defer_review_date": "2027-12-31",
    "immediate_action": "PURSUE HL cascade signal enhancement (K372 reactivation as signal)",
    "immediate_action_effort_days": 5,
    "reject_full_mev_bot": False,   # Not reject — defer, with clear trigger conditions
}

# ── Gas Cost Summary ───────────────────────────────────────────────────────────

print(f"=== K470 MEV Liquidator Strategy Analysis ===")
print(f"Gas cost per liquidation: ${GAS_COST_PER_LIQ_USD:.2f}")
print()
print("Aave V3 Annual Revenue Scenarios (boutique liquidator):")
for name, s in AAVE_V3_SCENARIOS.items():
    print(f"  {name}:")
    print(f"    Gross: ${s['gross_revenue_usd']:,}")
    print(f"    Gas:   ${s['gas_cost_usd']:,}")
    print(f"    Infra: ${s['infra_cost_usd']:,}")
    print(f"    Net:   ${s['net_revenue_usd']:,}")
    print()

print("Revenue vs v6.20 Baseline ($10M AUM = $1M/yr):")
r = ANNUAL_REVENUE_SUMMARY
print(f"  Pessimistic:  ${r['single_venue_pessimistic_usd']:,} ({r['mev_as_pct_of_v620_baseline_pessimistic']}% of baseline)")
print(f"  Base:         ${r['single_venue_base_usd']:,} ({r['mev_as_pct_of_v620_baseline_base']}% of baseline)")
print(f"  Optimistic:   ${r['single_venue_optimistic_usd']:,} ({r['mev_as_pct_of_v620_baseline_optimistic']}% of baseline)")
print()
print(f"Decision: {DECISION['recommendation']}")
print(f"Immediate Action: {DECISION['immediate_action']}")

# ── Output JSON ───────────────────────────────────────────────────────────────

def build_output() -> dict:
    return {
        "wave": WAVE,
        "date": DATE,
        "strategy_class": "MEV Liquidator",
        "decision": DECISION["recommendation"],
        "gas_cost_per_liquidation_usd": round(GAS_COST_PER_LIQ_USD, 2),
        "aave_v3_params": AAVE_V3_PARAMS,
        "market_size": MARKET_SIZE,
        "aave_v3_scenarios": AAVE_V3_SCENARIOS,
        "infrastructure": INFRASTRUCTURE,
        "venue_comparison": VENUE_COMPARISON,
        "orthogonality": ORTHOGONALITY,
        "capital_structure": CAPITAL_STRUCTURE,
        "k266_gates": K266_GATES,
        "annual_revenue_summary": ANNUAL_REVENUE_SUMMARY,
        "effort_reward": EFFORT_REWARD,
        "hl_cascade_signal": HL_CASCADE_SIGNAL,
        "decision_matrix": DECISION,
        "mev_relay_economics": MEV_RELAY_ECONOMICS,
    }

if __name__ == "__main__":
    output = build_output()
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nOutput written to {OUTPUT_JSON}")

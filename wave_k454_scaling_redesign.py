"""
wave_k454_scaling_redesign.py
K454: $100M+ AUM Scaling Redesign — v6.20 candidate
- Slippage ceiling analysis per strategy component
- Multi-venue 7-10 distribution model
- Position depth-aware allocator design
- BTC ETF flow alpha + multi-asset basket new sleeves
- Profit projections at $50M / $100M / $200M / $500M AUM
- Maximum sustainable AUM estimate

Constraints:
- NO new packages (json, math, os, datetime stdlib only)
- DO NOT modify existing production scripts
- REPO_ROOT pattern
"""

import json
import math
import os
from datetime import datetime, timezone

# ── Repo root ───────────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = os.path.join(REPO_ROOT, "wave_k454_scaling_redesign.json")

# ── K431 baseline (confirmed numbers from prior wave) ──────────────────────
# K431 findings:
#   $10M: $2.08M/yr net (1 venue HL)
#   $25M: $4.28M/yr (HL+Bybit)
#   $50M: $5.45M/yr (HL+Bybit+Drift)
#   $100M: NEGATIVE — slippage $37M > gross $33M

# K426 3x leverage: gross annual return = 33.28% of AUM
GROSS_ANN_RET_RATE = 0.3328

# Slippage model constants (K431 calibrated)
ETA = 10.0  # bps factor for sqrt market impact

# ── Strategy component definitions ─────────────────────────────────────────
# Each component: (name, weight_v613d, daily_vol_proxy_usd, trades_per_year,
#                  capacity_usd, scaling_exponent, ceiling_reason)
# scaling_exponent: 1.0 = linear, 0.5 = sublinear, 2.0 = quadratic (bad)
# capacity_usd: AUM ceiling (strategy-level, not total portfolio)

COMPONENTS_V613D = [
    {
        "name": "K198 ML Allocator",
        "weight": 0.00,    # allocator only, no direct position
        "capacity_usd": float("inf"),
        "scaling_exp": 0.0,
        "ceiling_reason": "no direct market exposure, scales freely",
        "slippage_rate_at_cap": 0.0,
        "gross_rate": 0.0,
    },
    {
        "name": "K208 Cross-Venue BTC Carry",
        "weight": 0.75,
        "capacity_usd": 200_000_000,   # deep market, $200M ceiling (K454 est)
        "scaling_exp": 1.5,            # sublinear due to multi-venue distribution
        "ceiling_reason": "BTC perp OI $10B+, 10 venues reduce per-venue impact",
        "slippage_rate_at_cap": 0.015,  # 1.5% of notional at $200M ceiling
        "gross_rate": 0.3328 * 0.75,    # 75% weight of gross
    },
    {
        "name": "K276b HL Long-Tail RWA",
        "weight": 0.20,
        "capacity_usd": 30_000_000,    # shallow OI, $30M ceiling
        "scaling_exp": 2.0,            # quadratic impact
        "ceiling_reason": "HL RWA OI $15-25M, no alternative venues",
        "slippage_rate_at_cap": 0.30,  # ~30% of notional consumed by slippage at cap
        "gross_rate": 0.3328 * 0.20,
    },
    {
        "name": "K297' HIP-3 PAXG",
        "weight": 0.12,
        "capacity_usd": 15_000_000,
        "scaling_exp": 2.0,
        "ceiling_reason": "OI ~$15M on HL, niche market",
        "slippage_rate_at_cap": 0.50,
        "gross_rate": 0.3328 * 0.12,
    },
    {
        "name": "K297' HIP-3 SPX",
        "weight": 0.08,
        "capacity_usd": 10_000_000,
        "scaling_exp": 2.0,
        "ceiling_reason": "OI ~$8M on HL, even shallower",
        "slippage_rate_at_cap": 0.60,
        "gross_rate": 0.3328 * 0.08,
    },
    {
        "name": "sUSDe Yield",
        "weight": 0.05,
        "capacity_usd": 10_000_000_000,  # Ethena protocol TVL ~$5-10B
        "scaling_exp": 0.0,              # zero slippage (smart contract yield)
        "ceiling_reason": "protocol TVL limited, ~$5-10B, zero market impact",
        "slippage_rate_at_cap": 0.0,
        "gross_rate": 0.05,              # ~5% APY from sUSDe
    },
    {
        "name": "K376 Momentum",
        "weight": 0.00,    # not in v6.13d main, paper-trade
        "capacity_usd": 50_000_000,
        "scaling_exp": 1.5,
        "ceiling_reason": "5min OHLCV depth limits, ~$50M ceiling",
        "slippage_rate_at_cap": 0.08,
        "gross_rate": 0.18,  # ~18% gross from K376
    },
    {
        "name": "K449 ETH-BTC Differential",
        "weight": 0.03,    # v6.16 addition
        "capacity_usd": 100_000_000,
        "scaling_exp": 1.5,
        "ceiling_reason": "ETH+BTC deep markets, orthogonal carry",
        "slippage_rate_at_cap": 0.02,
        "gross_rate": 0.3328 * 0.03,
    },
]

# ── v6.20 architecture (K454 proposal) ─────────────────────────────────────
COMPONENTS_V620 = [
    {
        "name": "K208 Multi-Venue BTC (10 venues)",
        "weight": 0.65,
        "capacity_usd": 500_000_000,   # 10 venues × $50M each = $500M theoretical
        "scaling_exp": 1.2,
        "ceiling_reason": "HL/Bybit/OKX/Drift/Aevo/dYdX/GMX/Vertex/Lighter/Variational",
        "slippage_rate_at_cap": 0.05,
        "gross_rate": 0.3328 * 0.65,
    },
    {
        "name": "K297' RWA (HL+Variational)",
        "weight": 0.05,
        "capacity_usd": 25_000_000,
        "scaling_exp": 2.0,
        "ceiling_reason": "RWA OI still limited even with Variational",
        "slippage_rate_at_cap": 0.40,
        "gross_rate": 0.3328 * 0.05,
    },
    {
        "name": "sUSDe Yield",
        "weight": 0.10,
        "capacity_usd": 10_000_000_000,
        "scaling_exp": 0.0,
        "ceiling_reason": "Ethena protocol TVL, zero market impact",
        "slippage_rate_at_cap": 0.0,
        "gross_rate": 0.05,
    },
    {
        "name": "K376 Momentum",
        "weight": 0.05,
        "capacity_usd": 50_000_000,
        "scaling_exp": 1.5,
        "ceiling_reason": "OHLCV depth limited",
        "slippage_rate_at_cap": 0.08,
        "gross_rate": 0.18,
    },
    {
        "name": "K449 ETH-BTC Differential",
        "weight": 0.05,
        "capacity_usd": 100_000_000,
        "scaling_exp": 1.5,
        "ceiling_reason": "Deep ETH+BTC markets",
        "slippage_rate_at_cap": 0.02,
        "gross_rate": 0.3328 * 0.05,
    },
    {
        "name": "BTC ETF Flow Alpha (new)",
        "weight": 0.05,
        "capacity_usd": 2_000_000_000,  # ETF flow itself is $1B+ daily
        "scaling_exp": 0.8,
        "ceiling_reason": "ETF flow signal capacity ~$2B (signal alpha, not position OI)",
        "slippage_rate_at_cap": 0.01,
        "gross_rate": 0.12,             # estimated 12% gross from ETF flow signal
    },
    {
        "name": "Multi-Asset Basket (BTC+ETH+SOL inv-vol)",
        "weight": 0.05,
        "capacity_usd": 300_000_000,
        "scaling_exp": 1.3,
        "ceiling_reason": "3-asset inv-vol rebalance across deep markets",
        "slippage_rate_at_cap": 0.03,
        "gross_rate": 0.25,
    },
    {
        "name": "Cash + Margin Buffer",
        "weight": 0.10,
        "capacity_usd": float("inf"),
        "scaling_exp": 0.0,
        "ceiling_reason": "idle capital buffer, scales linearly",
        "slippage_rate_at_cap": 0.0,
        "gross_rate": 0.045,            # ~4.5% T-Bill / USDC yield on buffer
    },
]

# ── Venue OI/capacity table ─────────────────────────────────────────────────
VENUES = {
    "HyperLiquid": {
        "btc_oi_usd": 1_200_000_000,   # $1.2B BTC OI on HL perp
        "fee_maker_bps": 0.4,
        "fee_taker_bps": 2.2,
        "max_k208_alloc_usd": 80_000_000,   # K454 conservative: 5% OI cap
        "rwa_oi_usd": 23_000_000,
        "latency_ms": 50,
        "status": "LIVE",
    },
    "Bybit": {
        "btc_oi_usd": 2_500_000_000,
        "fee_maker_bps": 0.2,
        "fee_taker_bps": 0.55,
        "max_k208_alloc_usd": 125_000_000,
        "rwa_oi_usd": 0,
        "latency_ms": 80,
        "status": "INTEGRATION_PLANNED",
    },
    "OKX": {
        "btc_oi_usd": 2_000_000_000,
        "fee_maker_bps": 0.2,
        "fee_taker_bps": 0.5,
        "max_k208_alloc_usd": 100_000_000,
        "rwa_oi_usd": 0,
        "latency_ms": 90,
        "status": "NEW_K454",
    },
    "Drift": {
        "btc_oi_usd": 300_000_000,
        "fee_maker_bps": 1.0,
        "fee_taker_bps": 5.0,
        "max_k208_alloc_usd": 15_000_000,
        "rwa_oi_usd": 0,
        "latency_ms": 300,
        "status": "POST_RECOVERY",
    },
    "Aevo": {
        "btc_oi_usd": 200_000_000,
        "fee_maker_bps": 0.3,
        "fee_taker_bps": 0.8,
        "max_k208_alloc_usd": 10_000_000,
        "rwa_oi_usd": 0,
        "latency_ms": 150,
        "status": "NEW_K454",
    },
    "dYdX_v4": {
        "btc_oi_usd": 400_000_000,
        "fee_maker_bps": 0.5,
        "fee_taker_bps": 1.0,
        "max_k208_alloc_usd": 20_000_000,
        "rwa_oi_usd": 0,
        "latency_ms": 200,
        "status": "NEW_K454",
    },
    "Vertex": {
        "btc_oi_usd": 150_000_000,
        "fee_maker_bps": 0.2,
        "fee_taker_bps": 0.4,
        "max_k208_alloc_usd": 7_500_000,
        "rwa_oi_usd": 0,
        "latency_ms": 120,
        "status": "NEW_K454",
    },
    "GMX_v2": {
        "btc_oi_usd": 250_000_000,
        "fee_maker_bps": 0.0,    # no maker/taker, price impact only
        "fee_taker_bps": 5.0,    # effective fee from price impact
        "max_k208_alloc_usd": 12_500_000,
        "rwa_oi_usd": 0,
        "latency_ms": 400,
        "status": "NEW_K454_LOW_PRIORITY",
    },
    "Lighter": {
        "btc_oi_usd": 80_000_000,
        "fee_maker_bps": 0.1,
        "fee_taker_bps": 0.3,
        "max_k208_alloc_usd": 4_000_000,
        "rwa_oi_usd": 0,
        "latency_ms": 100,
        "status": "NEW_K454_R14",
    },
    "Variational": {
        "btc_oi_usd": 50_000_000,
        "fee_maker_bps": 0.2,
        "fee_taker_bps": 0.6,
        "max_k208_alloc_usd": 2_500_000,
        "rwa_oi_usd": 5_000_000,   # RWA on Variational
        "latency_ms": 200,
        "status": "NEW_K443",
    },
}

# ── AUM tiers for analysis ─────────────────────────────────────────────────
AUM_TIERS = [
    10_000_000,
    25_000_000,
    50_000_000,
    100_000_000,
    200_000_000,
    500_000_000,
]

LEVERAGE = 3.0
OPEX_BASE_USD = 12_000    # per year base
OPEX_VENUE_USD = 8_000    # per additional venue per year (infra, monitoring)


# ── Helpers ──────────────────────────────────────────────────────────────────

def sqrt_impact_bps(position_usd: float, daily_vol_usd: float, eta: float = ETA) -> float:
    """Square-root market impact (Almgren-Chriss simplified)."""
    if daily_vol_usd <= 0 or position_usd <= 0:
        return 0.0
    return eta * math.sqrt(position_usd / daily_vol_usd)


def component_slippage_at_aum(comp: dict, aum: float, leverage: float = LEVERAGE) -> float:
    """
    Estimate annual slippage cost (USD) for a strategy component at a given AUM.
    Uses scaling_exp to model how slippage scales with position size.
    """
    notional = aum * comp["weight"] * leverage
    cap = comp["capacity_usd"]
    if cap == float("inf") or cap <= 0:
        return 0.0

    # Fraction of capacity deployed
    frac = min(notional / cap, 3.0)   # cap at 3x for model validity

    # Slippage cost = slippage_rate_at_cap × (frac ^ scaling_exp) × notional × trades
    # trades_per_year: RWA ~104, BTC ~504, others ~252
    trades_factor = 1.0
    slippage_cost = comp["slippage_rate_at_cap"] * (frac ** comp["scaling_exp"]) * notional * trades_factor

    return slippage_cost


def component_gross_profit(comp: dict, aum: float, leverage: float = LEVERAGE) -> float:
    """Gross annual profit (USD) for a strategy component."""
    notional = aum * comp["weight"] * leverage
    return comp["gross_rate"] * notional


def compute_aum_tier(aum: float, components: list, n_venues: int, architecture_name: str) -> dict:
    """
    Full profitability analysis at a given AUM tier.
    Returns structured dict with gross, slippage, net, per-component breakdown.
    """
    gross_total = 0.0
    slip_total = 0.0
    comp_breakdown = []

    for comp in components:
        gross = component_gross_profit(comp, aum, LEVERAGE)
        slip = component_slippage_at_aum(comp, aum, LEVERAGE)
        net = gross - slip
        comp_breakdown.append({
            "component": comp["name"],
            "weight_pct": round(comp["weight"] * 100, 1),
            "notional_usd": round(aum * comp["weight"] * LEVERAGE),
            "gross_usd": round(gross),
            "slippage_usd": round(slip),
            "net_usd": round(net),
            "oi_frac_pct": round(
                min(aum * comp["weight"] * LEVERAGE / comp["capacity_usd"], 1.0) * 100, 2
            ) if comp["capacity_usd"] != float("inf") else 0.0,
        })
        gross_total += gross
        slip_total += slip

    opex = OPEX_BASE_USD + OPEX_VENUE_USD * n_venues
    net_total = gross_total - slip_total - opex

    gross_rate_pct = (gross_total / aum) * 100
    slip_rate_pct  = (slip_total / aum) * 100
    net_rate_pct   = (net_total / aum) * 100

    return {
        "architecture": architecture_name,
        "aum_usd": aum,
        "leverage": LEVERAGE,
        "n_venues": n_venues,
        "gross_usd": round(gross_total),
        "slippage_usd": round(slip_total),
        "opex_usd": round(opex),
        "net_usd": round(net_total),
        "gross_pct": round(gross_rate_pct, 2),
        "slippage_pct": round(slip_rate_pct, 2),
        "net_pct": round(net_rate_pct, 2),
        "viable": net_total > 0,
        "components": comp_breakdown,
    }


def depth_aware_allocator_plan(target_btc_notional: float) -> dict:
    """
    Position depth-aware allocator: distribute target BTC notional across venues.
    Rule: max allocation per venue = 5% of BTC OI.
    Returns per-venue allocation and total achievable.
    """
    allocs = {}
    remaining = target_btc_notional
    total_achievable = 0.0

    for venue, info in sorted(VENUES.items(), key=lambda x: -x[1]["btc_oi_usd"]):
        if info["status"] in ("NEW_K454_LOW_PRIORITY",):
            continue  # skip low-priority venues
        max_alloc = info["max_k208_alloc_usd"]
        alloc = min(remaining, max_alloc)
        allocs[venue] = {
            "allocated_usd": round(alloc),
            "max_cap_usd": max_alloc,
            "venue_btc_oi_usd": info["btc_oi_usd"],
            "pct_of_oi": round(alloc / info["btc_oi_usd"] * 100, 2),
            "status": info["status"],
            "fee_maker_bps": info["fee_maker_bps"],
        }
        total_achievable += alloc
        remaining -= alloc
        if remaining <= 0:
            break

    return {
        "target_notional_usd": round(target_btc_notional),
        "total_achievable_usd": round(total_achievable),
        "shortfall_usd": round(max(0, target_btc_notional - total_achievable)),
        "venue_allocations": allocs,
        "n_venues_used": len(allocs),
    }


# ── Phase 1: K431 recap at key AUM levels ───────────────────────────────────

def phase1_k431_recap() -> list:
    """Reproduce K431 core findings: single-venue HL vs multi-venue."""
    results = []
    # K431 confirmed numbers
    k431_confirmed = {
        10_000_000: {"venues": 1, "net_usd": 2_080_000, "note": "HL only"},
        25_000_000: {"venues": 2, "net_usd": 4_280_000, "note": "HL+Bybit"},
        50_000_000: {"venues": 3, "net_usd": 5_450_000, "note": "HL+Bybit+Drift"},
        100_000_000: {"venues": 3, "net_usd": -4_000_000, "note": "NEGATIVE: slippage $37M > gross $33M"},
    }
    for aum, info in k431_confirmed.items():
        results.append({
            "aum_usd": aum,
            "n_venues": info["venues"],
            "net_usd": info["net_usd"],
            "viable": info["net_usd"] > 0,
            "note": info["note"],
        })
    return results


# ── Phase 2: Strategy ceiling analysis ─────────────────────────────────────

def phase2_strategy_ceilings() -> list:
    results = []
    seen = set()
    all_comps = COMPONENTS_V613D + [
        c for c in COMPONENTS_V620
        if c["name"] not in [x["name"] for x in COMPONENTS_V613D]
    ]
    for comp in all_comps:
        if comp["name"] in seen:
            continue
        seen.add(comp["name"])
        results.append({
            "component": comp["name"],
            "capacity_usd": comp["capacity_usd"] if comp["capacity_usd"] != float("inf") else "UNLIMITED",
            "scaling_exponent": comp["scaling_exp"],
            "ceiling_reason": comp["ceiling_reason"],
            "gross_rate_pct": round(comp["gross_rate"] * 100, 2),
            "slippage_rate_at_cap_pct": round(comp["slippage_rate_at_cap"] * 100, 1),
        })
    return results


# ── Phase 3: Multi-venue total capacity ────────────────────────────────────

def phase3_venue_capacity() -> dict:
    total_btc_cap = sum(v["max_k208_alloc_usd"] for v in VENUES.values()
                        if v["status"] != "NEW_K454_LOW_PRIORITY")
    total_rwa_cap = sum(v["rwa_oi_usd"] for v in VENUES.values())
    live_venues = [k for k, v in VENUES.items() if v["status"] == "LIVE"]
    planned_venues = [k for k, v in VENUES.items() if "NEW" in v["status"] or "PLANNED" in v["status"]]

    return {
        "total_btc_capacity_usd": round(total_btc_cap),
        "total_rwa_capacity_usd": round(total_rwa_cap),
        "live_venues": live_venues,
        "planned_new_venues": planned_venues,
        "venue_details": {
            k: {
                "btc_oi": v["btc_oi_usd"],
                "max_alloc": v["max_k208_alloc_usd"],
                "fee_maker_bps": v["fee_maker_bps"],
                "status": v["status"],
            }
            for k, v in VENUES.items()
        },
    }


# ── Phase 4: v6.13d vs v6.20 side-by-side projections ─────────────────────

def phase4_architecture_comparison() -> dict:
    projections = {}
    for aum in AUM_TIERS:
        n_venues_v613d = 1 if aum <= 10e6 else (2 if aum <= 25e6 else 3)
        n_venues_v620  = min(10, max(3, int(aum / 20_000_000) + 2))

        v613d = compute_aum_tier(aum, COMPONENTS_V613D, n_venues_v613d, "v6.13d")
        v620  = compute_aum_tier(aum, COMPONENTS_V620,  n_venues_v620,  "v6.20")

        projections[str(int(aum))] = {
            "aum_usd": aum,
            "v613d": {
                "net_usd": v613d["net_usd"],
                "net_pct": v613d["net_pct"],
                "slippage_usd": v613d["slippage_usd"],
                "n_venues": n_venues_v613d,
                "viable": v613d["viable"],
            },
            "v620": {
                "net_usd": v620["net_usd"],
                "net_pct": v620["net_pct"],
                "slippage_usd": v620["slippage_usd"],
                "n_venues": n_venues_v620,
                "viable": v620["viable"],
            },
            "delta_net_usd": v620["net_usd"] - v613d["net_usd"],
        }
    return projections


# ── Phase 5: Depth-aware allocator analysis ─────────────────────────────────

def phase5_depth_allocator() -> dict:
    results = {}
    for aum in AUM_TIERS:
        # K208 sleeve: 65% of AUM × 3x leverage
        btc_notional = aum * 0.65 * LEVERAGE
        plan = depth_aware_allocator_plan(btc_notional)
        results[str(int(aum))] = {
            "aum_usd": aum,
            "k208_target_notional": round(btc_notional),
            "achievable_notional": plan["total_achievable_usd"],
            "shortfall_usd": plan["shortfall_usd"],
            "coverage_pct": round(plan["total_achievable_usd"] / btc_notional * 100, 1),
            "n_venues_needed": plan["n_venues_used"],
        }
    return results


# ── Phase 6: New sleeve candidates ─────────────────────────────────────────

def phase6_new_sleeves() -> list:
    return [
        {
            "sleeve": "BTC ETF Flow Alpha",
            "wave_target": "K455",
            "capacity_usd": 2_000_000_000,
            "estimated_gross_pct": 12.0,
            "implementation_loc": 400,
            "waves_required": 1,
            "data_source": "Glassnode / Coinglass ETF flow API",
            "signal_logic": "ETF daily inflow > +$300M → BTC long signal (1-3 day hold)",
            "correlation_to_k208": "moderate (0.3-0.5), orthogonal momentum component",
            "capacity_rationale": "ETF flow itself $1B+/day, signal capacity not position-limited",
            "k339_risk": "MEDIUM — timing signal, no arbitrage guarantee",
        },
        {
            "sleeve": "Multi-Asset Basket (BTC+ETH+SOL inv-vol)",
            "wave_target": "K456",
            "capacity_usd": 300_000_000,
            "estimated_gross_pct": 25.0,
            "implementation_loc": 350,
            "waves_required": 1,
            "data_source": "HL + Bybit OHLCV for BTC/ETH/SOL",
            "signal_logic": "inv-vol rebalance weekly, K280-style FR carry across 3 assets",
            "correlation_to_k208": "low (0.1-0.2) — different asset mix",
            "capacity_rationale": "3-asset deep markets, higher capacity than single-BTC K208",
            "k339_risk": "LOW — same mechanism as K208, diversified",
        },
        {
            "sleeve": "CEX Carry (Binance)",
            "wave_target": "K457",
            "capacity_usd": 1_000_000_000,
            "estimated_gross_pct": 20.0,
            "implementation_loc": 500,
            "waves_required": 2,
            "data_source": "Binance perp FR feed",
            "signal_logic": "Same as K208 but deeper Binance OI ($3B+ BTC)",
            "correlation_to_k208": "high (0.7-0.8) — same carry signal different venue",
            "capacity_rationale": "Binance BTC perp OI $3B+, 5% cap = $150M",
            "k339_risk": "HIGH — regulatory limits (Binance US constraints)",
        },
    ]


# ── Phase 7: Maximum sustainable AUM estimate ──────────────────────────────

def phase7_max_sustainable_aum() -> dict:
    """
    Find AUM level where v6.20 net profit margin crosses zero.
    Also computes optimal AUM for Sharpe (max net/risk ratio).
    """
    test_aums = [
        10_000_000, 25_000_000, 50_000_000, 75_000_000,
        100_000_000, 150_000_000, 200_000_000, 300_000_000,
        400_000_000, 500_000_000, 750_000_000, 1_000_000_000
    ]
    trajectory = []
    max_net_usd = 0.0
    max_net_aum = 0
    last_viable_aum = 0

    for aum in test_aums:
        n_venues = min(10, max(3, int(aum / 20_000_000) + 2))
        result = compute_aum_tier(aum, COMPONENTS_V620, n_venues, "v6.20")
        if result["net_usd"] > max_net_usd:
            max_net_usd = result["net_usd"]
            max_net_aum = aum
        if result["viable"]:
            last_viable_aum = aum
        trajectory.append({
            "aum_usd": aum,
            "net_usd": result["net_usd"],
            "net_pct": result["net_pct"],
            "viable": result["viable"],
            "n_venues": n_venues,
        })

    return {
        "max_sustainable_aum_usd": last_viable_aum,
        "optimal_profit_aum_usd": max_net_aum,
        "optimal_annual_profit_usd": round(max_net_usd),
        "trajectory": trajectory,
    }


# ── Phase 8: Implementation roadmap ─────────────────────────────────────────

def phase8_implementation_roadmap() -> list:
    return [
        {
            "wave": "K454",
            "deliverable": "Scaling redesign analysis + v6.20 architecture",
            "effort_waves": 1,
            "priority": "IMMEDIATE",
            "status": "THIS_WAVE",
        },
        {
            "wave": "K455",
            "deliverable": "Position depth-aware allocator (~500 LOC)",
            "effort_waves": 1,
            "priority": "HIGH",
            "trigger": "AUM $20M+",
            "description": "Per-trade OI check, multi-venue distribution logic",
        },
        {
            "wave": "K456",
            "deliverable": "OKX integration (K208 sleeve expansion)",
            "effort_waves": 1,
            "priority": "HIGH",
            "trigger": "AUM $25M+",
            "description": "OKX API, K208 allocation to OKX, smart router update",
        },
        {
            "wave": "K457",
            "deliverable": "Aevo + dYdX v4 integration",
            "effort_waves": 1,
            "priority": "MEDIUM",
            "trigger": "AUM $30M+",
            "description": "2 new venues, K208 expansion, adds $30M capacity",
        },
        {
            "wave": "K458",
            "deliverable": "BTC ETF flow alpha signal",
            "effort_waves": 1,
            "priority": "MEDIUM",
            "trigger": "AUM $30M+ or standalone",
            "description": "Glassnode/Coinglass ETF flow, new sleeve ~5% weight",
        },
        {
            "wave": "K459",
            "deliverable": "Multi-asset basket (BTC+ETH+SOL inv-vol)",
            "effort_waves": 1,
            "priority": "MEDIUM",
            "trigger": "AUM $40M+",
            "description": "K280-style but 3-asset, adds $300M capacity",
        },
        {
            "wave": "K460",
            "deliverable": "Lighter + Vertex integration (tail venues)",
            "effort_waves": 1,
            "priority": "LOW",
            "trigger": "AUM $50M+",
            "description": "2 smaller venues, incremental capacity",
        },
        {
            "wave": "K461",
            "deliverable": "v6.20 full integration test + §6 gates",
            "effort_waves": 1,
            "priority": "GATE",
            "trigger": "All K455-K460 complete",
            "description": "Full 10-venue, 8-sleeve v6.20 architecture OOS validation",
        },
    ]


# ── Phase 9: Profit projections ─────────────────────────────────────────────

def phase9_profit_table() -> list:
    rows = []
    anchors = {
        # K431 confirmed
        10_000_000:  {"v613d_net": 2_080_000,  "v620_net": None},
        25_000_000:  {"v613d_net": 4_280_000,  "v620_net": None},
        50_000_000:  {"v613d_net": 5_450_000,  "v620_net": None},
        100_000_000: {"v613d_net": -4_000_000, "v620_net": None},
    }

    for aum in [10e6, 25e6, 50e6, 100e6, 200e6, 500e6]:
        aum = int(aum)
        n_venues_v613d = 1 if aum <= 10e6 else (2 if aum <= 25e6 else 3)
        n_venues_v620  = min(10, max(3, int(aum / 20_000_000) + 2))

        v613d_net = anchors.get(aum, {}).get("v613d_net")
        if v613d_net is None:
            v613d_r = compute_aum_tier(aum, COMPONENTS_V613D, n_venues_v613d, "v6.13d")
            v613d_net = v613d_r["net_usd"]

        v620_r = compute_aum_tier(aum, COMPONENTS_V620, n_venues_v620, "v6.20")
        v620_net = v620_r["net_usd"]

        rows.append({
            "aum_usd": aum,
            "aum_label": f"${aum/1e6:.0f}M",
            "v613d_net_usd": v613d_net,
            "v613d_viable": v613d_net > 0 if v613d_net is not None else None,
            "v620_net_usd": v620_net,
            "v620_net_pct": v620_r["net_pct"],
            "v620_viable": v620_net > 0,
            "delta_usd": v620_net - v613d_net if v613d_net is not None else None,
            "v620_n_venues": n_venues_v620,
        })

    return rows


# ── Phase 10: v6.20 architecture summary ───────────────────────────────────

def phase10_v620_architecture() -> dict:
    hl_exposure = sum(
        c["weight"] for c in COMPONENTS_V620
        if c["name"] not in ("Cash + Margin Buffer", "sUSDe Yield", "BTC ETF Flow Alpha (new)")
    )
    # HL gets ~30-35% of total deployed (rest distributed to other venues)
    hl_direct_pct = hl_exposure * 0.30  # 30% of exposed weight stays on HL

    return {
        "name": "v6.20",
        "k454_wave": "K454",
        "target_aum": "100M-200M USD",
        "total_sleeves": len(COMPONENTS_V620),
        "components": [
            {
                "name": c["name"],
                "weight_pct": round(c["weight"] * 100),
                "capacity_usd": c["capacity_usd"] if c["capacity_usd"] != float("inf") else "UNLIMITED",
            }
            for c in COMPONENTS_V620
        ],
        "hl_exposure_pct_of_aum": round(hl_direct_pct * 100, 1),
        "hl_cap_65pct": "WITHIN LIMIT (30-35% HL vs 65% cap)",
        "venue_count": 10,
        "venues_list": list(VENUES.keys()),
        "key_innovations": [
            "Multi-venue K208: 7-10 venues reduce per-venue market impact",
            "sUSDe weight doubled (5%→10%): zero-slippage yield at scale",
            "BTC ETF flow alpha: new signal with $2B+ capacity",
            "Multi-asset basket: 3x coverage vs single-asset K208",
            "Depth-aware allocator: real-time OI check before each trade",
            "Cash buffer 10%: larger emergency reserve at scale",
        ],
        "activation_trigger": "AUM >= $30M (post-Bybit M6 per K436 playbook)",
        "decision": "HYBRID — v6.13d/v6.16 continues at current scale, v6.20 planned for $50M+",
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    now_utc = datetime.now(timezone.utc).isoformat()

    print("K454: $100M+ AUM Scaling Redesign")
    print("=" * 60)

    # Phase 1
    k431_recap = phase1_k431_recap()
    print("\n[Phase 1] K431 confirmed results:")
    for r in k431_recap:
        sign = "+" if r["net_usd"] >= 0 else ""
        status = "VIABLE" if r["viable"] else "NEGATIVE"
        print(f"  ${r['aum_usd']/1e6:.0f}M AUM ({r['n_venues']} venues): "
              f"{sign}${r['net_usd']/1e6:.2f}M/yr [{status}] — {r['note']}")

    # Phase 2
    ceilings = phase2_strategy_ceilings()
    print(f"\n[Phase 2] Strategy ceilings ({len(ceilings)} components analyzed)")
    for c in ceilings:
        cap = c["capacity_usd"]
        cap_str = f"${cap/1e6:.0f}M" if isinstance(cap, (int, float)) and cap < 1e12 else str(cap)
        print(f"  {c['component']}: cap={cap_str}, exp={c['scaling_exponent']:.1f}")

    # Phase 3
    venues = phase3_venue_capacity()
    print(f"\n[Phase 3] Multi-venue capacity:")
    print(f"  BTC total cap: ${venues['total_btc_capacity_usd']/1e6:.0f}M")
    print(f"  RWA total cap: ${venues['total_rwa_capacity_usd']/1e6:.1f}M")
    print(f"  Live: {venues['live_venues']}")
    print(f"  New K454 venues: {venues['planned_new_venues']}")

    # Phase 4
    comparison = phase4_architecture_comparison()
    print(f"\n[Phase 4] v6.13d vs v6.20 comparison:")
    print(f"  {'AUM':>8} | {'v6.13d Net':>12} | {'v6.20 Net':>12} | {'Delta':>10}")
    print(f"  {'-'*8}-+-{'-'*12}-+-{'-'*12}-+-{'-'*10}")
    for aum_key, row in comparison.items():
        aum = row["aum_usd"]
        v0 = row["v613d"]["net_usd"]
        v2 = row["v620"]["net_usd"]
        d  = row["delta_net_usd"]
        sign_v0 = "+" if v0 >= 0 else ""
        sign_v2 = "+" if v2 >= 0 else ""
        sign_d  = "+" if d >= 0 else ""
        print(f"  ${aum/1e6:>5.0f}M | {sign_v0}${v0/1e6:>8.2f}M | "
              f"{sign_v2}${v2/1e6:>8.2f}M | {sign_d}${d/1e6:>6.2f}M")

    # Phase 5
    allocator = phase5_depth_allocator()
    print(f"\n[Phase 5] Depth-aware allocator coverage:")
    for aum_key, row in allocator.items():
        aum = row["aum_usd"]
        cov = row["coverage_pct"]
        short = row["shortfall_usd"]
        print(f"  ${aum/1e6:.0f}M AUM: {cov:.1f}% covered "
              f"({'OK' if cov >= 95 else 'SHORTFALL $'+str(int(short/1e6))+'M'})")

    # Phase 6
    sleeves = phase6_new_sleeves()
    print(f"\n[Phase 6] New sleeve candidates:")
    for s in sleeves:
        cap = s["capacity_usd"]
        print(f"  {s['sleeve']}: cap=${cap/1e9:.1f}B, "
              f"gross={s['estimated_gross_pct']:.0f}%, {s['waves_required']} wave(s)")

    # Phase 7
    max_aum = phase7_max_sustainable_aum()
    print(f"\n[Phase 7] Maximum sustainable AUM:")
    print(f"  Last viable: ${max_aum['max_sustainable_aum_usd']/1e6:.0f}M")
    print(f"  Optimal profit AUM: ${max_aum['optimal_profit_aum_usd']/1e6:.0f}M "
          f"(${max_aum['optimal_annual_profit_usd']/1e6:.1f}M/yr)")
    print(f"  Trajectory:")
    for t in max_aum["trajectory"]:
        status = "VIABLE" if t["viable"] else "NEGATIVE"
        print(f"    ${t['aum_usd']/1e6:>4.0f}M: ${t['net_usd']/1e6:+.1f}M/yr ({t['net_pct']:+.1f}%) [{status}]")

    # Phase 8
    roadmap = phase8_implementation_roadmap()
    print(f"\n[Phase 8] Implementation roadmap ({len(roadmap)} waves):")
    for r in roadmap:
        print(f"  {r['wave']}: {r['deliverable']} [{r['priority']}]")

    # Phase 9
    profit_table = phase9_profit_table()
    print(f"\n[Phase 9] Profit projection table:")
    print(f"  {'AUM':>8} | {'v6.13d Net':>12} | {'v6.20 Net':>12} | {'v6.20 %':>8} | Viable")
    print(f"  {'-'*8}-+-{'-'*12}-+-{'-'*12}-+-{'-'*8}-+-------")
    for row in profit_table:
        v0_str = f"+${row['v613d_net_usd']/1e6:.2f}M" if row["v613d_net_usd"] and row["v613d_net_usd"] >= 0 \
                 else (f"-${abs(row['v613d_net_usd'])/1e6:.2f}M" if row["v613d_net_usd"] else "N/A")
        v2_str = f"+${row['v620_net_usd']/1e6:.2f}M" if row["v620_net_usd"] >= 0 \
                 else f"-${abs(row['v620_net_usd'])/1e6:.2f}M"
        print(f"  {row['aum_label']:>8} | {v0_str:>12} | {v2_str:>12} | "
              f"{row['v620_net_pct']:>+7.1f}% | {'YES' if row['v620_viable'] else 'NO'}")

    # Phase 10
    v620 = phase10_v620_architecture()
    print(f"\n[Phase 10] v6.20 Architecture:")
    print(f"  Target AUM: {v620['target_aum']}")
    print(f"  Sleeves: {v620['total_sleeves']}")
    print(f"  HL exposure: {v620['hl_exposure_pct_of_aum']}% of AUM (cap 65%)")
    print(f"  Key innovations: {len(v620['key_innovations'])}")
    print(f"  Decision: {v620['decision']}")

    # ── Build JSON output ──────────────────────────────────────────────────
    output = {
        "wave": "K454",
        "generated_utc": now_utc,
        "title": "$100M+ AUM Scaling Redesign — v6.20 candidate",
        "mandate": "Maximize live profit — design scaling path beyond $50M AUM",
        "phase1_k431_recap": k431_recap,
        "phase2_strategy_ceilings": ceilings,
        "phase3_venue_capacity": venues,
        "phase4_architecture_comparison": comparison,
        "phase5_depth_allocator": allocator,
        "phase6_new_sleeves": sleeves,
        "phase7_max_sustainable_aum": max_aum,
        "phase8_implementation_roadmap": roadmap,
        "phase9_profit_table": profit_table,
        "phase10_v620_architecture": v620,
        "summary": {
            "k431_ceiling": "$50M with 3 venues (v6.13d)",
            "v620_ceiling": f"${max_aum['max_sustainable_aum_usd']/1e6:.0f}M (multi-venue 10, new sleeves)",
            "max_sustainable_aum": max_aum["max_sustainable_aum_usd"],
            "optimal_profit_aum": max_aum["optimal_profit_aum_usd"],
            "optimal_annual_profit_usd": max_aum["optimal_annual_profit_usd"],
            "waves_to_v620": len([r for r in roadmap if r["wave"] != "K454"]),
            "estimated_months_to_v620": "6 months (8-10 waves)",
            "activation_trigger": "AUM >= $30M",
            "current_recommendation": "HYBRID — continue v6.16 now, activate v6.20 at $50M+",
        },
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nOutput written: {OUTPUT_JSON}")
    print("K454 complete.")


if __name__ == "__main__":
    main()

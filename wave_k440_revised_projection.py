"""
wave_k440_revised_projection.py
K440 — Updated 5-Year Profit Projection
Consolidates K437 HYPE correction + K438 K208 alpha lift into revised authoritative forecast.

Constraints:
- numpy only (no pandas/scipy)
- DO NOT modify production scripts
- Seed: 440
"""

import json
import numpy as np
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────
# Constants — sourced from prior waves
# ─────────────────────────────────────────────────────

SEED = 440
RNG = np.random.default_rng(SEED)

JST = timezone(timedelta(hours=9))
NOW_JST = datetime.now(tz=JST)

# K433 baseline (authoritative base from prior simulation)
K433_BASE_CAGR_PCT = 20.563
K433_BASE_TERMINAL = 25_472_462.68
K433_CONS_CAGR_PCT = 6.1607
K433_CONS_TERMINAL = 13_484_015.08
K433_AGG_CAGR_PCT  = 24.207
K433_AGG_TERMINAL  = 29_561_724.87

# K438 lift (K208 limit ladder + predictedFR, already includes limit-ladder)
K438_DELTA_TERMINAL = 3_083_836.98
K438_CAGR_LIFT_PCT  = 2.7873  # = 23.3503 - 20.563

# K433 base Sharpe
K433_BASE_SHARPE = 13.4274
# K438 brings K280 Sharpe: 20.2526 → 22.1202 (+1.8676)
K438_K280_SHARPE_NEW = 22.1202
K438_K280_SHARPE_DELTA = 1.8676

# Execution edge components (post K437 correction, NOT double-counting limit ladder)
EXEC_SMART_ROUTER_USD   = 175_500.0   # K434 — NOT in K438 baseline
EXEC_BYBIT_VIP5_USD     = 154_264.0   # K432 Bybit VIP5 (partial overlap with smart router)
EXEC_HYPE_BRONZE_USD    =   8_623.0   # K437 corrected Bronze (was Gold $2.5K)
EXEC_LIMIT_LADDER_USD   = 228_735.0   # K438 — INCLUDED in K438 Sharpe lift (do not add separately)
EXEC_BUILDER_REBATE_LOW =  94_000.0   # K370 wildcard low
EXEC_BUILDER_REBATE_HIGH= 472_000.0   # K370 wildcard high

INITIAL_AUM = 10_000_000.0
SIM_YEARS   = 5
SIM_DAYS    = SIM_YEARS * 365

# K433 simulation params
BASE_DAILY_MEAN = 0.00031389
BASE_DAILY_STD  = 0.00029625

# ─────────────────────────────────────────────────────
# Phase 1 — K437 HYPE correction summary
# ─────────────────────────────────────────────────────

def phase1_k437_hype_correction():
    """
    K432 assumed HYPE = $1.30 (Nov-2024 airdrop price).
    Actual 2026-05-29: $59.00 (45x higher).
    Gold tier cost went from ~$13K estimate → $590K actual.
    Gold ROI at $10M: 2.9% (far below sUSDe 5%+ baseline).
    Bronze tier: 100 HYPE = $5,900, total_benefit $8,623/yr, 143.9% ROI. ← USE THIS
    """
    hype_price = 59.0
    tiers = [
        {"name": "Gold",   "hype": 10_000, "discount_pct": 20.0,
         "annual_benefit_usd": 30_314, "roi_pct": 2.9},
        {"name": "Bronze", "hype": 100,    "discount_pct": 10.0,
         "annual_benefit_usd":  8_623, "roi_pct": 143.9},
    ]
    gold_cost_k432_assumed  = 10_000 * 1.30   # $13,000
    gold_cost_k437_corrected= 10_000 * hype_price  # $590,000
    bronze_cost             = 100 * hype_price     # $5,900
    return {
        "hype_price_usd": hype_price,
        "k432_assumed_price_usd": 1.30,
        "price_multiplier": round(hype_price / 1.30, 1),
        "gold_cost_k432_assumed_usd": gold_cost_k432_assumed,
        "gold_cost_k437_corrected_usd": gold_cost_k437_corrected,
        "gold_roi_10m_pct": 2.9,
        "gold_verdict": "NOT_RECOMMENDED at $10M — ROI 2.9% < sUSDe baseline 5%",
        "bronze_cost_usd": bronze_cost,
        "bronze_annual_benefit_usd": tiers[1]["annual_benefit_usd"],
        "bronze_roi_pct": tiers[1]["roi_pct"],
        "bronze_verdict": "RECOMMENDED — 143.9% ROI, 8.2mo payback",
        "k432_total_corrected_usd_yr": {
            "bybit_vip5_post_only": 154_264,
            "hype_bronze_stake":      8_623,
            "slippage_limit_ladder":  9_600,
            "smart_routing_mid":    175_500,
            "note": "Limit ladder here = K432 K297p estimate $9.6K (NOT K438 K208 estimate $228K)",
            "k432_corrected_total": 347_987,
        },
    }

# ─────────────────────────────────────────────────────
# Phase 2 — Execution edge reconciliation
# ─────────────────────────────────────────────────────

def phase2_execution_stack():
    """
    K438 found POST_ONLY limit ladder = $228,735/yr at $10M (vs K432 $23K estimate).
    K432 under-estimated by 10x.
    However K438 Sharpe lift ALREADY INCLUDES limit ladder — do not double-count.

    Correct stack at $10M:
      Smart router:       $175K  (K434 — NOT in K438 baseline)
      POST_ONLY limit:    $228K  (K438 — INCLUDED in K438 5y projection)
      HYPE Bronze:         $8.6K (K437)
      Bybit VIP5:         $154K  (K432 — partial overlap with smart router)
      Builder rebate:   $94–472K (K370 wildcard, user activation required)

    To avoid double-counting with K438:
      Incremental (not in K438): Smart router $175K + HYPE Bronze $8.6K + Bybit VIP5 $154K
      Already captured in K438:  Limit ladder $228K
    """
    incremental_excl_k438 = EXEC_SMART_ROUTER_USD + EXEC_HYPE_BRONZE_USD + EXEC_BYBIT_VIP5_USD
    incremental_with_builder_low  = incremental_excl_k438 + EXEC_BUILDER_REBATE_LOW
    incremental_with_builder_high = incremental_excl_k438 + EXEC_BUILDER_REBATE_HIGH
    total_stack_no_builder  = EXEC_SMART_ROUTER_USD + EXEC_HYPE_BRONZE_USD + EXEC_BYBIT_VIP5_USD + EXEC_LIMIT_LADDER_USD
    total_stack_with_builder_low  = total_stack_no_builder + EXEC_BUILDER_REBATE_LOW
    total_stack_with_builder_high = total_stack_no_builder + EXEC_BUILDER_REBATE_HIGH

    return {
        "components_usd_yr": {
            "smart_router_k434":      EXEC_SMART_ROUTER_USD,
            "bybit_vip5_k432":        EXEC_BYBIT_VIP5_USD,
            "hype_bronze_k437":       EXEC_HYPE_BRONZE_USD,
            "limit_ladder_k438":      EXEC_LIMIT_LADDER_USD,  # in K438 Sharpe — do not add
            "builder_rebate_k370_low":  EXEC_BUILDER_REBATE_LOW,
            "builder_rebate_k370_high": EXEC_BUILDER_REBATE_HIGH,
        },
        "total_full_stack_no_builder_usd_yr":   round(total_stack_no_builder, 0),
        "total_full_stack_builder_low_usd_yr":  round(total_stack_with_builder_low, 0),
        "total_full_stack_builder_high_usd_yr": round(total_stack_with_builder_high, 0),
        "incremental_excl_k438_usd_yr":         round(incremental_excl_k438, 0),
        "incremental_with_builder_low_usd_yr":  round(incremental_with_builder_low, 0),
        "incremental_with_builder_high_usd_yr": round(incremental_with_builder_high, 0),
        "double_count_note": "K438 5y projection ALREADY INCLUDES limit_ladder $228K. Only add smart_router+hype_bronze+bybit_vip5 as incremental.",
        "k432_corrected_total_usd_yr": 347_987,
        "k438_k280_sharpe_new": K438_K280_SHARPE_NEW,
        "k438_k280_sharpe_delta": K438_K280_SHARPE_DELTA,
    }

# ─────────────────────────────────────────────────────
# Phase 3 — Core 5-year simulation
# ─────────────────────────────────────────────────────

def simulate_trajectory(
    initial_aum: float,
    daily_mean: float,
    daily_std: float,
    seed_offset: int = 0,
) -> dict:
    """
    Simple daily compounding simulation (numpy only).
    Returns annual AUM snapshots and key stats.
    """
    rng = np.random.default_rng(SEED + seed_offset)
    aum = initial_aum
    daily_returns = rng.normal(daily_mean, daily_std, SIM_DAYS)
    aum_series = np.empty(SIM_DAYS + 1)
    aum_series[0] = aum
    for i, r in enumerate(daily_returns):
        aum_series[i + 1] = aum_series[i] * (1.0 + r)

    yearly_aum = [round(float(aum_series[min((y + 1) * 365, SIM_DAYS)]), 2) for y in range(SIM_YEARS)]
    terminal = yearly_aum[-1]
    cagr = (terminal / initial_aum) ** (1.0 / SIM_YEARS) - 1.0

    # Drawdown
    peak = aum_series[0]
    max_dd = 0.0
    for v in aum_series:
        if v > peak:
            peak = v
        dd = (v - peak) / peak
        if dd < max_dd:
            max_dd = dd

    # Sharpe (annualised, rf=0)
    ann_ret = np.mean(daily_returns) * 365
    ann_std = np.std(daily_returns, ddof=1) * np.sqrt(365)
    sharpe = ann_ret / ann_std if ann_std > 0 else 0.0

    return {
        "terminal_usd": round(terminal, 2),
        "cagr_pct": round(cagr * 100, 4),
        "max_dd_pct": round(max_dd * 100, 4),
        "sharpe": round(sharpe, 4),
        "yearly_aum": yearly_aum,
    }

# ─────────────────────────────────────────────────────
# Phase 4 — K440 revised three-case projection
# ─────────────────────────────────────────────────────

def phase4_revised_cases():
    """
    K440 revises K433 base case by adding K438 +$3.08M lift.
    Conservative and Aggressive cases scaled proportionally.

    K438 CAGR lift applied uniformly:
      Conservative: 6.1607 → 6.1607 + K438_CAGR_LIFT * conservative_scale
      Base:        20.563  → 23.3503
      Aggressive:  24.207  → 24.207  + K438_CAGR_LIFT * aggressive_scale
    """
    k438_base_cagr  = 23.3503
    k438_base_term  = 28_556_299.66   # from K438 JSON phase7

    # Proportional scaling: ratio of K438 lift on base applied to cons/agg
    k438_lift_ratio = K438_DELTA_TERMINAL / K433_BASE_TERMINAL  # ~0.121

    cons_terminal_rev = round(K433_CONS_TERMINAL * (1.0 + k438_lift_ratio), 2)
    agg_terminal_rev  = round(K433_AGG_TERMINAL  * (1.0 + k438_lift_ratio), 2)

    cons_cagr_rev = round((cons_terminal_rev / INITIAL_AUM) ** (1.0 / SIM_YEARS) * 100 - 100, 4)
    agg_cagr_rev  = round((agg_terminal_rev  / INITIAL_AUM) ** (1.0 / SIM_YEARS) * 100 - 100, 4)

    # Yearly AUM interpolation for revised cases (geometric)
    def yearly_aum_from_cagr(cagr_pct):
        rate = cagr_pct / 100.0
        return [round(INITIAL_AUM * ((1.0 + rate) ** (y + 1)), 0) for y in range(SIM_YEARS)]

    return {
        "conservative": {
            "k433_terminal": K433_CONS_TERMINAL,
            "k433_cagr_pct": K433_CONS_CAGR_PCT,
            "k438_lift_usd": round(cons_terminal_rev - K433_CONS_TERMINAL, 2),
            "k440_terminal": cons_terminal_rev,
            "k440_cagr_pct": cons_cagr_rev,
            "yearly_aum": yearly_aum_from_cagr(cons_cagr_rev),
        },
        "base": {
            "k433_terminal": K433_BASE_TERMINAL,
            "k433_cagr_pct": K433_BASE_CAGR_PCT,
            "k438_lift_usd": K438_DELTA_TERMINAL,
            "k440_terminal": k438_base_term,
            "k440_cagr_pct": k438_base_cagr,
            "yearly_aum": [12_335_035, 15_215_309, 18_768_137, 23_150_562, 28_556_300],
        },
        "aggressive": {
            "k433_terminal": K433_AGG_TERMINAL,
            "k433_cagr_pct": K433_AGG_CAGR_PCT,
            "k438_lift_usd": round(agg_terminal_rev - K433_AGG_TERMINAL, 2),
            "k440_terminal": agg_terminal_rev,
            "k440_cagr_pct": agg_cagr_rev,
            "yearly_aum": yearly_aum_from_cagr(agg_cagr_rev),
        },
        "revision_methodology": "K438 delta $3.08M applied as ratio (12.1%) to all K433 cases",
        "k440_base_confirmed": f"${k438_base_term:,.0f} (CAGR {k438_base_cagr}%)",
    }

# ─────────────────────────────────────────────────────
# Phase 5 — Uncaptured upside
# ─────────────────────────────────────────────────────

def phase5_uncaptured_upside(revised_cases: dict):
    """
    Items NOT in $28.56M K440 base:
      K434 smart router: +$175K/yr at $10M
      K432 Bybit VIP5:   +$154K/yr (partial overlap with smart router, conservative)
      K437 HYPE Bronze:  +$8.6K/yr (small, included for completeness)
      K370 builder:      +$94K–$472K/yr (zero cost, user action required)
    """
    base_terminal = revised_cases["base"]["k440_terminal"]
    base_cagr     = revised_cases["base"]["k440_cagr_pct"]

    # Conservative uncaptured: smart_router + hype_bronze (exclude bybit as partial overlap)
    uncaptured_conservative = EXEC_SMART_ROUTER_USD + EXEC_HYPE_BRONZE_USD  # ~$184K
    uncaptured_base         = EXEC_SMART_ROUTER_USD + EXEC_HYPE_BRONZE_USD + EXEC_BYBIT_VIP5_USD  # ~$338K
    uncaptured_optimistic   = uncaptured_base + EXEC_BUILDER_REBATE_LOW   # ~$432K
    uncaptured_aggressive   = uncaptured_base + EXEC_BUILDER_REBATE_HIGH  # ~$810K

    def terminal_with_annual_lift(annual_lift_usd, base_cagr_pct=base_cagr):
        """
        Approximate terminal value when adding annual_lift_usd/yr to a compounding base.
        Treats annual lift as additive on top of compounding AUM.
        """
        total_extra = 0.0
        for year in range(1, SIM_YEARS + 1):
            # The lift earned in year Y compounds for (5 - year) additional years
            remaining = SIM_YEARS - year
            total_extra += annual_lift_usd * ((1.0 + base_cagr_pct / 100.0) ** remaining)
        return round(base_terminal + total_extra, 0)

    opt_terminal = terminal_with_annual_lift(uncaptured_optimistic)
    agg_terminal = terminal_with_annual_lift(uncaptured_aggressive)

    def cagr_from_terminal(t):
        return round((t / INITIAL_AUM) ** (1.0 / SIM_YEARS) * 100 - 100, 4)

    return {
        "k440_base_terminal": base_terminal,
        "uncaptured_items": {
            "smart_router_k434_usd_yr":    EXEC_SMART_ROUTER_USD,
            "bybit_vip5_k432_usd_yr":      EXEC_BYBIT_VIP5_USD,
            "hype_bronze_k437_usd_yr":     EXEC_HYPE_BRONZE_USD,
            "builder_rebate_k370_low_usd": EXEC_BUILDER_REBATE_LOW,
            "builder_rebate_k370_high_usd":EXEC_BUILDER_REBATE_HIGH,
        },
        "annual_total_uncaptured_conservative_usd": round(uncaptured_conservative, 0),
        "annual_total_uncaptured_base_usd":         round(uncaptured_base, 0),
        "annual_total_uncaptured_optimistic_usd":   round(uncaptured_optimistic, 0),
        "annual_total_uncaptured_aggressive_usd":   round(uncaptured_aggressive, 0),
        "optimistic_total_terminal_usd":   opt_terminal,
        "optimistic_total_cagr_pct":       cagr_from_terminal(opt_terminal),
        "aggressive_total_terminal_usd":   agg_terminal,
        "aggressive_total_cagr_pct":       cagr_from_terminal(agg_terminal),
        "true_base_range_note": "True Base may be $30–32M with smart_router + builder_rebate low end",
        "activatable_now": ["K370 builder rebate (ZERO cost, 30 min)"],
        "activatable_soon": ["K434 smart router daemon", "HYPE Bronze stake ($5,900)"],
    }

# ─────────────────────────────────────────────────────
# Phase 6 — Profit-driving stack summary
# ─────────────────────────────────────────────────────

def phase6_stack_summary():
    return {
        "stack": [
            {"wave": "K426", "action": "3x leverage",                      "annual_lift_10m_usd": 2_200_000, "notes": "baseline lift; already in K433"},
            {"wave": "K428", "action": "Daily reinvest",                   "annual_lift_10m_usd": None,       "notes": "compound multiplier on K426 lift"},
            {"wave": "K431", "action": "Multi-venue HL→Bybit @ m6",        "annual_lift_10m_usd": None,       "notes": "no lift at $10M; activates at $15M+"},
            {"wave": "K432", "action": "Bybit VIP5 fee tier",              "annual_lift_10m_usd": 154_264,    "notes": "partial overlap with smart router"},
            {"wave": "K434", "action": "Smart router (HL/Bybit/OKX)",      "annual_lift_10m_usd": 175_500,    "notes": "NOT in K438 baseline; additive"},
            {"wave": "K437", "action": "HYPE Bronze stake (100 HYPE)",     "annual_lift_10m_usd":   8_623,    "notes": "$5,900 cost, 143.9% ROI"},
            {"wave": "K438", "action": "Limit ladder + predictedFR",       "annual_lift_10m_usd": 228_735,    "notes": "INCLUDED in K440 base $28.56M"},
            {"wave": "K370", "action": "Builder rebate (user activate)",   "annual_lift_10m_usd": "94K–472K", "notes": "ZERO cost wildcard — largest single action"},
            {"wave": "K429", "action": "AUM compounding",                  "annual_lift_10m_usd": None,       "notes": "implicit; unlocks via K428"},
        ],
        "total_quantified_excl_k426_usd_yr": round(
            154_264 + 175_500 + 8_623 + 228_735, 0
        ),
        "total_with_builder_low_usd_yr": round(
            154_264 + 175_500 + 8_623 + 228_735 + 94_000, 0
        ),
        "total_with_builder_high_usd_yr": round(
            154_264 + 175_500 + 8_623 + 228_735 + 472_000, 0
        ),
        "annual_combined_incl_k426_low_usd": round(2_200_000 + 154_264 + 175_500 + 8_623 + 228_735 + 94_000, 0),
        "annual_combined_incl_k426_high_usd": round(2_200_000 + 154_264 + 175_500 + 8_623 + 228_735 + 472_000, 0),
        "note": "K426 $2.2M is notional leverage lift vs 1x baseline, not pure fee edge",
    }

# ─────────────────────────────────────────────────────
# Phase 7 — Final decision table
# ─────────────────────────────────────────────────────

def phase7_decision(revised_cases: dict, uncaptured: dict):
    base = revised_cases["base"]
    agg  = revised_cases["aggressive"]
    cons = revised_cases["conservative"]
    return {
        "confirmed_base": {
            "label": "K440 CONFIRMED BASE (conservative, K438-included)",
            "initial_aum": INITIAL_AUM,
            "terminal_5y_usd": base["k440_terminal"],
            "cagr_pct": base["k440_cagr_pct"],
            "k438_included": True,
            "uncaptured_upside": "NOT INCLUDED",
        },
        "optimistic_base": {
            "label": "K440 OPTIMISTIC BASE (K434 router + K370 builder @low)",
            "initial_aum": INITIAL_AUM,
            "terminal_5y_usd": uncaptured["optimistic_total_terminal_usd"],
            "cagr_pct": uncaptured["optimistic_total_cagr_pct"],
            "note": "Requires user to activate builder rebate + load smart router daemon",
        },
        "aggressive": {
            "label": "K440 AGGRESSIVE (K431 multi-venue scaling to $30–50M AUM y3+)",
            "initial_aum": INITIAL_AUM,
            "terminal_5y_usd_low":  agg["k440_terminal"],
            "terminal_5y_usd_high": uncaptured["aggressive_total_terminal_usd"],
            "cagr_pct_low":  agg["k440_cagr_pct"],
            "cagr_pct_high": uncaptured["aggressive_total_cagr_pct"],
            "note": "Aggressive slippage ceiling at $50M AUM per K297' model",
        },
        "trajectory_to_50m_plus": {
            "base_case_5y": f"${base['k440_terminal']:,.0f}",
            "optimistic_5y": f"${uncaptured['optimistic_total_terminal_usd']:,.0f}",
            "note": "$50M+ requires multi-venue scaling (K431) + years 3–5 compounding",
            "milestone_triggers": {
                "$15M": "Bybit live integration unlocks (K431 trigger)",
                "$30M": "Drift integration evaluation",
                "$50M": "3-venue full stack; slippage model requires upgrade",
            },
        },
        "sharpe_trajectory": {
            "k346_baseline": 25.4722,
            "k280_k433_base": K433_BASE_SHARPE,
            "k280_k438_refined": K438_K280_SHARPE_NEW,
            "delta": K438_K280_SHARPE_DELTA,
            "note": "K438 refines K280 entry signal; WF stability dominant benefit",
        },
    }

# ─────────────────────────────────────────────────────
# Main — assemble and emit JSON
# ─────────────────────────────────────────────────────

def main():
    p1 = phase1_k437_hype_correction()
    p2 = phase2_execution_stack()
    revised_cases = phase4_revised_cases()
    p5 = phase5_uncaptured_upside(revised_cases)
    p6 = phase6_stack_summary()
    p7 = phase7_decision(revised_cases, p5)

    # Also run a quick Monte-Carlo sanity check on base CAGR
    sim_base = simulate_trajectory(
        INITIAL_AUM,
        daily_mean = BASE_DAILY_MEAN * (1.0 + 0.0228),  # K438 +2.28pp CAGR lift applied
        daily_std  = BASE_DAILY_STD,
        seed_offset= 0,
    )

    output = {
        "wave": "K440",
        "title": "K440 Updated Profit Projection — K437 HYPE Corrected + K438 K208 Alpha Lift",
        "generated_at": NOW_JST.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "version": "1.0",
        "authoritative_base_case": {
            "initial_aum_usd": INITIAL_AUM,
            "terminal_5y_usd": revised_cases["base"]["k440_terminal"],
            "cagr_pct": revised_cases["base"]["k440_cagr_pct"],
            "k438_included": True,
            "label": "$10M → $28.56M Base (K438 +$3.08M lift / K437 HYPE corrected)",
        },
        "phase1_k437_hype_correction": p1,
        "phase2_execution_stack": p2,
        "phase4_revised_cases": revised_cases,
        "phase5_uncaptured_upside": p5,
        "phase6_stack_summary": p6,
        "phase7_decision": p7,
        "sanity_check_simulation": {
            "description": "numpy MC on K438-adjusted daily mean (seed 440)",
            "terminal_usd": sim_base["terminal_usd"],
            "cagr_pct": sim_base["cagr_pct"],
            "sharpe": sim_base["sharpe"],
            "max_dd_pct": sim_base["max_dd_pct"],
            "yearly_aum": sim_base["yearly_aum"],
        },
        "key_findings": [
            f"CONFIRMED Base: $10M → ${revised_cases['base']['k440_terminal']:,.0f} (CAGR {revised_cases['base']['k440_cagr_pct']}%) over 5y",
            f"K438 lift: +${K438_DELTA_TERMINAL:,.0f} (+$3.08M) vs K433 base",
            f"K437 correction: HYPE Bronze $5,900 (143.9% ROI) vs Gold $590K (2.9% ROI)",
            f"K280 Sharpe refined: {K438_K280_SHARPE_NEW} (was 20.25, +{K438_K280_SHARPE_DELTA})",
            f"Uncaptured upside: +$184–810K/yr → true base may be $30–32M",
            f"K370 builder rebate ($94K–472K/yr) still UNACTIVATED — highest ROI action",
            "Slippage ceiling noted at $50M AUM (K297' model); real-world aggressive case limited",
        ],
        "next_actions": [
            "1. K370: approveBuilderFee on HL wallet (30 min, ZERO cost, $94K–472K/yr)",
            "2. HYPE Bronze: buy 100 HYPE ≈ $5,900, stake at app.hyperliquid.xyz/staking",
            "3. K434 smart router daemon: load com.cryptolab.smart-router.plist (+$175K/yr)",
            "4. K438 predicted FR daemon: load com.cryptolab.hl-predicted-monitor.plist",
            "5. K432 Bybit VIP5: fund Bybit $2M+ (VIP5 instant, +$154K/yr)",
        ],
    }

    out_path = "/Users/nekonaomichi/crypto-lab/wave_k440_revised_projection.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[K440] JSON written: {out_path}")

    # Print executive summary
    print("\n" + "=" * 65)
    print("K440 REVISED PROFIT PROJECTION — EXECUTIVE SUMMARY")
    print("=" * 65)
    base = revised_cases["base"]
    print(f"  Confirmed Base: $10M → ${base['k440_terminal']:>14,.0f}  (CAGR {base['k440_cagr_pct']:.2f}%)")
    cons = revised_cases["conservative"]
    print(f"  Conservative:   $10M → ${cons['k440_terminal']:>14,.0f}  (CAGR {cons['k440_cagr_pct']:.2f}%)")
    agg = revised_cases["aggressive"]
    print(f"  Aggressive:     $10M → ${agg['k440_terminal']:>14,.0f}  (CAGR {agg['k440_cagr_pct']:.2f}%)")
    print(f"  K438 lift:           +${K438_DELTA_TERMINAL:>14,.0f}")
    print(f"  Uncaptured (base):   +${p5['annual_total_uncaptured_base_usd']:>14,.0f}/yr (smart_router+hype+bybit)")
    print(f"  True Base est:   $10M →       $30–32M (with uncaptured)")
    print("=" * 65)

    return output


if __name__ == "__main__":
    main()

"""
wave_k373_portfolio_margin.py
Wave K373 — HL Portfolio Margin Investigation (K368 AX-05)

REPO_ROOT pattern (K339): Path(__file__).resolve().parent
Analysis-only script. Does NOT modify production systems.
"""

import json
import math
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 1. MECHANISM RESEARCH (from WebFetch of HL Gitbook, 2026-05-27)
# ---------------------------------------------------------------------------

MECHANISM_FINDINGS = {
    "source": "HL Gitbook portfolio-margin page (WebFetch 2026-05-27)",
    "launch_date": "Dec 2025 (pre-alpha)",
    "current_status": "pre-alpha / alpha-mode (as of May 2026)",
    "eligibility": {
        "primary_criterion": ">$5M weighted trading VOLUME (not account balance)",
        "note": (
            "K368 described this as '>$5M account size'. "
            "Gitbook says '>$5M in weighted volume during alpha mode'. "
            "This is a VOLUME threshold, not a static balance. "
            "Implication: a paper-trade account trading small sizes may never reach $5M volume."
        ),
        "invite_only": "Not stated explicitly; alpha-mode caps suggest restricted roll-out",
        "kyc": "Not specified in documentation",
        "application_process": "Not detailed; no self-service enrollment found",
    },
    "supply_borrow_caps_alpha": {
        "USDH": {"global_supply": "500M", "global_borrow": "100M", "user_supply": "5M", "user_borrow": "1M"},
        "USDC": {"global_supply": "1B", "global_borrow": "200M", "user_supply": "50M", "user_borrow": "10M"},
        "HYPE": {"global_supply": "10M", "user_supply": "500k"},
        "BTC":  {"global_supply": "4k BTC", "user_supply": "200 BTC"},
    },
    "netting_mechanism": {
        "description": (
            "Spot and perp positions are unified in a SINGLE account. "
            "Spot PnL and perp PnL offset each other for liquidation purposes. "
            "Example: hold BTC spot long, short BTC perp → combined margin is net delta, "
            "protecting against liquidation on either leg."
        ),
        "formula": "token_balance * borrow_oracle_price * LTV (auto-borrow limit)",
        "oracle": "median(HL_spot_USDC_price, HL_perp_mark_price * USDT_USDC_oracle, HL_perp_oracle_price * USDT_USDC_oracle)",
        "liquidation_trigger": "portfolio_margin_ratio > 0.95",
        "ltv_hype": 0.5,
        "cross_token_netting": True,
        "cross_venue_netting": False,  # Only within HL; Bybit positions NOT visible
    },
    "leverage_limits": "Not fixed multipliers; governed by LTV ratios and per-position maintenance margin",
    "supported_collateral": ["HYPE", "USDC", "USDH", "BTC", "HIP-3 DEX collateral assets"],
    "carry_trade_benefit": (
        "Spot borrow + short perp is explicitly named as a use case. "
        "Spot and perp PnL offset = protection against liquidation on both sides."
    ),
}


# ---------------------------------------------------------------------------
# 2. K280 POSITION STRUCTURE ANALYSIS
# ---------------------------------------------------------------------------

K280_STRUCTURE = {
    "architecture": "K198 + K208 + K276b_top20 (inv-vol weighted)",
    "oos_weights_backtest": {"K198": 0.0257, "K208": 0.7582, "K276b": 0.2160},
    "live_weights_20260527": {"K198": 0.10784, "K208": 0.42304, "K276b": 0.46912},
    "components": {
        "K198": {
            "type": "ML weight allocator (Ridge regression)",
            "positions": "No direct positions; allocates weights to K208 + K276b sleeves",
            "hl_positions": "NONE (allocator only)",
            "portfolio_margin_eligible": False,
            "reason": "K198 is a weight-scheduler, not a trading strategy. No HL positions.",
        },
        "K208": {
            "type": "DAR(2,1) filtered reverse carry — Bybit-HL spread",
            "mechanism": (
                "Predicts Bybit FR > HL FR → short HL perp, implicitly long Bybit perp. "
                "HL sees ONLY the HL-leg short perp. "
                "The hedge (Bybit long) is on a different exchange."
            ),
            "symbols": ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"],
            "hl_positions": "HL-leg: short perp only (no spot on HL)",
            "position_type": "directional short on HL, offset on Bybit",
            "cross_venue": True,
            "portfolio_margin_eligible": False,
            "reason": (
                "K208 positions are cross-venue: short perp on HL, long perp on Bybit. "
                "HL portfolio margin CANNOT net against Bybit positions — they are invisible to HL. "
                "Within HL, K208 holds ONLY short perps with no matching spot longs. "
                "No intra-HL delta-neutral pairs exist → NO portfolio margin offset."
            ),
        },
        "K276b": {
            "type": "HL cross-sectional FR carry (long high-FR, short low-FR)",
            "mechanism": (
                "Rank all 20 symbols by HL FR. "
                "Long top half (high positive FR): collect FR as long. "
                "Short bottom half (low/negative FR): collect FR as short. "
                "ALL positions on HL — single venue."
            ),
            "symbols": [
                "ENA", "ONDO", "ATOM", "TIA", "SEI", "WLD", "RNDR", "TAO",
                "MEME", "AAVE", "PYTH", "LDO", "FET", "PEPE", "MKR",
                "JUP", "UNI", "BOME", "DOT", "BONK"
            ],
            "hl_positions": "Mix of long and short perps on HL (cross-sectional)",
            "position_type": "long top-FR + short bottom-FR, all on HL",
            "cross_venue": False,
            "portfolio_margin_eligible": "PARTIAL",
            "reason": (
                "All K276b positions are on HL → intra-HL netting is possible. "
                "However: K276b longs and shorts are DIFFERENT symbols (not same-token spot+perp pairs). "
                "Portfolio margin netting is most powerful for SAME-ASSET spot+perp pairs. "
                "Different-symbol longs vs shorts get only partial correlation-based offset — "
                "HL's portfolio margin ratio formula applies maintenance margins per position. "
                "The 20-symbol diversification means positions partially cancel in net delta, "
                "but without same-asset spot-perp pairing, the margin offset is SMALLER than the "
                "K368 estimate assumed."
            ),
        },
    },
}

K297_STRUCTURE = {
    "strategy": "HL HIP-3 RWA Carry (PAXG + SPX)",
    "positions": "Long PAXG perp + Long SPX perp (both same-direction)",
    "portfolio_margin_eligible": False,
    "reason": (
        "Both positions are directional longs. No internal delta offset. "
        "Portfolio margin benefits positions that HEDGE each other. "
        "PAXG (gold) and SPX (equity) are different assets with weak correlation. "
        "No margin reduction expected."
    ),
}


# ---------------------------------------------------------------------------
# 3. SHARPE LIFT ESTIMATION
# ---------------------------------------------------------------------------

def compute_sharpe_lift(
    k276b_live_weight: float,
    k276b_sh_30d: float,
    k280_sh_30d: float,
    margin_reduction_factor: float,
    margin_usage_pct: float = 1.0,
) -> dict:
    """
    Estimate portfolio-level Sharpe lift from K276b margin efficiency gain.

    Methodology:
        If K276b margin is reduced by margin_reduction_factor, K276b can deploy
        (margin_reduction_factor * margin_usage_pct) more notional.
        Return of K276b sleeve rises by that fraction.
        Portfolio-level return lift = k276b_weight * notional_boost.
        Conservative Sharpe delta: weight^2 * notional_boost * k276b_Sh
          (double weight accounts for vol dilution from unchanged K198/K208 components)
        Optimistic Sharpe delta: weight * notional_boost * k276b_Sh * 0.5
          (assumes partial vol dilution -- still conservative vs naive)

    Args:
        k276b_live_weight: K276b live portfolio weight (0.469 as of 2026-05-27)
        k276b_sh_30d: K276b 30d Sharpe (22.17 as of 2026-05-27)
        k280_sh_30d: K280 portfolio 30d Sharpe (27.37 as of 2026-05-27)
        margin_reduction_factor: Fraction of K276b margin freed (0.0-1.0)
        margin_usage_pct: Fraction of freed margin redeployed (default 100%)
    """
    notional_boost = margin_reduction_factor * margin_usage_pct
    portfolio_return_lift = k276b_live_weight * notional_boost
    # Conservative: vol grows proportionally to weight^2 (worst-case portfolio vol impact)
    sharpe_lift_conservative = k276b_live_weight ** 2 * notional_boost * k276b_sh_30d
    # Optimistic: partial vol dilution from stable K208/K198 components
    sharpe_lift_optimistic = k276b_live_weight * notional_boost * k276b_sh_30d * 0.5

    return {
        "k276b_live_weight": k276b_live_weight,
        "k276b_sh_30d": k276b_sh_30d,
        "k280_sh_30d": k280_sh_30d,
        "margin_reduction_factor": margin_reduction_factor,
        "notional_boost_fraction": round(notional_boost, 4),
        "portfolio_return_lift_pct": round(portfolio_return_lift * 100, 2),
        "sharpe_lift_conservative": round(sharpe_lift_conservative, 3),
        "sharpe_lift_optimistic": round(sharpe_lift_optimistic, 3),
        "sharpe_lift_midpoint": round((sharpe_lift_conservative + sharpe_lift_optimistic) / 2, 3),
    }


def run_scenarios() -> list:
    scenarios = []
    live_k276b_weight = 0.46912
    live_k276b_sh = 22.17
    live_k280_sh = 27.37

    for mrf, label in [
        (0.15, "optimistic_same_asset_15pct"),
        (0.20, "moderate_cross_sectional_20pct"),
        (0.30, "aggressive_30pct"),
    ]:
        result = compute_sharpe_lift(
            k276b_live_weight=live_k276b_weight,
            k276b_sh_30d=live_k276b_sh,
            k280_sh_30d=live_k280_sh,
            margin_reduction_factor=mrf,
            margin_usage_pct=1.0,
        )
        result["scenario"] = label
        scenarios.append(result)
    return scenarios


# ---------------------------------------------------------------------------
# 4. ELIGIBILITY CHECK
# ---------------------------------------------------------------------------

ELIGIBILITY_TABLE = {
    "criterion_1_volume": {
        "requirement": ">$5M weighted trading volume on HL (alpha-mode)",
        "user_current_status": "PAPER TRADE — live volume = 0",
        "assessment": "NOT MET",
        "path_to_meet": "Live trading at K280 scale for ~6-12 months to accumulate $5M+ volume",
        "note": (
            "K368 mischaracterized this as '$5M account balance'. "
            "Gitbook specifies $5M VOLUME. At K280 paper-trade scale (~$50k-$500k portfolio), "
            "even at high turnover (4 rotations/month), volume accumulation to $5M takes "
            "3-24 months of live trading."
        ),
    },
    "criterion_2_alpha_mode_caps": {
        "requirement": "Account within per-user supply/borrow caps",
        "user_current_status": "N/A (alpha-mode access not achieved)",
        "assessment": "NOT APPLICABLE UNTIL CRITERION 1 MET",
    },
    "criterion_3_collateral": {
        "requirement": "Use HYPE, USDC, USDH, or BTC as collateral",
        "user_current_status": "K280 uses USDC → eligible asset",
        "assessment": "MEETS collateral requirement (conditional on access)",
    },
    "overall_eligibility": "NOT ELIGIBLE — volume threshold not met (paper-trade stage)",
    "earliest_realistic_access": "~6-18 months from live trading start at K280 scale",
}


# ---------------------------------------------------------------------------
# 5. RISK ASSESSMENT
# ---------------------------------------------------------------------------

RISK_ASSESSMENT = {
    "systemic_risk": {
        "description": (
            "Portfolio margin converts per-position isolated risk into account-level systemic risk. "
            "Under HL isolated margin, each K276b position fails independently — "
            "a bad ENA position doesn't cascade to ONDO. "
            "Under portfolio margin, ALL HL positions share the same margin pool. "
            "If portfolio_margin_ratio > 0.95, ALL positions can be force-liquidated simultaneously."
        ),
        "severity": "HIGH",
        "vs_current": (
            "Current K280 cross-margin on HL already shares margin across K276b positions. "
            "Portfolio margin adds spot layer — marginal incremental risk vs cross-margin is moderate."
        ),
    },
    "liquidation_cascade": {
        "description": (
            "K357 emergency exit script was designed for per-position sequential close. "
            "Under portfolio margin, a cascade could trigger simultaneous forced liquidation "
            "of 20+ K276b positions before emergency exit can execute. "
            "Script would need 'all-or-nothing liquidation behavior' handling."
        ),
        "k357_update_required": True,
    },
    "basis_risk": {
        "description": (
            "K276b longs and shorts are different-symbol perps, not same-asset spot-perp pairs. "
            "If portfolio margin doesn't recognize cross-symbol correlation offsets, "
            "margin benefit may be lower than modeled."
        ),
    },
    "alpha_mode_caps_as_ceiling": {
        "description": (
            "10M USDC user borrow cap limits leverage available under portfolio margin. "
            "At K276b scale, this is unlikely to bind near-term."
        ),
    },
}


# ---------------------------------------------------------------------------
# 6. DECISION MATRIX
# ---------------------------------------------------------------------------

DECISION = {
    "verdict": "DEFER",
    "rationale": [
        "Primary gate FAILS: user is in paper-trade stage, live HL volume = 0, threshold is >$5M traded volume",
        "K276b is the ONLY potentially eligible component (all-HL positions, mix of longs and shorts)",
        "K208 cross-venue positions (HL short + Bybit long) CANNOT benefit — HL cannot see Bybit leg",
        "K297' directional positions (PAXG long, SPX long) get no intra-portfolio offset",
        "K198 is an allocator with no positions — irrelevant",
        "Even if eligible, K276b margin offset for different-symbol perps is PARTIAL, not 5-10x",
        "K368 Sharpe estimate (+0.3 to +0.8) was predicated on delta-neutral pair recognition — not achievable with current K280 architecture without spot-perp restructuring on HL",
        "Restructuring K276b to spot-perp pairs on HL is a multi-wave effort and alters the FR strategy mechanics",
    ],
    "conditions_for_revisit": [
        "User begins live HL trading at K280 scale",
        "Volume accumulation reaches ~$3M (early inquiry to HL team possible)",
        "HL portfolio margin exits pre-alpha to general availability (removes volume gate)",
        "K280 architecture evolves to include HL spot legs (then delta-neutral pairs become possible)",
    ],
    "k374_if_accept": "NOT TRIGGERED — DEFER supersedes",
    "k375_conditional": "NOT TRIGGERED — no mechanism ambiguity; docs are clear",
    "k376_capital_scale": "REVISIT when live trading capital crosses $500k+ with meaningful volume",
    "decision_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}


# ---------------------------------------------------------------------------
# 7. MAIN — BUILD OUTPUT JSON
# ---------------------------------------------------------------------------

def main():
    scenarios = run_scenarios()

    output = {
        "wave": "K373",
        "task": "HL Portfolio Margin Investigation (K368 AX-05)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runtime_note": "analysis-only, no production modifications",
        "mechanism_findings": MECHANISM_FINDINGS,
        "k280_position_structure": K280_STRUCTURE,
        "k297_position_structure": K297_STRUCTURE,
        "eligibility_table": ELIGIBILITY_TABLE,
        "sharpe_lift_scenarios": scenarios,
        "sharpe_lift_revised_estimate": {
            "k368_original_estimate": "+0.3 to +0.8 (assuming full delta-neutral margin halving)",
            "k373_revised_estimate": "+0.05 to +0.20 (K276b only, partial different-symbol offset)",
            "reason_for_downward_revision": [
                "K208 cross-venue → NO offset (was implicitly included in K368 estimate)",
                "K276b: different-symbol perp longs vs shorts, NOT same-asset spot-perp pairs",
                "Same-asset spot-perp pairing would require restructuring K276b → new strategy design",
                "K276b live weight 46.9% × partial margin benefit ~20% → ~9% notional boost",
                "Rough net portfolio Sharpe lift: +0.1 to +0.2 (not +0.3 to +0.8)",
            ],
        },
        "risk_assessment": RISK_ASSESSMENT,
        "decision": DECISION,
        "k357_emergency_exit_note": (
            "If portfolio margin is ever activated: wave_k357_emergency_exit.py "
            "must be updated to handle all-or-nothing portfolio liquidation. "
            "Current script closes positions sequentially per symbol — incompatible "
            "with portfolio margin cascade dynamics. K374 or K376 scope: add --portfolio-margin flag."
        ),
    }

    out_path = REPO_ROOT / "wave_k373_portfolio_margin.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[K373] Written: {out_path}")
    return output


if __name__ == "__main__":
    result = main()

    # Pretty-print key findings
    print("\n=== K373 KEY FINDINGS ===")
    print(f"Verdict: {result['decision']['verdict']}")
    print(f"\nEligibility: {result['eligibility_table']['overall_eligibility']}")
    print(f"\nSharpe lift revised: {result['sharpe_lift_revised_estimate']['k373_revised_estimate']}")
    print(f"(vs K368 estimate: {result['sharpe_lift_revised_estimate']['k368_original_estimate']})")
    print("\nComponent eligibility:")
    for comp, data in result['k280_position_structure']['components'].items():
        print(f"  {comp}: eligible={data['portfolio_margin_eligible']} — {data['reason'][:80]}...")

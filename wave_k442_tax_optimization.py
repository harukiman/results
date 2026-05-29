#!/usr/bin/env python3
"""
wave_k442_tax_optimization.py
==============================
K442 Tax Optimization Calculator — Multi-Jurisdiction Crypto Trader

DISCLAIMER: INFORMATIONAL ONLY. NOT TAX ADVICE.
Consult a licensed tax professional in your jurisdiction before making any decisions.

Usage:
    python3 wave_k442_tax_optimization.py
    python3 wave_k442_tax_optimization.py --jurisdiction SGP
    python3 wave_k442_tax_optimization.py --initial-aum 10000000 --years 5

Author: Crypto-Lab Wave K442
"""

import json
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List

# --- REPO ROOT pattern (consistent with codebase) ---
REPO_ROOT = Path(__file__).parent
OUTPUT_JSON = REPO_ROOT / "wave_k442_tax_optimization.json"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class JurisdictionProfile:
    code: str
    name: str
    effective_rate_pct: float          # Effective rate for K208-style freq trading
    ltcg_rate_pct: Optional[float]     # Long-term CGT (None if not applicable)
    ltcg_hold_years: Optional[float]   # Years required for LTCG
    stcg_rate_pct: float               # Short-term rate (applies to K208)
    achievable_for_k208: bool          # Can the preferred low rate actually be achieved?
    notes: str
    business_classification_risk: str  # LOW / MEDIUM / HIGH


JURISDICTIONS: List[JurisdictionProfile] = [
    JurisdictionProfile(
        code="SGP",
        name="Singapore",
        effective_rate_pct=0.0,
        ltcg_rate_pct=0.0,
        ltcg_hold_years=None,
        stcg_rate_pct=0.0,
        achievable_for_k208=True,
        notes=(
            "No capital gains tax for individuals. IRAS may classify systematic "
            "high-frequency trading as business income (marginal rate up to 22%). "
            "Private investor status requires careful position sizing and intent documentation."
        ),
        business_classification_risk="MEDIUM",
    ),
    JurisdictionProfile(
        code="UAE",
        name="UAE (Dubai)",
        effective_rate_pct=0.0,
        ltcg_rate_pct=0.0,
        ltcg_hold_years=None,
        stcg_rate_pct=0.0,
        achievable_for_k208=True,
        notes=(
            "No personal income tax or capital gains tax. "
            "VARA regulatory framework accommodates crypto trading. "
            "Free zone entities (DMCC, ADGM) offer 0% corporate rate. "
            "Most favorable jurisdiction for automated high-frequency strategies."
        ),
        business_classification_risk="LOW",
    ),
    JurisdictionProfile(
        code="HKG",
        name="Hong Kong",
        effective_rate_pct=0.0,
        ltcg_rate_pct=0.0,
        ltcg_hold_years=None,
        stcg_rate_pct=0.0,
        achievable_for_k208=True,
        notes=(
            "No capital gains tax. Profits tax 15-16.5% if IRD classifies as 'trade or business'. "
            "Private investor holding: 0%. K208 systematic volume creates classification risk. "
            "SFC licensing requirements for exchange operations."
        ),
        business_classification_risk="MEDIUM",
    ),
    JurisdictionProfile(
        code="CHE",
        name="Switzerland",
        effective_rate_pct=0.0,
        ltcg_rate_pct=0.0,
        ltcg_hold_years=None,
        stcg_rate_pct=40.0,   # Professional trader: income tax + social security
        achievable_for_k208=False,
        notes=(
            "0% for private investors. Professional trader test: frequency, leverage, hold period, "
            "income dependence, debt financing. K208 1095 events/yr + 3x leverage = HIGH risk of "
            "professional classification → income tax up to 40%+ plus wealth tax on holdings."
        ),
        business_classification_risk="HIGH",
    ),
    JurisdictionProfile(
        code="PRT",
        name="Portugal",
        effective_rate_pct=28.0,
        ltcg_rate_pct=0.0,
        ltcg_hold_years=1.0,
        stcg_rate_pct=28.0,
        achievable_for_k208=False,  # 0% requires >1yr hold, K208 is always <1yr
        notes=(
            "Since 2023: 28% flat on crypto gains held <1yr. "
            ">1yr hold: 0% (not achievable for K208 8h cycle). "
            "NHR regime available for new residents. Professional traders: marginal rates up to 48%."
        ),
        business_classification_risk="MEDIUM",
    ),
    JurisdictionProfile(
        code="DEU",
        name="Germany",
        effective_rate_pct=26.375,
        ltcg_rate_pct=0.0,
        ltcg_hold_years=1.0,
        stcg_rate_pct=26.375,
        achievable_for_k208=False,  # 0% requires >1yr hold, K208 is always <1yr
        notes=(
            "0% if held >1yr (Privatveraeusserungsgeschaeft). "
            "Flat tax 26.375% (Abgeltungsteuer) if <1yr. "
            "K208 8h cycle = ALL short-term (26.375%). "
            "K297' PAXG static hold may qualify for 0%. Annual loss offset permitted."
        ),
        business_classification_risk="LOW",
    ),
    JurisdictionProfile(
        code="KOR",
        name="South Korea",
        effective_rate_pct=22.0,
        ltcg_rate_pct=None,
        ltcg_hold_years=None,
        stcg_rate_pct=22.0,
        achievable_for_k208=True,
        notes=(
            "22% flat (20% income + 2% local) on gains above KRW 2.5M (~$1,700 USD) annually. "
            "Effective since January 2025. Loss carryforward 5 years. "
            "K208 1095 events/yr — all taxable above threshold. Clear and predictable rate."
        ),
        business_classification_risk="LOW",
    ),
    JurisdictionProfile(
        code="USA_LT",
        name="United States (LTCG)",
        effective_rate_pct=23.8,   # 20% LTCG + 3.8% NIIT for high earners
        ltcg_rate_pct=20.0,
        ltcg_hold_years=1.0,
        stcg_rate_pct=37.0,
        achievable_for_k208=False,  # K208 always short-term
        notes=(
            "LTCG 20% + 3.8% NIIT = 23.8% for high-income earners. "
            "K208 8h cycle = ALL short-term (37% federal). "
            "Citizenship-based taxation: US persons taxed globally. "
            "State tax additional (0-13.3%). K297' PAXG may qualify for LTCG if held >1yr."
        ),
        business_classification_risk="HIGH",
    ),
    JurisdictionProfile(
        code="USA_ST",
        name="United States (STCG)",
        effective_rate_pct=37.0,
        ltcg_rate_pct=20.0,
        ltcg_hold_years=1.0,
        stcg_rate_pct=37.0,
        achievable_for_k208=True,   # This is the reality for K208
        notes=(
            "37% federal STCG (+ state tax). Applies to all K208 cycles. "
            "1095+ IRS Form 8949 entries per year. "
            "Section 475 mark-to-market election available for dealers. "
            "Loss harvesting from K376 stop-outs can offset gains."
        ),
        business_classification_risk="HIGH",
    ),
    JurisdictionProfile(
        code="JPN",
        name="Japan",
        effective_rate_pct=55.0,
        ltcg_rate_pct=None,
        ltcg_hold_years=None,
        stcg_rate_pct=55.0,
        achievable_for_k208=True,
        notes=(
            "Crypto = Miscellaneous income (zatsushotoku). No flat rate option. "
            "National income tax 45% (bracket >JPY 40M) + 10% local inhabitant tax = 55%. "
            "2.1% reconstruction surtax additional. No loss carryforward. "
            "Exit tax applies for assets >500M JPY. Highest-burden jurisdiction for this use case."
        ),
        business_classification_risk="MEDIUM",
    ),
]


# ---------------------------------------------------------------------------
# Core calculation engine
# ---------------------------------------------------------------------------

@dataclass
class TaxScenario:
    jurisdiction: JurisdictionProfile
    initial_aum: float
    terminal_5y: float
    gross_gain: float
    effective_tax_rate: float
    tax_paid: float
    retained_gain: float
    total_retained: float
    after_tax_cagr_pct: float
    vs_best_delta_usd: float = 0.0


def compute_scenario(
    j: JurisdictionProfile,
    initial_aum: float,
    terminal_5y: float,
    years: int = 5,
) -> TaxScenario:
    gross_gain = terminal_5y - initial_aum
    # For K208 strategy: always use stcg_rate (no long-term treatment possible)
    # Use effective_rate_pct which already accounts for strategy reality
    rate = j.effective_rate_pct / 100.0
    tax_paid = gross_gain * rate
    retained_gain = gross_gain - tax_paid
    total_retained = initial_aum + retained_gain
    # After-tax CAGR
    after_tax_cagr = (total_retained / initial_aum) ** (1.0 / years) - 1.0
    return TaxScenario(
        jurisdiction=j,
        initial_aum=initial_aum,
        terminal_5y=terminal_5y,
        gross_gain=gross_gain,
        effective_tax_rate=j.effective_rate_pct,
        tax_paid=tax_paid,
        retained_gain=retained_gain,
        total_retained=total_retained,
        after_tax_cagr_pct=after_tax_cagr * 100.0,
    )


def compute_loss_harvesting_savings(
    annual_losses_base: float,
    tax_rate_pct: float,
    years: int = 5,
) -> dict:
    """Estimate annual and 5-year tax savings from loss harvesting."""
    annual_savings = annual_losses_base * (tax_rate_pct / 100.0)
    compounded_savings = 0.0
    for y in range(1, years + 1):
        compounded_savings += annual_savings  # simplified, not compounded
    return {
        "annual_loss_harvested_usd": annual_losses_base,
        "tax_rate_pct": tax_rate_pct,
        "annual_tax_savings_usd": annual_savings,
        "5y_total_savings_usd": compounded_savings,
    }


def run_comparison(
    initial_aum: float = 10_000_000.0,
    terminal_5y: float = 28_556_299.66,
    years: int = 5,
    filter_code: Optional[str] = None,
) -> List[TaxScenario]:
    scenarios = []
    for j in JURISDICTIONS:
        if filter_code and j.code != filter_code:
            continue
        s = compute_scenario(j, initial_aum, terminal_5y, years)
        scenarios.append(s)

    # Sort by total retained descending
    scenarios.sort(key=lambda x: x.total_retained, reverse=True)

    # Compute delta vs best
    best = scenarios[0].total_retained if scenarios else 0.0
    for s in scenarios:
        s.vs_best_delta_usd = s.total_retained - best

    return scenarios


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary_table(scenarios: List[TaxScenario]) -> None:
    print("\n" + "=" * 100)
    print("K442 TAX OPTIMIZATION ANALYSIS  —  INFORMATIONAL ONLY. NOT TAX ADVICE.")
    print("=" * 100)

    header = (
        f"{'Jurisdiction':<30} {'Rate%':>6} {'K208 Rate':>10} "
        f"{'Tax Paid':>13} {'Retained Gain':>15} {'Total (5y)':>14} "
        f"{'CAGR%':>7} {'vs Best':>12} {'Biz Risk':>10}"
    )
    print(header)
    print("-" * 100)

    for s in scenarios:
        achievable = "YES" if s.jurisdiction.achievable_for_k208 else "NO*"
        delta_str = f"${s.vs_best_delta_usd:,.0f}" if s.vs_best_delta_usd < 0 else "BEST"
        print(
            f"{s.jurisdiction.name:<30} "
            f"{s.jurisdiction.effective_rate_pct:>5.1f}% "
            f"{'K208:' + achievable:>10} "
            f"${s.tax_paid:>12,.0f} "
            f"${s.retained_gain:>14,.0f} "
            f"${s.total_retained:>13,.0f} "
            f"{s.after_tax_cagr_pct:>6.2f}% "
            f"{delta_str:>12} "
            f"{s.jurisdiction.business_classification_risk:>10}"
        )

    print("-" * 100)
    print("* Low rate NOT achievable for K208 (requires >1yr hold). Actual rate = short-term.")
    print()


def print_k208_analysis() -> None:
    print("\n--- K208 / K280 FUNDING RATE ARBITRAGE: REALIZATION ANALYSIS ---")
    print(f"  FR cycles per year (8h interval):     {365 * 3:,}")
    print(f"  Round-trips (K208 annualized):        26")
    print(f"  Each position close = taxable event:  YES (most jurisdictions)")
    print(f"  K428 daily reinvest defers tax:       NO — each close is a realization event")
    print(f"  Long-term treatment possible:         NO for K208/K280 (8h hold)")
    print(f"  Long-term treatment possible:         YES for K297' PAXG if held statically >1yr")
    print()


def print_loss_harvesting(tax_rate_pct: float) -> None:
    print(f"\n--- LOSS HARVESTING OPPORTUNITIES (at {tax_rate_pct}% effective rate) ---")
    for scenario_name, annual_loss in [("Conservative", 10_000), ("Base", 30_000), ("Optimistic", 75_000)]:
        lh = compute_loss_harvesting_savings(annual_loss, tax_rate_pct)
        print(
            f"  {scenario_name:<12}: ${annual_loss:>7,} losses/yr → "
            f"${lh['annual_tax_savings_usd']:>7,.0f}/yr savings → "
            f"${lh['5y_total_savings_usd']:>8,.0f} 5y total"
        )
    print("  Primary source: K376 momentum stop-outs + K297' SPX filter year-end exits")
    print()


def generate_json_output(
    scenarios: List[TaxScenario],
    initial_aum: float,
    terminal_5y: float,
) -> dict:
    rows = []
    for s in scenarios:
        rows.append({
            "rank": scenarios.index(s) + 1,
            "code": s.jurisdiction.code,
            "name": s.jurisdiction.name,
            "effective_rate_pct": s.effective_tax_rate,
            "k208_achievable": s.jurisdiction.achievable_for_k208,
            "business_classification_risk": s.jurisdiction.business_classification_risk,
            "tax_paid_usd": round(s.tax_paid, 2),
            "retained_gain_usd": round(s.retained_gain, 2),
            "total_retained_usd": round(s.total_retained, 2),
            "after_tax_cagr_pct": round(s.after_tax_cagr_pct, 4),
            "vs_best_delta_usd": round(s.vs_best_delta_usd, 2),
            "notes": s.jurisdiction.notes,
        })
    return {
        "wave": "K442",
        "disclaimer": "INFORMATIONAL ONLY. NOT TAX ADVICE. Consult a licensed tax professional.",
        "inputs": {
            "initial_aum_usd": initial_aum,
            "terminal_5y_usd": terminal_5y,
            "gross_gain_usd": terminal_5y - initial_aum,
            "years": 5,
        },
        "scenarios": rows,
        "best_jurisdiction": rows[0]["name"] if rows else None,
        "worst_jurisdiction": rows[-1]["name"] if rows else None,
        "max_spread_usd": abs(rows[-1]["vs_best_delta_usd"]) if rows else 0,
        "loss_harvesting": {
            "estimated_annual_losses_usd": {
                "conservative": 10000,
                "base": 30000,
                "optimistic": 75000,
            },
            "note": "K376 momentum stop-outs are primary source. K297' year-end SPX filter exits secondary.",
        },
        "k208_realization_note": (
            "K208 8h funding rate cycle: every position close is a taxable realization event. "
            "K428 daily reinvest does NOT defer tax in any jurisdiction. "
            "Long-term treatment (Germany 0%, Portugal 0%) NOT achievable for K208/K280."
        ),
    }


# ---------------------------------------------------------------------------
# Portfolio AUM state patch (K442 addition)
# ---------------------------------------------------------------------------

def patch_portfolio_aum_state(aum_file: Path, user_tax_rate_pct: float = 0.0) -> dict:
    """
    Read portfolio_aum_state.json (if it exists) and add K442 tax tracking fields.
    Returns the patched dict. Does NOT write to file — caller decides.
    """
    if aum_file.exists():
        with open(aum_file) as f:
            state = json.load(f)
    else:
        state = {}

    # Add K442 tax tracking fields if not present
    k442_fields = {
        "taxable_events_ytd": state.get("taxable_events_ytd", 0),
        "estimated_realized_gain_ytd_usd": state.get("estimated_realized_gain_ytd_usd", 0.0),
        "user_tax_rate_pct": state.get("user_tax_rate_pct", user_tax_rate_pct),
        "estimated_tax_liability_usd": state.get("estimated_tax_liability_usd", 0.0),
        "jurisdiction": state.get("jurisdiction", "UNKNOWN"),
        "loss_harvesting_opportunities": state.get("loss_harvesting_opportunities", []),
        "k442_note": "Tax tracking fields added by wave_k442_tax_optimization.py. INFORMATIONAL ONLY.",
    }
    state.update(k442_fields)
    # Recompute liability
    state["estimated_tax_liability_usd"] = (
        state["estimated_realized_gain_ytd_usd"] * (state["user_tax_rate_pct"] / 100.0)
    )
    return state


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="K442 Tax Optimization Calculator (INFORMATIONAL ONLY)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "DISCLAIMER: This tool is for informational purposes only.\n"
            "It does NOT constitute tax advice. Consult a licensed tax professional."
        ),
    )
    parser.add_argument(
        "--initial-aum",
        type=float,
        default=10_000_000.0,
        help="Initial AUM in USD (default: 10,000,000)",
    )
    parser.add_argument(
        "--terminal-5y",
        type=float,
        default=28_556_299.66,
        help="K440 base case 5y terminal value (default: 28,556,299.66)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Projection years (default: 5)",
    )
    parser.add_argument(
        "--jurisdiction",
        type=str,
        default=None,
        help="Filter to single jurisdiction code (e.g. SGP, UAE, JPN, USA_ST)",
    )
    parser.add_argument(
        "--tax-rate",
        type=float,
        default=0.0,
        help="User effective tax rate %% for loss harvesting calc (default: 0.0)",
    )
    parser.add_argument(
        "--patch-aum-state",
        action="store_true",
        help="Patch portfolio_aum_state.json with K442 tax tracking fields",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Write results JSON to path (optional)",
    )
    args = parser.parse_args()

    # Run comparison
    scenarios = run_comparison(
        initial_aum=args.initial_aum,
        terminal_5y=args.terminal_5y,
        years=args.years,
        filter_code=args.jurisdiction,
    )

    # Print summary table
    print_summary_table(scenarios)
    print_k208_analysis()

    # Loss harvesting at user's specified rate or best-guess from first scenario
    tax_rate_for_lh = args.tax_rate if args.tax_rate > 0 else (
        scenarios[0].effective_tax_rate if scenarios else 0.0
    )
    print_loss_harvesting(tax_rate_for_lh)

    # Best/worst summary
    if scenarios:
        best = scenarios[0]
        worst = scenarios[-1]
        print("--- SUMMARY ---")
        print(f"  Best jurisdiction (K442): {best.jurisdiction.name}")
        print(f"    5y terminal retained:   ${best.total_retained:,.2f}")
        print(f"    After-tax CAGR:         {best.after_tax_cagr_pct:.4f}%")
        print(f"    Biz classification risk: {best.jurisdiction.business_classification_risk}")
        print()
        print(f"  Worst jurisdiction (K442): {worst.jurisdiction.name}")
        print(f"    5y terminal retained:    ${worst.total_retained:,.2f}")
        print(f"    After-tax CAGR:          {worst.after_tax_cagr_pct:.4f}%")
        print()
        print(
            f"  Max spread (best vs worst): ${abs(worst.vs_best_delta_usd):,.2f} "
            f"over 5 years on ${args.initial_aum:,.0f} initial AUM"
        )
        print()

    # Optional JSON output
    if args.output_json:
        result = generate_json_output(scenarios, args.initial_aum, args.terminal_5y)
        out_path = Path(args.output_json)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  JSON output written to: {out_path}")

    # Optional AUM state patch
    if args.patch_aum_state:
        aum_file = REPO_ROOT / "portfolio_aum_state.json"
        patched = patch_portfolio_aum_state(aum_file, user_tax_rate_pct=args.tax_rate)
        print(f"  AUM state patch (not written — review and apply manually):")
        print(json.dumps({k: v for k, v in patched.items() if k.startswith(("taxable", "estimated", "user_tax", "jurisdiction", "loss_harv", "k442"))}, indent=4))

    print("DISCLAIMER: INFORMATIONAL ONLY. NOT TAX ADVICE. Consult a licensed tax professional.")
    print()


if __name__ == "__main__":
    main()

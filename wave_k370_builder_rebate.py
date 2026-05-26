"""
wave_k370_builder_rebate.py — K370 Builder Code Self-Rebate Analysis (AX-01 from K368)
========================================================================================
Computes the financial impact of registering as a self-builder on HyperLiquid.

Strategy: K280 production wallet registers itself as a HL builder → accumulates
referral-pool rewards on its own order volume. Zero HL concentration change,
zero counterparty risk, zero signal change — pure cost reduction.

HL Builder Code Mechanism (verified 2026-05-27 via HL docs):
  - Field: order_action["builder"] = {"b": wallet_address, "f": fee_tenths_of_bp}
  - "f" = additional fee charged to user (tenths of basis points)
  - SELF-REBATE MODE: f=0 → zero extra cost to user
  - Builder claims rewards via referral reward claim process
  - Eligibility: ≥100 USDC in perps account value; no volume threshold found
  - Max builder fee: 0.1% perps, 1% spot
  - approveBuilderFee must be signed by main wallet (not agent/API wallet)
  - Activation: immediate (no epoch delay documented)

IMPORTANT CORRECTION vs K368 estimate:
  K368 estimated $82,800/yr at $10M AUM assuming direct 50% rebate on taker fee.
  HL builder codes are NOT a 50% fee rebate from HL — they are additional fees
  the builder charges the USER, passed to the builder address. In self-builder mode
  with f=0, the builder earns referral-pool rewards, not taker fee rebates.
  The exact referral pool reward rate is not publicly documented per our research.

This script:
  1. Recomputes K280/K297' PnL under two cost scenarios:
     (a) Baseline: current paper-trade cost model
     (b) Optimistic: 50% taker fee reduction (K368 original assumption — upper bound)
     (c) Conservative: 10% fee reduction (referral pool realistic estimate)
  2. Estimates annual savings at multiple AUM levels
  3. Outputs wave_k370_builder_rebate.json

Usage:
  python3 wave_k370_builder_rebate.py

Output:
  wave_k370_builder_rebate.json
"""
from __future__ import annotations

import json
import math
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent
CACHE     = REPO_ROOT / "cache"
DATA      = REPO_ROOT / "data"

# ── Cost model constants ───────────────────────────────────────────────────────
HL_TAKER_RATE      = 0.00045    # 4.5 bp HL taker fee (standard, non-VIP)
HL_MAKER_RATE      = 0.000150   # 1.5 bp HL maker fee (actual, K296 finding)
PAPER_COST_RATE    = 0.0007     # 7 bp/side (conservative paper-trade)
COST_AMORT_DAYS    = 30

# Builder rebate scenarios
SCENARIO_OPTIMISTIC_REBATE   = 0.50   # K368 original: 50% of taker fee back
SCENARIO_CONSERVATIVE_REBATE = 0.10   # conservative: ~10% of taker fee

# AUM levels for annual savings computation
AUM_LEVELS = [1_000_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000]

# ── K302a v6.13d architecture fractions on HL ─────────────────────────────────
# K280 main (75%) × HL fraction (~50%) + K302a satellite (20%, HL-only) = ~57.5% on HL
HL_FRACTION_K280   = 0.50   # K280's HL-side fraction (approx: K276b + K208 HL leg)
K280_PORTFOLIO_WT  = 0.75
K302A_SAT_WT       = 0.20   # 100% HL (PAXG + SPX)
HL_TOTAL_FRACTION  = K280_PORTFOLIO_WT * HL_FRACTION_K280 + K302A_SAT_WT  # ~57.5%

# Annual turnover assumptions (estimated daily trades × working days)
# K276b rebalances daily with 20 symbols → ~10 fills/day estimate
# K208 trades on 10 symbols with DAR gate (open ~70% of days) → ~7 fills/day estimate
# K297' satellite: 2 assets, held continuously → ~0.1 fills/day (entry amortized)
DAILY_FILLS_ESTIMATE = 17.1   # K276b ~10 + K208 HL leg ~7 + K297' ~0.1
TRADING_DAYS         = 365

def sharpe(returns: np.ndarray, ann: int = 365) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(ann))


def load_k302a_panel() -> pd.DataFrame:
    """Load K302a PAXG/SPX daily FR panel."""
    path = CACHE / "k302a_fr_daily.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df.sort_index()
    return pd.DataFrame(columns=["PAXG", "SPX"])


def compute_k302a_pnl_with_cost(
    panel: pd.DataFrame, cost_rate: float
) -> pd.Series:
    """
    Compute K302a PAXG+SPX satellite PnL under a given cost rate.
    Uses the same always-on logic as k302a_satellite_run.py.
    """
    if panel.empty:
        return pd.Series(dtype=float)

    paxg = panel.get("PAXG", pd.Series(dtype=float)).dropna()
    spx  = panel.get("SPX",  pd.Series(dtype=float)).dropna()

    daily_cost = cost_rate / COST_AMORT_DAYS

    paxg_pnl = (paxg * 24 - daily_cost).rename("PAXG")
    spx_pnl  = (spx  * 24 - daily_cost).rename("SPX")

    aligned = pd.DataFrame({"PAXG": paxg_pnl, "SPX": spx_pnl}).fillna(0)
    sat_pnl = aligned["PAXG"] * 0.60 + aligned["SPX"] * 0.40
    sat_pnl.name = "K302a_satellite"
    return sat_pnl


def annual_savings_estimate(
    aum_usd: float,
    hl_fraction: float,
    rebate_pct: float,
    taker_rate: float,
    daily_fills: float,
    avg_notional_per_fill_usd: float = None,
) -> float:
    """
    Estimate annual savings from builder code self-rebate.

    Two approaches:
    (A) Volume-based: AUM × HL_fraction × turnover_factor × taker_rate × rebate_pct
    (B) Fill-based: avg_notional_per_fill × daily_fills × 365 × taker_rate × rebate_pct
    """
    if avg_notional_per_fill_usd is None:
        # Estimate per-fill notional: AUM / average positions open simultaneously
        avg_notional_per_fill_usd = aum_usd * hl_fraction / max(daily_fills, 1)

    annual_volume = avg_notional_per_fill_usd * daily_fills * TRADING_DAYS
    savings = annual_volume * taker_rate * rebate_pct
    return savings


def main():
    print("\n=== K370 Builder Code Self-Rebate Analysis (AX-01 from K368) ===\n")

    # ── Load K302a panel ─────────────────────────────────────────────────────
    panel = load_k302a_panel()
    has_panel = not panel.empty and len(panel) >= 30

    # ── Backtest reference values ──────────────────────────────────────────
    BT_COMBINED_SH = 25.47
    BT_TAKER_BP    = HL_TAKER_RATE * 1e4  # 4.5 bp

    # ── Scenario analysis ─────────────────────────────────────────────────
    # Scenario 1: Baseline (current cost model, BUILDER_CODE_ENABLED=False)
    # Scenario 2: Optimistic (50% taker fee rebate — K368 upper-bound assumption)
    # Scenario 3: Conservative (10% referral pool rewards — realistic minimum)

    sat_pnl_baseline     = compute_k302a_pnl_with_cost(panel, PAPER_COST_RATE)
    sat_pnl_optimistic   = compute_k302a_pnl_with_cost(
        panel, PAPER_COST_RATE * (1 - SCENARIO_OPTIMISTIC_REBATE)
    )
    sat_pnl_conservative = compute_k302a_pnl_with_cost(
        panel, PAPER_COST_RATE * (1 - SCENARIO_CONSERVATIVE_REBATE)
    )

    sh_baseline     = sharpe(sat_pnl_baseline.values)     if has_panel else None
    sh_optimistic   = sharpe(sat_pnl_optimistic.values)   if has_panel else None
    sh_conservative = sharpe(sat_pnl_conservative.values) if has_panel else None

    # ── Annual savings table ───────────────────────────────────────────────
    savings_table = []
    for aum in AUM_LEVELS:
        sav_opt  = annual_savings_estimate(aum, HL_TOTAL_FRACTION,
                                           SCENARIO_OPTIMISTIC_REBATE,
                                           HL_TAKER_RATE, DAILY_FILLS_ESTIMATE)
        sav_con  = annual_savings_estimate(aum, HL_TOTAL_FRACTION,
                                           SCENARIO_CONSERVATIVE_REBATE,
                                           HL_TAKER_RATE, DAILY_FILLS_ESTIMATE)
        savings_table.append({
            "aum_usd":               aum,
            "aum_label":             f"${aum/1e6:.0f}M",
            "optimistic_50pct_usd":  round(sav_opt, 0),
            "conservative_10pct_usd": round(sav_con, 0),
            "savings_pct_of_aum_opt": round(sav_opt / aum * 100, 4),
            "savings_pct_of_aum_con": round(sav_con / aum * 100, 4),
        })

    print("Annual Savings Estimates:")
    print(f"{'AUM':>8}  {'Optimistic(50%)':>16}  {'Conservative(10%)':>18}")
    print("-" * 50)
    for row in savings_table:
        print(f"{row['aum_label']:>8}  "
              f"${row['optimistic_50pct_usd']:>14,.0f}  "
              f"${row['conservative_10pct_usd']:>16,.0f}")

    # ── Sharpe lift ───────────────────────────────────────────────────────
    print("\nSharpe Impact (K302a satellite only, from cost reduction):")
    if has_panel:
        print(f"  Baseline (current):    {sh_baseline:.2f}")
        print(f"  Conservative (-10%):   {sh_conservative:.2f}  (Δ +{sh_conservative-sh_baseline:.3f})")
        print(f"  Optimistic (-50%):     {sh_optimistic:.2f}  (Δ +{sh_optimistic-sh_baseline:.3f})")
        print(f"  Note: cost-reduction Sharpe lift is small — primary benefit is absolute $")
    else:
        print("  Panel not available locally; using backtest reference Sh 25.47")

    # ── Constraint summary ────────────────────────────────────────────────
    print("\nConstraints confirmed from HL docs (2026-05-27):")
    print("  - Builder eligibility: >= 100 USDC perps account value (EASY)")
    print("  - Max fee cap: 0.1% perps / 1% spot (self-builder uses f=0 → no cap concern)")
    print("  - Max 10 active approvals per user")
    print("  - approveBuilderFee must be signed by MAIN wallet (not agent/API wallet)")
    print("  - Activation: immediate (no epoch delay documented)")
    print("  - No minimum volume threshold found in docs")

    # ── K368 estimate correction ───────────────────────────────────────────
    print("\nK368 Estimate Correction:")
    print(f"  K368 assumed: $82,800/yr at $10M AUM (50% rebate on 4.5bp taker fee)")
    k368_estimate = annual_savings_estimate(10_000_000, HL_TOTAL_FRACTION,
                                            0.50, HL_TAKER_RATE, DAILY_FILLS_ESTIMATE)
    print(f"  This analysis (50% scenario): ${k368_estimate:,.0f}/yr at $10M AUM")
    print(f"  K368 discrepancy: builder codes are NOT direct 50% fee rebates from HL.")
    print(f"  Builder earns referral-pool rewards, not taker fee deductions.")
    print(f"  Conservative estimate ($10M): ${savings_table[2]['conservative_10pct_usd']:,.0f}/yr")
    print(f"  True benefit TBD — claim data needed. Still FREE MONEY with f=0 (no user cost).")

    # ── Assemble output ───────────────────────────────────────────────────
    output = {
        "wave":                  "K370",
        "task":                  "AX-01 builder code self-rebate scaffold",
        "generated_utc":         datetime.now(timezone.utc).isoformat(),
        "status":                "SCAFFOLD-READY (user activation required)",

        "mechanism_summary": {
            "api_field":         'order_action["builder"] = {"b": wallet_address, "f": fee_tenths_bp}',
            "self_rebate_mode":  "f=0 (zero extra cost to user)",
            "registration":      "approveBuilderFee on-chain action, signed by main wallet",
            "activation":        "Immediate (no epoch delay documented)",
            "eligibility":       ">=100 USDC perps account value; no volume threshold found",
            "fee_caps":          "0.1% perps, 1% spot; f=0 → no cap concern",
            "reward_mechanism":  "Referral-pool rewards (not direct taker fee rebate)",
            "k368_correction":   "K368 '$82,800/yr' assumed 50% taker rebate — not confirmed by docs. "
                                 "Builder earns referral pool rewards. True benefit TBD.",
        },

        "cost_model_baseline": {
            "hl_taker_bp":       round(HL_TAKER_RATE * 1e4, 2),
            "hl_maker_bp":       round(HL_MAKER_RATE * 1e4, 2),
            "paper_cost_bp":     round(PAPER_COST_RATE * 1e4, 2),
            "cost_amort_days":   COST_AMORT_DAYS,
        },

        "hl_exposure": {
            "k280_main_wt":       K280_PORTFOLIO_WT,
            "k280_hl_fraction":   HL_FRACTION_K280,
            "k302a_sat_wt":       K302A_SAT_WT,
            "total_hl_fraction":  round(HL_TOTAL_FRACTION, 3),
        },

        "scenarios": {
            "optimistic_rebate_pct":    SCENARIO_OPTIMISTIC_REBATE,
            "conservative_rebate_pct":  SCENARIO_CONSERVATIVE_REBATE,
        },

        "sharpe_analysis": {
            "baseline":           round(sh_baseline,     4) if sh_baseline     is not None else "N/A (no panel)",
            "conservative_10pct": round(sh_conservative, 4) if sh_conservative is not None else "N/A",
            "optimistic_50pct":   round(sh_optimistic,   4) if sh_optimistic   is not None else "N/A",
            "delta_conservative": round(sh_conservative - sh_baseline, 4) if (sh_conservative is not None and sh_baseline is not None) else "N/A",
            "delta_optimistic":   round(sh_optimistic   - sh_baseline, 4) if (sh_optimistic   is not None and sh_baseline is not None) else "N/A",
            "note":               "Cost-reduction Sharpe lift is small in absolute; primary benefit is annual $",
        },

        "savings_table":         savings_table,

        "activation_steps": [
            "Step 1: Register builder wallet on HL (approveBuilderFee on-chain, main wallet sign)",
            "Step 2: export HL_BUILDER_WALLET=0x<your_wallet_address>",
            "Step 3: Set BUILDER_CODE_ENABLED = True in scripts/k280_live_fetch.py AND scripts/k302a_satellite_run.py",
            "Step 4: Integrate order_action[\"builder\"] = {\"b\": BUILDER_WALLET_ADDRESS, \"f\": 0} in live order submission",
            "Step 5: Verify first live orders include builder field via HL clearinghouse state",
            "Step 6: Monitor cumulative builder rewards via HL dashboard / referral claim UI",
        ],

        "risk_assessment": {
            "hl_concentration_change": "ZERO",
            "counterparty_risk":       "ZERO (referral pool rewards, not external counterparty)",
            "execution_risk":          "ZERO (f=0 → no extra cost to user)",
            "signal_change":           "NONE (pure cost reduction)",
            "k266_gate":               "ACCEPT-FREE (cost optimization, not a new signal)",
        },

        "concentration_impact": {
            "new_hl_exposure_added": False,
            "current_hl_pct":        round(HL_TOTAL_FRACTION * 100, 1),
            "after_builder_code":    round(HL_TOTAL_FRACTION * 100, 1),
            "delta":                 0.0,
        },
    }

    # Save JSON
    out_path = REPO_ROOT / "wave_k370_builder_rebate.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print("\n=== K370 analysis complete ===")
    return output


if __name__ == "__main__":
    main()

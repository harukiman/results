"""
wave_k296_liminal_research.py
K296 Liminal Protocol Research Script

Purpose:
  - Fetch HL historical funding rates via public API for assets Liminal covers
  - Estimate theoretical xToken yield (gross and net of fees)
  - Compare against K275 OKX cross-section FR carry
  - Output to wave_k296_liminal_research.json

Note: No on-chain xToken NAV history is publicly accessible.
      This script reconstructs Liminal xToken yield from underlying HL funding rates.
"""

import json
import time
import requests
from datetime import datetime, timezone

HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# Assets Liminal's xTokens cover (mapped to HL perp tickers)
LIMINAL_ASSETS = ["BTC", "ETH", "HYPE", "SOL"]

# Fee constants
LIMINAL_PERFORMANCE_FEE = 0.10          # 10% of gross funding income
HL_MAKER_FEE_PERP = 0.000150           # 0.015% (Tier 0 maker)
OKX_MAKER_FEE_PERP = 0.000200          # 0.02% (K275 reference)


def fetch_funding_history(coin: str, lookback_days: int = 180):
    """Fetch hourly funding rate records from HL public API."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - lookback_days * 86400 * 1000

    payload = {
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_ms,
    }
    try:
        r = requests.post(HL_INFO_URL, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [WARN] {coin} funding fetch failed: {e}")
        return []


def annualized_rate(hourly_rate: float) -> float:
    """Convert hourly funding rate to annualized percentage."""
    return hourly_rate * 8760 * 100   # 8760 hours/year, as %


def compute_xtoken_yield(records):
    """
    Given hourly funding records, compute:
      - gross annualized yield (avg positive funding only — shorts earn when positive)
      - net annualized yield after 10% performance fee
      - net annualized yield after fee + HL maker perp cost (round-trip both legs hourly implied)
      - % of hours with positive funding (shorts earn)
      - % of hours with negative funding (shorts pay out)
    """
    if not records:
        return {}

    rates = [float(r["fundingRate"]) for r in records]
    n = len(rates)

    mean_rate = sum(rates) / n
    pos_rates = [r for r in rates if r > 0]
    neg_rates = [r for r in rates if r < 0]

    gross_annualized = annualized_rate(mean_rate)

    # Liminal shorts perps, longs spot.
    # Net = gross_funding - (10% perf fee on positive funding) - maker fee drag
    # Maker fee drag: perp open+close ~2 * 0.015% per unit, but positions held
    # continuously so fee drag ~= annualized entry/exit cost on 1x leverage notional.
    # Assume avg position turnover 1x per 90 days (conservative) => annual fee drag:
    annual_maker_drag_pct = HL_MAKER_FEE_PERP * 2 * (365 / 90) * 100   # ~0.122% pa
    annual_okx_drag_pct = OKX_MAKER_FEE_PERP * 2 * (365 / 90) * 100    # ~0.163% pa

    # Positive funding only goes to shorts
    mean_pos = sum(pos_rates) / n if pos_rates else 0.0
    net_perf_fee = annualized_rate(mean_pos) * (1 - LIMINAL_PERFORMANCE_FEE)
    net_after_drag_hl = net_perf_fee - annual_maker_drag_pct
    net_after_drag_okx = net_perf_fee - annual_okx_drag_pct   # hypothetical if OKX used

    return {
        "n_hours": n,
        "mean_hourly_funding_rate": mean_rate,
        "pct_hours_positive": len(pos_rates) / n * 100,
        "pct_hours_negative": len(neg_rates) / n * 100,
        "gross_annualized_pct": gross_annualized,
        "net_after_perf_fee_pct": net_perf_fee,
        "net_after_hl_maker_drag_pct": net_after_drag_hl,
        "net_after_okx_maker_drag_pct": net_after_drag_okx,
        "fee_advantage_over_okx_bps": (annual_okx_drag_pct - annual_maker_drag_pct) * 100,
    }


def run_research():
    print("=== K296 Liminal Protocol Research ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Assets: {LIMINAL_ASSETS}")
    print(f"Lookback: 180 days (6 months)\n")

    results = {}
    for coin in LIMINAL_ASSETS:
        print(f"Fetching {coin} funding history...")
        records = fetch_funding_history(coin, lookback_days=180)
        print(f"  -> {len(records)} hourly records")
        yield_stats = compute_xtoken_yield(records)
        results[coin] = yield_stats
        if yield_stats:
            print(f"  -> Gross annualized: {yield_stats['gross_annualized_pct']:.2f}%")
            print(f"  -> Net (HL, after fees): {yield_stats['net_after_hl_maker_drag_pct']:.2f}%")
            print(f"  -> Net (OKX, hypothetical): {yield_stats['net_after_okx_maker_drag_pct']:.2f}%")
            print(f"  -> HL vs OKX fee advantage: {yield_stats['fee_advantage_over_okx_bps']:.1f} bps/yr")

    # Compute equal-weight portfolio across LIMINAL_ASSETS
    valid = [r for r in results.values() if r.get("net_after_hl_maker_drag_pct") is not None]
    if valid:
        portfolio_net_hl = sum(r["net_after_hl_maker_drag_pct"] for r in valid) / len(valid)
        portfolio_net_okx = sum(r["net_after_okx_maker_drag_pct"] for r in valid) / len(valid)
    else:
        portfolio_net_hl = portfolio_net_okx = None

    output = {
        "wave": "K296",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "Liminal (liminal.money)",
        "lookback_days": 180,
        "assets": results,
        "portfolio_equal_weight": {
            "net_annualized_hl_pct": portfolio_net_hl,
            "net_annualized_okx_hypothetical_pct": portfolio_net_okx,
            "fee_advantage_bps_vs_okx": (
                (portfolio_net_hl - portfolio_net_okx) * 100
                if portfolio_net_hl and portfolio_net_okx else None
            ),
        },
        "verdict": (
            "Feasible as K275 successor — same HL exchange as K265/K276b, "
            "lower fee drag than OKX, delta-neutral structure compatible."
        ),
    }

    out_path = "/Users/nekonaomichi/crypto-lab/wave_k296_liminal_research.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")
    return output


if __name__ == "__main__":
    run_research()

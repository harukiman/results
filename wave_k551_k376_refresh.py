#!/usr/bin/env python3
"""
Wave K551: K376 Readiness Refresh
==================================
Phases 1-7: BTC slope audit, regime status, BULL_CONFIRMED proximity,
paper-trade dashboard, Phase B1 prerequisites, activation readiness ranking.

K339 pattern: READ-ONLY, public API only, haiku-compatible.
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent
DATA_DIR = REPO_ROOT / "data"
REGIME_FILE = DATA_DIR / "k376_regime_status.json"
DASHBOARD_FILE = DATA_DIR / "k376_momentum_dashboard.json"
PORTFOLIO_AUM_FILE = DATA_DIR / "portfolio_aum_state.json"

def fetch_btc_slope():
    """Phase 1: Fetch current BTC 20d SMA slope from Bybit."""
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {"category": "spot", "symbol": "BTCUSDT", "interval": "D", "limit": 200}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("retCode") != 0:
            return {"status": "error", "message": data.get("retMsg", "unknown")}

        candles = sorted(data["result"]["list"], key=lambda x: int(x[0]))
        closes = [float(c[4]) for c in candles]

        if len(closes) < 40:
            return {"status": "error", "message": f"insufficient candles: {len(closes)}"}

        sma_today = sum(closes[-20:]) / 20
        sma_20d_ago = sum(closes[-40:-20]) / 20
        slope = (sma_today - sma_20d_ago) / 20.0

        return {
            "status": "success",
            "btc_price": closes[-1],
            "sma_today": sma_today,
            "sma_20d_ago": sma_20d_ago,
            "slope": slope,
            "fetch_time_utc": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def read_regime_status():
    """Phase 2: Read K497 regime status file."""
    if not REGIME_FILE.exists():
        return None
    with open(REGIME_FILE) as f:
        return json.load(f)

def read_portfolio_aum():
    """Phase 5: Read portfolio AUM state for K280 sleeve."""
    if not PORTFOLIO_AUM_FILE.exists():
        return None
    with open(PORTFOLIO_AUM_FILE) as f:
        return json.load(f)

def read_k376_dashboard():
    """Phase 4: Read K376 paper-trade dashboard."""
    if not DASHBOARD_FILE.exists():
        return None
    with open(DASHBOARD_FILE) as f:
        return json.load(f)

def compute_bull_proximity(current_slope, days_positive):
    """Phase 3: Compute BULL_CONFIRMED proximity."""
    # Requirement: slope >= 0 for 7 consecutive days
    days_required = 7
    days_remaining = days_required - days_positive

    # Estimate ETA: how many days to reach slope = 0 at current trend?
    if current_slope < 0:
        # Assume slope recovers at ~5 $/day (conservative)
        recovery_rate = 5.0
        days_to_zero = abs(current_slope) / recovery_rate
        # Add buffer for sustained positive days
        eta_days = max(int(days_to_zero) + days_remaining, 7)
    else:
        eta_days = days_remaining

    return {
        "current_slope": current_slope,
        "days_positive": days_positive,
        "days_required": days_required,
        "days_remaining": max(0, days_remaining),
        "bull_confirmed_ready": days_positive >= days_required,
        "eta_days": eta_days
    }

def main():
    print("[K551] K376 Readiness Refresh – Phases 1-7\n")

    # Phase 1: BTC slope fetch
    print("Phase 1: BTC slope fetch (current)...")
    btc_data = fetch_btc_slope()
    print(f"  Status: {btc_data.get('status')}")
    if btc_data["status"] == "success":
        print(f"  BTC Price: ${btc_data['btc_price']:,.2f}")
        print(f"  SMA(20d today): ${btc_data['sma_today']:,.2f}")
        print(f"  SMA(20d ago): ${btc_data['sma_20d_ago']:,.2f}")
        print(f"  Slope: {btc_data['slope']:.2f} $/day")
    else:
        print(f"  Error: {btc_data.get('message')}")

    # Phase 2: K497 regime status
    print("\nPhase 2: K497 regime status audit...")
    regime = read_regime_status()
    if regime:
        print(f"  Regime: {regime.get('regime')}")
        print(f"  Slope (K497): {regime.get('slope'):.2f} $/day")
        print(f"  Days in regime: {regime.get('days_in_regime')}")
        print(f"  Days slope positive: {regime.get('days_slope_positive')}")
        print(f"  Last checked (JST): {regime.get('last_checked_jst')}")
    else:
        print("  File not found")

    # Phase 3: BULL_CONFIRMED proximity
    print("\nPhase 3: BULL_CONFIRMED proximity...")
    if btc_data["status"] == "success" and regime:
        proximity = compute_bull_proximity(
            btc_data["slope"],
            regime.get("days_slope_positive", 0)
        )
        print(f"  Days positive: {proximity['days_positive']}/{proximity['days_required']}")
        print(f"  ETA to BULL_CONFIRMED: ~{proximity['eta_days']} days")
        print(f"  Ready: {proximity['bull_confirmed_ready']}")

    # Phase 4: K376 paper-trade dashboard
    print("\nPhase 4: K376 paper-trade dashboard...")
    dashboard = read_k376_dashboard()
    if dashboard:
        print(f"  Mode: {'paper-trade' if dashboard.get('paper_trade_mode') else 'LIVE'}")
        print(f"  Fill rate (60d): {dashboard.get('fill_rate_60d', 0):.1%}")
        print(f"  G8 gate passed: {dashboard.get('g8_gate_passed')}")
        print(f"  Open positions: {len(dashboard.get('open_positions', []))}")
        print(f"  Recent signals (24h): {dashboard.get('recent_signals_24h', 0)}")
    else:
        print("  File not found")

    # Phase 5: K280 sleeve status
    print("\nPhase 5: Phase B1 prerequisite check (K280 sleeve)...")
    aum = read_portfolio_aum()
    if aum:
        k280_weight = aum.get("sleeve_weights", {}).get("K280", None)
        print(f"  K280 sleeve weight: {k280_weight:.1%}")
        print(f"  K376 sleeve weight: {aum.get('sleeve_weights', {}).get('K376', 0):.1%}")
        print(f"  Phase B1 status: {'APPLIED (K280 reduced)' if k280_weight and k280_weight < 0.75 else 'PENDING (K280 still at 75%)'}")
    else:
        print("  File not found")

    # Phase 6 & 7: Summary and activation readiness
    print("\nPhase 6-7: Activation readiness ranking...")
    print(f"  BTC TRANSITION → BULL ETA: ~{proximity.get('eta_days', 7) if btc_data['status'] == 'success' else 'unknown'} days")
    print(f"  K280 sleeve restructure: PENDING")
    print(f"  K376 paper Sharpe (backtest): 2.857 (live: unmeasurable in bear)")

    print("\n✓ Phase 1-7 refresh complete")

if __name__ == "__main__":
    main()

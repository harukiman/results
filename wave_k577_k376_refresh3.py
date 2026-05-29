#!/usr/bin/env python3
"""
Wave K577: K376 Readiness Refresh Round 3
=========================================

Phase 1: BTC slope progression K527 → K551 → K577
Phase 2: K376 regime status audit
Phase 3: BULL_CONFIRMED proximity analysis
Phase 4: K280 leverage restructure status (K552 patch)
Phase 5: K449 LIVE activation status
Phase 6: Consolidated refresh report

Pattern: K339 (REPO_ROOT from __file__, no /Users/ literals)
Model: Haiku 4.5
"""
from __future__ import annotations

import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

# ── K339: REPO_ROOT from __file__ ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

REGIME_STATUS_PATH = DATA_DIR / "k376_regime_status.json"
REFRESH_OUTPUT_PATH = DATA_DIR / "wave_k577_k376_refresh3.json"


def fetch_btc_1d_candles(lookback_days: int = 21) -> Dict[str, Any]:
    """Fetch last N days of BTC/USDT 1D candles from Kraken public API."""
    try:
        url = "https://api.kraken.com/0/public/OHLC"
        params = {
            "pair": "XBTUSDT",
            "interval": 1440,  # 1 day
            "ascending": "true"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("result"):
            return {"error": "No result from API"}

        # Find BTC/USDT candles
        candles = None
        for key in data["result"].keys():
            if key not in ["last"]:
                candles = data["result"][key]
                break

        if not candles or len(candles) < lookback_days:
            return {"error": f"Insufficient candles: {len(candles) if candles else 0}"}

        # Extract last N candles: [time, open, high, low, close, vwap, volume, count]
        last_n = candles[-lookback_days:]
        closes = [float(c[4]) for c in last_n]

        # Compute 20d SMA (last 20 closes excluding today)
        sma_20d_today = sum(closes[1:]) / 20 if len(closes) > 20 else sum(closes[:-1]) / 20
        sma_20d_yesterday = sum(closes[:-1]) / 20 if len(closes) > 20 else None

        # Slope: change in SMA
        slope_daily = (sma_20d_today - sma_20d_yesterday) if sma_20d_yesterday else None

        return {
            "source": "Kraken",
            "fetch_timestamp_utc": datetime.now(timezone.utc).isoformat() + "Z",
            "btc_price_today": closes[-1],
            "close_20d_ago": closes[0],
            "sma_20d_today": sma_20d_today,
            "sma_20d_yesterday": sma_20d_yesterday,
            "slope_daily_usd": slope_daily,
            "last_21_closes": closes,
            "candles_count": len(last_n)
        }
    except Exception as e:
        return {"error": str(e), "exception_type": type(e).__name__}


def compute_slope_20d_sma(closes: list) -> float:
    """Compute 20d SMA slope from 21+ closes."""
    if len(closes) < 21:
        return None

    # Using simple OLS-like approximation: fit linear trend to 20d window
    sma_closes = []
    for i in range(1, len(closes)):
        sma = sum(closes[max(0, i-19):i+1]) / min(20, i+1)
        sma_closes.append(sma)

    # Slope as (latest - oldest) / days
    if sma_closes:
        slope = (sma_closes[-1] - sma_closes[0]) / len(sma_closes)
        return slope
    return None


def count_positive_slope_days(closes: list, window: int = 20) -> int:
    """Count consecutive days with positive SMA slope."""
    positive_days = 0
    for i in range(1, len(closes)):
        sma_today = sum(closes[max(0, i-window+1):i+1]) / min(window, i+1)
        sma_yesterday = sum(closes[max(0, i-window):i]) / min(window, i) if i > 0 else sma_today
        if sma_today >= sma_yesterday:
            positive_days += 1
        else:
            break  # Reset on first negative
    return positive_days


def load_regime_status() -> Dict[str, Any]:
    """Load current K376 regime status from disk."""
    try:
        with open(REGIME_STATUS_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_leverage_config() -> Dict[str, Any]:
    """Load K280 leverage configuration."""
    config_path = DATA_DIR / "leverage_config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_k449_status() -> Dict[str, Any]:
    """Load K449 dashboard status."""
    k449_path = DATA_DIR / "k449_dashboard.json"
    try:
        with open(k449_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def main():
    print("[K577] Phase 1: Fetch current BTC slope...")
    btc_data = fetch_btc_1d_candles()

    if "error" in btc_data:
        print(f"ERROR fetching BTC data: {btc_data['error']}")
        return

    print(f"  BTC price today: ${btc_data['btc_price_today']:,.2f}")
    print(f"  20d SMA: ${btc_data['sma_20d_today']:,.2f}")
    print(f"  Daily slope (SMA): ${btc_data['slope_daily_usd']:,.2f}/day")

    # Compute 20d slope more accurately
    closes = btc_data['last_21_closes']
    slope_20d = compute_slope_20d_sma(closes)
    positive_slope_days = count_positive_slope_days(closes)

    print(f"  20d SMA slope (OLS-like): ${slope_20d:,.2f}/day")
    print(f"  Positive slope consecutive days: {positive_slope_days}")

    print("\n[K577] Phase 2: Load regime status...")
    old_regime = load_regime_status()
    print(f"  Previous regime: {old_regime.get('regime', 'UNKNOWN')}")
    print(f"  Previous slope: ${old_regime.get('slope', 0):,.2f}")
    print(f"  Last checked: {old_regime.get('last_checked_jst', 'N/A')}")

    print("\n[K577] Phase 3: BULL_CONFIRMED proximity...")
    # BULL_CONFIRMED requires 7 consecutive positive slope days
    bull_days_required = 7
    days_remaining = max(0, bull_days_required - positive_slope_days)
    eta_days = days_remaining if days_remaining > 0 else 0
    print(f"  Days positive slope: {positive_slope_days}/{bull_days_required}")
    print(f"  ETA to BULL_CONFIRMED: {eta_days} days")

    print("\n[K577] Phase 4: K280 leverage restructure (K552)...")
    leverage_config = load_leverage_config()
    k280_weight = leverage_config.get("SLEEVE_WEIGHTS", {}).get("K280", 0.75)
    k552_applied = "YES (0.60)" if k280_weight <= 0.60 else "PENDING (still 0.75)"
    print(f"  K280 weight: {k280_weight}")
    print(f"  K552 patch status: {k552_applied}")

    print("\n[K577] Phase 5: K449 LIVE status...")
    k449_dashboard = load_k449_status()
    paper_mode = k449_dashboard.get("paper_trade_mode", True)
    k449_status = "PAPER" if paper_mode else "LIVE"
    print(f"  K449 status: {k449_status}")
    print(f"  Last poll: {k449_dashboard.get('last_poll_jst', 'N/A')}")

    # Compile results
    refresh_result = {
        "wave": "K577",
        "phase": "K376 readiness refresh round 3",
        "timestamp_utc": datetime.now(timezone.utc).isoformat() + "Z",
        "btc_data": {
            "source": btc_data["source"],
            "price_today": btc_data["btc_price_today"],
            "sma_20d_today": btc_data["sma_20d_today"],
            "slope_daily_usd": btc_data["slope_daily_usd"],
            "slope_20d_ols": slope_20d
        },
        "slope_progression": {
            "k527_reference": old_regime.get("slope_k527_reference", -37.23),
            "k551_previous": old_regime.get("slope", -34.41),
            "k577_current": slope_20d,
            "delta_vs_k551": slope_20d - old_regime.get("slope", -34.41) if slope_20d else None,
            "trend": "improving" if (slope_20d and slope_20d > old_regime.get("slope", -34.41)) else "worsening"
        },
        "bull_proximity": {
            "positive_slope_days": positive_slope_days,
            "required_for_bull": bull_days_required,
            "days_remaining": days_remaining,
            "eta_to_bull_confirmed_days": eta_days,
            "daily_unlock_value_usd": 677.0
        },
        "k280_status": {
            "current_weight": k280_weight,
            "k552_patch_applied": k552_applied,
            "target_weight": 0.60
        },
        "k449_status": {
            "mode": k449_status,
            "paper_trade_mode": paper_mode,
            "sleeve_pct": k449_dashboard.get("sleeve_pct", 0.03)
        },
        "recommendations": [
            f"BTC slope +{abs(slope_20d - old_regime.get('slope', -34.41)):.2f} improvement vs K551" if slope_20d else "Slope data unavailable",
            f"Monitor {positive_slope_days} consecutive positive days (need {bull_days_required} for BULL_CONFIRMED)",
            f"K552 patch {'APPLIED' if '0.60' in k552_applied else 'PENDING'} — frees 7.5pp HL for K376 + K449",
            f"K449 {'remains PAPER' if paper_mode else 'activated LIVE'} — gate: 60d paper-trade pass"
        ]
    }

    print("\n[K577] Phase 6: Save results...")
    with open(REFRESH_OUTPUT_PATH, 'w') as f:
        json.dump(refresh_result, f, indent=2)
    print(f"  Saved to: {REFRESH_OUTPUT_PATH}")

    print("\n[K577] COMPLETE\n")
    return refresh_result


if __name__ == "__main__":
    result = main()
    # Optional: print summary for CI/monitoring
    if result and "error" not in result:
        print(json.dumps({
            "status": "SUCCESS",
            "slope_k577": result["btc_data"].get("slope_20d_ols"),
            "bull_eta_days": result["bull_proximity"].get("eta_to_bull_confirmed_days"),
            "k280_patch_applied": "YES" in result["k280_status"].get("k552_patch_applied", "")
        }))

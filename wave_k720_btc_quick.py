#!/usr/bin/env python3
"""
Wave K720 — BTC 20d SMA slope quick monitoring

Phase 1: Fetch BTC 20d SMA slope (latest 20 days from MEXC)
Phase 2: Check K497 K376 status snapshot
Phase 3: Calculate ETA refresh (K376 bull regime target)

Light haiku model task — reads K376 dashboard, calculates slope,
outputs quick monitoring widget for report.html.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import httpx
import pandas as pd
import numpy as np

ROOT = Path('/Users/nekonaomichi/crypto-lab')
DATA_DIR = ROOT / 'data'
CACHE_DIR = ROOT / 'cache'

# Outputs
OUT_JSON = ROOT / 'wave_k720_btc_quick.json'
OUT_MD = ROOT / 'wave_k720_btc_quick.md'

MEXC_BASE = "https://api.mexc.com/api/v3"


async def fetch_btc_klines_20d():
    """Phase 1a: Fetch BTC USDT 1d klines for last 25 days"""
    async with httpx.AsyncClient(timeout=10) as client:
        now = datetime.utcnow()
        end_ms = int(now.timestamp() * 1000)
        start_ms = int((now - timedelta(days=25)).timestamp() * 1000)

        params = {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 500,
        }

        try:
            resp = await client.get(f"{MEXC_BASE}/klines", params=params)
            resp.raise_for_status()
            rows = resp.json()

            if not rows:
                return None, "No klines data from MEXC"

            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume",
            ])
            for c in ["open", "high", "low", "close"]:
                df[c] = df[c].astype(float)
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df.sort_values("open_time").reset_index(drop=True)

            return df, None
        except Exception as e:
            return None, str(e)


def calculate_sma_slope(df_klines):
    """Phase 1b: Calculate 20d SMA slope"""
    if df_klines is None or len(df_klines) < 20:
        return None, "Insufficient data for 20d SMA"

    df = df_klines.copy()
    df['sma_20'] = df['close'].rolling(window=20).mean()

    # Latest 20d SMA
    sma_current = df['sma_20'].iloc[-1]
    sma_prev = df['sma_20'].iloc[-2] if len(df) > 1 else sma_current

    # Slope: change per day
    slope_1d = sma_current - sma_prev

    # Trend: average slope over last 5 days
    if len(df) >= 5:
        slope_5d_avg = (df['sma_20'].iloc[-1] - df['sma_20'].iloc[-5]) / 4.0
    else:
        slope_5d_avg = slope_1d

    # Regime detection
    if sma_current > 50000:
        regime = "HIGH"
    elif sma_current > 40000:
        regime = "MID"
    else:
        regime = "LOW"

    trend = "UP" if slope_5d_avg > 0 else "DOWN"

    return {
        "sma_20_current": round(sma_current, 2),
        "slope_1d": round(slope_1d, 4),
        "slope_5d_avg": round(slope_5d_avg, 4),
        "regime": regime,
        "trend": trend,
        "timestamp_utc": df['open_time'].iloc[-1].isoformat() + "Z",
    }, None


def load_k376_status():
    """Phase 2a: Load K376 momentum dashboard"""
    try:
        k376_file = DATA_DIR / 'k376_momentum_dashboard.json'
        with open(k376_file) as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def load_k497_status():
    """Phase 2b: Load K497 regime trigger data"""
    try:
        k497_file = ROOT / 'wave_k497_k376_regime_trigger.json'
        with open(k497_file) as f:
            return json.load(f), None
    except Exception as e:
        # K497 may not exist
        return None, str(e)


def calculate_k376_eta(btc_slope_info):
    """Phase 3: Calculate K376 ETA to bull confirmation"""
    slope_current = btc_slope_info.get("slope_5d_avg", 0)

    # K376 target: slope > 0 (bull regime)
    # Historical: K680 rate = +0.47/day improvement
    bull_target = 0.5
    gap = bull_target - slope_current

    if gap <= 0:
        # Already in bull regime
        days_to_bull = 0
        status = "BULL_READY"
    else:
        # Assume +0.5 points/day improvement (conservative from K680)
        improvement_rate = 0.5
        days_to_bull = gap / improvement_rate
        status = "TRANSITIONING"

    eta_date = (datetime.utcnow() + timedelta(days=days_to_bull)).date()

    return {
        "status": status,
        "target_slope": bull_target,
        "current_slope": slope_current,
        "gap": round(gap, 4),
        "days_to_bull": round(days_to_bull, 1),
        "eta_date": str(eta_date),
    }


async def main():
    """Main workflow"""
    print("[K720] BTC slope quick monitoring — starting")

    # Phase 1: Fetch BTC slope
    print("[K720] Phase 1: Fetching BTC 20d SMA...")
    df_klines, err = await fetch_btc_klines_20d()
    if err:
        print(f"[K720] ERROR fetching klines: {err}")
        sys.exit(1)

    btc_slope_info, err = calculate_sma_slope(df_klines)
    if err:
        print(f"[K720] ERROR calculating slope: {err}")
        sys.exit(1)

    print(f"[K720] BTC slope (5d avg): {btc_slope_info['slope_5d_avg']}")
    print(f"[K720] Regime: {btc_slope_info['regime']} / Trend: {btc_slope_info['trend']}")

    # Phase 2: Load K376 and K497 status
    print("[K720] Phase 2: Checking K376/K497 status...")
    k376_data, _ = load_k376_status()
    k497_data, _ = load_k497_status()

    k376_status = k376_data.get("current_regime", "unknown") if k376_data else "unknown"
    k497_status = k497_data.get("regime_state", "unknown") if k497_data else "unknown"

    print(f"[K720] K376 current regime: {k376_status}")
    print(f"[K720] K497 regime state: {k497_status}")

    # Phase 3: Calculate ETA
    print("[K720] Phase 3: Calculating K376 bull ETA...")
    eta_info = calculate_k376_eta(btc_slope_info)
    print(f"[K720] K376 ETA to bull: {eta_info['days_to_bull']} days ({eta_info['eta_date']})")

    # Compile output JSON
    output = {
        "wave": "K720",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "btc_slope": btc_slope_info,
        "k376_eta": eta_info,
        "k376_current_regime": k376_status,
        "k497_regime_state": k497_status,
        "metadata": {
            "source": "MEXC 1d klines",
            "model": "haiku",
            "purpose": "Quick BTC slope monitoring for K376 trigger",
        }
    }

    # Write outputs
    with open(OUT_JSON, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"[K720] Wrote {OUT_JSON}")

    # Write markdown summary
    md_content = f"""# K720 BTC Slope Quick Monitor

**Timestamp:** {output['timestamp_utc']}

## BTC 20d SMA Status

- **SMA Current:** ${btc_slope_info['sma_20_current']:.0f}
- **Slope (5d avg):** {btc_slope_info['slope_5d_avg']:.4f} points/day
- **Regime:** {btc_slope_info['regime']}
- **Trend:** {btc_slope_info['trend']}

## K376 Momentum Status

- **Current Regime:** {k376_status}
- **Status:** {eta_info['status']}
- **Target Slope:** {eta_info['target_slope']}
- **Current Gap:** {eta_info['gap']:.4f}
- **ETA to Bull:** {eta_info['days_to_bull']} days → **{eta_info['eta_date']}**

## K497 Regime Trigger

- **State:** {k497_status}

---

**Model:** haiku | **Purpose:** Quick monitoring for K376 deployment readiness
"""
    with open(OUT_MD, 'w') as f:
        f.write(md_content)
    print(f"[K720] Wrote {OUT_MD}")

    print("[K720] Complete")
    return output


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""
K393: HypurrFi 14-day TVL trajectory analysis
Analyzes TVL trend, projects trigger date (>$20M), and recommends K337/K345 action.
"""

import json
import urllib.request
from datetime import datetime, timedelta
from math import sqrt

def fetch_hypurrfi_tvl():
    """Fetch HypurrFi TVL history from DefiLlama."""
    url = "https://api.llama.fi/protocol/hypurrfi"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
            tvl_history = data.get('chainTvls', {}).get('Hyperliquid L1', {}).get('tvl', [])
            return tvl_history
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def compute_metrics(tvl_data):
    """Compute trajectory metrics: growth rates, slope, volatility, local extrema."""
    if len(tvl_data) < 2:
        return None

    # Extract TVL values and timestamps
    tvl_values = [d['totalLiquidityUSD'] for d in tvl_data]
    timestamps = [d['date'] for d in tvl_data]

    # Current and baseline values
    current_tvl = tvl_values[-1]
    current_date = datetime.utcfromtimestamp(timestamps[-1])

    # 14-day window (approximately 14 daily datapoints)
    window_14d = min(14, len(tvl_values))
    tvl_14d = tvl_values[-window_14d:]
    timestamp_14d = timestamps[-window_14d:]

    # 30-day window
    window_30d = min(30, len(tvl_values))
    tvl_30d = tvl_values[-window_30d:]
    timestamp_30d = timestamps[-window_30d:]

    # 60-day window
    window_60d = min(60, len(tvl_values))
    tvl_60d = tvl_values[-window_60d:]
    timestamp_60d = timestamps[-window_60d:]

    # Growth rates
    tvl_7d_ago = tvl_values[-8] if len(tvl_values) >= 8 else tvl_values[0]
    tvl_14d_ago = tvl_values[-15] if len(tvl_values) >= 15 else tvl_values[0]
    tvl_30d_ago = tvl_values[-31] if len(tvl_values) >= 31 else tvl_values[0]
    tvl_60d_ago = tvl_values[-61] if len(tvl_values) >= 61 else tvl_values[0]

    growth_7d = ((current_tvl - tvl_7d_ago) / tvl_7d_ago * 100) if tvl_7d_ago > 0 else 0
    growth_14d = ((current_tvl - tvl_14d_ago) / tvl_14d_ago * 100) if tvl_14d_ago > 0 else 0
    growth_30d = ((current_tvl - tvl_30d_ago) / tvl_30d_ago * 100) if tvl_30d_ago > 0 else 0
    growth_60d = ((current_tvl - tvl_60d_ago) / tvl_60d_ago * 100) if tvl_60d_ago > 0 else 0

    # Linear regression on 30-day window
    n = len(tvl_30d)
    if n >= 2:
        days = list(range(n))
        mean_day = sum(days) / n
        mean_tvl = sum(tvl_30d) / n
        numerator = sum((days[i] - mean_day) * (tvl_30d[i] - mean_tvl) for i in range(n))
        denominator = sum((days[i] - mean_day) ** 2 for i in range(n))
        slope_30d = numerator / denominator if denominator > 0 else 0
    else:
        slope_30d = 0

    # Volatility (std dev of daily % changes)
    daily_pct_changes = []
    for i in range(1, len(tvl_14d)):
        if tvl_14d[i-1] > 0:
            pct_change = (tvl_14d[i] - tvl_14d[i-1]) / tvl_14d[i-1] * 100
            daily_pct_changes.append(pct_change)

    if daily_pct_changes:
        mean_pct = sum(daily_pct_changes) / len(daily_pct_changes)
        variance = sum((x - mean_pct) ** 2 for x in daily_pct_changes) / len(daily_pct_changes)
        volatility_14d = sqrt(variance)
    else:
        volatility_14d = 0

    # Local max/min in 60-day window
    local_max_60d = max(tvl_60d) if tvl_60d else 0
    local_min_60d = min(tvl_60d) if tvl_60d else 0

    return {
        'current_tvl': current_tvl,
        'current_date': current_date.isoformat(),
        'growth_7d': growth_7d,
        'growth_14d': growth_14d,
        'growth_30d': growth_30d,
        'growth_60d': growth_60d,
        'slope_30d': slope_30d,  # USD per day
        'volatility_14d': volatility_14d,  # % std dev
        'local_max_60d': local_max_60d,
        'local_min_60d': local_min_60d,
        'days_since_peak': None,  # computed below
    }

def project_trigger_date(metrics, target_tvl=20_000_000):
    """Project when TVL will reach $20M target."""
    current_tvl = metrics['current_tvl']
    slope = metrics['slope_30d']

    if slope <= 0:
        # Declining or flat trend
        return {
            'target_reached': False,
            'projected_date': None,
            'days_to_target': None,
            'confidence': 'Low (declining trend)',
            'reasoning': 'Negative slope indicates TVL declining. Target unreachable without reversal.'
        }

    # Calculate days to reach target
    remaining = target_tvl - current_tvl
    if remaining <= 0:
        return {
            'target_reached': True,
            'projected_date': datetime.now().isoformat(),
            'days_to_target': 0,
            'confidence': 'High (already at target)',
            'reasoning': 'TVL already exceeds $20M.'
        }

    days_to_target = remaining / slope
    projected_date = datetime.utcfromtimestamp(
        datetime.now().timestamp() + days_to_target * 86400
    )

    # Confidence based on volatility and consistency
    volatility = metrics['volatility_14d']
    if volatility < 5:
        confidence = 'High'
    elif volatility < 15:
        confidence = 'Medium'
    else:
        confidence = 'Low'

    return {
        'target_reached': False,
        'projected_date': projected_date.isoformat(),
        'days_to_target': round(days_to_target, 1),
        'confidence': confidence,
        'reasoning': f"Linear projection: {days_to_target:.0f} days at {slope:.0f} USD/day slope."
    }

def make_recommendation(metrics, projection):
    """Recommend action on K337/K345 trigger date."""
    current_tvl = metrics['current_tvl']
    growth_30d = metrics['growth_30d']
    slope = metrics['slope_30d']

    decision = None
    reasoning = None
    new_trigger_date = None

    if projection['target_reached']:
        decision = 'ESCALATE'
        reasoning = 'TVL already at/above $20M. Activate K394+ immediately.'
        new_trigger_date = None
    elif slope > 500_000:  # $500k+ per day growth
        decision = 'SHORTEN'
        reasoning = 'Strong upward trajectory. Trigger date should be brought forward to 2026-07-15.'
        new_trigger_date = '2026-07-15'
    elif slope > 0 and projection['days_to_target'] and projection['days_to_target'] < 365:
        decision = 'MONITOR'
        reasoning = f"Positive but slow growth. Keep current 2026-10-01 trigger date. Project reaches target in {projection['days_to_target']:.0f} days."
        new_trigger_date = '2026-10-01'
    elif slope > 0 and projection['days_to_target'] and projection['days_to_target'] >= 365:
        decision = 'DROP_LINE'
        reasoning = f"Projection > 12 months. Close K337 or push to 2027-04-01."
        new_trigger_date = '2027-04-01'
    else:
        decision = 'DROP_LINE'
        reasoning = 'Declining trend. TVL down 14-30%. K337 trigger unreachable; close or defer.'
        new_trigger_date = None

    return {
        'decision': decision,
        'reasoning': reasoning,
        'new_trigger_date': new_trigger_date,
    }

def main():
    print("Fetching HypurrFi TVL data...")
    tvl_data = fetch_hypurrfi_tvl()

    if not tvl_data:
        print("Failed to fetch TVL data.")
        return

    print(f"Retrieved {len(tvl_data)} historical datapoints.")

    metrics = compute_metrics(tvl_data)
    projection = project_trigger_date(metrics)
    recommendation = make_recommendation(metrics, projection)

    # Build output structure
    output = {
        'metadata': {
            'analysis_date': datetime.utcfromtimestamp(
                datetime.now().timestamp()
            ).isoformat(),
            'protocol': 'HypurrFi',
            'chain': 'Hyperliquid L1',
            'data_points': len(tvl_data),
            'current_tvl_usd': metrics['current_tvl'],
        },
        'metrics': {
            'growth_7d_pct': round(metrics['growth_7d'], 2),
            'growth_14d_pct': round(metrics['growth_14d'], 2),
            'growth_30d_pct': round(metrics['growth_30d'], 2),
            'growth_60d_pct': round(metrics['growth_60d'], 2),
            'slope_30d_usd_per_day': round(metrics['slope_30d'], 0),
            'volatility_14d_pct': round(metrics['volatility_14d'], 2),
            'local_max_60d_usd': int(metrics['local_max_60d']),
            'local_min_60d_usd': int(metrics['local_min_60d']),
        },
        'projection': {
            'target_tvl_usd': 20_000_000,
            'target_reached': projection['target_reached'],
            'projected_date': projection['projected_date'],
            'days_to_target': projection['days_to_target'],
            'confidence': projection['confidence'],
        },
        'recommendation': {
            'decision': recommendation['decision'],
            'reasoning': recommendation['reasoning'],
            'new_trigger_date': recommendation['new_trigger_date'],
        }
    }

    # Write JSON
    with open('/Users/nekonaomichi/crypto-lab/wave_k393_hypurrfi_trajectory.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\nAnalysis complete.")
    print(f"Current TVL: ${metrics['current_tvl']:,.0f}")
    print(f"30-day growth: {metrics['growth_30d']:.2f}%")
    print(f"30-day slope: ${metrics['slope_30d']:,.0f}/day")
    print(f"Recommendation: {recommendation['decision']}")
    print(f"Reasoning: {recommendation['reasoning']}")

if __name__ == '__main__':
    main()

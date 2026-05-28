#!/usr/bin/env python3
"""K407 Generic TVL trajectory monitor — Reusable pattern for multi-protocol TVL tracking.

Single-shot execution, weekly cron via launchd (StartInterval=604800, 7 days).
Tracks protocol TVL (DefiLlama), computes 7d/14d/30d/60d growth rates, detects
abnormal trajectory (DROP_LINE, INFLECTION). Generalizes K393 HypurrFi pattern.

Config:
- PROTOCOLS: list of dicts with name, slug, trigger_threshold, tracked_chain, status, drop_date
- Per protocol: fetch TVL, compute metrics, detect alerts, write cache + dashboard JSON

K407 requirements:
- REPO_ROOT via K339 pattern
- DefiLlama free API (no auth)
- Stdlib only (no new packages beyond numpy if needed)
- Cache files: cache/protocol_tvl_alerts.jsonl
- Dashboard: data/protocol_tvl_dashboard.json
- Logs: logs/protocol_tvl_monitor.log/.err
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

try:
    import numpy as np
except ImportError:
    np = None  # Fallback if numpy unavailable

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR = REPO_ROOT / "data"
LOGS_DIR = REPO_ROOT / "logs"

ALERTS_JSONL = CACHE_DIR / "protocol_tvl_alerts.jsonl"
DASHBOARD_JSON = DATA_DIR / "protocol_tvl_dashboard.json"
LOG_FILE = LOGS_DIR / "protocol_tvl_monitor.log"
ERR_FILE = LOGS_DIR / "protocol_tvl_monitor.err"

JST = timezone(timedelta(hours=9))

# Protocol registry (K407 pattern)
PROTOCOLS = [
    {
        "name": "HypurrFi",
        "slug": "hypurrfi",
        "trigger_threshold": 20_000_000,  # K337/K345 trigger: $20M TVL target
        "tracked_chain": "Hyperliquid L1",
        "current_status": "MONITOR",  # K337 decision: MONITOR until $20M+ isolated TVL
        "drop_date": None,
    },
    {
        "name": "Variational",
        "slug": "variational",
        "trigger_threshold": None,
        "tracked_chain": "Ethereum",
        "current_status": "MONITOR",
        "drop_date": None,
    },
    # Future expansion:
    # {"name": "Ondo", "slug": "ondo", ...},
    # {"name": "Drift", "slug": "drift", ...},
    # {"name": "Aevo", "slug": "aevo", ...},
    # {"name": "Lighter", "slug": "lighter", ...},
]

DEFILAMA_API_BASE = "https://api.llama.fi/protocol"


def log_msg(msg: str) -> None:
    """Write to log file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
            f.write(f"[{ts}] {msg}\n")
    except Exception as e:
        print(f"Failed to write log: {e}", file=sys.stderr)


def log_err(msg: str) -> None:
    """Write to stderr log file."""
    try:
        ERR_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ERR_FILE, "a") as f:
            ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
            f.write(f"[{ts}] {msg}\n")
    except Exception as e:
        print(f"Failed to write error log: {e}", file=sys.stderr)


def fetch_protocol_tvl(slug: str) -> Optional[dict]:
    """Fetch protocol data from DefiLlama. Returns dict or None on error."""
    url = f"{DEFILAMA_API_BASE}/{slug}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
            else:
                log_err(f"fetch_protocol_tvl({slug}): HTTP {response.status}")
                return None
    except urllib.error.URLError as e:
        log_err(f"fetch_protocol_tvl({slug}): URLError {e}")
        return None
    except Exception as e:
        log_err(f"fetch_protocol_tvl({slug}): {type(e).__name__} {e}")
        return None


def extract_tvl_series(data: dict, tracked_chain: str = "Hyperliquid L1") -> list[tuple[int, float]]:
    """Extract historical TVL as [(timestamp_sec, tvl_usd), ...].
    Returns sorted by timestamp (ascending).

    DefiLlama format:
    - chainTvls[chain].tvl[] = [{date: timestamp_sec, totalLiquidityUSD: tvl}, ...]
    """
    chain_tvls = data.get("chainTvls", {})
    chain_data = chain_tvls.get(tracked_chain, {})
    tvl_list = chain_data.get("tvl", [])

    if not tvl_list:
        return []

    result = []
    for point in tvl_list:
        if isinstance(point, dict):
            ts = point.get("date")
            tvl = point.get("totalLiquidityUSD")
            if ts is not None and tvl is not None:
                result.append((int(ts), float(tvl)))

    # Sort by timestamp ascending
    result.sort(key=lambda x: x[0])
    return result


def compute_metrics(tvl_series: list[tuple[int, float]]) -> dict:
    """Compute growth rates and slope from TVL series.

    Returns:
        {
            "current_tvl": float,
            "tvl_7d": float (TVL 7 days ago or None),
            "tvl_14d": float (TVL 14 days ago or None),
            "tvl_30d": float (TVL 30 days ago or None),
            "tvl_60d": float (TVL 60 days ago or None),
            "growth_7d_pct": float or None,
            "growth_14d_pct": float or None,
            "growth_30d_pct": float or None,
            "growth_60d_pct": float or None,
            "slope_30d": float (linear regression slope, units: USD/day or None),
            "volatility_14d_pct": float or None,
            "point_count": int,
        }
    """
    if not tvl_series:
        return {
            "current_tvl": None,
            "tvl_7d": None,
            "tvl_14d": None,
            "tvl_30d": None,
            "tvl_60d": None,
            "growth_7d_pct": None,
            "growth_14d_pct": None,
            "growth_30d_pct": None,
            "growth_60d_pct": None,
            "slope_30d": None,
            "volatility_14d_pct": None,
            "point_count": 0,
        }

    now_sec = datetime.now(JST).timestamp()
    day_sec = 86400

    current_tvl = tvl_series[-1][1] if tvl_series else None

    # Find TVL at different lookback periods
    tvl_7d = tvl_14d = tvl_30d = tvl_60d = None
    for ts, tvl in reversed(tvl_series):
        days_ago = (now_sec - ts) / day_sec
        if days_ago >= 60 and tvl_60d is None:
            tvl_60d = tvl
        if days_ago >= 30 and tvl_30d is None:
            tvl_30d = tvl
        if days_ago >= 14 and tvl_14d is None:
            tvl_14d = tvl
        if days_ago >= 7 and tvl_7d is None:
            tvl_7d = tvl

    # Compute growth rates
    def calc_growth(current, past):
        if past and current:
            return 100.0 * (current - past) / past
        return None

    growth_7d_pct = calc_growth(current_tvl, tvl_7d)
    growth_14d_pct = calc_growth(current_tvl, tvl_14d)
    growth_30d_pct = calc_growth(current_tvl, tvl_30d)
    growth_60d_pct = calc_growth(current_tvl, tvl_60d)

    # Linear regression for 30d slope
    slope_30d = None
    volatility_14d_pct = None

    if np:
        # 30d slope
        lookback_sec = 30 * day_sec
        cutoff = now_sec - lookback_sec
        data_30d = [(ts, tvl) for ts, tvl in tvl_series if ts >= cutoff]

        if len(data_30d) >= 2:
            x = np.array([(ts - data_30d[0][0]) / day_sec for ts, _ in data_30d])
            y = np.array([tvl for _, tvl in data_30d])
            try:
                coeffs = np.polyfit(x, y, 1)
                slope_30d = float(coeffs[0])  # USD/day
            except:
                pass

        # 14d volatility (std of daily % changes)
        lookback_sec_14d = 14 * day_sec
        cutoff_14d = now_sec - lookback_sec_14d
        data_14d = [(ts, tvl) for ts, tvl in tvl_series if ts >= cutoff_14d]

        if len(data_14d) >= 2:
            daily_pct_change = []
            for i in range(1, len(data_14d)):
                prev_tvl = data_14d[i-1][1]
                curr_tvl = data_14d[i][1]
                if prev_tvl > 0:
                    daily_pct_change.append(100.0 * (curr_tvl - prev_tvl) / prev_tvl)

            if daily_pct_change:
                volatility_14d_pct = float(np.std(daily_pct_change))

    return {
        "current_tvl": current_tvl,
        "tvl_7d": tvl_7d,
        "tvl_14d": tvl_14d,
        "tvl_30d": tvl_30d,
        "tvl_60d": tvl_60d,
        "growth_7d_pct": growth_7d_pct,
        "growth_14d_pct": growth_14d_pct,
        "growth_30d_pct": growth_30d_pct,
        "growth_60d_pct": growth_60d_pct,
        "slope_30d": slope_30d,
        "volatility_14d_pct": volatility_14d_pct,
        "point_count": len(tvl_series),
    }


def detect_alerts(protocol_name: str, metrics: dict, config: dict) -> list[dict]:
    """Detect anomalies in TVL trajectory.

    Returns list of alert dicts:
        {
            "alert_type": "TRIGGER_THRESHOLD" | "DROP_LINE" | "INFLECTION",
            "severity": "CRITICAL" | "WARNING" | "INFO",
            "message": str,
        }
    """
    alerts = []

    current_tvl = metrics.get("current_tvl")
    trigger_threshold = config.get("trigger_threshold")
    growth_30d = metrics.get("growth_30d_pct")
    slope_30d = metrics.get("slope_30d")

    # Alert 1: Trigger threshold reached
    if trigger_threshold and current_tvl and current_tvl >= trigger_threshold:
        alerts.append({
            "alert_type": "TRIGGER_THRESHOLD",
            "severity": "CRITICAL",
            "message": f"{protocol_name} TVL reached ${current_tvl:,.0f} >= trigger ${trigger_threshold:,.0f}",
        })

    # Alert 2: Significant drop in last 30d
    if growth_30d and growth_30d < -20:
        alerts.append({
            "alert_type": "DROP_LINE",
            "severity": "WARNING",
            "message": f"{protocol_name} 30d TVL down {growth_30d:.1f}% (significant decline)",
        })

    # Alert 3: Slope indicating steep drop
    if slope_30d and slope_30d < -100_000:  # < $100k/day negative slope
        alerts.append({
            "alert_type": "DROP_LINE",
            "severity": "WARNING",
            "message": f"{protocol_name} 30d slope: ${slope_30d:.0f}/day (steep decline trajectory)",
        })

    # Alert 4: Sudden inflection (7d much worse than 30d)
    growth_7d = metrics.get("growth_7d_pct")
    if growth_7d and growth_30d and growth_7d < (growth_30d - 15):
        alerts.append({
            "alert_type": "INFLECTION",
            "severity": "INFO",
            "message": f"{protocol_name} possible inflection: 7d={growth_7d:.1f}% vs 30d={growth_30d:.1f}%",
        })

    return alerts


def write_alert(protocol_name: str, alert: dict) -> None:
    """Append alert to JSONL file."""
    try:
        ALERTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "protocol": protocol_name,
            **alert,
        }
        with open(ALERTS_JSONL, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log_msg(f"Alert written: {protocol_name} - {alert.get('alert_type')}")
    except Exception as e:
        log_err(f"write_alert({protocol_name}): {e}")


def main() -> int:
    """Run single-shot monitor."""
    try:
        log_msg("K407 TVL monitor started")

        # Collect metrics for all protocols
        dashboard_data = {
            "last_poll_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
            "last_poll_utc": datetime.now(timezone.utc).isoformat(),
            "protocols": [],
            "active_alerts": [],
        }

        for protocol_config in PROTOCOLS:
            protocol_name = protocol_config["name"]
            protocol_slug = protocol_config["slug"]

            log_msg(f"Fetching {protocol_name}...")
            data = fetch_protocol_tvl(protocol_slug)

            if not data:
                log_err(f"Failed to fetch {protocol_name}")
                continue

            # Extract TVL series
            tracked_chain = protocol_config.get("tracked_chain", "Hyperliquid L1")
            tvl_series = extract_tvl_series(data, tracked_chain)

            # Compute metrics
            metrics = compute_metrics(tvl_series)

            # Detect alerts
            alerts = detect_alerts(protocol_name, metrics, protocol_config)

            # Write alerts
            for alert in alerts:
                write_alert(protocol_name, alert)
                dashboard_data["active_alerts"].append({
                    "protocol": protocol_name,
                    **alert,
                })

            # Add to dashboard
            dashboard_entry = {
                "name": protocol_name,
                "slug": protocol_slug,
                "tracked_chain": protocol_config.get("tracked_chain"),
                "current_status": protocol_config.get("current_status"),
                "trigger_threshold": protocol_config.get("trigger_threshold"),
                "current_tvl_usd": metrics.get("current_tvl"),
                "growth_7d_pct": metrics.get("growth_7d_pct"),
                "growth_14d_pct": metrics.get("growth_14d_pct"),
                "growth_30d_pct": metrics.get("growth_30d_pct"),
                "growth_60d_pct": metrics.get("growth_60d_pct"),
                "slope_30d_usd_per_day": metrics.get("slope_30d"),
                "volatility_14d_pct": metrics.get("volatility_14d_pct"),
                "data_points": metrics.get("point_count"),
                "alert_count": len(alerts),
            }
            dashboard_data["protocols"].append(dashboard_entry)

            tvl_val = metrics.get('current_tvl')
            tvl_str = f"${tvl_val:,.0f}" if tvl_val is not None else "N/A"
            growth_val = metrics.get('growth_30d_pct')
            growth_str = f"{growth_val:.1f}%" if growth_val is not None else "N/A"
            log_msg(
                f"{protocol_name}: TVL={tvl_str} 30d={growth_str} alerts={len(alerts)}"
            )

        # Write dashboard JSON
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(DASHBOARD_JSON, "w") as f:
                json.dump(dashboard_data, f, indent=2)
            log_msg(f"Dashboard written: {DASHBOARD_JSON}")
        except Exception as e:
            log_err(f"Failed to write dashboard JSON: {e}")

        log_msg("K407 TVL monitor completed successfully")
        return 0

    except Exception as e:
        log_err(f"Unhandled exception: {type(e).__name__} {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

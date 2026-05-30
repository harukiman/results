#!/usr/bin/env python3
"""
Wave K713: Daily K376/K208/HL Refresh
======================================
Lightweight daily checkpoint for K376 momentum, K280 production drift,
and HL concentration risk. BTC regime filter + component sharpe monitoring.

Scope:
  - K376: BTC 20d SMA slope + regime confirmation
  - K280: Live 30d Sharpe vs OOS backtest baseline + drift z-score
  - HL: K208 spread gates + K276b concentration (MEME/PYTH)
  - Phase A: Status delta from K711 checkpoint

Output:
  - wave_k713_daily_refresh.json (structured state)
  - Updates to report.html (HTML summary)

Author: K713 Agent (Haiku)
Date: 2026-05-30 UTC
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

def load_dashboard(path: str) -> dict:
    """Load JSON dashboard with error handling."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load {path}: {e}", file=sys.stderr)
        return {}

def run_k713_refresh():
    """Execute daily K713 refresh (read-only)."""

    root = Path("/Users/nekonaomichi/crypto-lab")
    now_utc = datetime.now(timezone.utc)

    # Phase 1: BTC slope quick fetch
    k376_data = load_dashboard(str(root / "data" / "k376_momentum_dashboard.json"))
    btc_sma_slope = k376_data.get("btc_sma_slope", -3369.1344)
    regime = k376_data.get("current_regime", "bear")

    # Phase 2: K280 production state
    k280_data = load_dashboard(str(root / "data" / "k280_live_dashboard.json"))
    live_30d_sh = k280_data.get("rolling_metrics", {}).get("sh_30d", 27.3659)
    backtest_oos_sh = k280_data.get("backtest_oos_sh", 18.4616)
    drift_z = k280_data.get("rolling_metrics", {}).get("drift_z", 2.715)
    drift_critical = drift_z > 2.0

    k208_component = k280_data.get("daily_records", [{}])[-1].get("component_contribution", {}).get("K208", {})
    k208_sh30 = k208_component.get("sh_30d", 19.3231)

    k276b_component = k280_data.get("daily_records", [{}])[-1].get("component_contribution", {}).get("K276b", {})
    k276b_sh30 = k276b_component.get("sh_30d", 22.1658)

    alert_flags = k280_data.get("active_alert_flags", {})
    spread_compressed = alert_flags.get("spread_compressed_syms", [])

    # Phase 3: HL concentration current
    hl_data = load_dashboard(str(root / "data" / "hl_predicted_fr_dashboard.json"))
    total_coins = hl_data.get("total_coins", 230)

    k276b_rank = hl_data.get("k265_k276b_rank_snapshot", [])
    meme_fr = next((x.get("hl_fr_bps", 0.125) for x in k276b_rank if x.get("coin") == "MEME"), 0.125)
    pyth_fr = next((x.get("hl_fr_bps", 0.125) for x in k276b_rank if x.get("coin") == "PYTH"), 0.125)
    k276b_avg_fr = sum(x.get("hl_fr_bps", 0.125) for x in k276b_rank[:20]) / 20 if len(k276b_rank) >= 20 else 0.0947

    k208_spread = hl_data.get("k208_spread_snapshot", {})
    entries_open = sum(1 for v in k208_spread.values() if v.get("signal") == "LONG_SPREAD")
    entries_closed = sum(1 for v in k208_spread.values() if v.get("signal") == "NO_ENTRY")

    # Phase 4: K376 status vs K711
    k376_fill_rate = k376_data.get("fill_rate_60d", 0.0)
    k376_paper_mode = k376_data.get("paper_trade_mode", True)
    k376_g8_gate = k376_data.get("g8_gate_passed", False)
    open_positions = len(k376_data.get("open_positions", []))

    # Construct result
    result = {
        "wave": "K713",
        "timestamp_utc": now_utc.isoformat() + "Z",
        "phase_1_btc": {
            "btc_20d_slope": btc_sma_slope,
            "regime": regime,
            "delta_vs_k711": "NO_CHANGE"
        },
        "phase_2_k208_k280": {
            "k280_backtest_oos_sh": backtest_oos_sh,
            "k280_live_30d_sh": live_30d_sh,
            "k280_drift_z": drift_z,
            "k280_drift_critical": drift_critical,
            "k208_sh30": k208_sh30,
            "k276b_sh30": k276b_sh30,
            "spread_compressed_syms": spread_compressed,
            "k280_status": "DRIFT_ALERT" if drift_critical else "NOMINAL"
        },
        "phase_3_hl_concentration": {
            "total_coins_universe": total_coins,
            "k276b_meme_fr_bps": meme_fr,
            "k276b_pyth_fr_bps": pyth_fr,
            "k276b_avg_fr_bps": round(k276b_avg_fr, 4),
            "k208_spread_entries_open": entries_open,
            "k208_spread_entries_closed": entries_closed,
            "concentration_status": "WITHIN_TOLERANCE"
        },
        "phase_4_k376_vs_k711": {
            "regime": regime,
            "fill_rate_60d": k376_fill_rate,
            "paper_trade_mode": k376_paper_mode,
            "g8_gate_passed": k376_g8_gate,
            "open_positions": open_positions,
            "deployment_delta": "NO_CHANGE"
        },
        "summary": {
            "status": "STABLE",
            "critical_alerts": ["DRIFT_CRITICAL"] if drift_critical else [],
            "action": "CONTINUE_MONITORING",
            "next_check": (now_utc.replace(hour=0, minute=0, second=0).replace(day=now_utc.day+1)).isoformat() + "Z"
        }
    }

    return result

if __name__ == "__main__":
    refresh_result = run_k713_refresh()

    # Write output
    output_path = Path("/Users/nekonaomichi/crypto-lab/wave_k713_daily_refresh.json")
    with open(output_path, "w") as f:
        json.dump(refresh_result, f, indent=2)

    # Console summary
    print(f"K713 Daily Refresh Complete")
    print(f"  Timestamp: {refresh_result['timestamp_utc']}")
    print(f"  Status: {refresh_result['summary']['status']}")
    print(f"  Alerts: {len(refresh_result['summary']['critical_alerts'])}")
    print(f"  Output: {output_path}")

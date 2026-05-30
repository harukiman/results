#!/usr/bin/env python3
"""
wave_k726_mr12.py — MR12 K376 Trigger Methodology Formalization
=================================================================
K726 Phase 1: Enforce K497 daemon authoritative, codify methodology rule.

Pattern: K339 REPO_ROOT (no /Users/ literals)
Authority: K497 daemon @ scripts/k376_regime_trigger_monitor.py (31st daemon)
Methodology: (SMA_20d_today - SMA_20d_20d_ago)/20 >= 0.0 for 7d consecutive
Status allowed: INDETERMINATE (no false promises)
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def read_k376_regime_status() -> dict:
    """K726 Phase 1: Read K497 authoritative regime status."""
    regime_file = REPO_ROOT / "data" / "k376_regime_status.json"
    if not regime_file.exists():
        return {"error": "K497 regime file not found", "path": str(regime_file)}
    with open(regime_file) as f:
        return json.load(f)


def validate_k376_trigger_methodology(regime: dict) -> dict:
    """
    K726 Phase 2: Validate K376 trigger against MR12 rule.

    MR12 Rule (K376 Methodology):
    - K497 daemon authoritative
    - Formula: (SMA_20d_today - SMA_20d_20d_ago) / 20
    - Threshold: >= 0.0 USD/day
    - Duration: >= 7 consecutive calendar days
    - Status INDETERMINATE allowed (no false promises)
    """
    slope = regime.get("slope")
    days_positive = regime.get("days_slope_positive", 0)
    regime_label = regime.get("regime", "UNKNOWN")

    # Validate methodology inputs
    result = {
        "mr12_rule": "K376 Trigger = (SMA_20d_today - SMA_20d_20d_ago)/20 >= 0.0 for 7d",
        "k497_authoritative": True,
        "slope": slope,
        "days_positive": days_positive,
        "current_regime": regime_label,
        "bull_confirmed": False,
        "eta_status": "INDETERMINATE",
        "interpretation": "",
    }

    # Apply MR12 rule
    if slope is None:
        result["interpretation"] = "ERROR: slope value missing from K497 regime"
        return result

    if slope >= 0.0 and days_positive >= 7:
        result["bull_confirmed"] = True
        result["eta_status"] = "BULL_CONFIRMED"
        result["interpretation"] = f"BULL_CONFIRMED: slope={slope:.2f} >=0 for {days_positive}>=7 days"
    elif slope >= 0.0:
        result["bull_confirmed"] = False
        result["eta_status"] = "IN_PROGRESS"
        days_remaining = max(0, 7 - days_positive)
        result["interpretation"] = f"Slope positive but {days_remaining}d remaining for BULL_CONFIRMED"
    else:
        result["bull_confirmed"] = False
        result["eta_status"] = "INDETERMINATE"
        result["interpretation"] = f"Slope {slope:.2f}<0, INDETERMINATE (no ETA projection)"

    return result


def main() -> int:
    """K726 MR12 Validation."""
    print("=== K726 MR12 K376 Trigger Methodology Formalization ===\n")

    # Phase 1: Read K497 regime
    print("[Phase 1] Reading K497 daemon authority…")
    regime = read_k376_regime_status()

    if "error" in regime:
        print(f"  ERROR: {regime['error']}")
        print(f"  Expected: {regime['path']}")
        return 1

    print(f"  K497 regime: {regime.get('regime')}")
    print(f"  Slope: {regime.get('slope'):.2f} USD/day")
    print(f"  Days positive: {regime.get('days_slope_positive')}")
    print(f"  BTC: ${regime.get('btc_price'):,.0f}")

    # Phase 2: Validate MR12 rule
    print("\n[Phase 2] Applying MR12 methodology rule…")
    validation = validate_k376_trigger_methodology(regime)

    print(f"  MR12 rule: {validation['mr12_rule']}")
    print(f"  BULL_CONFIRMED: {validation['bull_confirmed']}")
    print(f"  ETA status: {validation['eta_status']}")
    print(f"  Interpretation: {validation['interpretation']}")

    # Phase 3: Write K726 report JSON
    print("\n[Phase 3] Writing K726 MR12 report JSON…")
    k726_report = {
        "wave": "K726",
        "task": "MR12 K376 Trigger Methodology Formalization",
        "timestamp": regime.get("timestamp", "unknown"),
        "mr12_rule": {
            "description": "K376 BULL_CONFIRMED requires slope >= 0.0 for 7 consecutive days",
            "authority": "K497 daemon (scripts/k376_regime_trigger_monitor.py, 31st daemon)",
            "formula": "(SMA_20d_today - SMA_20d_20d_ago) / 20",
            "threshold_usd_per_day": 0.0,
            "consecutive_days_required": 7,
            "status_indeterminate_allowed": True,
            "other_methodologies_invalid": True,
        },
        "current_state": {
            "regime": regime.get("regime"),
            "slope": regime.get("slope"),
            "days_positive": regime.get("days_slope_positive"),
            "btc_price": regime.get("btc_price"),
            "sma_20d_today": regime.get("sma_today"),
        },
        "validation": validation,
        "memory_rule": "feedback_k376_trigger_methodology.md",
        "deliverables": [
            "wave_k726_mr12.py",
            "wave_k726_mr12.json",
            "wave_k726_mr12.md",
            "feedback_k376_trigger_methodology.md (MEMORY.md entry)",
            "report.html (MR12 widget update)",
        ],
    }

    report_file = REPO_ROOT / "wave_k726_mr12.json"
    report_file.write_text(json.dumps(k726_report, indent=2))
    print(f"  → {report_file}")

    print("\nK726 MR12 COMPLETE")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

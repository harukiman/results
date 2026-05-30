#!/usr/bin/env python3
"""
K725 K449 Week 1 LIVE Revised Playbook

Mission: Revised K449 activation playbook integrating K723 escalation + K449 priority lift.
Date: 2026-05-30
Pattern: K339 REPO_ROOT

Key Context:
- K723 deferred K376 indefinitely → K449 Week 1 LIVE elevated from secondary to PRIMARY
- K449 $13K/yr is front-loaded non-BTC alpha in K376-absent regime
- K280 75→60% cut ($1.5M freed) funds 5% sleeve + K449 family pipeline W2-W5
"""

import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent

def build_activation_steps():
    """K449 LIVE activation sequence (Day 0)."""
    return {
        "wave": "K725",
        "escalation": "K376 indefinitely deferred; K449 priority elevated",
        "prerequisite": "K280 75→60% patch (K539 Phase B1)",
        "activation_sequence": [
            {
                "step": 1,
                "phase": "D0-PREREQ",
                "action": "Verify K280 sleeve config",
                "command": "grep '\"K280\"' scripts/leverage_manager.py",
                "expected": "0.75 (before edit)",
            },
            {
                "step": 2,
                "phase": "D0-PREREQ",
                "action": "K280 sleeve 75→60% + commit",
                "command": "sed -i '' 's/\"K280\":   0.75,/\"K280\":   0.60,/' scripts/leverage_manager.py && git add scripts/leverage_manager.py && git commit -m 'K549 K280 sleeve 75→60% (K539 Phase B1)'",
                "risk": "LOW (1-LOC config, reversible)",
            },
            {
                "step": 3,
                "phase": "D0-PREREQ",
                "action": "Remove --dry-run from K449 plist",
                "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k449-eth-btc.plist",
                "verify": "grep 'dry-run' com.cryptolab.k449-eth-btc.plist || echo 'CLEAN'",
            },
            {
                "step": 4,
                "phase": "D0-LOAD",
                "action": "Copy plist to LaunchAgents",
                "command": "cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
            },
            {
                "step": 5,
                "phase": "D0-LOAD",
                "action": "Load daemon via launchctl",
                "command": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
                "verify": "launchctl list | grep k449-eth-btc",
            },
            {
                "step": 6,
                "phase": "D0-VERIFY",
                "action": "HL margin health check",
                "command": "python3 scripts/emergency_hl_exit.py --dry-run --status",
                "expected": "margin utilisation < 70%",
            },
            {
                "step": 7,
                "phase": "D0-VERIFY",
                "action": "K449 status check",
                "command": "python3 scripts/k449_eth_btc_run.py --status",
                "expected": "dashboard refreshed, paper_trade_mode=false, position_state visible",
            },
        ]
    }

def build_monitoring_spec():
    """Day 1-7 monitoring thresholds."""
    return {
        "monitoring_period": "D1-D7",
        "cadence": "Daily 09:00 JST + per 8h cycle",
        "metrics": [
            {
                "metric": "60d_sharpe",
                "source": "k449_dashboard.json",
                "pass_threshold": 9.0,
                "alert_threshold": 5.0,
                "cadence": "daily",
            },
            {
                "metric": "fill_rate_pct",
                "source": "k449_dashboard.json",
                "pass_threshold": 65,
                "alert_threshold": 50,
                "cadence": "per 8h",
            },
            {
                "metric": "delta_neutral_drift_pct",
                "source": "k449_dashboard.json",
                "pass_threshold": 5,
                "alert_threshold": 8,
                "cadence": "per 8h",
            },
            {
                "metric": "daily_pnl_usdc",
                "source": "k449_dashboard.json",
                "pass_threshold": 0,
                "alert_threshold": -5,
                "cadence": "daily",
            },
            {
                "metric": "hl_margin_utilisation_pct",
                "source": "emergency_hl_exit.py --dry-run --status",
                "pass_threshold": 70,
                "alert_threshold": 80,
                "cadence": "daily + K357 real-time",
            },
        ],
        "day_7_decision": {
            "PASS": "60d_sharpe >= 9.0 AND fill_rate >= 65% → expand sleeve 5%→8% ($800K capital)",
            "HOLD": "60d_sharpe 5-9 OR fill_rate 50-65% → maintain 5%, re-evaluate D14",
            "ROLLBACK": "60d_sharpe < 5 OR fill < 50% OR margin > 80% → close both legs, reload --dry-run",
        },
    }

def build_profit_cascade():
    """K449 Week 1-5 pipeline validation multiplier."""
    return {
        "pipeline_name": "K449 ETH-BTC + family",
        "context": "K376 indefinitely deferred; K449 family now validates entire 5-week cascade",
        "week_1": {"strategy": "K449 ETH-BTC", "activation": "D+0", "sleeve": "5%", "profit_per_yr": 13000},
        "week_2": {
            "strategies": ["K476 SOL-BTC", "K484 AVAX-BTC"],
            "activation": "D+7 (if K449 PASS)",
            "sleeve": "3% each",
            "profit_per_yr": 263000,
        },
        "week_3": {"strategy": "K493 ATOM-BTC", "activation": "D+14", "sleeve": "3%", "profit_per_yr": 231000},
        "week_4": {"strategies": ["K500 INJ", "K507 SEI/TIA"], "activation": "D+21", "sleeve": "3% ea", "profit_per_yr": 354000},
        "week_5": {"strategy": "K512 APT-BTC", "activation": "D+28", "sleeve": "3%", "profit_per_yr": 302000},
        "grand_total_w1_w5": 1163000,
        "with_k481_builder_rebate": 1410000,
        "strategic_value": "K449 PASS unlocks entire $1.16M/yr family. 89x validation multiplier.",
    }

def build_risk_register():
    """K725 risk update (K723 context: K376 gone, K449 critical)."""
    return {
        "risks": [
            {
                "risk": "Paper vs LIVE Sharpe divergence",
                "severity": "MEDIUM",
                "trigger": "60d_sharpe < 5 OR fill_rate < 50%",
                "mitigation": "D7 rollback protocol — close both legs, reload --dry-run",
            },
            {
                "risk": "HL concentration breach >65%",
                "severity": "HIGH",
                "trigger": "HL exposure > 60% after K449 activation",
                "mitigation": "Daily verify post-activation; hold K476 if HL > 60%",
            },
            {
                "risk": "FR differential collapse (ETH=BTC FR)",
                "severity": "LOW",
                "trigger": "NEUTRAL state > 14 days",
                "mitigation": "No action; strategy auto-resumes when FR re-opens",
            },
            {
                "risk": "K280 sleeve cut profit loss",
                "severity": "MEDIUM",
                "trigger": "K280 30d Sharpe < 8",
                "mitigation": "Accept: $1.16M pipeline EV >> $247K K280 loss (pending K376)",
            },
            {
                "risk": "Week 2 cascade (K476+K484) concentration",
                "severity": "MEDIUM",
                "trigger": "HL exposure > 65% after K476",
                "mitigation": "48h gap between K476/K484; hold K484 if HL > 60%",
            },
        ]
    }

def main():
    """Generate K725 revised playbook."""
    output = {
        "wave_id": "K725",
        "title": "K449 Week 1 LIVE Revised Playbook (K723 Escalation)",
        "timestamp": datetime.now().isoformat() + " JST",
        "context": {
            "baseline": "K549 Day 0-7 Week 1 LIVE plan",
            "escalation": "K723 K376 indefinitely deferred → K449 elevated from secondary to PRIMARY",
            "profit_lift": "$13K/yr K449 + $260K/yr K481 = $260K Week 1 | $1.16M/yr W1-W5 pipeline",
        },
        "activation_steps": build_activation_steps(),
        "monitoring_spec": build_monitoring_spec(),
        "profit_cascade": build_profit_cascade(),
        "risk_register": build_risk_register(),
        "prerequisite": {
            "file": "scripts/leverage_manager.py",
            "field": "SLEEVE_WEIGHTS['K280']",
            "before": 0.75,
            "after": 0.60,
            "rationale": "K539 Phase B1 — frees 7.5pp HL headroom, enables K449 5% sleeve + K449 family W2-W5",
        },
        "deliverables": [
            "wave_k725_k449_revised.py (this file, K339 pattern)",
            "wave_k725_k449_revised.json (structured summary)",
            "wave_k725_k449_revised.md (user-actionable guide)",
            "report.html update (K449 Week 1 priority widget)",
        ],
    }

    # Write JSON
    json_path = REPO_ROOT / "wave_k725_k449_revised.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"✓ JSON: {json_path}")

    # Print summary
    print("\n=== K725 K449 Week 1 LIVE Revised Playbook ===")
    print(f"Context: {output['context']['escalation']}")
    print(f"Profit: {output['context']['profit_lift']}")
    print(f"Steps: {len(output['activation_steps']['activation_sequence'])} (D0 prereq + load + verify)")
    print(f"Risk: 5 items (HL concentration is CRITICAL)")
    print(f"Strategic value: K449 PASS validates $1.16M/yr W1-W5 pipeline (89x multiplier)")

if __name__ == "__main__":
    main()

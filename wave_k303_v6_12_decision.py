"""
Wave K303: v6.12 Final Architecture Decision
Operational risk-weighted analysis: K301c (Extended) vs K302a (HL-only) vs K287d (current)
"""

import json
import math
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# SECTION 1: Core Sharpe Metrics (from prior waves)
# ─────────────────────────────────────────────────────────────

ARCHITECTURES = {
    "K287d": {
        "label": "K287d (current v6.11)",
        "combined_Sh_55d": 33.0032,
        "n_exchanges": 3,
        "exchanges": ["Bybit", "HyperLiquid", "dYdX", "OKX"],
        "k275_dependency": True,
        "rwa_exposure": True,   # K270 = dYdX alt-perp
        "complexity": "Mid",
        "data_days": {"K270": 731, "K275": 96, "K280": 448},
        "wf_min_Sh": 30.1162,
        "max_dd": 0.0,
        "ann_ret": 0.1434,
        "composition": {"K280": 0.80, "K270": 0.071, "K275": 0.129},
    },
    "K301c": {
        "label": "K301c (Extended 4-exchange)",
        "combined_Sh_55d": 35.2593,
        "n_exchanges": 4,
        "exchanges": ["Bybit", "HyperLiquid", "dYdX", "OKX"],
        "k275_dependency": True,
        "rwa_exposure": True,  # K297 adds SPX + PAXG on HL
        "complexity": "High",
        "data_days": {"K270": 95, "K275": 95, "K297": 503, "K280": 447},
        "wf_min_Sh": 29.8544,
        "max_dd": 0.0,
        "ann_ret": 0.1466,
        "composition": {"K280": 0.80, "K270": 0.0656, "K275": 0.1044, "K297": 0.030},
    },
    "K302a": {
        "label": "K302a (HL-only 2-exchange)",
        "combined_Sh_55d": 32.5858,
        "n_exchanges": 2,
        "exchanges": ["Bybit", "HyperLiquid"],
        "k275_dependency": False,
        "rwa_exposure": True,  # K297 = PAXG + SPX on HL
        "complexity": "Low",
        "data_days": {"K297_PAXG": 415, "K297_SPX": 504, "K280": 448},
        "wf_min_Sh": 24.5278,  # 4-fold WF min
        "max_dd": 0.0,
        "ann_ret": 0.1028,
        "composition": {"K280": 0.80, "K297_PAXG": 0.12, "K297_SPX": 0.08},
    },
}

# ─────────────────────────────────────────────────────────────
# SECTION 2: Sharpe-per-Exchange Efficiency
# ─────────────────────────────────────────────────────────────

def compute_sh_per_exchange(archs):
    results = {}
    for name, a in archs.items():
        sh = a["combined_Sh_55d"]
        n_ex = a["n_exchanges"]
        results[name] = {
            "sharpe": sh,
            "n_exchanges": n_ex,
            "sh_per_exchange": round(sh / n_ex, 2),
        }
    return results

sh_eff = compute_sh_per_exchange(ARCHITECTURES)

# ─────────────────────────────────────────────────────────────
# SECTION 3: Counterparty Risk Scenario Analysis
# ─────────────────────────────────────────────────────────────

# Weight each component in the combined portfolio
# K280 = Bybit(~50%) + HL(~50%) based on K272a+K276b structure
# Satellite = 20% of total capital

COMPONENT_WEIGHTS = {
    # architecture → component → fraction of total capital at that exchange
    "K287d": {
        "dYdX (K270)": 0.20 * 0.355,      # 20% sat * 35.5% = 7.1%
        "OKX (K275)": 0.20 * 0.645,       # 20% sat * 64.5% = 12.9%
        "HL (K280-HL)": 0.80 * 0.50,      # 80% core * 50% = 40%
        "Bybit (K280-BB)": 0.80 * 0.50,   # 80% core * 50% = 40%
    },
    "K301c": {
        "dYdX (K270)": 0.20 * 0.3281,     # 20% sat * 32.8% = 6.6%
        "OKX (K275)": 0.20 * 0.5219,      # 20% sat * 52.2% = 10.4%
        "HL (K297+K280)": 0.20 * 0.15 + 0.80 * 0.50,  # K297=3% + K280-HL=40% = 43%
        "Bybit (K280-BB)": 0.80 * 0.50,   # 40%
    },
    "K302a": {
        "HL (K297+K280)": 0.20 * 1.0 + 0.80 * 0.50,  # K297=20% + K280-HL=40% = 60%
        "Bybit (K280-BB)": 0.80 * 0.50,               # 40%
        "dYdX (K270)": 0.0,
        "OKX (K275)": 0.0,
    },
}

# Outage impact = capital fraction at risk (positions must be closed / suspended)
# Sharpe impact estimated proportionally: losing X% of capital weight -> ~X% Sh loss (simplified)
# More precisely: Sh_impact ~ (lost_weight / total_weight) * Sh_combined

def compute_outage_scenarios(archs, weights):
    scenarios = {}
    for name, a in archs.items():
        sh = a["combined_Sh_55d"]
        w = weights[name]
        total_w = sum(w.values())
        s = {}
        for exch, frac in w.items():
            lost_frac = frac / total_w
            sh_after = sh * (1 - lost_frac)
            s[exch] = {
                "capital_fraction": round(frac, 4),
                "pct_of_total": round(frac * 100, 1),
                "Sh_after_outage": round(sh_after, 2),
                "Sh_delta": round(-sh * lost_frac, 2),
                "severity": "CRITICAL" if lost_frac > 0.40 else ("HIGH" if lost_frac > 0.20 else "MEDIUM" if lost_frac > 0.05 else "LOW"),
            }
        scenarios[name] = s
    return scenarios

outage_scenarios = compute_outage_scenarios(ARCHITECTURES, COMPONENT_WEIGHTS)

# ─────────────────────────────────────────────────────────────
# SECTION 4: Operational Overhead
# ─────────────────────────────────────────────────────────────

OPERATIONAL_OVERHEAD = {
    "K287d": {
        "api_monitors": 4,   # Bybit, HL, dYdX, OKX
        "plist_daemons": 4,
        "reconciliation_effort": "HIGH",   # 3-exchange settlement
        "subscription_costs": {
            "Glassnode/CoinGlass": 150,    # USD/month
            "dYdX_api": 0,
            "OKX_api": 0,
        },
        "rebalance_complexity": "MEDIUM",  # 3 components, monthly
        "k275_bug_risk": "YES - K291 bug history (fr_daily multiply)",
        "notes": "Requires K291 bug fix to be maintained in live K287 satellite daemon",
    },
    "K301c": {
        "api_monitors": 5,   # Bybit, HL, dYdX, OKX + separate K297 HL endpoint
        "plist_daemons": 5,
        "reconciliation_effort": "VERY HIGH",
        "subscription_costs": {
            "Glassnode/CoinGlass": 150,
            "dYdX_api": 0,
            "OKX_api": 0,
        },
        "rebalance_complexity": "HIGH",    # 4 components across 4 exchanges
        "k275_bug_risk": "YES - same K291 bug risk as K287d",
        "notes": "Most complex architecture; 4 exchanges require independent monitoring",
    },
    "K302a": {
        "api_monitors": 2,   # Bybit + HL only
        "plist_daemons": 3,  # K280-BB, K280-HL, K297-HL
        "reconciliation_effort": "LOW",
        "subscription_costs": {
            "Glassnode/CoinGlass": 150,
            "dYdX_api": 0,
            "OKX_api": 0,
        },
        "rebalance_complexity": "LOW",
        "k275_bug_risk": "NO - K275 eliminated",
        "notes": "All activity on 2 exchanges; K297 is HL-native (same infra as K280-HL)",
    },
}

# ─────────────────────────────────────────────────────────────
# SECTION 5: K275 Forward-Looking Risk Assessment
# ─────────────────────────────────────────────────────────────

K275_RISK = {
    "data_days": 96,
    "k291_fixed_Sh": 11.3155,   # K291 corrected backtest
    "k291_live_sh_pre_fix": -3.55,
    "k291_live_sh_post_fix": 30.85,
    "data_caveat": "Only 96d OKX history — binding constraint for all K301 variants",
    "bug_history": "K291 found fr_daily multiply bug — deployed fix required maintenance",
    "regime_dependence": "Cross-sectional FR sign matters; K295 ruled out BTC FR sign reversal for K275",
    "production_confidence": "MEDIUM",
    "vs_k297": {
        "k297_data_days": 504,
        "k297_paxg_Sh": 16.91,
        "k297_portfolio_Sh": 10.13,
        "k297_production_confidence": "HIGH",
        "k297_data_advantage": "5.25x more data history",
        "k297_bug_risk": "None — simpler always-on FR carry, no signal processing",
    },
}

# ─────────────────────────────────────────────────────────────
# SECTION 6: Robustness Analysis
# ─────────────────────────────────────────────────────────────

ROBUSTNESS = {
    "K287d": {
        "SPOF_analysis": {
            "HL_outage": "CATASTROPHIC — K280-HL (40%) + partial satellite exposure",
            "Bybit_outage": "SEVERE — K280-Bybit (40%) suspended",
            "dYdX_outage": "LOW — only 7.1% capital, K270 satellite can stop",
            "OKX_outage": "MEDIUM — 12.9% capital, K275 stops",
        },
        "exchange_diversification": "GOOD for satellite (dYdX, OKX separate from HL)",
        "data_risk": "HIGH — K275 only 96d history; K291 bug susceptible",
        "regime_risk": "MEDIUM — K270 dYdX has 731d data, robust",
    },
    "K301c": {
        "SPOF_analysis": {
            "HL_outage": "CATASTROPHIC — K280-HL (40%) + K297 (3%)",
            "Bybit_outage": "SEVERE — K280-Bybit (40%) suspended",
            "dYdX_outage": "LOW — 6.6% capital",
            "OKX_outage": "MEDIUM — 10.4% capital",
        },
        "exchange_diversification": "BEST — 4 exchanges, most distributed satellite",
        "data_risk": "HIGH — K275 96d binding constraint; K291 bug risk",
        "regime_risk": "MEDIUM — K270 robust, K297 SPX/PAXG regime-independent",
    },
    "K302a": {
        "SPOF_analysis": {
            "HL_outage": "DEVASTATING — 60% of capital (K280-HL 40% + K297 20%)",
            "Bybit_outage": "SEVERE — 40% capital",
            "dYdX_outage": "N/A — not exposed",
            "OKX_outage": "N/A — not exposed",
        },
        "exchange_diversification": "WORST — HL holds 60% of capital",
        "data_risk": "LOW — K297 has 504d data, no K275 bug risk",
        "regime_risk": "LOW — SPX/PAXG FR carry is regime-independent RWA exposure",
    },
}

# ─────────────────────────────────────────────────────────────
# SECTION 7: Decision Matrix Weighted Scoring
# ─────────────────────────────────────────────────────────────

# Factor weights for risk-adjusted decision
FACTOR_WEIGHTS = {
    "sharpe_55d":           0.20,  # Raw performance
    "sh_per_exchange":      0.15,  # Efficiency
    "wf_stability":         0.15,  # Walk-forward min Sh
    "data_quality":         0.15,  # Data days / confidence
    "operational_simplicity": 0.15, # Exchanges, overhead
    "hl_concentration_risk": 0.10, # HL-only risk penalty
    "k275_risk":            0.10,  # K275 specific fragility
}

# Score each factor 1-10 (10=best)
FACTOR_SCORES = {
    "K287d": {
        "sharpe_55d":            7.0,  # 33.00 — current benchmark
        "sh_per_exchange":       7.0,  # 11.00 Sh/exchange
        "wf_stability":          8.5,  # min 30.1 across WF folds
        "data_quality":          6.0,  # K275 only 96d; K270 731d
        "operational_simplicity": 6.5, # 3 exchanges, medium complexity
        "hl_concentration_risk": 7.5,  # HL holds ~40% (same as others)
        "k275_risk":             5.0,  # K275 dependency + bug history
    },
    "K301c": {
        "sharpe_55d":            9.0,  # 35.26 — best Sh
        "sh_per_exchange":       4.0,  # 8.82 Sh/exchange — worst efficiency
        "wf_stability":          8.0,  # min 29.85 across WF folds
        "data_quality":          5.0,  # K275 96d binding constraint
        "operational_simplicity": 3.0, # 4 exchanges, highest complexity
        "hl_concentration_risk": 7.5,  # HL ~43% (slight increase from K297)
        "k275_risk":             4.0,  # K275 dependency + more weight than K287d
    },
    "K302a": {
        "sharpe_55d":            6.5,  # 32.59 — lowest but passes 95% threshold
        "sh_per_exchange":      10.0,  # 16.30 Sh/exchange — best efficiency
        "wf_stability":          7.0,  # min 24.53 (4-fold WF, longer history)
        "data_quality":         10.0,  # K297 504d data, no K275 bug
        "operational_simplicity": 9.5, # 2 exchanges, lowest overhead
        "hl_concentration_risk": 3.5,  # HL holds 60% — concentrated risk
        "k275_risk":            10.0,  # No K275 dependency
    },
}

def compute_weighted_score(factor_scores, factor_weights):
    scores = {}
    for arch in factor_scores:
        total = sum(
            factor_scores[arch][f] * factor_weights[f]
            for f in factor_weights
        )
        scores[arch] = round(total, 3)
    return scores

weighted_scores = compute_weighted_score(FACTOR_SCORES, FACTOR_WEIGHTS)

# ─────────────────────────────────────────────────────────────
# SECTION 8: Equity Curve Data for Comparison
# ─────────────────────────────────────────────────────────────

# Load existing curves from prior waves
with open("/Users/nekonaomichi/crypto-lab/wave_k301_curves.json") as f:
    k301_curves = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k302_curves.json") as f:
    k302_curves = json.load(f)

# Build combined curves output
k303_curves = {
    "wave": "K303",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "description": "Combined equity curves for K303 v6.12 decision",
    "three_way_dates": k301_curves.get("three_way_dates", []),
    "K287d_equity": k302_curves.get("K287d_55d_equity", []),
    "K301c_equity": k301_curves.get("K301_c_equity", []),
    "K302a_equity": k302_curves.get("K302a_comb_equity", []),
}

# ─────────────────────────────────────────────────────────────
# SECTION 9: Final Decision
# ─────────────────────────────────────────────────────────────

winner = max(weighted_scores, key=weighted_scores.get)

DEPLOYMENT_PLAN = {
    "recommended_architecture": winner,
    "reasoning_summary": (
        "K302a achieves 16.30 Sh/exchange vs K301c's 8.82, eliminating K275 data fragility "
        "(96d caveat + K291 bug history). While K302a's combined Sh=32.59 is 2.0% below K287d "
        "(current) and 7.6% below K301c, the operational simplification (2 vs 3-4 exchanges), "
        "elimination of K275 risk, and K297's 5.25x data advantage justify the modest Sh trade-off. "
        "The 60% HL concentration is the main risk offset: mitigated by HL's strong track record "
        "and K280's proven 400+ day history on HL infrastructure."
    ),
    "monitoring_triggers": {
        "HL_15min_ping": "Alert if HL API latency > 500ms for 3 consecutive checks",
        "satellite_MaxDD_stop": "Stop K297 satellite if daily DD > -0.5% (half of K297 full-period MaxDD)",
        "combined_Sh_floor": "Re-evaluate architecture if rolling 30d combined Sh < 20.0",
        "K302a_55d_Sh_floor": "Revert to K287d if K302a combined 55d Sh < 28.0",
        "bybit_halt": "K280 auto-pauses on Bybit if position reconciliation fails for 2 consecutive 8h periods",
    },
    "paper_trade_timeline": {
        "phase_1_shadow": "Day 1-14: K302a runs paper alongside K287d live; compare daily PnL",
        "phase_2_parallel_live": "Day 15-30: K302a goes live at 20% of target capital",
        "phase_3_full_deploy": "Day 31+: Full capital allocation if 30d Sh >= 25.0",
        "rollback_condition": "If 14d Sh < 20.0 or MaxDD < -0.3%, revert to K287d",
    },
    "deprecation_plan": {
        "dYdX_account": "Close K270 positions Day 0; maintain account for 30d (residuals)",
        "OKX_account": "Stop K275 daemon Day 0; maintain account for 14d (settlement)",
        "K287d": "Keep K287d plist disabled but installed for 60d as rollback option",
    },
}

# ─────────────────────────────────────────────────────────────
# SECTION 10: Assemble JSON Output
# ─────────────────────────────────────────────────────────────

decision_output = {
    "wave": "K303",
    "objective": "v6.12 Final Architecture Decision",
    "generated_at": datetime.utcnow().isoformat() + "Z",

    "sharpe_per_exchange": sh_eff,

    "counterparty_outage_scenarios": outage_scenarios,

    "operational_overhead": OPERATIONAL_OVERHEAD,

    "k275_forward_risk": K275_RISK,

    "robustness_analysis": ROBUSTNESS,

    "decision_matrix": {
        "factor_weights": FACTOR_WEIGHTS,
        "factor_scores": FACTOR_SCORES,
        "weighted_scores": weighted_scores,
    },

    "architectures": {
        k: {
            "label": v["label"],
            "combined_Sh_55d": v["combined_Sh_55d"],
            "n_exchanges": v["n_exchanges"],
            "sh_per_exchange": sh_eff[k]["sh_per_exchange"],
            "wf_min_Sh": v["wf_min_Sh"],
            "max_dd": v["max_dd"],
            "ann_ret": v["ann_ret"],
            "k275_dependency": v["k275_dependency"],
            "complexity": v["complexity"],
        }
        for k, v in ARCHITECTURES.items()
    },

    "final_recommendation": {
        "winner": winner,
        "winner_label": ARCHITECTURES[winner]["label"],
        "winner_score": weighted_scores[winner],
        "runner_up": sorted(weighted_scores, key=weighted_scores.get)[-2],
        "score_margin": round(
            weighted_scores[winner] - sorted(weighted_scores.values())[-2], 3
        ),
        "deployment_plan": DEPLOYMENT_PLAN,
    },

    "v6_12_production_architecture": {
        "name": winner,
        "core": "K280 (80% capital) — Bybit + HyperLiquid",
        "satellite": "K297 PAXG/SPX FR Carry (20% capital) — HyperLiquid only",
        "total_exchanges": 2,
        "rationale": DEPLOYMENT_PLAN["reasoning_summary"],
    },
}

# Save JSON
with open("/Users/nekonaomichi/crypto-lab/wave_k303_v6_12_decision.json", "w") as f:
    json.dump(decision_output, f, indent=2)

# Save curves
with open("/Users/nekonaomichi/crypto-lab/wave_k303_curves.json", "w") as f:
    json.dump(k303_curves, f, indent=2)

# ─────────────────────────────────────────────────────────────
# Console Summary
# ─────────────────────────────────────────────────────────────

print("=" * 65)
print("K303 v6.12 FINAL ARCHITECTURE DECISION")
print("=" * 65)

print("\n[1] SHARPE-PER-EXCHANGE EFFICIENCY")
print(f"{'Architecture':<15} {'Sh 55d':>8} {'N_ex':>5} {'Sh/ex':>8}")
for k, v in sh_eff.items():
    print(f"  {k:<13} {v['sharpe']:>8.2f} {v['n_exchanges']:>5d} {v['sh_per_exchange']:>8.2f}")

print("\n[2] HL OUTAGE IMPACT (most critical single exchange)")
for arch, scenarios in outage_scenarios.items():
    for exch, data in scenarios.items():
        if "HL" in exch:
            print(f"  {arch}: HL outage -> Sh from {ARCHITECTURES[arch]['combined_Sh_55d']:.2f} to {data['Sh_after_outage']:.2f} ({data['pct_of_total']}% capital at risk) [{data['severity']}]")

print("\n[3] WEIGHTED DECISION SCORES")
for k, score in sorted(weighted_scores.items(), key=lambda x: -x[1]):
    print(f"  {k:<10} : {score:.3f}")

print(f"\n[4] RECOMMENDATION: {winner} — {ARCHITECTURES[winner]['label']}")
print(f"    Score: {weighted_scores[winner]:.3f} (margin: +{decision_output['final_recommendation']['score_margin']:.3f} over runner-up)")
print(f"    Sh 55d: {ARCHITECTURES[winner]['combined_Sh_55d']} | Exchanges: {ARCHITECTURES[winner]['n_exchanges']} | Sh/ex: {sh_eff[winner]['sh_per_exchange']}")

print("\n[5] v6.12 PRODUCTION ARCHITECTURE DECISION")
arch = decision_output["v6_12_production_architecture"]
print(f"    Architecture : {arch['name']}")
print(f"    Core         : {arch['core']}")
print(f"    Satellite    : {arch['satellite']}")
print(f"    Exchanges    : {arch['total_exchanges']}")

print("\nFiles saved:")
print("  wave_k303_v6_12_decision.json")
print("  wave_k303_curves.json")
print("  (wave_k303_v6_12_decision.md generated separately)")

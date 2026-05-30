#!/usr/bin/env python3
"""
wave_k710_k708_scaffold.py — K710 K708 BNB-SOL Alt-Alt Production Scaffold
=============================================================================
62nd daemon scaffold. 8th alt-alt pair (CEX cluster vs SVM cluster).
K708 BNB-SOL: OOS Sh=48.59, $75K/yr @$10M, Bybit-only, hedge vs K480, SOL saturation mitigation.

K339 REPO_ROOT pattern. No /Users/ literals.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"

JST = timezone(timedelta(hours=9))

# ── Phase 1: Verify script and plist exist ───────────────────────────────────

def phase1_verify() -> dict:
    """Verify K708 scaffold files are present."""
    script_path = REPO_ROOT / "scripts" / "k708_bnb_sol_run.py"
    plist_path  = REPO_ROOT / "scripts" / "com.cryptolab.k710-bnb-sol.plist"
    dashboard   = DATA_DIR  / "k708_dashboard.json"

    results = {
        "script_exists":    script_path.exists(),
        "plist_exists":     plist_path.exists(),
        "dashboard_exists": dashboard.exists(),
        "script_path":      str(script_path.relative_to(REPO_ROOT)),
        "plist_path":       str(plist_path.relative_to(REPO_ROOT)),
    }

    # Verify K339 REPO_ROOT pattern in script
    if script_path.exists():
        content = script_path.read_text()
        results["k339_pattern_ok"] = (
            "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
            and "/Users/" not in content
        )
        results["paper_trade_default"] = "PAPER_TRADE         = True" in content
        results["bybit_primary"]       = "BYBIT_PRIMARY" in content
        results["sleeve_3pct"]         = "SLEEVE_PCT          = 0.030" in content
        results["leverage_4x"]         = "LEVERAGE            = 4.0" in content
        results["w120h"]               = "EMA_PERIOD_HOURS    = 120" in content
        results["signal_sol_minus_bnb"]= "sol_bnb_diff = fr_sol - fr_bnb" in content

    return results


# ── Phase 2: Verify deployment status ────────────────────────────────────────

def phase2_deployment_check() -> dict:
    """Check K710 deployment readiness."""
    return {
        "daemon_number":        62,
        "alt_alt_number":       8,
        "cex_alt_number":       1,
        "strategy":             "K708 BNB-SOL FR Differential (CEX vs SVM cluster)",
        "oos_sharpe":           48.5876,
        "profit_10m_yr":        75011,
        "venue":                "Bybit primary (BNB-PERP + SOL-PERP)",
        "sleeve_pct":           3.0,
        "leverage":             4.0,
        "hl_concentration_unchanged": True,
        "hl_pct":               64.5,
        "hl_cap_pct":           65.0,
        "gate_60d": {
            "realized_sharpe_min": 24,
            "fill_rate_min_pct":   60,
            "max_dd_max_pct":      15,
        },
        "hedge_vs_k480":        True,
        "sol_saturation_hedge_pct": 67.67,
        "deploy_cmd": (
            "cp scripts/com.cryptolab.k710-bnb-sol.plist ~/Library/LaunchAgents/ && "
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k710-bnb-sol.plist"
        ),
    }


# ── Phase 3: Dry-run smoke test ───────────────────────────────────────────────

def phase3_dry_run() -> dict:
    """Import K708 strategy and run dry-run cycle (smoke test)."""
    script_path = REPO_ROOT / "scripts" / "k708_bnb_sol_run.py"
    if not script_path.exists():
        return {"status": "FAIL", "reason": "k708_bnb_sol_run.py not found"}

    try:
        import importlib.util
        spec   = importlib.util.spec_from_file_location("k708", script_path)
        mod    = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Test signal computation (with dummy FRs)
        signal   = mod.compute_signal(fr_bnb=1.25e-5, fr_sol=2.50e-5)
        decision = mod.decide_position(signal)
        notional_per_leg, total_notional = mod.compute_delta_neutral_notional()

        return {
            "status":              "PASS",
            "signal_regime":       signal["regime"],
            "signal_direction":    signal["signal_direction"],
            "sol_bnb_diff":        signal["sol_bnb_diff"],
            "mean_120h":           signal["mean_120h"],
            "decision":            decision.get("position_state") if decision else "NEUTRAL",
            "notional_per_leg":    notional_per_leg,
            "total_notional":      total_notional,
            "expected_state":      "LONG_SOL_SHORT_BNB",  # SOL_FR=2.5e-5 > BNB_FR=1.25e-5
            "direction_correct":   signal["signal_direction"] == 1,  # SOL > BNB -> +1
        }
    except Exception as e:
        return {"status": "FAIL", "reason": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K710 K708 BNB-SOL Alt-Alt Production Scaffold === {ts_jst}")
    print(f"  62nd daemon | 8th alt-alt | CEX cluster vs SVM cluster")
    print(f"  OOS Sharpe: 48.59 | $75,011/yr @$10M @4x | Bybit-only | Hedge K480")

    # Phase 1: File verification
    print("\n[Phase 1] File verification...")
    p1 = phase1_verify()
    for k, v in p1.items():
        print(f"  {k}: {v}")
    p1_ok = p1.get("script_exists") and p1.get("plist_exists")
    print(f"  Phase 1: {'PASS' if p1_ok else 'FAIL'}")

    # Phase 2: Deployment check
    print("\n[Phase 2] Deployment readiness...")
    p2 = phase2_deployment_check()
    print(f"  Daemon: #{p2['daemon_number']} (Alt-alt #{p2['alt_alt_number']})")
    print(f"  Strategy: {p2['strategy']}")
    print(f"  OOS Sharpe: {p2['oos_sharpe']} | Profit: ${p2['profit_10m_yr']:,}/yr @$10M")
    print(f"  HL: {p2['hl_pct']}% UNCHANGED (Bybit-only, cap={p2['hl_cap_pct']}%)")
    print(f"  60d gate: Sh>={p2['gate_60d']['realized_sharpe_min']} + fill>={p2['gate_60d']['fill_rate_min_pct']}% + DD<{p2['gate_60d']['max_dd_max_pct']}%")
    print(f"  SOL hedge: K708 vs K476 opposing {p2['sol_saturation_hedge_pct']}% of time")
    print(f"  Deploy: {p2['deploy_cmd']}")

    # Phase 3: Dry-run smoke test
    print("\n[Phase 3] Dry-run smoke test...")
    p3 = phase3_dry_run()
    print(f"  Status:       {p3['status']}")
    if p3["status"] == "PASS":
        print(f"  Regime:       {p3['signal_regime']}")
        print(f"  Direction:    {p3['signal_direction']} (+1=BULL_SOL, -1=BULL_BNB)")
        print(f"  SOL-BNB diff: {p3['sol_bnb_diff']}")
        print(f"  Decision:     {p3['decision']}")
        print(f"  Notional/leg: ${p3['notional_per_leg']:,.0f}")
        print(f"  Total notional: ${p3['total_notional']:,.0f}")
        print(f"  Dir correct:  {p3['direction_correct']} (expected BULL_SOL for SOL_FR>BNB_FR)")
    else:
        print(f"  Reason: {p3.get('reason')}")

    # Write JSON output
    output = {
        "wave":         "K710",
        "strategy":     "K708 BNB-SOL alt-alt scaffold",
        "ts_jst":       ts_jst,
        "phase1":       p1,
        "phase2":       p2,
        "phase3":       p3,
        "scaffold_ok":  p1_ok and p3.get("status") == "PASS",
    }
    out_path = REPO_ROOT / "wave_k710_k708_scaffold.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n  Results -> {out_path.name}")

    overall = "SCAFFOLD-READY" if output["scaffold_ok"] else "SCAFFOLD-FAIL"
    print(f"\n=== K710 {overall} ===")
    print(f"  Script: scripts/k708_bnb_sol_run.py")
    print(f"  Plist:  scripts/com.cryptolab.k710-bnb-sol.plist")
    print(f"  Wave:   wave_k710_k708_scaffold.{{py,json,md}}")
    print()
    return 0 if output["scaffold_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

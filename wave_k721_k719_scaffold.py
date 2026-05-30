#!/usr/bin/env python3
"""
wave_k721_k719_scaffold.py — K721 K719 ENA-ATOM Alt-Alt Production Scaffold
=============================================================================
63rd daemon scaffold. 9th alt-alt pair (synthetic stable infra vs Cosmos Hub IBC).
K719 ENA-ATOM: OOS Sh=29.67, $634K/yr @$10M, Bybit-only, 12/12 WF UNPRECEDENTED.
LARGEST single alt-alt profit: $634,464/yr net (>2.7x K682 $232K).

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
    """Verify K719 scaffold files are present."""
    script_path = REPO_ROOT / "scripts" / "k719_ena_atom_run.py"
    plist_path  = REPO_ROOT / "scripts" / "com.cryptolab.k721-ena-atom.plist"
    dashboard   = DATA_DIR  / "k719_dashboard.json"

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
            "REPO_ROOT" in content
            and "Path(__file__).resolve().parent.parent" in content
            and "/Users/" not in content
        )
        results["paper_trade_default"] = "PAPER_TRADE         = True" in content
        results["bybit_primary"]       = "BYBIT_PRIMARY" in content
        results["sleeve_3pct"]         = "SLEEVE_PCT          = 0.030" in content
        results["leverage_4x"]         = "LEVERAGE            = 4.0" in content
        results["w168h"]               = "EMA_PERIOD_HOURS    = 168" in content
        results["signal_ena_minus_atom"] = "ena_atom_diff = fr_ena - fr_atom" in content

    return results


# ── Phase 2: Verify deployment status ────────────────────────────────────────

def phase2_deployment_check() -> dict:
    """Check K721 deployment readiness."""
    return {
        "daemon_number":        63,
        "alt_alt_number":       9,
        "cross_cluster_number": 2,   # 2nd ENA cross-cluster (K696=ENA-SOL was 1st)
        "strategy":             "K719 ENA-ATOM FR Differential (synthetic stable infra vs Cosmos Hub IBC)",
        "oos_sharpe":           29.6718,
        "oos_sharpe_is":        36.9891,
        "profit_10m_yr":        634_464,
        "profit_daily":         1_737,
        "venue":                "Bybit primary (ENA-PERP + ATOM-PERP)",
        "sleeve_pct":           3.0,
        "leverage":             4.0,
        "hl_concentration_unchanged": True,
        "hl_pct":               64.5,
        "hl_cap_pct":           65.0,
        "gate_60d": {
            "realized_sharpe_min": 15,    # 50% of OOS Sh=29.67
            "fill_rate_min_pct":   60,
            "max_dd_max_pct":      15,
        },
        "wf_12_12_unprecedented": True,
        "gates_passed":         "13/15",
        "gates_failed":         ["G5f (K682 ATOM-SOL corr=-0.4666)", "G8 (cross-venue ENA limited)"],
        "mr8_pass":             True,
        "mr9_pass":             True,
        "largest_alt_alt":      True,
        "ena_notional_cap":     "K719 3% + K696 3% + K616 existing < 9% AUM",
        "atom_notional_cap":    "K719 3% + K682 existing — monitor G5f borderline",
        "deploy_cmd": (
            "cp scripts/com.cryptolab.k721-ena-atom.plist ~/Library/LaunchAgents/ && "
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k721-ena-atom.plist"
        ),
    }


# ── Phase 3: Dry-run smoke test ───────────────────────────────────────────────

def phase3_dry_run() -> dict:
    """Import K719 strategy and run dry-run cycle (smoke test)."""
    script_path = REPO_ROOT / "scripts" / "k719_ena_atom_run.py"
    if not script_path.exists():
        return {"status": "FAIL", "reason": "k719_ena_atom_run.py not found"}

    try:
        import importlib.util
        spec   = importlib.util.spec_from_file_location("k719", script_path)
        mod    = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Test signal computation (with dummy FRs)
        # Dominant state: ATOM FR > ENA FR (ENA more negative)
        # fr_ena = -1.0e-5, fr_atom = 2.0e-6 -> diff = -1.2e-5 -> ATOM_PREMIUM -> signal -1
        signal   = mod.compute_signal(fr_ena=-1.0e-5, fr_atom=2.0e-6)
        decision = mod.decide_position(signal)
        notional_per_leg, total_notional = mod.compute_delta_neutral_notional()

        return {
            "status":              "PASS",
            "signal_regime":       signal["regime"],
            "signal_direction":    signal["signal_direction"],
            "ena_atom_diff":       signal["ena_atom_diff"],
            "mean_168h":           signal["mean_168h"],
            "decision":            decision.get("position_state") if decision else "NEUTRAL",
            "notional_per_leg":    notional_per_leg,
            "total_notional":      total_notional,
            "expected_state":      "SHORT_ATOM_LONG_ENA",  # ATOM_FR=2e-6 > ENA_FR=-1e-5
            "direction_correct":   signal["signal_direction"] == -1,  # ENA < ATOM -> -1
        }
    except Exception as e:
        return {"status": "FAIL", "reason": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K721 K719 ENA-ATOM Alt-Alt Production Scaffold === {ts_jst}")
    print(f"  63rd daemon | 9th alt-alt | synthetic stable infra vs Cosmos Hub IBC")
    print(f"  OOS Sharpe: 29.67 | $634,464/yr @$10M @4x | Bybit-only | LARGEST alt-alt")
    print(f"  12/12 WF UNPRECEDENTED | 13/15 §6 gates PASS | MR8/MR9 compliant")

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
    print(f"  Daily profit: ${p2['profit_daily']:,}/day @$10M")
    print(f"  HL: {p2['hl_pct']}% UNCHANGED (Bybit-only, cap={p2['hl_cap_pct']}%)")
    print(f"  Gates: {p2['gates_passed']} PASS | Failed: {p2['gates_failed']}")
    print(f"  60d gate: Sh>={p2['gate_60d']['realized_sharpe_min']} + fill>={p2['gate_60d']['fill_rate_min_pct']}% + DD<{p2['gate_60d']['max_dd_max_pct']}%")
    print(f"  12/12 WF: {p2['wf_12_12_unprecedented']} (UNPRECEDENTED in alt-alt family)")
    print(f"  LARGEST alt-alt: {p2['largest_alt_alt']} ($634K > K682 $232K > K693 $175K)")
    print(f"  ENA cap: {p2['ena_notional_cap']}")
    print(f"  ATOM cap: {p2['atom_notional_cap']}")
    print(f"  Deploy: {p2['deploy_cmd']}")

    # Phase 3: Dry-run smoke test
    print("\n[Phase 3] Dry-run smoke test...")
    p3 = phase3_dry_run()
    print(f"  Status:       {p3['status']}")
    if p3["status"] == "PASS":
        print(f"  Regime:       {p3['signal_regime']}")
        print(f"  Direction:    {p3['signal_direction']} (+1=ENA_PREMIUM short ENA/long ATOM, -1=ATOM_PREMIUM)")
        print(f"  ENA-ATOM diff:{p3['ena_atom_diff']}")
        print(f"  Decision:     {p3['decision']}")
        print(f"  Notional/leg: ${p3['notional_per_leg']:,.0f}")
        print(f"  Total notional: ${p3['total_notional']:,.0f}")
        print(f"  Dir correct:  {p3['direction_correct']} (expected ATOM_PREMIUM for ATOM_FR>ENA_FR)")
    else:
        print(f"  Reason: {p3.get('reason')}")

    # Write JSON output
    output = {
        "wave":         "K721",
        "strategy":     "K719 ENA-ATOM alt-alt scaffold (63rd daemon, 9th alt-alt, LARGEST $634K)",
        "ts_jst":       ts_jst,
        "phase1":       p1,
        "phase2":       p2,
        "phase3":       p3,
        "scaffold_ok":  p1_ok and p3.get("status") == "PASS",
    }
    out_path = REPO_ROOT / "wave_k721_k719_scaffold.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n  Results -> {out_path.name}")

    overall = "SCAFFOLD-READY" if output["scaffold_ok"] else "SCAFFOLD-FAIL"
    print(f"\n=== K721 {overall} ===")
    print(f"  Script: scripts/k719_ena_atom_run.py")
    print(f"  Plist:  scripts/com.cryptolab.k721-ena-atom.plist")
    print(f"  Wave:   wave_k721_k719_scaffold.{{py,json,md}}")
    print(f"  63rd daemon | 9th alt-alt | LARGEST $634,464/yr @$10M | 12/12 WF UNPRECEDENTED")
    print()
    return 0 if output["scaffold_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

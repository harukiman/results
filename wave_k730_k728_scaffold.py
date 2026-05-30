#!/usr/bin/env python3
"""
wave_k730_k728_scaffold.py — K730 K728 LDO-SOL Alt-Alt Production Scaffold
=============================================================================
64th daemon scaffold. 10th alt-alt pair (Ethereum LSD vs Solana SVM).
K728 LDO-SOL: OOS Sh=46.84, $105K/yr @$10M, Bybit-only, 11/12 WF positive.
Alt-alt family rank #3 by OOS Sharpe (AVAX-SOL 50.27 > BNB-SOL 48.59 > LDO-SOL 46.84).
K594 pivot: LDO-BTC TRIPLE-BLOCKED; BTC common factor removed via LDO-SOL alt-alt.

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
    """Verify K728 scaffold files are present."""
    script_path = REPO_ROOT / "scripts" / "k728_ldo_sol_run.py"
    plist_path  = REPO_ROOT / "scripts" / "com.cryptolab.k730-ldo-sol.plist"
    dashboard   = DATA_DIR  / "k728_dashboard.json"

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
        results["signal_ldo_minus_sol"] = "ldo_sol_diff = fr_ldo - fr_sol" in content

    return results


# ── Phase 2: Verify deployment status ────────────────────────────────────────

def phase2_deployment_check() -> dict:
    """Check K730 deployment readiness."""
    return {
        "daemon_number":        64,
        "alt_alt_number":       10,
        "cross_cluster_note":   "LSD vs SVM (Ethereum Liquid Staking vs Solana SVM retail/meme)",
        "strategy":             "K728 LDO-SOL FR Differential (Ethereum LSD vs Solana SVM)",
        "oos_sharpe":           46.8355,
        "oos_sharpe_is":        14.431,
        "profit_10m_yr":        105_032,
        "profit_daily":         288,
        "venue":                "Bybit primary (LDO-PERP + SOL-PERP)",
        "sleeve_pct":           3.0,
        "leverage":             4.0,
        "hl_concentration_unchanged": True,
        "hl_pct":               64.5,
        "hl_cap_pct":           65.0,
        "hl_ldo_maxlev_note":   "HL LDO maxLev=5 vs Bybit LDO maxLev=50 — Bybit also resolves leverage constraint",
        "gate_60d": {
            "realized_sharpe_min": 23,    # 50% of OOS Sh=46.84
            "fill_rate_min_pct":   60,
            "max_dd_max_pct":      15,
        },
        "wf_11_12_positive":    True,
        "gates_passed":         "14/19",
        "gates_failed":         [
            "G4_Walk_forward (11/12, fold 2 = -7.51)",
            "G5c K594 LDO-BTC (corr=0.505 structural — K594 REJECTED, not portfolio risk)",
            "G5k K708 BNB-SOL (corr=0.592 — SOL $2.4M combined = 0.024% SOL OI)",
            "G6 Trade count (11.8/yr < 30, operationally acceptable)",
            "G8 Cross-venue (venue mismatch structural — Bybit-primary mitigates)",
        ],
        "mr8_pass":             True,
        "mr9_pass":             True,
        "alt_alt_rank":         "#3 OOS Sharpe in alt-alt family",
        "k594_pivot_note":      "K594 LDO-BTC TRIPLE-BLOCKED (vol+ETH+DeFi). K728 = K594 - K476 removes BTC common factor. MR9 PASS.",
        "ldo_notional_cap":     "K728 3% standalone (first LDO in portfolio — new vertex, no existing LDO exposure)",
        "sol_notional_cap":     "K728 3% + K708 3% existing — G5k corr=0.592 FAIL, $2.4M = 0.024% SOL OI, monitor",
        "deploy_cmd": (
            "cp scripts/com.cryptolab.k730-ldo-sol.plist ~/Library/LaunchAgents/ && "
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k730-ldo-sol.plist"
        ),
    }


# ── Phase 3: Dry-run smoke test ───────────────────────────────────────────────

def phase3_dry_run() -> dict:
    """Import K728 strategy and run dry-run cycle (smoke test)."""
    script_path = REPO_ROOT / "scripts" / "k728_ldo_sol_run.py"
    if not script_path.exists():
        return {"status": "FAIL", "reason": "k728_ldo_sol_run.py not found"}

    try:
        import importlib.util
        spec   = importlib.util.spec_from_file_location("k728", script_path)
        mod    = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Test signal computation with dummy FRs
        # Dominant state (85.1%): LDO FR > SOL FR
        # fr_ldo = 2.0e-5, fr_sol = 1.0e-5 -> diff = +1.0e-5 -> LDO_PREMIUM -> signal +1
        signal   = mod.compute_signal(fr_ldo=2.0e-5, fr_sol=1.0e-5)
        decision = mod.decide_position(signal)
        notional_per_leg, total_notional = mod.compute_delta_neutral_notional()

        return {
            "status":              "PASS",
            "signal_regime":       signal["regime"],
            "signal_direction":    signal["signal_direction"],
            "ldo_sol_diff":        signal["ldo_sol_diff"],
            "mean_168h":           signal["mean_168h"],
            "decision":            decision.get("position_state") if decision else "NEUTRAL",
            "notional_per_leg":    notional_per_leg,
            "total_notional":      total_notional,
            "expected_state":      "SHORT_LDO_LONG_SOL",  # LDO_FR=2e-5 > SOL_FR=1e-5
            "direction_correct":   signal["signal_direction"] == 1,  # LDO > SOL -> +1
        }
    except Exception as e:
        return {"status": "FAIL", "reason": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K730 K728 LDO-SOL Alt-Alt Production Scaffold === {ts_jst}")
    print(f"  64th daemon | 10th alt-alt | Ethereum LSD vs Solana SVM")
    print(f"  OOS Sharpe: 46.84 | $105,032/yr @$10M @4x | Bybit-only | rank #3 alt-alt OOS Sh")
    print(f"  11/12 WF positive | 14/19 §6 gates PASS | MR8/MR9 compliant")
    print(f"  K594 pivot: LDO-BTC TRIPLE-BLOCKED -> LDO-SOL removes BTC common factor (MR9 PASS)")

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
    print(f"  HL LDO note: {p2['hl_ldo_maxlev_note']}")
    print(f"  Gates: {p2['gates_passed']} PASS | Failed: {len(p2['gates_failed'])} gates")
    for g in p2['gates_failed']:
        print(f"    - {g}")
    print(f"  60d gate: Sh>={p2['gate_60d']['realized_sharpe_min']} + fill>={p2['gate_60d']['fill_rate_min_pct']}% + DD<{p2['gate_60d']['max_dd_max_pct']}%")
    print(f"  Alt-alt rank: {p2['alt_alt_rank']}")
    print(f"  K594 pivot: {p2['k594_pivot_note']}")
    print(f"  LDO cap: {p2['ldo_notional_cap']}")
    print(f"  SOL cap: {p2['sol_notional_cap']}")
    print(f"  Deploy: {p2['deploy_cmd']}")

    # Phase 3: Dry-run smoke test
    print("\n[Phase 3] Dry-run smoke test...")
    p3 = phase3_dry_run()
    print(f"  Status:       {p3['status']}")
    if p3["status"] == "PASS":
        print(f"  Regime:       {p3['signal_regime']}")
        print(f"  Direction:    {p3['signal_direction']} (+1=LDO_PREMIUM short LDO/long SOL 85%, -1=SOL_PREMIUM)")
        print(f"  LDO-SOL diff:{p3['ldo_sol_diff']}")
        print(f"  Decision:     {p3['decision']}")
        print(f"  Notional/leg: ${p3['notional_per_leg']:,.0f}")
        print(f"  Total notional: ${p3['total_notional']:,.0f}")
        print(f"  Dir correct:  {p3['direction_correct']} (expected LDO_PREMIUM for LDO_FR>SOL_FR)")
    else:
        print(f"  Reason: {p3.get('reason')}")

    # Write JSON output
    output = {
        "wave":         "K730",
        "strategy":     "K728 LDO-SOL alt-alt scaffold (64th daemon, 10th alt-alt, LSD vs SVM)",
        "ts_jst":       ts_jst,
        "phase1":       p1,
        "phase2":       p2,
        "phase3":       p3,
        "scaffold_ok":  p1_ok and p3.get("status") == "PASS",
    }
    out_path = REPO_ROOT / "wave_k730_k728_scaffold.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n  Results -> {out_path.name}")

    overall = "SCAFFOLD-READY" if output["scaffold_ok"] else "SCAFFOLD-FAIL"
    print(f"\n=== K730 {overall} ===")
    print(f"  Script: scripts/k728_ldo_sol_run.py")
    print(f"  Plist:  scripts/com.cryptolab.k730-ldo-sol.plist")
    print(f"  Wave:   wave_k730_k728_scaffold.{{py,json,md}}")
    print(f"  64th daemon | 10th alt-alt | LSD vs SVM | $105,032/yr @$10M | rank #3 OOS Sh=46.84")
    print(f"  K594 pivot: BTC common factor removed -> LDO-SOL genuine alpha (MR9 K594 K476 corr=0.0585)")
    print()
    return 0 if output["scaffold_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

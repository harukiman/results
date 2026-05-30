#!/usr/bin/env python3
"""
wave_k750_k747_scaffold.py — K750 K747 TAO-SOL Alt-Alt Scaffold
================================================================
K339 REPO_ROOT pattern. TAO (Bittensor AI L1) vs SOL (Solana SVM).

SCAFFOLD SUMMARY
----------------
Wave K750 implements the production scaffold for K747 TAO-SOL FR Differential.
K747 = FIFTEENTH ALT-ALT pair (AI L1 × SVM cross-cluster, 69th daemon).

K747 ACCEPT CONDITIONAL (28/29 §6 gates):
  OOS Sharpe: 12.233 (W=168h, zero threshold)
  G4 WF: 12/12 ALL POSITIVE — UNPRECEDENTED (best WF in alt-alt family)
  G8 FAIL: Bybit TAO 84.6% floor-capped (structural, not signal failure)
  G5c AVAX bypass: 0.0126 PASS (vs ONDO-SOL -0.4148 FAIL)
  HL-only: both TAO-PERP + SOL-PERP on HL (maxLeverage=5)
  HL 65.0% AT CAP: paper-gate strict until K498 OKX activation
  TAO = 13th vertex. MR9 L002: all future TAO-X pairs blocked.
  K523 central $17,210/yr @$10M @4x @2.5% sleeve

PHASES IMPLEMENTED
------------------
Phase 1:  scripts/k747_tao_sol_run.py
Phase 2:  scripts/com.cryptolab.k747-tao-sol.plist (69th daemon, 8h interval)
Phase 3:  data/leverage_config.json (K747_TAO_SOL: 4.0 + k747_notes)
Phase 4:  scripts/verify_deployment_status.py (registry +1)
Phase 5:  scripts/emergency_hl_exit.py (--include-k747 flag, §63)
Phase 6:  docs/k302a_runbook.md (§63 playbook entry)
Phase 7:  data/k747_dashboard.json (initial scaffold state)
Phase 8:  wave_k750_k747_scaffold.json (this run results)
Phase 9:  wave_k750_k747_scaffold.md (summary report)
Phase 10: report.html (HTML update)

60D GATE (K750)
---------------
Activation requires ALL THREE:
  1. Realized Sharpe >= 6 (over 60d paper-trade period)
  2. Fill rate >= 60%
  3. Max drawdown < 15%
  AND K498 OKX activation (HL concentration must drop below 65%)

K523 3-POINT PROJECTION
------------------------
Conservative: $12,907/yr  @$10M @4x @2.5%
Central:      $17,210/yr  @$10M @4x @2.5%  ← report this
Optimistic:   $45,289/yr  @$10M @4x @2.5%
Upper bound:  $53,281/yr  (NOT central — K523 mandatory)

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))
UTC = timezone.utc


# ─────────────────────────────────────────────────────────────────────────────
# Scaffold verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_scaffold() -> dict:
    """Verify all K750 scaffold components exist and are consistent."""
    checks = {}

    # Phase 1: run script
    run_script = REPO_ROOT / "scripts" / "k747_tao_sol_run.py"
    checks["phase1_run_script"] = {
        "path": "scripts/k747_tao_sol_run.py",
        "exists": run_script.exists(),
        "pass": run_script.exists(),
    }

    # Phase 2: plist
    plist = REPO_ROOT / "scripts" / "com.cryptolab.k747-tao-sol.plist"
    checks["phase2_plist"] = {
        "path": "scripts/com.cryptolab.k747-tao-sol.plist",
        "exists": plist.exists(),
        "pass": plist.exists(),
    }

    # Phase 3: leverage_config.json
    lev_cfg = DATA_DIR / "leverage_config.json"
    k747_in_lev = False
    if lev_cfg.exists():
        try:
            lev_data = json.loads(lev_cfg.read_text())
            k747_in_lev = "K747_TAO_SOL" in lev_data
        except Exception:
            pass
    checks["phase3_leverage_config"] = {
        "path": "data/leverage_config.json",
        "k747_entry_exists": k747_in_lev,
        "pass": k747_in_lev,
    }

    # Phase 4: verify_deployment_status.py
    vds = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    k747_in_vds = False
    if vds.exists():
        content = vds.read_text()
        k747_in_vds = "k747-tao-sol" in content
    checks["phase4_verify_deployment"] = {
        "path": "scripts/verify_deployment_status.py",
        "k747_entry_exists": k747_in_vds,
        "pass": k747_in_vds,
    }

    # Phase 5: emergency_hl_exit.py
    ehe = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    k747_in_ehe = False
    if ehe.exists():
        content = ehe.read_text()
        k747_in_ehe = "include-k747" in content or "include_k747" in content
    checks["phase5_emergency_exit"] = {
        "path": "scripts/emergency_hl_exit.py",
        "k747_flag_exists": k747_in_ehe,
        "pass": k747_in_ehe,
    }

    # Phase 6: runbook
    runbook = REPO_ROOT / "docs" / "k302a_runbook.md"
    k747_in_runbook = False
    if runbook.exists():
        content = runbook.read_text()
        k747_in_runbook = "§63" in content and "k747" in content.lower()
    checks["phase6_runbook"] = {
        "path": "docs/k302a_runbook.md",
        "k747_section_exists": k747_in_runbook,
        "pass": k747_in_runbook,
    }

    # Phase 7: dashboard
    dash_path = DATA_DIR / "k747_dashboard.json"
    checks["phase7_dashboard"] = {
        "path": "data/k747_dashboard.json",
        "exists": dash_path.exists(),
        "pass": dash_path.exists(),
    }

    all_pass = all(v.get("pass", False) for v in checks.values())
    gates_passed = sum(1 for v in checks.values() if v.get("pass", False))
    gates_total  = len(checks)

    return {
        "all_pass":     all_pass,
        "gates_passed": gates_passed,
        "gates_total":  gates_total,
        "checks":       checks,
        "ts_jst":       datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main scaffold driver
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K750 K747 TAO-SOL Alt-Alt Scaffold — {ts_jst} ===")
    print(f"  Strategy:    TAO-SOL FR Differential (FIFTEENTH ALT-ALT pair)")
    print(f"  Wave:        K750 (scaffold wave for K747 ACCEPT CONDITIONAL)")
    print(f"  Daemon:      69th (fifteenth alt-alt pair)")
    print(f"  OOS Sharpe:  12.233 (W=168h, zero threshold, ~217d OOS)")
    print(f"  G4 WF:       12/12 ALL POSITIVE — UNPRECEDENTED (best WF in family)")
    print(f"  G8:          FAIL (Bybit TAO 84.6% floor) → HL-only deployment")
    print(f"  AVAX bypass: G5c=0.013 PASS (vs ONDO G5c=-0.415 FAIL). AI≠AVAX subnet.")
    print(f"  TAO vertex:  13th. MR9 L002: all future TAO-X pairs blocked.")
    print(f"  HL cap:      65.0% AT CAP — paper-gate strict")
    print(f"  Profit:      central $17,210/yr @$10M @4x @2.5% sleeve (K523 3-point)")
    print(f"  60d gate:    Realized Sh>=6 + fill>=60% + maxDD<15%")
    print(f"  Live trigger: K498 OKX activation + 60d gate")

    print(f"\n  [Verification] Checking scaffold components...")
    result = verify_scaffold()
    for phase, info in result["checks"].items():
        status = "PASS" if info.get("pass") else "FAIL"
        print(f"    [{status}] {phase}: {info.get('path', '')}")

    print(f"\n  Scaffold gates: {result['gates_passed']}/{result['gates_total']} PASS")
    print(f"  Overall:        {'ALL PASS' if result['all_pass'] else 'INCOMPLETE — check logs'}")

    # Write scaffold results JSON
    out_path = REPO_ROOT / "wave_k750_k747_scaffold.json"
    scaffold_data = {
        "wave":       "K750",
        "strategy":   "K747 TAO-SOL FR Differential Alt-Alt (AI L1 × SVM — 13th vertex)",
        "run_time_jst": ts_jst,
        "k747_result": {
            "decision":        "ACCEPT CONDITIONAL",
            "gates_passed":    28,
            "gates_total":     29,
            "g8_fail_reason":  "Bybit TAO 84.6% floor-capped (structural venue noise, not signal)",
            "g4_wf":           "12/12 ALL POSITIVE — UNPRECEDENTED",
            "oos_sharpe":      12.233,
            "w_hours":         168,
            "sleeve_pct":      2.5,
            "leverage":        4.0,
            "venue":           "HL-only (TAO-PERP + SOL-PERP)",
            "hl_concentration": 65.0,
            "paper_gate_strict": True,
            "live_trigger":    "K498 OKX activation + 60d gate",
            "tao_vertex":      "13th vertex. MR9 L002: all future TAO-X blocked.",
            "avax_bypass":     "G5c=0.013 PASS, G5k=0.129 PASS (AI L1 ≠ AVAX subnet)",
        },
        "k523_projection": {
            "conservative_yr": 12907,
            "central_yr":      17210,
            "optimistic_yr":   45289,
            "upper_bound_yr":  53281,
            "note":            "K523 mandatory 3-point. Upper bound ≠ central.",
        },
        "gate_60d": {
            "realized_sharpe_min":   6.0,
            "fill_rate_min_pct":     60,
            "max_drawdown_max_pct":  15,
            "additional_gate":       "K498 OKX activation (HL% must drop below 65%)",
        },
        "daemon": {
            "number":   "69th",
            "label":    "com.cryptolab.k747-tao-sol",
            "script":   "scripts/k747_tao_sol_run.py",
            "interval_s": 28800,
        },
        "scaffold_verification": result,
    }
    out_path.write_text(json.dumps(scaffold_data, indent=2))
    print(f"\n  Results written -> {out_path}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

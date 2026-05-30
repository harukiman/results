#!/usr/bin/env python3
"""
wave_k756_k754_scaffold.py — K756 K754 PEPE-SOL Alt-Alt Scaffold
=================================================================
K339 REPO_ROOT pattern. PEPE (Ethereum ERC-20 meme leader) vs SOL (Solana SVM).

SCAFFOLD SUMMARY
----------------
Wave K756 implements the production scaffold for K754 PEPE-SOL FR Differential.
K754 = SIXTEENTH ALT-ALT pair (Eth meme cluster × SVM cross-cluster, 71st daemon).

K754 ACCEPT CONDITIONAL:
  OOS Sharpe: 44.43 (W=84h, zero threshold, ~210d OOS)
  G4 WF: 12/12 ALL POSITIVE (min_sh=5.56) — strong WF validation
  G5: 22/22 PASS (max_corr=0.247 G5l SEI-SOL — well below 0.40)
  G6: 64.2 entries/yr OOS PASS (W=84h chosen over W=168h for G6 compliance)
  G8: HL+Bybit+OKX confirmed (Bybit=1000PEPE denomination)
  HL primary: PEPE-PERP + SOL-PERP on HL
  HL 66.8% AT CAP (K751 audit): paper-gate strict until K498/v6.52 OKX activation
  PEPE = 14th vertex. MR9 L002: all future PEPE-X pairs blocked.
  L003 AVAX=0.4125 PASS | L010 HBAR=0.4272 PASS — proximity warnings (monthly recheck)
  K523 central $62,000/yr @$10M @4x @2.5% sleeve

PHASES IMPLEMENTED
------------------
Phase 1:  scripts/k754_pepe_sol_run.py
Phase 2:  scripts/com.cryptolab.k754-pepe-sol.plist (71st daemon, 8h interval)
Phase 3:  data/leverage_config.json (K754_PEPE_SOL: 4.0 + k754_notes)
Phase 4:  scripts/verify_deployment_status.py (registry +1)
Phase 5:  scripts/emergency_hl_exit.py (--include-k754 flag, §71)
Phase 6:  docs/k302a_runbook.md (§71 playbook entry)
Phase 7:  data/k754_dashboard.json (initial scaffold state)
Phase 8:  wave_k756_k754_scaffold.json (this run results)
Phase 9:  wave_k756_k754_scaffold.py (this file — scaffold verification runner)
Phase 10: report.html (HTML update)

60D GATE (K756)
---------------
Activation requires ALL:
  1. Realized Sharpe >= 6 (over 60d paper-trade period)
  2. Fill rate >= 60%
  3. Max drawdown < 15%
  4. K498/v6.52 OKX activation (HL% must drop below 65%)
  5. L003/L010 monthly recheck: AVAX < 0.45 AND HBAR < 0.45

K523 3-POINT PROJECTION
------------------------
Conservative: $34,758/yr  @$10M @4x @2.5%
Central:      $62,000/yr  @$10M @4x @2.5%  ← report this
Optimistic:   $85,678/yr  @$10M @4x @2.5%
Note: Upper bound ≠ central (K523 mandatory).

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
    """Verify all K756 scaffold components exist and are consistent."""
    checks = {}

    # Phase 1: run script
    run_script = REPO_ROOT / "scripts" / "k754_pepe_sol_run.py"
    checks["phase1_run_script"] = {
        "path": "scripts/k754_pepe_sol_run.py",
        "exists": run_script.exists(),
        "pass": run_script.exists(),
    }

    # Phase 2: plist
    plist = REPO_ROOT / "scripts" / "com.cryptolab.k754-pepe-sol.plist"
    checks["phase2_plist"] = {
        "path": "scripts/com.cryptolab.k754-pepe-sol.plist",
        "exists": plist.exists(),
        "pass": plist.exists(),
    }

    # Phase 3: leverage_config.json
    lev_cfg = DATA_DIR / "leverage_config.json"
    k754_in_lev = False
    if lev_cfg.exists():
        try:
            lev_data = json.loads(lev_cfg.read_text())
            k754_in_lev = "K754_PEPE_SOL" in lev_data
        except Exception:
            pass
    checks["phase3_leverage_config"] = {
        "path": "data/leverage_config.json",
        "k754_entry_exists": k754_in_lev,
        "pass": k754_in_lev,
    }

    # Phase 4: verify_deployment_status.py
    vds = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    k754_in_vds = False
    if vds.exists():
        content = vds.read_text()
        k754_in_vds = "k754-pepe-sol" in content
    checks["phase4_verify_deployment"] = {
        "path": "scripts/verify_deployment_status.py",
        "k754_entry_exists": k754_in_vds,
        "pass": k754_in_vds,
    }

    # Phase 5: emergency_hl_exit.py
    ehe = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    k754_in_ehe = False
    if ehe.exists():
        content = ehe.read_text()
        k754_in_ehe = "include-k754" in content or "include_k754" in content
    checks["phase5_emergency_exit"] = {
        "path": "scripts/emergency_hl_exit.py",
        "k754_flag_exists": k754_in_ehe,
        "pass": k754_in_ehe,
    }

    # Phase 6: runbook
    runbook = REPO_ROOT / "docs" / "k302a_runbook.md"
    k754_in_runbook = False
    if runbook.exists():
        content = runbook.read_text()
        k754_in_runbook = "§71" in content and "k754" in content.lower()
    checks["phase6_runbook"] = {
        "path": "docs/k302a_runbook.md",
        "k754_section_exists": k754_in_runbook,
        "pass": k754_in_runbook,
    }

    # Phase 7: dashboard
    dash_path = DATA_DIR / "k754_dashboard.json"
    checks["phase7_dashboard"] = {
        "path": "data/k754_dashboard.json",
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
    print(f"\n=== K756 K754 PEPE-SOL Alt-Alt Scaffold — {ts_jst} ===")
    print(f"  Strategy:    PEPE-SOL FR Differential (SIXTEENTH ALT-ALT pair)")
    print(f"  Wave:        K756 (scaffold wave for K754 ACCEPT CONDITIONAL)")
    print(f"  Daemon:      71st (sixteenth alt-alt pair)")
    print(f"  OOS Sharpe:  44.43 (W=84h, zero threshold, ~210d OOS)")
    print(f"  G4 WF:       12/12 ALL POSITIVE (min_sh=5.56)")
    print(f"  G5:          22/22 PASS (max_corr=0.247 G5l SEI-SOL)")
    print(f"  G6:          64.2/yr OOS PASS (W=84h G6-safe vs W=168h 29.5/yr FAIL)")
    print(f"  G8:          HL+Bybit+OKX confirmed (Bybit=1000PEPE denomination)")
    print(f"  PEPE vertex: 14th. MR9 L002: all future PEPE-X pairs blocked.")
    print(f"  HL cap:      66.8% AT CAP (K751 audit) — paper-gate strict")
    print(f"  L003 AVAX:   0.4125 PASS — proximity warning (monthly recheck)")
    print(f"  L010 HBAR:   0.4272 PASS — proximity warning (monthly recheck)")
    print(f"  Profit:      central $62,000/yr @$10M @4x @2.5% sleeve (K523 3-point)")
    print(f"  60d gate:    Realized Sh>=6 + fill>=60% + maxDD<15% + K498/v6.52")

    print(f"\n  [Verification] Checking scaffold components...")
    result = verify_scaffold()
    for phase, info in result["checks"].items():
        status = "PASS" if info.get("pass") else "FAIL"
        print(f"    [{status}] {phase}: {info.get('path', '')}")

    print(f"\n  Scaffold gates: {result['gates_passed']}/{result['gates_total']} PASS")
    print(f"  Overall:        {'ALL PASS' if result['all_pass'] else 'INCOMPLETE — check logs'}")

    # Write scaffold results JSON
    out_path = REPO_ROOT / "wave_k756_k754_scaffold.json"
    scaffold_data = {
        "wave":       "K756",
        "strategy":   "K754 PEPE-SOL FR Differential Alt-Alt (Eth ERC-20 meme leader × Solana SVM — 14th vertex)",
        "run_time_jst": ts_jst,
        "k754_result": {
            "decision":            "ACCEPT CONDITIONAL",
            "g4_wf":               "12/12 ALL POSITIVE (min_sh=5.56)",
            "g5_result":           "22/22 PASS (max_corr=0.247 G5l SEI-SOL — well below 0.40)",
            "g6_entries_yr":       64.2,
            "g6_note":             "W=84h G6-safe vs W=168h 29.5/yr FAIL (<30/yr threshold)",
            "g8_result":           "HL+Bybit+OKX confirmed (Bybit=1000PEPE denomination)",
            "oos_sharpe":          44.43,
            "max_dd_oos_pct":      -0.107,
            "w_hours":             84,
            "sleeve_pct":          0.025,
            "leverage":            4.0,
            "venue":               "HL primary (PEPE-PERP + SOL-PERP), Bybit fallback (1000PEPE denomination)",
            "hl_concentration":    66.8,
            "paper_gate_strict":   True,
            "live_trigger":        "K498/v6.52 OKX activation (HL% < 65%) + 60d gate + L003/L010 monthly recheck",
            "pepe_vertex":         "14th vertex. MR9 L002: all future PEPE-X auto-blocked.",
            "l003_avax_corr":      0.4125,
            "l010_hbar_corr":      0.4272,
            "proximity_warning":   "L003 AVAX=0.4125 + L010 HBAR=0.4272 — both near 0.45 threshold. Monthly recheck.",
        },
        "k523_projection": {
            "conservative_yr": 34758,
            "central_yr":      62000,
            "optimistic_yr":   85678,
            "note":            "K523 mandatory 3-point. Central=$62K @$10M @4x @2.5%.",
        },
        "gate_60d": {
            "realized_sharpe_min":   6.0,
            "fill_rate_min_pct":     60,
            "max_drawdown_max_pct":  15,
            "additional_gate":       "K498/v6.52 OKX activation (HL% must drop below 65.0%)",
            "l003_l010_recheck":     "Monthly: AVAX < 0.45 AND HBAR < 0.45",
        },
        "daemon": {
            "number":     "71st",
            "label":      "com.cryptolab.k754-pepe-sol",
            "script":     "scripts/k754_pepe_sol_run.py",
            "interval_s": 28800,
        },
        "scaffold_verification": result,
        "vertex_set_after_k754": [
            "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ",
            "LDO", "SEI", "SOL", "TIA", "TAO", "PEPE"
        ],
        "alt_alt_family_count": 16,
    }
    out_path.write_text(json.dumps(scaffold_data, indent=2))
    print(f"\n  Results written -> {out_path}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

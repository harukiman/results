#!/usr/bin/env python3
"""
wave_k761_k759_scaffold.py — K761 K759 WIF-SOL Alt-Alt Scaffold
================================================================
K339 REPO_ROOT pattern. WIF (dogwifhat SOL-native meme) vs SOL (Solana SVM).

SCAFFOLD SUMMARY
----------------
Wave K761 implements the production scaffold for K759 WIF-SOL FR Differential.
K759 = SEVENTEENTH ALT-ALT pair (SOL meme cluster × SVM cross-cluster, 72nd daemon).

K759 CONDITIONAL_ACCEPT:
  OOS Sharpe: 24.4547 (W=168h, zero threshold, ~210d OOS)
  G4 WF: 12/12 ALL POSITIVE (min_sh=9.895) — strong WF validation
  G5: all PASS (max_corr=0.3819 G5w PEPE-SOL — 0.018 margin below 0.40)
  G5w PEPE-SOL=0.382: proximity → reduced sleeve 2.0% (vs 2.5% standard)
  G6: 31.2 entries/yr OOS PASS (W=168h family standard, G6-compliant)
  G8: HL+Bybit+OKX confirmed (WIF: HL WIFUSDC, Bybit WIFUSDT, OKX WIF-PERP)
  HL primary: WIF-PERP + SOL-PERP on HL
  HL 66.8% AT CAP (K751 audit): paper-gate strict until K498/v6.52 OKX activation
  L011 WIF-SOL corr=0.487 PASS (< 0.50 SOL-ecosystem threshold, borderline, monthly recheck)
  WIF = 15th vertex. MR9 L002: all future WIF-X pairs blocked.
  K523 central $54,245/yr @$10M @4x @2.0% sleeve

PHASES IMPLEMENTED
------------------
Phase 1:  scripts/k759_wif_sol_run.py
Phase 2:  scripts/com.cryptolab.k759-wif-sol.plist (72nd daemon, 8h interval)
Phase 3:  data/leverage_config.json (K759_WIF_SOL: 4.0 + k759_notes)
Phase 4:  scripts/verify_deployment_status.py (registry +1)
Phase 5:  scripts/emergency_hl_exit.py (--include-k759 flag, §72)
Phase 6:  docs/k302a_runbook.md (§72 playbook entry)
Phase 7:  data/k759_dashboard.json (initial scaffold state)
Phase 8:  wave_k761_k759_scaffold.json (this run results)
Phase 9:  wave_k761_k759_scaffold.py (this file — scaffold verification runner)
Phase 10: report.html (HTML update)

60D GATE (K761)
---------------
Activation requires ALL:
  1. Realized Sharpe >= 6 (over 60d paper-trade period)
  2. Fill rate >= 60%
  3. Max drawdown < 15%
  4. K498/v6.52 OKX activation (HL% must drop below 65%)
  5. L011 monthly recheck: corr(WIF,SOL) < 0.50 OOS
  6. G5w monthly recheck: corr(WIF-SOL, PEPE-SOL) < 0.40

K523 3-POINT PROJECTION
------------------------
Conservative: $20,655/yr  @$10M @4x @2.0%
Central:      $54,245/yr  @$10M @4x @2.0%  <- report this
Optimistic:   $76,847/yr  @$10M @4x @2.0%
Note: Upper bound != central (K523 mandatory). Sleeve 2.0% (reduced from 2.5% — G5w proximity).

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
    """Verify all K761 scaffold components exist and are consistent."""
    checks = {}

    # Phase 1: run script
    run_script = REPO_ROOT / "scripts" / "k759_wif_sol_run.py"
    checks["phase1_run_script"] = {
        "path": "scripts/k759_wif_sol_run.py",
        "exists": run_script.exists(),
        "pass": run_script.exists(),
    }

    # Phase 2: plist
    plist = REPO_ROOT / "scripts" / "com.cryptolab.k759-wif-sol.plist"
    checks["phase2_plist"] = {
        "path": "scripts/com.cryptolab.k759-wif-sol.plist",
        "exists": plist.exists(),
        "pass": plist.exists(),
    }

    # Phase 3: leverage_config.json
    lev_cfg = DATA_DIR / "leverage_config.json"
    k759_in_lev = False
    if lev_cfg.exists():
        try:
            lev_data = json.loads(lev_cfg.read_text())
            k759_in_lev = "K759_WIF_SOL" in lev_data
        except Exception:
            pass
    checks["phase3_leverage_config"] = {
        "path": "data/leverage_config.json",
        "k759_entry_exists": k759_in_lev,
        "pass": k759_in_lev,
    }

    # Phase 4: verify_deployment_status.py
    vds = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    k759_in_vds = False
    if vds.exists():
        content = vds.read_text()
        k759_in_vds = "k759-wif-sol" in content
    checks["phase4_verify_deployment"] = {
        "path": "scripts/verify_deployment_status.py",
        "k759_entry_exists": k759_in_vds,
        "pass": k759_in_vds,
    }

    # Phase 5: emergency_hl_exit.py
    ehe = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    k759_in_ehe = False
    if ehe.exists():
        content = ehe.read_text()
        k759_in_ehe = "include-k759" in content or "include_k759" in content
    checks["phase5_emergency_exit"] = {
        "path": "scripts/emergency_hl_exit.py",
        "k759_flag_exists": k759_in_ehe,
        "pass": k759_in_ehe,
    }

    # Phase 6: runbook
    runbook = REPO_ROOT / "docs" / "k302a_runbook.md"
    k759_in_runbook = False
    if runbook.exists():
        content = runbook.read_text()
        k759_in_runbook = "§72" in content and "k759" in content.lower()
    checks["phase6_runbook"] = {
        "path": "docs/k302a_runbook.md",
        "k759_section_exists": k759_in_runbook,
        "pass": k759_in_runbook,
    }

    # Phase 7: dashboard
    dash_path = DATA_DIR / "k759_dashboard.json"
    checks["phase7_dashboard"] = {
        "path": "data/k759_dashboard.json",
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
    print(f"\n=== K761 K759 WIF-SOL Alt-Alt Scaffold — {ts_jst} ===")
    print(f"  Strategy:    WIF-SOL FR Differential (SEVENTEENTH ALT-ALT pair)")
    print(f"  Wave:        K761 (scaffold wave for K759 CONDITIONAL_ACCEPT)")
    print(f"  Daemon:      72nd (seventeenth alt-alt pair)")
    print(f"  OOS Sharpe:  24.4547 (W=168h, zero threshold, ~210d OOS)")
    print(f"  G4 WF:       12/12 ALL POSITIVE (min_sh=9.895)")
    print(f"  G5:          all PASS (max_corr=0.3819 G5w PEPE-SOL — 0.018 margin)")
    print(f"  G5w:         PEPE-SOL=0.382 proximity → reduced sleeve 2.0% (vs 2.5%)")
    print(f"  G6:          31.2/yr OOS PASS (W=168h family standard)")
    print(f"  G8:          HL+Bybit+OKX confirmed (WIF: WIFUSDC/WIFUSDT/OKX)")
    print(f"  L011:        raw_corr(WIF,SOL)=0.487 PASS (borderline, monthly recheck)")
    print(f"  WIF vertex:  15th. MR9 L002: all future WIF-X pairs blocked.")
    print(f"  HL cap:      66.8% AT CAP (K751 audit) — paper-gate strict")
    print(f"  Profit:      central $54,245/yr @$10M @4x @2.0% sleeve (K523 3-point)")
    print(f"  60d gate:    Realized Sh>=6 + fill>=60% + maxDD<15% + K498/v6.52")

    print(f"\n  [Verification] Checking scaffold components...")
    result = verify_scaffold()
    for phase, info in result["checks"].items():
        status = "PASS" if info.get("pass") else "FAIL"
        print(f"    [{status}] {phase}: {info.get('path', '')}")

    print(f"\n  Scaffold gates: {result['gates_passed']}/{result['gates_total']} PASS")
    print(f"  Overall:        {'ALL PASS' if result['all_pass'] else 'INCOMPLETE — check logs'}")

    # Write scaffold results JSON
    out_path = REPO_ROOT / "wave_k761_k759_scaffold.json"
    scaffold_data = {
        "wave":       "K761",
        "strategy":   "K759 WIF-SOL FR Differential Alt-Alt (SOL-native meme × Solana SVM — 15th vertex)",
        "run_time_jst": ts_jst,
        "k759_result": {
            "decision":            "CONDITIONAL_ACCEPT",
            "g4_wf":               "12/12 ALL POSITIVE (min_sh=9.895)",
            "g5_result":           "all PASS (max_corr=0.3819 G5w PEPE-SOL — 0.018 margin below 0.40)",
            "g5w_pepe_sol":        0.3819,
            "g5w_note":            "PEPE-SOL proximity=0.382 (0.018 margin) → sleeve reduced to 2.0%",
            "g6_entries_yr":       31.2,
            "g6_note":             "W=168h family standard G6-safe vs 30/yr minimum",
            "g8_result":           "HL+Bybit+OKX confirmed (WIF: WIFUSDC/WIFUSDT/OKX WIF-PERP)",
            "oos_sharpe":          24.4547,
            "max_dd_oos_pct":      -0.2164,
            "w_hours":             168,
            "sleeve_pct":          0.020,
            "sleeve_note":         "Reduced from 2.5% to 2.0% — G5w PEPE-SOL proximity=0.382 (0.018 margin)",
            "leverage":            4.0,
            "venue":               "HL primary (WIF-PERP + SOL-PERP), Bybit fallback (WIFUSDT)",
            "hl_concentration":    66.8,
            "paper_gate_strict":   True,
            "live_trigger":        "K498/v6.52 OKX activation (HL% < 65%) + 60d gate + L011 monthly recheck",
            "wif_vertex":          "15th vertex. MR9 L002: all future WIF-X auto-blocked.",
            "l011_wif_sol_corr":   0.4869,
            "l011_oos_corr":       0.0541,
            "l011_note":           "raw_corr(WIF,SOL)=0.487 PASS (< 0.50 SOL-ecosystem threshold, borderline, OOS=0.054 near-zero). Monthly recheck.",
            "l003_avax_corr":      0.3823,
            "l004_carry_oos":      0.7753,
            "l007_fil_corr":       0.3318,
            "l010_hbar_corr":      0.4011,
        },
        "k523_projection": {
            "conservative_yr": 20655,
            "central_yr":      54245,
            "optimistic_yr":   76847,
            "sleeve_pct":      0.020,
            "note":            "K523 mandatory 3-point. Central=$54.2K @$10M @4x @2.0% (reduced sleeve — G5w proximity).",
        },
        "gate_60d": {
            "realized_sharpe_min":   6.0,
            "fill_rate_min_pct":     60,
            "max_drawdown_max_pct":  15,
            "additional_gate":       "K498/v6.52 OKX activation (HL% must drop below 65.0%)",
            "l011_recheck":          "Monthly: corr(WIF,SOL) < 0.50 OOS",
            "g5w_recheck":           "Monthly: corr(WIF-SOL, PEPE-SOL) < 0.40",
        },
        "daemon": {
            "number":     "72nd",
            "label":      "com.cryptolab.k759-wif-sol",
            "script":     "scripts/k759_wif_sol_run.py",
            "interval_s": 28800,
        },
        "scaffold_verification": result,
        "vertex_set_after_k759": [
            "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ",
            "LDO", "SEI", "SOL", "TIA", "TAO", "PEPE", "WIF"
        ],
        "alt_alt_family_count": 17,
        "cross_sleeve_note": "WIF-SOL (2.0%) + PEPE-SOL (2.0%) = 4.0% combined meme-vs-SOL cluster sleeve",
    }
    out_path.write_text(json.dumps(scaffold_data, indent=2))
    print(f"\n  Results written -> {out_path}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

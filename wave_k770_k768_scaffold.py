#!/usr/bin/env python3
"""
wave_k770_k768_scaffold.py — K770 K768 BLUR-SOL Alt-Alt Scaffold
================================================================
K339 REPO_ROOT pattern. BLUR (Ethereum L1 NFT marketplace) vs SOL (Solana SVM).

SCAFFOLD SUMMARY
----------------
Wave K770 implements the production scaffold for K768 BLUR-SOL FR Differential.
K768 = EIGHTEENTH ALT-ALT pair (NFT marketplace × SVM cross-cluster, 75th daemon).

K768 CONDITIONAL_ACCEPT:
  OOS Sharpe: 14.9799 (W=168h, zero threshold, ~210d OOS)
  G4 WF: 20/21 POSITIVE (positive_frac=0.952) — strong WF validation
  G5: G1-G4+G6-G9 ALL PASS. G5 FIL-SOL full=0.4398 FAIL (OOS=0.2805 PASS).
  G5 exception: SOL-anchor contamination. Raw FR independent (L007=0.0478).
  G6: 38.2 entries/yr OOS PASS (W=168h family standard G6-safe)
  G8: HL+Bybit confirmed (BLUR: HL listed 2024-05, Bybit BLURUSDT 4594 rows)
  HL primary: BLUR-PERP + SOL-PERP on HL
  HL 66.8% AT CAP (K751 audit): paper-gate strict until all 4 live conditions met
  BLUR = 16th vertex. MR9 L002: all future BLUR-X pairs blocked.
  Sleeve: 0.6% LIQUIDITY-LIMITED (HL BLUR $0.6M/day → $60K pos max)
  K523 central $61,000/yr @$10M @4x @0.6% sleeve

PHASES IMPLEMENTED
------------------
Phase 1:  scripts/k768_blur_sol_run.py
Phase 2:  scripts/com.cryptolab.k768-blur-sol.plist (75th daemon, 8h interval)
Phase 3:  data/leverage_config.json (K768_BLUR_SOL: 4.0 + k768_notes)
Phase 4:  scripts/verify_deployment_status.py (registry +1)
Phase 5:  scripts/emergency_hl_exit.py (--include-k768 flag, §76)
Phase 6:  docs/k302a_runbook.md (§76 playbook entry)
Phase 7:  data/k768_dashboard.json (initial scaffold state)
Phase 8:  wave_k770_k768_scaffold.json (this run results)
Phase 9:  wave_k770_k768_scaffold.py (this file — scaffold verification runner)
Phase 10: report.html (HTML update)
Phase 11: 4 live-elevation conditions documented

4 LIVE-ELEVATION CONDITIONS (K770 governance — all required before live):
  1. G5 FIL-SOL rolling 90d OOS corr < 0.40 (currently 0.2805 PASS — borderline)
  2. HL BLUR daily volume > $1M/day sustained (currently $0.6M — sub-threshold)
  3. HL cap < 65% (currently 66.8% — requires K498/v6.52 OKX)
  4. Governance review of NFT marketplace cluster (no family precedent)

K523 3-POINT PROJECTION
------------------------
Conservative: $37,000/yr  @$10M @4x @0.6%
Central:      $61,000/yr  @$10M @4x @0.6%  <- report this
Optimistic:   $153,000/yr @$10M @4x @2.5% ref (not viable at $0.6M/day liquidity)
Note: Upper bound != central (K523 mandatory). Optimistic = condition 2 met ($2.5M/day vol).

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
    """Verify all K770 scaffold components exist and are consistent."""
    checks = {}

    # Phase 1: run script
    run_script = REPO_ROOT / "scripts" / "k768_blur_sol_run.py"
    checks["phase1_run_script"] = {
        "path": "scripts/k768_blur_sol_run.py",
        "exists": run_script.exists(),
        "pass": run_script.exists(),
    }

    # Phase 2: plist
    plist = REPO_ROOT / "scripts" / "com.cryptolab.k768-blur-sol.plist"
    checks["phase2_plist"] = {
        "path": "scripts/com.cryptolab.k768-blur-sol.plist",
        "exists": plist.exists(),
        "pass": plist.exists(),
    }

    # Phase 3: leverage_config.json
    lev_cfg = DATA_DIR / "leverage_config.json"
    k768_in_lev = False
    if lev_cfg.exists():
        try:
            lev_data = json.loads(lev_cfg.read_text())
            k768_in_lev = "K768_BLUR_SOL" in lev_data
        except Exception:
            pass
    checks["phase3_leverage_config"] = {
        "path": "data/leverage_config.json",
        "k768_entry_exists": k768_in_lev,
        "pass": k768_in_lev,
    }

    # Phase 4: verify_deployment_status.py
    vds = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    k768_in_vds = False
    if vds.exists():
        content = vds.read_text()
        k768_in_vds = "k768-blur-sol" in content
    checks["phase4_verify_deployment"] = {
        "path": "scripts/verify_deployment_status.py",
        "k768_entry_exists": k768_in_vds,
        "pass": k768_in_vds,
    }

    # Phase 5: emergency_hl_exit.py
    ehe = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    k768_in_ehe = False
    if ehe.exists():
        content = ehe.read_text()
        k768_in_ehe = "include-k768" in content or "include_k768" in content
    checks["phase5_emergency_exit"] = {
        "path": "scripts/emergency_hl_exit.py",
        "k768_flag_exists": k768_in_ehe,
        "pass": k768_in_ehe,
    }

    # Phase 6: runbook
    runbook = REPO_ROOT / "docs" / "k302a_runbook.md"
    k768_in_runbook = False
    if runbook.exists():
        content = runbook.read_text()
        k768_in_runbook = "§76" in content and "k768" in content.lower()
    checks["phase6_runbook"] = {
        "path": "docs/k302a_runbook.md",
        "k768_section_exists": k768_in_runbook,
        "pass": k768_in_runbook,
    }

    # Phase 7: dashboard
    dash_path = DATA_DIR / "k768_dashboard.json"
    checks["phase7_dashboard"] = {
        "path": "data/k768_dashboard.json",
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
    print(f"\n=== K770 K768 BLUR-SOL Alt-Alt Scaffold — {ts_jst} ===")
    print(f"  Strategy:    BLUR-SOL FR Differential (EIGHTEENTH ALT-ALT pair)")
    print(f"  Wave:        K770 (scaffold wave for K768 CONDITIONAL_ACCEPT)")
    print(f"  Daemon:      75th (eighteenth alt-alt pair)")
    print(f"  OOS Sharpe:  14.9799 (W=168h, zero threshold, ~210d OOS)")
    print(f"  G4 WF:       20/21 POSITIVE (positive_frac=0.952)")
    print(f"  G5:          FIL-SOL full=0.4398 FAIL / OOS=0.2805 PASS (SOL-anchor exception)")
    print(f"  G6:          38.2/yr OOS PASS (W=168h family standard)")
    print(f"  G8:          HL+Bybit confirmed (BLUR: HL 2024-05, Bybit BLURUSDT 4594 rows)")
    print(f"  Liquidity:   HL BLUR $0.6M/day → 0.6% sleeve ($60K pos max)")
    print(f"  BLUR vertex: 16th. MR9 L002: all future BLUR-X pairs blocked.")
    print(f"  HL cap:      66.8% AT CAP (K751 audit) — paper-gate strict")
    print(f"  Profit:      central $61,000/yr @$10M @4x @0.6% sleeve (K523 3-point)")
    print(f"  4 conditions: G5-FIL-SOL 90d + vol>$1M/day + HL<65% + governance")

    print(f"\n  [Verification] Checking scaffold components...")
    result = verify_scaffold()
    for phase, info in result["checks"].items():
        status = "PASS" if info.get("pass") else "FAIL"
        print(f"    [{status}] {phase}: {info.get('path', '')}")

    print(f"\n  Scaffold gates: {result['gates_passed']}/{result['gates_total']} PASS")
    print(f"  Overall:        {'ALL PASS' if result['all_pass'] else 'INCOMPLETE — check logs'}")

    # Write scaffold results JSON
    out_path = REPO_ROOT / "wave_k770_k768_scaffold.json"
    scaffold_data = {
        "wave":       "K770",
        "strategy":   "K768 BLUR-SOL FR Differential Alt-Alt (Ethereum L1 NFT marketplace × Solana SVM — 16th vertex)",
        "run_time_jst": ts_jst,
        "k768_result": {
            "decision":            "CONDITIONAL_ACCEPT",
            "g4_wf":               "20/21 POSITIVE (positive_frac=0.952)",
            "g5_result":           "G1-G4+G6-G9 ALL PASS. G5 FIL-SOL full=0.4398 FAIL (OOS=0.2805 PASS). SOL-anchor exception documented.",
            "g5_fil_sol":          {"full": 0.4398, "is": 0.5112, "oos": 0.2805, "exception": "SOL-anchor contamination. Raw FR independent: L007=0.0478."},
            "g6_entries_yr":       38.2,
            "g6_note":             "W=168h family standard G6-safe vs 30/yr minimum",
            "g8_result":           "HL+Bybit confirmed (BLUR: HL 2024-05, Bybit BLURUSDT 4594 rows 2023-02+)",
            "oos_sharpe":          14.9799,
            "max_dd_oos_pct":      -0.0068,
            "w_hours":             168,
            "sleeve_pct":          0.006,
            "sleeve_note":         "0.6% LIQUIDITY-LIMITED (HL BLUR $0.6M/day → $60K pos max, 10% daily vol rule)",
            "leverage":            4.0,
            "venue":               "HL primary (BLUR-PERP + SOL-PERP), Bybit fallback (BLURUSDT)",
            "hl_concentration":    66.8,
            "paper_gate_strict":   True,
            "live_trigger":        "ALL 4 live-elevation conditions (K770) + 60d gate passage",
            "blur_vertex":         "16th vertex. MR9 L002: all future BLUR-X auto-blocked.",
            "l003_avax_corr":      0.0445,
            "l004_carry":          "IS=0.836 OOS=0.482 PASS",
            "l007_fil_corr":       0.0478,
            "l010_hbar_corr":      0.0784,
            "l011_sol_corr":       0.0603,
        },
        "k523_projection": {
            "conservative_yr": 37000,
            "central_yr":      61000,
            "optimistic_yr":   153000,
            "sleeve_pct":      0.006,
            "note":            "K523 mandatory 3-point. Central=$61K @$10M @4x @0.6% (liquidity-limited).",
        },
        "gate_60d": {
            "realized_sharpe_min":   6.0,
            "fill_rate_min_pct":     60,
            "max_drawdown_max_pct":  15,
            "live_conditions": [
                "G5 FIL-SOL rolling 90d OOS corr < 0.40 (currently 0.2805 PASS — borderline)",
                "HL BLUR daily volume > $1M/day sustained (currently $0.6M — sub-threshold)",
                "HL cap < 65% via K498/v6.52 OKX activation (currently 66.8% AT CAP)",
                "Governance review of NFT marketplace cluster (no family precedent — K770 open)",
            ],
        },
        "daemon": {
            "number":     "75th",
            "label":      "com.cryptolab.k768-blur-sol",
            "script":     "scripts/k768_blur_sol_run.py",
            "interval_s": 28800,
        },
        "scaffold_verification": result,
        "vertex_set_after_k768": [
            "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ",
            "LDO", "SEI", "SOL", "TIA", "TAO", "PEPE", "WIF", "BLUR"
        ],
        "alt_alt_family_count": 18,
        "nft_cluster_note": "First NFT marketplace protocol in alt-alt universe. Governance review required (condition 4).",
    }
    out_path.write_text(json.dumps(scaffold_data, indent=2))
    print(f"\n  Results written -> {out_path}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

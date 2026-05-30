#!/usr/bin/env python3
"""
wave_k779_k777_scaffold.py — K779 K777 EIGEN-SOL Alt-Alt Scaffold
==================================================================
Wave K779: Production scaffold for K777 EIGEN-SOL FR Differential (ACCEPT CONDITIONAL).
78th daemon, 21st alt-alt scaffold evaluated (20th alt-alt pair), 19th vertex EIGEN (ETH-restaking).

Scaffold tasks:
  Phase 1:  Verify scripts/k777_eigen_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k777-eigen-sol.plist (78th daemon, 8h/28800s)
  Phase 3:  Add K777 entry to data/leverage_config.json
  Phase 4:  Add K777 DaemonSpec to scripts/verify_deployment_status.py
  Phase 5:  Add --include-k777 flag to scripts/emergency_hl_exit.py
  Phase 6:  Add §79 section to docs/k302a_runbook.md
  Phase 7:  Initialize data/k777_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Update report.html (K779 K777 EIGEN-SOL scaffold entry)
  Phase 10: Generate wave_k779_k777_scaffold.json

K777 ACCEPT CONDITIONAL parameters:
  OOS Sharpe:      35.90 (W=84h, zero threshold, 118.6d OOS — G9 marginal)
  G4 Walk-Forward: 4/4 positive (fold Sh: 64.10/32.33/36.69/35.42 — all strong)
  G5 24/25:        G5z BLUR-SOL OOS=0.441 borderline (W=84; W=48=0.345 PASS)
  G5q:             LDO-SOL sig_corr=0.147 PASS (restaking distinct from LSD)
  G8:              PASS (HL + Bybit EIGENUSDT confirmed 2024-09-18)
  G9:              MARGINAL OOS=118.6d < 120d (1.4d short, operational data limit)
  Sleeve:          1.5% — $84K central @$10M @4x
  K523 central:    $84,307/yr @$10M @4x @1.5%
  Vertex:          EIGEN = 19th vertex (1st ETH-restaking cluster)
  HL cap:          66.8% AT CAP -> paper-gate strict

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# -- K339 canonical paths -----------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent
DATA_DIR    = REPO_ROOT / "data"
DOCS_DIR    = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE         = "K779"
STRATEGY     = "K777"
PAIR         = "EIGEN-SOL"
DAEMON_NUM   = "78th"
ALT_ALT_N    = "twenty-first"   # scaffold count (evaluated)
ALT_ALT_PAIR = "twentieth"      # actual pair number in family
VERTEX_N     = "19th"
CLUSTER      = "ETH restaking AVS economy × Solana SVM"
OOS_SHARPE   = 35.90
SLEEVE_PCT   = 0.015
LEVERAGE     = 4.0
CENTRAL_YR   = 84307
K523_CONS    = 63230
K523_OPT     = 295813
HL_CAP_PCT   = 66.8


def ts_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def check(condition: bool, msg: str) -> bool:
    tag = "PASS" if condition else "FAIL"
    print(f"  [{tag}] {msg}")
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 -- Verify run script
# ─────────────────────────────────────────────────────────────────────────────

def phase1_run_script() -> bool:
    path   = SCRIPTS_DIR / "k777_eigen_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k777_eigen_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k777_eigen_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 -- Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path   = SCRIPTS_DIR / "com.cryptolab.k777-eigen-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k777-eigen-sol.plist exists")
    if not exists:
        return False

    content      = path.read_text()
    interval_ok  = "<integer>28800</integer>" in content
    label_ok     = "com.cryptolab.k777-eigen-sol" in content
    paper_ok     = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k777-eigen-sol")
    check(paper_ok,    "plist PAPER_TRADE=True default")
    return interval_ok and label_ok and paper_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 -- leverage_config.json
# ─────────────────────────────────────────────────────────────────────────────

def phase3_leverage_config() -> bool:
    path = DATA_DIR / "leverage_config.json"
    if not path.exists():
        check(False, "data/leverage_config.json exists")
        return False

    config   = json.loads(path.read_text())
    k777_key = "K777_EIGEN_SOL"

    if k777_key in config:
        check(True, f"data/leverage_config.json: {k777_key} entry present")
    else:
        check(False, f"data/leverage_config.json: {k777_key} entry MISSING")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 -- verify_deployment_status.py
# ─────────────────────────────────────────────────────────────────────────────

def phase4_verify_deployment() -> bool:
    path = SCRIPTS_DIR / "verify_deployment_status.py"
    if not path.exists():
        check(False, "scripts/verify_deployment_status.py exists")
        return False

    content = path.read_text()
    present = "k777-eigen-sol" in content
    check(present, "verify_deployment_status.py: K777 DaemonSpec present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 -- emergency_hl_exit.py
# ─────────────────────────────────────────────────────────────────────────────

def phase5_emergency_exit() -> bool:
    path = SCRIPTS_DIR / "emergency_hl_exit.py"
    if not path.exists():
        check(False, "scripts/emergency_hl_exit.py exists")
        return False

    content = path.read_text()
    present = "include-k777" in content
    check(present, "emergency_hl_exit.py: --include-k777 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 -- k302a_runbook.md §79
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§79" in content and "K777 EIGEN-SOL" in content
    check(present, "docs/k302a_runbook.md: §79 K777 EIGEN-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 -- data/k777_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path   = DATA_DIR / "k777_dashboard.json"
    exists = path.exists()
    check(exists, "data/k777_dashboard.json exists")
    if not exists:
        return False

    try:
        dash     = json.loads(path.read_text())
        wave_ok  = dash.get("wave") == "K779"
        strat_ok = "K777" in dash.get("strategy", "")
        check(wave_ok,  "data/k777_dashboard.json: wave=K779")
        check(strat_ok, "data/k777_dashboard.json: strategy contains K777")
        return wave_ok and strat_ok
    except Exception as e:
        check(False, f"data/k777_dashboard.json: JSON parse error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 -- Full validation
# ─────────────────────────────────────────────────────────────────────────────

def phase8_validate() -> dict:
    results = {
        "run_script":         phase1_run_script(),
        "plist":              phase2_plist(),
        "leverage_config":    phase3_leverage_config(),
        "verify_deployment":  phase4_verify_deployment(),
        "emergency_exit":     phase5_emergency_exit(),
        "runbook_s79":        phase6_runbook(),
        "dashboard":          phase7_dashboard(),
    }
    all_pass = all(results.values())
    passed   = sum(results.values())
    total    = len(results)
    print(f"\n  Scaffold validation: {passed}/{total} PASS  (all_pass={all_pass})")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 -- Update report.html
# ─────────────────────────────────────────────────────────────────────────────

def phase9_report_html(checks: dict) -> bool:
    path = REPO_ROOT / "report.html"
    if not path.exists():
        check(False, "report.html exists")
        return False

    content = path.read_text()
    if "K779" in content and "K777" in content and "EIGEN-SOL" in content:
        check(True, "report.html: K779 K777 EIGEN-SOL entry already present")
        return True

    all_pass     = all(checks.values())
    status_badge = (
        '<span style="color:#27ae60;font-weight:bold">SCAFFOLD-READY</span>'
        if all_pass else
        '<span style="color:#e67e22;font-weight:bold">SCAFFOLD-PARTIAL</span>'
    )
    checks_html = "".join(
        f'<span style="color:{"#27ae60" if v else "#e74c3c"}">'
        f'{"&#10003;" if v else "&#10007;"} {k}</span><br>'
        for k, v in checks.items()
    )

    entry = f"""
<!-- K779 K777 EIGEN-SOL scaffold entry -->
<div class="wave-entry" style="border-left:4px solid #1a6bb5;padding:12px;margin:8px 0;background:#1a1a2e;border-radius:4px">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <strong style="color:#1a6bb5">K779</strong>
      <span style="color:#e0e0e0;margin-left:8px">K777 EIGEN-SOL FR Differential Scaffold</span>
      <span style="color:#aaa;font-size:0.85em;margin-left:8px">(78th daemon, 20th alt-alt pair, 19th vertex EIGEN ETH-restaking)</span>
    </div>
    <div>{status_badge}</div>
  </div>
  <div style="margin-top:8px;font-size:0.88em;color:#ccc">
    <strong>OOS Sh:</strong> 35.90 (W=84h) &nbsp;|&nbsp;
    <strong>G4:</strong> 4/4 positive (avg 42.14) &nbsp;|&nbsp;
    <strong>G5:</strong> 24/25 PASS; G5z BLUR-SOL OOS=0.441 borderline &nbsp;|&nbsp;
    <strong>G6:</strong> 33.9/yr PASS &nbsp;|&nbsp;
    <strong>G8:</strong> HL+Bybit PASS &nbsp;|&nbsp;
    <strong>G9:</strong> MARGINAL 118.6d
  </div>
  <div style="margin-top:4px;font-size:0.88em;color:#ccc">
    <strong>Signal:</strong> EIGEN_FR - SOL_FR (W=84h, zero threshold) &nbsp;|&nbsp;
    <strong>Sleeve:</strong> 1.5% @$10M &nbsp;|&nbsp;
    <strong>Leverage:</strong> 4x &nbsp;|&nbsp;
    <strong>Venue:</strong> HL primary + Bybit fallback (EIGENUSDT confirmed)
  </div>
  <div style="margin-top:4px;font-size:0.88em;color:#ccc">
    <strong>K523:</strong> cons=$63K | ctr=$84K | opt=$296K/yr @$10M &nbsp;|&nbsp;
    <strong>MaxDD OOS:</strong> -0.55% &nbsp;|&nbsp;
    <strong>HL:</strong> 66.8% AT CAP &#8594; paper-gate strict
  </div>
  <div style="margin-top:4px;font-size:0.85em;color:#aaa">
    EIGEN = 19th vertex (1st ETH-restaking cluster). MR9 L002: all future EIGEN-X blocked.
    G5z monthly recheck: BLUR-SOL OOS 0.441 (W=84); W=48=0.345 PASS (window artifact).
    G5q LDO-SOL=0.147 PASS (restaking distinct from LSD). G9: wait 180d full OOS.
    Live gate: Sh&ge;15 + fill&ge;60% + maxDD&lt;15% + K498/v6.52 + G9-180d + G5z&lt;0.40.
  </div>
  <div style="margin-top:6px;font-size:0.82em;color:#888">
    {checks_html}
    <span style="color:#666">Updated: {ts_jst()}</span>
  </div>
</div>
"""

    if "</body>" in content:
        new_content = content.replace("</body>", entry + "\n</body>", 1)
    else:
        new_content = content + entry

    path.write_text(new_content)
    check(True, "report.html: K779 K777 EIGEN-SOL entry added")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 -- Generate wave_k779_k777_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    all_pass = all(checks.values())
    result   = {
        "wave":     WAVE,
        "strategy": f"K777 EIGEN-SOL FR Differential Alt-Alt (ETH restaking AVS economy × Solana SVM — 19th vertex EIGEN)",
        "run_time_jst": ts_jst(),
        "k777_result": {
            "decision":         "ACCEPT CONDITIONAL",
            "g4_wf":            "4/4 positive (fold Sh: 64.10/32.33/36.69/35.42 — all strong)",
            "g5_result":        "24/25 PASS; G5z BLUR-SOL OOS=0.441 borderline (W=84); W=48=0.345 PASS",
            "g5z_note":         "G5z root cause: ETH-ecosystem alts vs SOL macro (Apr-May 2026 ETH/SOL divergence). Window-sensitivity artifact.",
            "g5q":              "LDO-SOL sig_corr=0.147 (W=84) PASS — restaking distinct from LSD mechanism",
            "g6_entries_yr":    33.9,
            "g6_note":          "W=84h G6-safe vs 20/yr threshold (33.9/yr OOS PASS)",
            "g8_result":        "PASS — HL EIGEN-PERP (from 2025-10-12) + Bybit EIGENUSDT (from 2024-09-18)",
            "g9_result":        "MARGINAL: OOS=118.6d < 120d (1.4d short, operational data limit). Monitor for full 180d.",
            "oos_sharpe":       OOS_SHARPE,
            "max_dd_oos_pct":   -0.5541,
            "w_hours":          84,
            "w_fallback_hours": 168,
            "w_fallback_note":  "W=168h fallback OOS Sh=33.17 if SOL liquidity issue",
            "sleeve_pct":       SLEEVE_PCT,
            "leverage":         LEVERAGE,
            "venue":            "HL primary (EIGEN-PERP + SOL-PERP). Bybit fallback (EIGENUSDT + SOLUSDT).",
            "hl_concentration": HL_CAP_PCT,
            "paper_gate_strict": True,
            "live_trigger":     (
                "K498/v6.52 OKX activation (HL% < 65%) + live gate (Sh>=15 + fill>=60% + maxDD<15%) "
                "+ G9 full 180d OOS + G5z BLUR-SOL W=84 OOS < 0.40 (monthly recheck)"
            ),
            "eigen_vertex":     "19th vertex (1st ETH-restaking cluster). MR9 L002: all future EIGEN-X auto-blocked.",
            "cluster":          "ETH restaking / AVS economy (EigenLayer) × Solana SVM",
            "eigen_fr_ann_approx_pct": -12.0,
            "restaking_vs_lsd": "LDO=liquid staking (stETH, consensus layer yield). EIGEN=restaking (AVS security, restaking yield). Mechanistically distinct.",
            "l003_avax":        "corr=0.0656 PASS (<0.45)",
            "l004_carry_full":  0.514,
            "l004_carry_oos":   0.436,
            "l007_fil":         "corr=0.0546 PASS (<0.45)",
            "l010_hbar":        "corr=0.1835 PASS (<0.45)",
            "l011_sol_direct":  "corr=0.1276 PASS (<0.50)",
            "g5q_ldo_sol":      "sig_corr=0.1368 (W=84) PASS — restaking distinct from LSD",
            "vol_ratio_full":   1.868,
            "vol_ratio_30d":    3.97,
            "bybit_eigen_listing": "EIGENUSDT from 2024-09-18. Linear perp. G8 PASS.",
            "hl_eigen_listing": "EIGEN-PERP from 2025-10-12. $1.10M/day. maxLeverage=5.",
        },
        "k523_projection": {
            "conservative_yr": K523_CONS,
            "central_yr":      CENTRAL_YR,
            "optimistic_yr":   K523_OPT,
            "note": f"K523 mandatory 3-point. Central=${CENTRAL_YR:,}/yr @$10M @{LEVERAGE}x @{SLEEVE_PCT:.1%}.",
        },
        "live_gate": {
            "realized_sharpe_min":    15.0,
            "fill_rate_min_pct":      60,
            "max_drawdown_max_pct":   15,
            "additional_gate":        "K498/v6.52 OKX activation required (HL% must drop below 65.0%)",
            "g9_gate":                "Full 180d OOS data required before live deployment",
            "g5z_gate":               "G5z BLUR-SOL W=84 OOS must settle < 0.40 on monthly recheck",
        },
        "daemon": {
            "number":      DAEMON_NUM,
            "label":       "com.cryptolab.k777-eigen-sol",
            "script":      "scripts/k777_eigen_sol_run.py",
            "interval_s":  28800,
        },
        "scaffold_verification": {
            "all_pass":     all_pass,
            "gates_passed": sum(checks.values()),
            "gates_total":  len(checks),
            "checks":       checks,
            "ts_jst":       ts_jst(),
        },
        "vertex_set_after_k777": [
            "APT","ATOM","AVAX","BNB","ENA","FIL","HBAR","INJ","LDO","SEI",
            "SOL","TIA","TAO","PEPE","WIF","BLUR","AXS","IO","EIGEN"
        ],
        "alt_alt_family_count":   20,
        "alt_alt_scaffold_count": 21,
        "note_mr9":    "EIGEN = 19th vertex (1st ETH-restaking cluster). MR9 L002: all future EIGEN-X pairs auto-blocked. EigenLayer AVS economy.",
        "note_g9":     "G9 marginal: OOS=118.6d < 120d (1.4d short). Monitor for full 180d before live.",
        "note_g5z":    "G5z BLUR-SOL borderline: OOS=0.441 (W=84). W=48 OOS=0.345 PASS. Monthly recheck required.",
        "note_g5q":    "G5q LDO-SOL=0.147 PASS (W=84). Restaking (EIGEN) distinct from LSD (LDO). Mechanism confirmed.",
        "note_hl_cap": "HL 66.8% AT CAP. Paper-gate strict. All live EIGEN-SOL capital requires K498/v6.52 OKX activation first.",
    }
    out_path = REPO_ROOT / "wave_k779_k777_scaffold.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    check(True, f"wave_k779_k777_scaffold.json written ({out_path})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*70}")
    print(f"K779 K777 EIGEN-SOL Alt-Alt Scaffold -- {ts_jst()}")
    print(f"{'='*70}")
    print(f"  Wave: {WAVE} | Strategy: K777 {PAIR} | Daemon: {DAEMON_NUM}")
    print(f"  OOS Sh={OOS_SHARPE} | G4 4/4 | G5 24/25 (G5z borderline) | G6 33.9/yr")
    print(f"  G8=PASS (HL+Bybit) | G9=MARGINAL (118.6d < 120d)")
    print(f"  Sleeve={SLEEVE_PCT:.1%} | Lev={LEVERAGE}x | HL={HL_CAP_PCT}% AT CAP")
    print(f"  K523: ${K523_CONS:,}/${CENTRAL_YR:,}/${K523_OPT:,}/yr @$10M")
    print(f"  EIGEN = {VERTEX_N} vertex (1st ETH-restaking). MR9 L002: all EIGEN-X blocked.")
    print(f"  Live gate: Sh>=15 + fill>=60% + maxDD<15% + K498/v6.52 + G9-180d + G5z<0.40")
    print(f"{'='*70}\n")

    print("Phase 8: Validation (all files should already be created):")
    checks = phase8_validate()

    print("\nPhase 9: Update report.html:")
    phase9_report_html(checks)

    print("\nPhase 10: Generate scaffold JSON:")
    result = phase10_json(checks)

    all_pass = all(checks.values())
    print(f"\n{'='*70}")
    print(f"K779 scaffold complete. All pass: {all_pass}")
    print(f"  Scaffold: {sum(checks.values())}/{len(checks)} checks PASS")
    print(f"  Decision: ACCEPT CONDITIONAL (G5z borderline, G9 marginal, HL paper-gate strict)")
    print(f"  Next: live gate (Sh>=15 + fill>=60% + maxDD<15%) after K498/v6.52 + G9-180d + G5z<0.40")
    print(f"{'='*70}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

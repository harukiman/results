#!/usr/bin/env python3
"""
wave_k776_k774_scaffold.py — K776 K774 IO-SOL Alt-Alt Scaffold
===============================================================
Wave K776: Production scaffold for K774 IO-SOL FR Differential (ACCEPT CONDITIONAL).
77th daemon, 20th alt-alt scaffold evaluated (19th alt-alt pair), 18th vertex IO (GPU-DePIN).

Scaffold tasks:
  Phase 1:  Verify scripts/k774_io_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k774-io-sol.plist (77th daemon, 8h/28800s)
  Phase 3:  Add K774 entry to data/leverage_config.json
  Phase 4:  Add K774 DaemonSpec to scripts/verify_deployment_status.py
  Phase 5:  Add --include-k774 flag to scripts/emergency_hl_exit.py
  Phase 6:  Add §78 section to docs/k302a_runbook.md
  Phase 7:  Initialize data/k774_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Update report.html (K776 K774 IO-SOL scaffold entry)
  Phase 10: Generate wave_k776_k774_scaffold.json

K774 ACCEPT CONDITIONAL parameters:
  OOS Sharpe:      19.884 (W=168h, zero threshold, 150.2d OOS — G9 marginal)
  G4 Walk-Forward: 12/12 ALL POSITIVE (min_sh=5.866)
  G5 26/26:        all gates PASS (max_corr=0.2778 G5s HBAR-SOL — all well below 0.40)
  G5v:             IO-SOL vs TAO-SOL corr=0.047 PASS (GPU-DePIN distinct from AI L1)
  G5s monitor:     HBAR-SOL borderline IS=0.352, full=0.278 — monthly recheck
  G8:              STRUCTURAL_NA (IO HIP-3 HL-only — no Bybit listing; K735/K747 precedent)
  G9:              MARGINAL OOS=150.2d < 180d — 60d gate compensates; monitor 180d
  Sleeve:          1.5% (HIP-3 HL-only liquidity constraint — IO $1.42M/day)
  K523 central:    $28,009/yr @$10M @4x @1.5%
  Vertex:          IO = 18th vertex (1st GPU-DePIN cluster)
  HL cap:          66.8% AT CAP → paper-gate strict

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent
DATA_DIR    = REPO_ROOT / "data"
DOCS_DIR    = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE         = "K776"
STRATEGY     = "K774"
PAIR         = "IO-SOL"
DAEMON_NUM   = "77th"
ALT_ALT_N    = "twentieth"    # scaffold count (evaluated)
ALT_ALT_PAIR = "nineteenth"   # actual pair number in family
VERTEX_N     = "18th"
CLUSTER      = "GPU-DePIN × Solana SVM"
OOS_SHARPE   = 19.884
SLEEVE_PCT   = 0.015
LEVERAGE     = 4.0
CENTRAL_YR   = 28009
K523_CONS    = 21007
K523_OPT     = 73707
HL_CAP_PCT   = 66.8


def ts_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def check(condition: bool, msg: str) -> bool:
    tag = "PASS" if condition else "FAIL"
    print(f"  [{tag}] {msg}")
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Verify run script
# ─────────────────────────────────────────────────────────────────────────────

def phase1_run_script() -> bool:
    path = SCRIPTS_DIR / "k774_io_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k774_io_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k774_io_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k774-io-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k774-io-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k774-io-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k774-io-sol")
    check(paper_ok,    "plist PAPER_TRADE=True default")
    return interval_ok and label_ok and paper_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — leverage_config.json
# ─────────────────────────────────────────────────────────────────────────────

def phase3_leverage_config() -> bool:
    path = DATA_DIR / "leverage_config.json"
    if not path.exists():
        check(False, "data/leverage_config.json exists")
        return False

    config = json.loads(path.read_text())
    k774_key = "K774_IO_SOL"

    if k774_key in config:
        check(True, f"data/leverage_config.json: {k774_key} entry already present")
    else:
        check(False, f"data/leverage_config.json: {k774_key} entry MISSING (add manually)")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — verify_deployment_status.py
# ─────────────────────────────────────────────────────────────────────────────

def phase4_verify_deployment() -> bool:
    path = SCRIPTS_DIR / "verify_deployment_status.py"
    if not path.exists():
        check(False, "scripts/verify_deployment_status.py exists")
        return False

    content = path.read_text()
    present = "k774-io-sol" in content
    check(present, "verify_deployment_status.py: K774 DaemonSpec present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — emergency_hl_exit.py
# ─────────────────────────────────────────────────────────────────────────────

def phase5_emergency_exit() -> bool:
    path = SCRIPTS_DIR / "emergency_hl_exit.py"
    if not path.exists():
        check(False, "scripts/emergency_hl_exit.py exists")
        return False

    content = path.read_text()
    present = "include-k774" in content
    check(present, "emergency_hl_exit.py: --include-k774 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §78
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§78" in content and "K774 IO-SOL" in content
    check(present, "docs/k302a_runbook.md: §78 K774 IO-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — data/k774_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k774_dashboard.json"
    exists = path.exists()
    check(exists, "data/k774_dashboard.json exists")
    if not exists:
        return False

    try:
        dash = json.loads(path.read_text())
        wave_ok  = dash.get("wave") == "K776"
        strat_ok = "K774" in dash.get("strategy", "")
        check(wave_ok,  "data/k774_dashboard.json: wave=K776")
        check(strat_ok, "data/k774_dashboard.json: strategy contains K774")
        return wave_ok and strat_ok
    except Exception as e:
        check(False, f"data/k774_dashboard.json: JSON parse error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 — Full validation
# ─────────────────────────────────────────────────────────────────────────────

def phase8_validate() -> dict:
    results = {
        "run_script":         phase1_run_script(),
        "plist":              phase2_plist(),
        "leverage_config":    phase3_leverage_config(),
        "verify_deployment":  phase4_verify_deployment(),
        "emergency_exit":     phase5_emergency_exit(),
        "runbook_s78":        phase6_runbook(),
        "dashboard":          phase7_dashboard(),
    }
    all_pass = all(results.values())
    passed   = sum(results.values())
    total    = len(results)
    print(f"\n  Scaffold validation: {passed}/{total} PASS  (all_pass={all_pass})")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 — Update report.html
# ─────────────────────────────────────────────────────────────────────────────

def phase9_report_html(checks: dict) -> bool:
    path = REPO_ROOT / "report.html"
    if not path.exists():
        check(False, "report.html exists")
        return False

    content = path.read_text()
    if "K776" in content and "K774" in content and "IO-SOL" in content:
        check(True, "report.html: K776 K774 IO-SOL entry already present")
        return True

    all_pass = all(checks.values())
    status_badge = (
        '<span style="color:#27ae60;font-weight:bold">SCAFFOLD-READY</span>'
        if all_pass else
        '<span style="color:#e67e22;font-weight:bold">SCAFFOLD-PARTIAL</span>'
    )
    checks_html = "".join(
        f'<span style="color:{"#27ae60" if v else "#e74c3c"}">'
        f'{"✓" if v else "✗"} {k}</span><br>'
        for k, v in checks.items()
    )

    entry = f"""
<!-- K776 K774 IO-SOL scaffold entry -->
<div class="wave-entry" style="border-left:4px solid #8e44ad;padding:12px;margin:8px 0;background:#1a1a2e;border-radius:4px">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <strong style="color:#8e44ad">K776</strong>
      <span style="color:#e0e0e0;margin-left:8px">K774 IO-SOL FR Differential Scaffold</span>
      <span style="color:#aaa;font-size:0.85em;margin-left:8px">(77th daemon, 19th alt-alt pair, 18th vertex IO GPU-DePIN)</span>
    </div>
    <div>{status_badge}</div>
  </div>
  <div style="margin-top:8px;font-size:0.88em;color:#ccc">
    <strong>OOS Sh:</strong> 19.884 &nbsp;|&nbsp;
    <strong>G4:</strong> 12/12 ALL POSITIVE &nbsp;|&nbsp;
    <strong>G5:</strong> 26/26 PASS (max=0.2778 G5s HBAR-SOL) &nbsp;|&nbsp;
    <strong>G6:</strong> 48.6/yr PASS &nbsp;|&nbsp;
    <strong>G8:</strong> STRUCTURAL_NA (HL-only) &nbsp;|&nbsp;
    <strong>G9:</strong> MARGINAL 150.2d &lt; 180d
  </div>
  <div style="margin-top:4px;font-size:0.88em;color:#ccc">
    <strong>Signal:</strong> IO_FR - SOL_FR (W=168h, zero threshold) &nbsp;|&nbsp;
    <strong>Sleeve:</strong> 1.5% @$10M &nbsp;|&nbsp;
    <strong>Leverage:</strong> 4x &nbsp;|&nbsp;
    <strong>Venue:</strong> HL-only (IO HIP-3, NOT on Bybit)
  </div>
  <div style="margin-top:4px;font-size:0.88em;color:#ccc">
    <strong>K523:</strong> cons=$21K | ctr=$28K | opt=$74K/yr @$10M &nbsp;|&nbsp;
    <strong>MaxDD OOS:</strong> -0.39% &nbsp;|&nbsp;
    <strong>HL:</strong> 66.8% AT CAP → paper-gate strict
  </div>
  <div style="margin-top:4px;font-size:0.85em;color:#aaa">
    IO = 18th vertex (1st GPU-DePIN cluster). MR9 L002: all future IO-X blocked.
    Double carry (BEAR_IO structural): SHORT IO -17.9%/yr + LONG SOL +2.59%/yr.
    G5v IO-SOL vs TAO-SOL=0.047 PASS (GPU-DePIN distinct from AI L1).
    G5s HBAR-SOL monthly recheck (IS=0.352 borderline). G9 monitor for full 180d.
  </div>
  <div style="margin-top:6px;font-size:0.82em;color:#888">
    {checks_html}
    <span style="color:#666">Updated: {ts_jst()}</span>
  </div>
</div>
"""

    # Insert before </body> or at a known insertion point
    if "</body>" in content:
        new_content = content.replace("</body>", entry + "\n</body>", 1)
    else:
        new_content = content + entry

    path.write_text(new_content)
    check(True, "report.html: K776 K774 IO-SOL entry added")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Generate wave_k776_k774_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    all_pass = all(checks.values())
    result = {
        "wave": WAVE,
        "strategy": f"K774 IO-SOL FR Differential Alt-Alt (GPU-DePIN × Solana SVM — 18th vertex IO)",
        "run_time_jst": ts_jst(),
        "k774_result": {
            "decision": "ACCEPT CONDITIONAL",
            "g4_wf": "12/12 ALL POSITIVE (min_sh=5.866)",
            "g5_result": "26/26 PASS (max_corr=0.2778 G5s HBAR-SOL — all well below 0.40)",
            "g5v": "IO-SOL vs TAO-SOL corr=0.047 PASS (GPU-DePIN distinct from AI L1)",
            "g5s_monitor": "HBAR-SOL borderline (IS=0.352, full=0.278) — monthly recheck required",
            "g6_entries_yr": 48.6,
            "g6_note": "W=168h G6-safe vs 30/yr threshold (all grid configs PASS)",
            "g8_result": "STRUCTURAL_NA — IO HIP-3 HL-only (no Bybit listing; K735/K747 precedent)",
            "g9_result": "MARGINAL: OOS=150.2d < 180d threshold. 60d gate compensates.",
            "oos_sharpe": OOS_SHARPE,
            "max_dd_oos_pct": -0.389955,
            "w_hours": 168,
            "sleeve_pct": SLEEVE_PCT,
            "leverage": LEVERAGE,
            "venue": "HL-only (IO-PERP + SOL-PERP). IO NOT on Bybit (HIP-3 fresh Jan 2025).",
            "hl_concentration": HL_CAP_PCT,
            "paper_gate_strict": True,
            "live_trigger": (
                "K498/v6.52 OKX activation (HL% < 65%) + 60d gate (Sh>=10 + fill>=60% + maxDD<15%) "
                "+ G9 full 180d OOS + G5s HBAR-SOL stable on monthly recheck"
            ),
            "io_vertex": "18th vertex (1st GPU-DePIN cluster). MR9 L002: all future IO-X auto-blocked.",
            "cluster": "GPU-DePIN (io.net GPU compute marketplace) × Solana SVM",
            "io_fr_ann_pct": -17.8941,
            "sol_fr_ann_pct": 2.5922,
            "double_carry": "BEAR_IO structural: SHORT IO -17.9%/yr + LONG SOL +2.59%/yr = double carry both favorable",
            "io_vs_tao_distinction": "io.net = GPU compute supply aggregation (hardware DePIN) DISTINCT from Bittensor TAO AI L1 (substrate tokenization)",
            "l003_avax": "corr=0.2402 PASS (<0.45)",
            "l004_carry_full": 0.5194,
            "l004_carry_oos": 0.5662,
            "l007_fil": "signal corr=-0.0831 PASS (<0.45)",
            "l010_hbar": "corr=0.2212 PASS (<0.45)",
            "l011_sol_direct": "corr=0.1516 PASS (<0.50)",
            "grid_note": "Best grid W=48h T=0.25 OOS Sh=31.42 (61 entries/yr). W=168h chosen for family consistency.",
        },
        "k523_projection": {
            "conservative_yr": K523_CONS,
            "central_yr": CENTRAL_YR,
            "optimistic_yr": K523_OPT,
            "note": f"K523 mandatory 3-point. Central=${CENTRAL_YR:,}/yr @$10M @{LEVERAGE}x @{SLEEVE_PCT:.1%}."
        },
        "gate_60d": {
            "realized_sharpe_min": 10.0,
            "fill_rate_min_pct": 60,
            "max_drawdown_max_pct": 15,
            "additional_gate": "K498/v6.52 OKX activation required (HL% must drop below 65.0%)",
            "g9_gate": "Full 180d OOS data required before live deployment",
            "g5s_gate": "HBAR-SOL corr stable on monthly recheck (IS=0.352 borderline)",
        },
        "daemon": {
            "number": DAEMON_NUM,
            "label": "com.cryptolab.k774-io-sol",
            "script": "scripts/k774_io_sol_run.py",
            "interval_s": 28800,
        },
        "scaffold_verification": {
            "all_pass": all_pass,
            "gates_passed": sum(checks.values()),
            "gates_total": len(checks),
            "checks": checks,
            "ts_jst": ts_jst(),
        },
        "vertex_set_after_k774": [
            "APT","ATOM","AVAX","BNB","ENA","FIL","HBAR","INJ","LDO","SEI",
            "SOL","TIA","TAO","PEPE","WIF","BLUR","AXS","IO"
        ],
        "alt_alt_family_count": 19,
        "alt_alt_scaffold_count": 20,
        "note_mr9": "IO = 18th vertex (1st GPU-DePIN cluster). MR9 L002: all future IO-X pairs auto-blocked. io.net GPU compute marketplace.",
        "note_g9": "G9 marginal: OOS=150.2d < 180d. Monitor for full 180d before live. 60d gate compensates.",
        "note_g5s": "G5s HBAR-SOL borderline: IS=0.352, full=0.278. Monthly recheck required.",
        "note_hl_cap": "HL 66.8% AT CAP. Paper-gate strict. All live IO-SOL capital requires K498/v6.52 OKX activation first.",
    }
    out_path = REPO_ROOT / "wave_k776_k774_scaffold.json"
    out_path.write_text(json.dumps(result, indent=2))
    check(True, f"wave_k776_k774_scaffold.json written ({out_path})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*70}")
    print(f"K776 K774 IO-SOL Alt-Alt Scaffold — {ts_jst()}")
    print(f"{'='*70}")
    print(f"  Wave: {WAVE} | Strategy: K774 {PAIR} | Daemon: {DAEMON_NUM}")
    print(f"  OOS Sh={OOS_SHARPE} | G4 12/12 | G5 26/26 | G6 48.6/yr")
    print(f"  G8=STRUCTURAL_NA (HL-only) | G9=MARGINAL (150.2d < 180d)")
    print(f"  Sleeve={SLEEVE_PCT:.1%} | Lev={LEVERAGE}x | HL={HL_CAP_PCT}% AT CAP")
    print(f"  K523: ${K523_CONS:,}/${CENTRAL_YR:,}/${K523_OPT:,}/yr @$10M")
    print(f"  IO = {VERTEX_N} vertex (1st GPU-DePIN). MR9 L002: all IO-X blocked.")
    print(f"{'='*70}\n")

    print("Phase 8: Validation (all files should already be created):")
    checks = phase8_validate()

    print("\nPhase 9: Update report.html:")
    phase9_report_html(checks)

    print("\nPhase 10: Generate scaffold JSON:")
    result = phase10_json(checks)

    all_pass = all(checks.values())
    print(f"\n{'='*70}")
    print(f"K776 scaffold complete. All pass: {all_pass}")
    print(f"  Scaffold: {sum(checks.values())}/{len(checks)} checks PASS")
    print(f"  Decision: ACCEPT CONDITIONAL (G9 marginal, HL paper-gate strict)")
    print(f"  Next: 60d paper-trade gate → live after K498/v6.52 + G9 180d + G5s stable")
    print(f"{'='*70}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

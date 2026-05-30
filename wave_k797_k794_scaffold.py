#!/usr/bin/env python3
"""
wave_k797_k794_scaffold.py — K797 K794 ME-SOL Alt-Alt Scaffold (RESEARCH_ONLY)
=================================================================
Wave K797: Production scaffold for K794 ME-SOL FR Differential
  (CONDITIONAL_ACCEPT_RESEARCH_ONLY 8/9 — G8 FAIL HL-only $85K/day).
84th daemon, 26th alt-alt scaffold (25th alt-alt pair evaluated), 23rd vertex candidate ME.

Scaffold tasks:
  Phase 1:  Verify scripts/k794_me_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k794-me-sol.plist (84th daemon, 8h/28800s)
  Phase 3:  Verify K794 entry in data/leverage_config.json
  Phase 4:  Verify K794 DaemonSpec in scripts/verify_deployment_status.py
  Phase 5:  Verify --include-k794 flag in scripts/emergency_hl_exit.py
  Phase 6:  Verify §85 section in docs/k302a_runbook.md
  Phase 7:  Verify data/k794_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Verify report.html (K797 K794 ME-SOL scaffold entry)
  Phase 10: Generate wave_k797_k794_scaffold.json

K794 CONDITIONAL_ACCEPT_RESEARCH_ONLY parameters:
  OOS Sharpe:      19.47 (W=84h, zero threshold, 217d OOS — G9 PASS >= 180d)
  IS Sharpe:       19.13 (W=84h) — OOS > IS (no directional overfit — GOOD)
  G2 Perm p-value: 0.000 — timing alpha confirmed (THIN: +0.45 Sh above carry IS Sh=18.68)
  G3 DSR:          t-stat=15.04, p=0.000 — PASS
  G4 Walk-Forward: 11/11 ALL POSITIVE (min_fold_sh=2.43 Fold 2)
  G5 28/28:        ALL PASS (max_corr=0.2075 G5z EIGEN-SOL, below 0.40)
  G5w:             PEPE-SOL=0.057 PASS (ETH meme cluster CLEAR)
  G5y:             WIF-SOL=0.013 PASS (SOL-native meme cluster CLEAR)
  G5ab:            MEME-SOL=0.008 PASS (22nd vertex ERC-20 meme cluster CLEAR)
  G6:              30.2 entries/yr OOS PASS MARGINAL (0.2/yr above 30/yr threshold)
  G7:              OOS ann ret 3x=260.7% PASS
  G8:              FAIL — ME HL-only HIP-3 (OI=$2.26M, $85K/day — Bybit/OKX not listed)
  G9:              PASS — OOS=217 days (above 180d threshold)
  L004:            PASS — ME bidirectional (carry_full=0.5713 carry_oos=0.5014)
  L004_DIFF:       BORDERLINE full=0.282 (<0.30 floor), OOS=0.396 PASS (G2 overrides)
  Sleeve:          0.25% (@$10M = $25K margin, $75K notional at 3x)
  K523 central:    $39,100/yr @$10M @3x @0.25%
  Vertex:          ME = 23rd vertex candidate (1st SVM NFT marketplace cluster)
  HL cap:          66.8% AT CAP -> research-only + paper-gate strict
  RESEARCH_ONLY:   HARDCODED in k794_me_sol_run.py — NOT eligible for live
  G8 gate:         NOT resolving until Bybit/OKX ME listing + vol > $500K/day
  Re-eval trigger: ME vol > $500K/day AND Bybit listing AND G2 > +1 Sh
  Live gate:       NOT ELIGIBLE (research-only — requires governance review)

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

WAVE         = "K797"
STRATEGY     = "K794"
PAIR         = "ME-SOL"
DAEMON_NUM   = "84th"
ALT_ALT_N    = "twenty-sixth"    # scaffold count
ALT_ALT_PAIR = "twenty-fifth"    # actual pair number in family
VERTEX_N     = "23rd"
CLUSTER      = "SVM NFT Marketplace × Solana SVM"
OOS_SHARPE   = 19.47
IS_SHARPE    = 19.13
SLEEVE_PCT   = 0.0025
LEVERAGE     = 3.0
CENTRAL_YR   = 39100
K523_CONS    = 24763
K523_OPT     = 55392
HL_CAP_PCT   = 66.8
RESEARCH_ONLY = True  # HARDCODED


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
    path = SCRIPTS_DIR / "k794_me_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k794_me_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k794_me_sol_run.py syntax OK")

    # Verify RESEARCH_ONLY=True is hardcoded
    content = path.read_text()
    research_ok = "RESEARCH_ONLY       = True" in content or "RESEARCH_ONLY = True" in content
    check(research_ok, "scripts/k794_me_sol_run.py: RESEARCH_ONLY=True hardcoded")
    return syntax_ok and research_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k794-me-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k794-me-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k794-me-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k794-me-sol")
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
    k794_key = "K794_ME_SOL"

    if k794_key in config:
        check(True, f"data/leverage_config.json: {k794_key} entry present")
        entry = config[k794_key]
        research_ok = entry.get("research_only", False)
        check(research_ok, f"data/leverage_config.json: {k794_key}.research_only=True")
        return research_ok
    else:
        check(False, f"data/leverage_config.json: {k794_key} entry MISSING")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — verify_deployment_status.py
# ─────────────────────────────────────────────────────────────────────────────

def phase4_verify_deployment() -> bool:
    path = SCRIPTS_DIR / "verify_deployment_status.py"
    if not path.exists():
        check(False, "scripts/verify_deployment_status.py exists")
        return False

    content = path.read_text()
    present = "k794-me-sol" in content
    check(present, "verify_deployment_status.py: K794 DaemonSpec present")
    research_note = "RESEARCH-ONLY" in content or "RESEARCH_ONLY" in content
    check(research_note, "verify_deployment_status.py: RESEARCH_ONLY note present for K794")
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
    present = "include-k794" in content
    check(present, "emergency_hl_exit.py: --include-k794 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §85
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§85" in content and "K794 ME-SOL" in content
    check(present, "docs/k302a_runbook.md: §85 K794 ME-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — data/k794_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k794_dashboard.json"
    exists = path.exists()
    check(exists, "data/k794_dashboard.json exists")
    if not exists:
        return False

    try:
        dash = json.loads(path.read_text())
        wave_ok     = dash.get("wave") == "K797"
        strat_ok    = "K794" in dash.get("strategy", "")
        research_ok = dash.get("research_only", False) is True
        check(wave_ok,     "data/k794_dashboard.json: wave=K797")
        check(strat_ok,    "data/k794_dashboard.json: strategy contains K794")
        check(research_ok, "data/k794_dashboard.json: research_only=True")
        return wave_ok and strat_ok and research_ok
    except Exception as e:
        check(False, f"data/k794_dashboard.json: JSON parse error: {e}")
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
        "runbook_s85":        phase6_runbook(),
        "dashboard":          phase7_dashboard(),
    }
    all_pass = all(results.values())
    passed   = sum(results.values())
    total    = len(results)
    print(f"\n  Scaffold validation: {passed}/{total} PASS  (all_pass={all_pass})")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 — Verify report.html
# ─────────────────────────────────────────────────────────────────────────────

def phase9_report_html(checks: dict) -> bool:
    path = REPO_ROOT / "report.html"
    if not path.exists():
        check(False, "report.html exists")
        return False

    content = path.read_text()
    if "K797" in content and "K794" in content and "ME-SOL" in content:
        check(True, "report.html: K797 K794 ME-SOL entry already present")
        return True

    check(False, "report.html: K797 K794 ME-SOL entry MISSING -- add manually")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Generate wave_k797_k794_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    out_path = REPO_ROOT / "wave_k797_k794_scaffold.json"
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
            check(True, f"wave_k797_k794_scaffold.json exists and valid JSON")
            return result
        except Exception as e:
            check(False, f"wave_k797_k794_scaffold.json: JSON parse error: {e}")

    # Write scaffold JSON
    all_pass = all(checks.values())
    result = {
        "wave": WAVE,
        "strategy": (
            f"K794 ME-SOL FR Differential Alt-Alt "
            f"(SVM NFT Marketplace Magic Eden x Solana SVM — {VERTEX_N} vertex candidate ME, RESEARCH_ONLY)"
        ),
        "run_time_jst": ts_jst(),
        "research_only": RESEARCH_ONLY,
        "decision": "CONDITIONAL_ACCEPT_RESEARCH_ONLY",
        "gates": "8/9 (G8 FAIL)",
        "oos_sharpe": OOS_SHARPE,
        "is_sharpe": IS_SHARPE,
        "k523_central_yr": CENTRAL_YR,
        "k523_cons_yr": K523_CONS,
        "k523_opt_yr": K523_OPT,
        "sleeve_pct": SLEEVE_PCT,
        "leverage": LEVERAGE,
        "daemon_num": DAEMON_NUM,
        "alt_alt_scaffold_n": ALT_ALT_N,
        "alt_alt_pair_n": ALT_ALT_PAIR,
        "vertex_n": VERTEX_N,
        "cluster": CLUSTER,
        "hl_cap_pct": HL_CAP_PCT,
        "g8_result": "FAIL -- ME HL-only HIP-3 (OI=$2.26M, $85K/day -- no Bybit/OKX)",
        "g9_result": "PASS -- OOS=217 days (above 180d threshold)",
        "g6_result": "MARGINAL 30.2/yr (0.2/yr above 30/yr threshold). G6 fallback: W=48h (57/yr).",
        "g2_result": "p=0.000 -- timing alpha confirmed (THIN: +0.45 Sh above carry IS Sh=18.68)",
        "g4_result": "11/11 ALL POSITIVE (min_fold_sh=2.43 Fold 2)",
        "g5_result": "28/28 ALL PASS: max_corr=0.2075 (G5z EIGEN-SOL, below 0.40)",
        "g5_meme_checks": {
            "G5w_PEPE_SOL": "0.057 PASS",
            "G5y_WIF_SOL": "0.013 PASS",
            "G5ab_MEME_SOL": "0.008 PASS",
        },
        "l004_result": "PASS (carry_full=0.5713 carry_oos=0.5014 -- bidirectional)",
        "l004_diff_result": "BORDERLINE full=0.282 (<0.30 floor), OOS=0.396 PASS (G2 overrides)",
        "vol_ratio": 12.66,
        "raw_corr": 0.0472,
        "me_fr_mean_bps": -0.693,
        "timing_alpha_sh": 0.45,
        "re_eval_triggers": [
            "ME daily vol > $500K/day (currently $85K/day)",
            "Bybit/OKX ME perp listing confirmed (G8 FAIL resolution)",
            "G2 timing alpha > +1 Sh (currently thin +0.45 Sh above carry)",
            "HL concentration < 65% (currently 66.8% AT CAP)",
        ],
        "vertex_set_candidate": [
            "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ", "LDO", "SEI",
            "SOL", "TIA", "TAO", "PEPE", "WIF", "BLUR", "AXS", "IO", "EIGEN", "COMP",
            "BIO", "MEME", "ME"
        ],
        "scaffold_verification": {
            "all_pass": all_pass,
            "gates_passed": sum(checks.values()),
            "gates_total": len(checks),
            "checks": checks,
            "ts_jst": ts_jst(),
        },
    }
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    check(True, f"wave_k797_k794_scaffold.json written ({out_path})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*70}")
    print(f"K797 K794 ME-SOL Alt-Alt Scaffold (RESEARCH_ONLY) — {ts_jst()}")
    print(f"{'='*70}")
    print(f"  Wave: {WAVE} | Strategy: K794 {PAIR} | Daemon: {DAEMON_NUM}")
    print(f"  Mode: RESEARCH_ONLY={RESEARCH_ONLY} (HARDCODED -- not configurable via env)")
    print(f"  OOS Sh={OOS_SHARPE} | IS Sh={IS_SHARPE} (OOS > IS -- no directional overfit)")
    print(f"  G2 p=0.000 timing alpha THIN +0.45 Sh above carry (IS carry Sh=18.68)")
    print(f"  G4 11/11 ALL POSITIVE (min_sh=2.43 Fold 2) | G5 28/28 ALL PASS | G6 30.2/yr MARGINAL")
    print(f"  G5w PEPE-SOL=0.057 | G5y WIF-SOL=0.013 | G5ab MEME-SOL=0.008 (meme clusters CLEAR)")
    print(f"  G8 FAIL: ME HL-only HIP-3 ($85K/day -- no Bybit/OKX)")
    print(f"  G9 PASS: OOS=217 days (>= 180d threshold)")
    print(f"  L004 PASS: ME bidirectional (carry_full=0.5713 carry_oos=0.5014)")
    print(f"  L004_DIFF BORDERLINE: full=0.282 (<0.30 floor), OOS=0.396 PASS. G2 overrides. Monthly recheck.")
    print(f"  Sleeve={SLEEVE_PCT:.2%} | Lev={LEVERAGE}x (HL max for ME) | HL={HL_CAP_PCT}% AT CAP")
    print(f"  K523: ${K523_CONS:,}/${CENTRAL_YR:,}/${K523_OPT:,}/yr @$10M")
    print(f"  ME = {VERTEX_N} vertex candidate (1st SVM NFT marketplace cluster). MR9 L002: all ME-X blocked.")
    print(f"  Re-eval trigger: ME vol > $500K/day + Bybit listing + G2 > +1 Sh")
    print(f"  Live gate: NOT ELIGIBLE (RESEARCH_ONLY hardcoded)")
    print(f"{'='*70}\n")

    print("Phase 8: Validation (all files should already be created):")
    checks = phase8_validate()

    print("\nPhase 9: Verify report.html:")
    phase9_report_html(checks)

    print("\nPhase 10: Generate scaffold JSON:")
    result = phase10_json(checks)

    all_pass = all(checks.values())
    print(f"\n{'='*70}")
    print(f"K797 scaffold complete. All pass: {all_pass}")
    print(f"  Scaffold: {sum(checks.values())}/{len(checks)} checks PASS")
    print(f"  Decision: CONDITIONAL_ACCEPT_RESEARCH_ONLY 8/9 (G8 FAIL -- HL-only HIP-3 $85K/day)")
    print(f"  Mode: RESEARCH_ONLY HARDCODED -- monitor paper-trade only")
    print(f"  Re-eval: ME vol > $500K/day + Bybit + G2 > +1 Sh + HL% < 65%")
    print(f"  Next: continue monitoring; trigger gov review when all 4 re-eval triggers met")
    print(f"{'='*70}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

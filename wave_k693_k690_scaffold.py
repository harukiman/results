#!/usr/bin/env python3
"""
wave_k693_k690_scaffold.py — K693 Wave Driver + Verification
=============================================================
Verifies all K693 deliverables for the K690 SEI-SOL production scaffold:
  - Phase 1:  Strategy script (k690_sei_sol_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k690-sei-sol.plist, 58th daemon)
  - Phase 3:  Dashboard (k690_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k690 flag)
  - Phase 5:  Leverage manager (K690_SEI_SOL cap + SLEEVE_WEIGHTS_V645)
  - Phase 6:  Leverage config (k690_notes + K690_SEI_SOL)
  - Phase 7:  Deployment verification (58th daemon)
  - Phase 8:  Runbook §60 (K690 SEI-SOL playbook)
  - Phase 9:  HTML update (K690 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=12, K693 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K690 pattern (K693 scaffold):
  - Signal: diff = SEI_FR - SOL_FR (direct alt-alt, no base asset)
  - W=168h rolling mean, zero threshold (sign only)
  - FIFTH ALT-ALT pair (no BTC/ETH leg) — WF 12/12 UNPRECEDENTED in family
  - Both SEI-PERP and SOL-PERP on Bybit (HL 62.5% headroom preserved)
  - OOS Sharpe 25.11 (W=168h, ~218d OOS, 12/12 G4 folds positive)
  - $104,174/yr net @$10M @4x (3% standalone sleeve)
  - K507+K476 algebraic overlap: run K690 STANDALONE
  - K682+K686+K690 share SOL leg: monitor SOL triple-exposure
  - Anti-corr K690 vs K507 = -0.5109 (K690 HEDGES K507 long-SEI)
  - Mid-cap alt-alt exception: SEI/SOL vol ratio=1.32x, ADF p=1.01e-23, OU 4.41h STRONG
  - SEI NEGATIVE mean FR -3.65%/ann: dominant BEAR_SEI regime carry-positive in both legs

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / "cache"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE     = "K693"
STRATEGY = "K690 SEI-SOL FR Differential (FIFTH ALT-ALT pair, Bybit-only, Cosmos EVM parallel vs Solana SVM retail)"


def _check_file(path: Path, description: str) -> dict:
    exists = path.exists()
    size   = path.stat().st_size if exists else 0
    return {
        "path":        str(path.relative_to(REPO_ROOT)),
        "description": description,
        "exists":      exists,
        "size_bytes":  size,
        "status":      "PASS" if exists and size > 0 else "FAIL",
    }


def check_deliverables() -> dict:
    """Verify all K693 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k690_sei_sol_run.py",
            "Phase 1: K690 strategy script (K339 pattern, W=168h, alt-alt direct diff, Bybit-only)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k690-sei-sol.plist",
            "Phase 2: 58th daemon plist (StartInterval 28800, Bybit-only)"
        ),
        _check_file(
            DATA_DIR / "k690_dashboard.json",
            "Phase 3: Dashboard (alt-alt diff signal, regime, alt_alt_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k690 flag, §60)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K690_SEI_SOL cap + SLEEVE_WEIGHTS_V645)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K690_SEI_SOL: 4.0 + k690_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (58th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §60 (K690 SEI-SOL playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K690 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k693_k690_scaffold.py",
            "Phase 11: Wave driver (this file)"
        ),
    ]
    return {
        "checks":   checks,
        "total":    len(checks),
        "passed":   sum(1 for c in checks if c["status"] == "PASS"),
        "failed":   sum(1 for c in checks if c["status"] == "FAIL"),
        "all_pass": all(c["status"] == "PASS" for c in checks),
    }


def check_content_integrity() -> dict:
    """Spot-check key content in critical files."""
    results = {}

    # Check k690_sei_sol_run.py
    script_path = REPO_ROOT / "scripts" / "k690_sei_sol_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["k339_repo_root"]           = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]      = "PAPER_TRADE         = True" in content
        results["sleeve_3pct"]              = "SLEEVE_PCT          = 0.030" in content
        results["leverage_4x"]             = "LEVERAGE            = 4.0" in content
        results["rolling_168h"]            = "EMA_PERIOD_HOURS    = 168" in content
        results["zero_threshold"]          = "SIGNAL_SIGMA_MULT   = 0.0" in content
        results["bybit_only"]             = "BYBIT_ONLY" in content
        results["post_only"]             = "POST_ONLY_PARALLEL" in content
        results["fifth_alt_alt"]          = "FIFTH ALT-ALT" in content
        results["sei_sol_diff"]           = "sei_sol_diff" in content
        results["symbols_sei_sol"]        = 'SYMBOLS = ("SEI", "SOL")' in content
        results["dashboard_path"]         = "k690_dashboard.json" in content
        results["oos_sh_25_11"]           = "25.11" in content
        results["k507_k476_warning"]      = "K507+K476" in content or "K507 SEI-BTC" in content
        results["hl_62_5"]                = "62.5" in content
        results["profit_104k"]            = "104,174" in content
        results["58th_daemon"]            = "58th" in content
        results["wf_12_12"]               = "12/12" in content
        results["negative_fr"]            = "NEGATIVE" in content
        results["carry_dominant"]         = "carry-positive" in content or "CARRY-POSITIVE" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k690_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]         = "regime" in dash
            results["dashboard_oos_perf"]       = "oos_performance" in dash
            results["dashboard_alt_mech"]       = "alt_alt_mechanism" in dash
            results["dashboard_hl_625"]         = dash.get("hl_concentration_pct") == 62.5
            results["dashboard_gate_sh12"]      = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 12.0
            results["dashboard_sleeve_030"]     = dash.get("sleeve_pct") == 0.030
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k690_cap"]    = cfg.get("exchange_caps", {}).get("K690_SEI_SOL") == 4.0
            results["cfg_k690_notes"]  = "k690_notes" in cfg
            results["cfg_sleeve_030"]  = cfg.get("k690_notes", {}).get("sleeve_pct") == 0.03
            results["cfg_bybit_only"]  = cfg.get("k690_notes", {}).get("bybit_only") is True
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k690"]     = "--include-k690" in content
        results["emer_k690_bybit_note"]  = "K690 SEI-SOL: Bybit-only" in content or "K690 SEI-SOL CLOSE SUMMARY" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k690_cap"]        = "K690_SEI_SOL" in content
        results["lev_v645_weights"]    = "SLEEVE_WEIGHTS_V645" in content
        results["lev_k690_030pct"]     = '"K690":    0.03,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k690_label"]      = "com.cryptolab.k690-sei-sol" in content
        results["vds_58th_daemon"]     = "58th daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section60"]    = "## §60 K690 SEI-SOL FR Differential" in content
        results["runbook_fifth_altalt"] = "FIFTH ALT-ALT" in content
        results["runbook_k507_overlap"] = "K507+K476" in content or "K507 SEI-BTC" in content
        results["runbook_profit_104k"]  = "104,174" in content or "104K" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k693_scaffold"]  = "K693" in content
        results["html_58th_daemon"]    = "58th" in content
        results["html_k690_scaffold_ready"] = "SCAFFOLD-READY" in content and "K690" in content

    return results


def run_dry_run_check() -> dict:
    """Run k690_sei_sol_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k690_sei_sol_run.py"
    if not script_path.exists():
        return {"status": "SKIP", "reason": "script missing"}
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--status"],
            capture_output=True, text=True, timeout=15,
            cwd=str(REPO_ROOT),
        )
        ok = result.returncode == 0
        return {
            "status":       "PASS" if ok else "FAIL",
            "returncode":   result.returncode,
            "stdout_lines": result.stdout.strip().splitlines()[:5],
            "stderr_lines": result.stderr.strip().splitlines()[:3],
        }
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "reason": "script took > 15s"}
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def generate_report() -> dict:
    """Generate full K693 scaffold verification report."""
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    deliverables = check_deliverables()
    content      = check_content_integrity()
    dry_run      = run_dry_run_check()

    content_pass = sum(1 for v in content.values() if v is True)
    content_fail = sum(1 for v in content.values() if v is False)

    # Overall status
    overall = (
        deliverables["all_pass"]
        and content_fail == 0
        and dry_run.get("status") in ("PASS", "SKIP")
    )

    report = {
        "wave":              WAVE,
        "strategy":          STRATEGY,
        "run_time_jst":      ts_jst,
        "overall_status":    "PASS" if overall else "PARTIAL",
        "deliverables":      deliverables,
        "content_integrity": {
            "checks": content,
            "pass":   content_pass,
            "fail":   content_fail,
        },
        "dry_run":           dry_run,
        "scaffold_summary": {
            "daemon_number":        "58th",
            "strategy":             "K690 SEI-SOL FR Differential (FIFTH ALT-ALT pair)",
            "signal":               "sign(rolling_mean_168h(SEI_FR - SOL_FR))",
            "threshold":            "zero (sign only)",
            "ema_window_h":         168,
            "leverage":             4.0,
            "sleeve_pct":           0.030,
            "venue":                "Bybit-only (SEI-PERP + SOL-PERP, both Bybit)",
            "hl_concentration_pct": 62.5,
            "hl_cap_note":          "62.5% within 65% cap — Bybit-only preferred (2.5pp headroom preserved)",
            "oos_sharpe":           25.11,
            "oos_period":           "~2025-10-23 to 2026-05-23",
            "profit_net_yr_10m":    104174,
            "fifth_alt_alt":        True,
            "family_rank":          "G4 WF 12/12 UNPRECEDENTED — all 12 walk-forward folds positive (prior best: K679/K686 at 11/12). OOS Sh: K686=50.27 > K682=43.43 > K679=39.29 > K690=25.11 > K684=9.65.",
            "midcap_altalt":        "SEI/SOL vol ratio=1.32x. Mid-cap alt-alt exception applied. ADF stat -12.7158, p=1.01e-23. OU half-life=4.41h STRONG.",
            "carry_dominant":       "SEI mean FR -3.65%/ann NEGATIVE. Dominant BEAR_SEI (~90%+): LONG SOL/SHORT SEI carry-positive in BOTH legs.",
            "anti_corr_k507":       "corr(K690, K507) = -0.5109 — K690 HEDGES K507 long-SEI exposure",
            "k507_k476_overlap":    "Standalone (SEI-SOL = K507_dir - K476_dir algebraic identity — K690 STANDALONE 3%)",
            "sol_triple_exposure":  "K690+K682+K686 share SOL leg — monitor combined SOL notional (up to $1.8M @$10M)",
            "paper_gate":           "60d: Sh>=12 (50% of OOS 25.11) + fill>=60% + maxDD<15%",
            "activation_status":    "SCAFFOLD-READY",
            "plist":                "scripts/com.cryptolab.k690-sei-sol.plist",
            "log_files":            ["logs/k690_sei_sol.log", "logs/k690_sei_sol.err"],
            "g4_unprecedented":     "12/12 folds positive — UNPRECEDENTED in alt-alt family. K693 key differentiator vs prior accepts.",
        },
        "deliverable_files": [
            "scripts/k690_sei_sol_run.py",
            "scripts/com.cryptolab.k690-sei-sol.plist",
            "data/k690_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k690 added)",
            "scripts/leverage_manager.py   (K690_SEI_SOL cap + SLEEVE_WEIGHTS_V645)",
            "data/leverage_config.json     (K690_SEI_SOL: 4.0 + k690_notes)",
            "scripts/verify_deployment_status.py  (58th daemon)",
            "docs/k302a_runbook.md         (§60 added)",
            "report.html                   (K690 SCAFFOLD-READY row added)",
            "wave_k693_k690_scaffold.py    (this file)",
            "wave_k693_k690_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k693_k690_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K693 Wave Driver — K690 SEI-SOL Production Scaffold ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K693 deliverables...")
    print()

    report = generate_report()

    print(f"  Overall status:   {report['overall_status']}")
    print(f"  Deliverables:     {report['deliverables']['passed']}/{report['deliverables']['total']} PASS")
    print(f"  Content checks:   {report['content_integrity']['pass']} PASS / {report['content_integrity']['fail']} FAIL")
    print(f"  Dry-run:          {report['dry_run'].get('status', 'N/A')}")
    print()

    if report["deliverables"]["failed"] > 0:
        print("  FAILED deliverables:")
        for c in report["deliverables"]["checks"]:
            if c["status"] == "FAIL":
                print(f"    FAIL: {c['path']} — {c['description']}")

    if report["content_integrity"]["fail"] > 0:
        print("  FAILED content checks:")
        for k, v in report["content_integrity"]["checks"].items():
            if v is False:
                print(f"    FAIL: {k}")

    print(f"\n  Scaffold summary:")
    s = report["scaffold_summary"]
    print(f"    Daemon:         {s['daemon_number']} daemon")
    print(f"    Strategy:       {s['strategy']}")
    print(f"    Signal:         {s['signal']}")
    print(f"    Threshold:      {s['threshold']}")
    print(f"    Sleeve:         {s['sleeve_pct']:.1%}  Leverage: {s['leverage']}x")
    print(f"    Venue:          {s['venue']}")
    print(f"    HL conc:        {s['hl_concentration_pct']:.1f}% ({s['hl_cap_note']})")
    print(f"    OOS Sharpe:     {s['oos_sharpe']}  ({s['oos_period']})")
    print(f"    Profit:         ${s['profit_net_yr_10m']:,}/yr net @$10M @4x (3% standalone)")
    print(f"    Family rank:    {s['family_rank']}")
    print(f"    Mid-cap:        {s['midcap_altalt']}")
    print(f"    Carry:          {s['carry_dominant']}")
    print(f"    Anti-corr K507: {s['anti_corr_k507']}")
    print(f"    K507+K476:      {s['k507_k476_overlap']}")
    print(f"    SOL triple:     {s['sol_triple_exposure']}")
    print(f"    G4 12/12:       {s['g4_unprecedented']}")
    print(f"    60d gate:       {s['paper_gate']}")
    print(f"    Status:         {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k693_k690_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

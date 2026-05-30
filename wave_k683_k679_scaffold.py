#!/usr/bin/env python3
"""
wave_k683_k679_scaffold.py — K683 Wave Driver + Verification
=============================================================
Verifies all K683 deliverables for the K679 APT-SOL production scaffold:
  - Phase 1:  Strategy script (k679_apt_sol_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k679-apt-sol.plist, 55th daemon)
  - Phase 3:  Dashboard (k679_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k679 flag)
  - Phase 5:  Leverage manager (K679_APT_SOL cap + SLEEVE_WEIGHTS_V645)
  - Phase 6:  Leverage config (k679_notes + K679_APT_SOL)
  - Phase 7:  Deployment verification (55th daemon)
  - Phase 8:  Runbook §56 (K679 APT-SOL playbook)
  - Phase 9:  HTML update (K679 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=20, K683 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K679 pattern (K683 scaffold):
  - Signal: diff = APT_FR - SOL_FR (direct alt-alt, no base asset)
  - W=168h rolling mean, zero threshold (sign only)
  - FIRST ALT-ALT pair (no BTC/ETH leg)
  - Both APT-PERP and SOL-PERP on Bybit (HL at 65.5% OVER cap)
  - OOS Sharpe 39.29 (FIRST ALT-ALT record)
  - $234,700/yr net @$10M @4x (3% standalone sleeve)
  - K512+K476 algebraic overlap: run K679 STANDALONE

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

WAVE     = "K683"
STRATEGY = "K679 APT-SOL FR Differential (FIRST ALT-ALT pair, Bybit-only, Move-VM vs SVM)"


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
    """Verify all K683 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k679_apt_sol_run.py",
            "Phase 1: K679 strategy script (K339 pattern, W=168h, alt-alt direct diff, Bybit-only)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k679-apt-sol.plist",
            "Phase 2: 55th daemon plist (StartInterval 28800, Bybit-only)"
        ),
        _check_file(
            DATA_DIR / "k679_dashboard.json",
            "Phase 3: Dashboard (alt-alt diff signal, regime, alt_alt_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k679 flag, §56)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K679_APT_SOL cap + SLEEVE_WEIGHTS_V645)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K679_APT_SOL: 4.0 + k679_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (55th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §56 (K679 APT-SOL playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K679 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k683_k679_scaffold.py",
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

    # Check k679_apt_sol_run.py
    script_path = REPO_ROOT / "scripts" / "k679_apt_sol_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["k339_repo_root"]        = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]   = "PAPER_TRADE         = True" in content
        results["sleeve_3pct"]           = "SLEEVE_PCT          = 0.030" in content
        results["leverage_4x"]           = "LEVERAGE            = 4.0" in content
        results["rolling_168h"]          = "EMA_PERIOD_HOURS    = 168" in content
        results["zero_threshold"]        = "SIGNAL_SIGMA_MULT   = 0.0" in content
        results["bybit_only"]            = "BYBIT_ONLY" in content
        results["post_only"]             = "POST_ONLY_PARALLEL" in content
        results["first_alt_alt"]         = "FIRST ALT-ALT" in content
        results["apt_sol_diff"]          = "apt_sol_diff" in content
        results["symbols_apt_sol_only"]  = 'SYMBOLS = ("APT", "SOL")' in content
        results["dashboard_path"]        = "k679_dashboard.json" in content
        results["oos_sh_39_29"]          = "39.29" in content
        results["k512_k476_warning"]     = "K512+K476" in content
        results["hl_65_5_over_cap"]      = "65.5" in content
        results["profit_234k"]           = "234,700" in content
        results["55th_daemon"]           = "55th" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k679_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_alt_mech"]    = "alt_alt_mechanism" in dash
            results["dashboard_hl_655"]      = dash.get("hl_concentration_pct") == 65.5
            results["dashboard_gate_sh20"]   = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 20.0
            results["dashboard_sleeve_030"]  = dash.get("sleeve_pct") == 0.030
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k679_cap"]    = cfg.get("exchange_caps", {}).get("K679_APT_SOL") == 4.0
            results["cfg_k679_notes"]  = "k679_notes" in cfg
            results["cfg_sleeve_030"]  = cfg.get("k679_notes", {}).get("sleeve_pct") == 0.03
            results["cfg_bybit_only"]  = cfg.get("k679_notes", {}).get("bybit_only") is True
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k679"]   = "--include-k679" in content
        results["emer_k679_bybit_note"] = "K679 APT-SOL: Bybit-only" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k679_cap"]        = "K679_APT_SOL" in content
        results["lev_v645_weights"]    = "SLEEVE_WEIGHTS_V645" in content
        results["lev_k679_030pct"]     = '"K679":    0.03,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k679_label"]      = "com.cryptolab.k679-apt-sol" in content
        results["vds_55th_daemon"]     = "55th daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section56"]   = "## §56 K679 APT-SOL FR Differential" in content
        results["runbook_first_altalt"] = "FIRST ALT-ALT" in content
        results["runbook_k512_overlap"] = "K512+K476" in content
        results["runbook_profit_234k"] = "234,700" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k683_scaffold"]  = "K683" in content or "K679 APT-SOL" in content
        results["html_55th_daemon"]    = "55th daemon" in content

    return results


def run_dry_run_check() -> dict:
    """Run k679_apt_sol_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k679_apt_sol_run.py"
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
    """Generate full K683 scaffold verification report."""
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
            "daemon_number":        "55th",
            "strategy":             "K679 APT-SOL FR Differential (FIRST ALT-ALT pair)",
            "signal":               "sign(rolling_mean_168h(APT_FR - SOL_FR))",
            "threshold":            "zero (sign only)",
            "ema_window_h":         168,
            "leverage":             4.0,
            "sleeve_pct":           0.030,
            "venue":                "Bybit-only (APT-PERP + SOL-PERP, both Bybit)",
            "hl_concentration_pct": 65.5,
            "hl_cap_note":          "65.5% OVER 65% cap — Bybit-only mandatory",
            "oos_sharpe":           39.29,
            "profit_net_yr_10m":    234700,
            "first_alt_alt":        True,
            "k512_k476_overlap":    "Standalone (no netting with K512 APT-BTC / K476 SOL-BTC)",
            "paper_gate":           "60d: Sh>=20 + fill>=60% + maxDD<15%",
            "activation_status":    "SCAFFOLD-READY",
            "plist":                "scripts/com.cryptolab.k679-apt-sol.plist",
            "log_files":            ["logs/k679_apt_sol.log", "logs/k679_apt_sol.err"],
        },
        "deliverable_files": [
            "scripts/k679_apt_sol_run.py",
            "scripts/com.cryptolab.k679-apt-sol.plist",
            "data/k679_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k679 added)",
            "scripts/leverage_manager.py   (K679_APT_SOL cap + SLEEVE_WEIGHTS_V645)",
            "data/leverage_config.json     (K679_APT_SOL: 4.0 + k679_notes)",
            "scripts/verify_deployment_status.py  (55th daemon)",
            "docs/k302a_runbook.md         (§56 added)",
            "report.html                   (K679 row added)",
            "wave_k683_k679_scaffold.py    (this file)",
            "wave_k683_k679_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k683_k679_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K683 Wave Driver — K679 APT-SOL Production Scaffold ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K683 deliverables...")
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
    print(f"    HL conc:        {s['hl_concentration_pct']:.1f}% OVER cap ({s['hl_cap_note']})")
    print(f"    OOS Sharpe:     {s['oos_sharpe']}  (FIRST ALT-ALT record)")
    print(f"    Profit:         ${s['profit_net_yr_10m']:,}/yr net @$10M @4x (3% standalone)")
    print(f"    K512+K476:      {s['k512_k476_overlap']}")
    print(f"    60d gate:       {s['paper_gate']}")
    print(f"    Status:         {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k683_k679_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

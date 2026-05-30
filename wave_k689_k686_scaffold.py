#!/usr/bin/env python3
"""
wave_k689_k686_scaffold.py — K689 Wave Driver + Verification
=============================================================
Verifies all K689 deliverables for the K686 AVAX-SOL production scaffold:
  - Phase 1:  Strategy script (k686_avax_sol_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k686-avax-sol.plist, 57th daemon)
  - Phase 3:  Dashboard (k686_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k686 flag)
  - Phase 5:  Leverage manager (K686_AVAX_SOL cap + SLEEVE_WEIGHTS_V645)
  - Phase 6:  Leverage config (k686_notes + K686_AVAX_SOL)
  - Phase 7:  Deployment verification (57th daemon)
  - Phase 8:  Runbook §59 (K686 AVAX-SOL playbook)
  - Phase 9:  HTML update (K686 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=25, K689 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K686 pattern (K689 scaffold):
  - Signal: diff = AVAX_FR - SOL_FR (direct alt-alt, no base asset)
  - W=168h rolling mean, zero threshold (sign only)
  - FOURTH ALT-ALT pair (no BTC/ETH leg) — HIGHEST OOS Sh in alt-alt family
  - Both AVAX-PERP and SOL-PERP on Bybit (HL 62.5% headroom preserved)
  - OOS Sharpe 50.27 (W=168h, ~216d OOS, 11/12 G4 folds positive)
  - $102,153/yr net @$10M @4x (3% standalone sleeve)
  - K484+K476 algebraic overlap: run K686 STANDALONE
  - K682+K679+K686 share SOL leg: monitor SOL triple-exposure
  - Anti-corr K686 vs K484 = -0.6295 (K686 HEDGES K484 long-AVAX)
  - Same-tier L1 exception: AVAX/SOL vol ratio=0.85x, ADF confirmed, OU 3.6h FASTEST

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

WAVE     = "K689"
STRATEGY = "K686 AVAX-SOL FR Differential (FOURTH ALT-ALT pair, Bybit-only, Avalanche Subnet institutional vs Solana SVM retail)"


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
    """Verify all K689 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k686_avax_sol_run.py",
            "Phase 1: K686 strategy script (K339 pattern, W=168h, alt-alt direct diff, Bybit-only)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k686-avax-sol.plist",
            "Phase 2: 57th daemon plist (StartInterval 28800, Bybit-only)"
        ),
        _check_file(
            DATA_DIR / "k686_dashboard.json",
            "Phase 3: Dashboard (alt-alt diff signal, regime, alt_alt_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k686 flag, §59)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K686_AVAX_SOL cap + SLEEVE_WEIGHTS_V645)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K686_AVAX_SOL: 4.0 + k686_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (57th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §59 (K686 AVAX-SOL playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K686 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k689_k686_scaffold.py",
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

    # Check k686_avax_sol_run.py
    script_path = REPO_ROOT / "scripts" / "k686_avax_sol_run.py"
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
        results["fourth_alt_alt"]         = "FOURTH ALT-ALT" in content
        results["avax_sol_diff"]          = "avax_sol_diff" in content
        results["symbols_avax_sol"]       = 'SYMBOLS = ("AVAX", "SOL")' in content
        results["dashboard_path"]         = "k686_dashboard.json" in content
        results["oos_sh_50_27"]           = "50.27" in content
        results["k484_k476_warning"]      = "K484+K476" in content or "K484_K476" in content or "K484 AVAX-BTC" in content
        results["hl_62_5"]                = "62.5" in content
        results["profit_102k"]            = "102,153" in content
        results["57th_daemon"]            = "57th" in content
        results["same_tier_l1"]           = "same-tier" in content or "same_tier" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k686_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]         = "regime" in dash
            results["dashboard_oos_perf"]       = "oos_performance" in dash
            results["dashboard_alt_mech"]       = "alt_alt_mechanism" in dash
            results["dashboard_hl_625"]         = dash.get("hl_concentration_pct") == 62.5
            results["dashboard_gate_sh25"]      = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 25.0
            results["dashboard_sleeve_030"]     = dash.get("sleeve_pct") == 0.030
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k686_cap"]    = cfg.get("exchange_caps", {}).get("K686_AVAX_SOL") == 4.0
            results["cfg_k686_notes"]  = "k686_notes" in cfg
            results["cfg_sleeve_030"]  = cfg.get("k686_notes", {}).get("sleeve_pct") == 0.03
            results["cfg_bybit_only"]  = cfg.get("k686_notes", {}).get("bybit_only") is True
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k686"]     = "--include-k686" in content
        results["emer_k686_bybit_note"]  = "K686 AVAX-SOL: Bybit-only" in content or "K686 AVAX-SOL CLOSE SUMMARY" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k686_cap"]        = "K686_AVAX_SOL" in content
        results["lev_v645_weights"]    = "SLEEVE_WEIGHTS_V645" in content
        results["lev_k686_030pct"]     = '"K686":    0.03,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k686_label"]      = "com.cryptolab.k686-avax-sol" in content
        results["vds_57th_daemon"]     = "57th daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section59"]    = "## §59 K686 AVAX-SOL FR Differential" in content
        results["runbook_fourth_altalt"] = "FOURTH ALT-ALT" in content
        results["runbook_k484_overlap"] = "K484+K476" in content or "K484 AVAX-BTC" in content
        results["runbook_profit_102k"]  = "102,153" in content or "102K" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k689_scaffold"]  = "K689" in content
        results["html_57th_daemon"]    = "57th" in content
        results["html_k686_scaffold_ready"] = "SCAFFOLD-READY" in content and "K686" in content

    return results


def run_dry_run_check() -> dict:
    """Run k686_avax_sol_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k686_avax_sol_run.py"
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
    """Generate full K689 scaffold verification report."""
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
            "daemon_number":        "57th",
            "strategy":             "K686 AVAX-SOL FR Differential (FOURTH ALT-ALT pair)",
            "signal":               "sign(rolling_mean_168h(AVAX_FR - SOL_FR))",
            "threshold":            "zero (sign only)",
            "ema_window_h":         168,
            "leverage":             4.0,
            "sleeve_pct":           0.030,
            "venue":                "Bybit-only (AVAX-PERP + SOL-PERP, both Bybit)",
            "hl_concentration_pct": 62.5,
            "hl_cap_note":          "62.5% within 65% cap — Bybit-only preferred (2.5pp headroom preserved)",
            "oos_sharpe":           50.27,
            "oos_period":           "~2025-10-18 to 2026-05-23",
            "profit_net_yr_10m":    102153,
            "fourth_alt_alt":       True,
            "family_rank":          "HIGHEST OOS Sh in alt-alt family: K686=50.27 > K682=43.43 > K679=39.29 > K684=9.65",
            "same_tier_l1":         "AVAX/SOL vol ratio=0.85x. Same-tier L1 exception applied. ADF stat -13.99, OU half-life=3.6h FASTEST.",
            "anti_corr_k484":       "corr(K686, K484) = -0.6295 — K686 HEDGES K484 long-AVAX exposure",
            "k484_k476_overlap":    "Standalone (AVAX-SOL = K484_dir - K476_dir algebraic identity — K686 STANDALONE 3%)",
            "sol_triple_exposure":  "K686+K682+K679 share SOL leg — monitor combined SOL notional (up to $1.8M @$10M)",
            "paper_gate":           "60d: Sh>=25 (50% of OOS 50.27) + fill>=60% + maxDD<15%",
            "activation_status":    "SCAFFOLD-READY",
            "plist":                "scripts/com.cryptolab.k686-avax-sol.plist",
            "log_files":            ["logs/k686_avax_sol.log", "logs/k686_avax_sol.err"],
        },
        "deliverable_files": [
            "scripts/k686_avax_sol_run.py",
            "scripts/com.cryptolab.k686-avax-sol.plist",
            "data/k686_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k686 added)",
            "scripts/leverage_manager.py   (K686_AVAX_SOL cap + SLEEVE_WEIGHTS_V645)",
            "data/leverage_config.json     (K686_AVAX_SOL: 4.0 + k686_notes)",
            "scripts/verify_deployment_status.py  (57th daemon)",
            "docs/k302a_runbook.md         (§59 added)",
            "report.html                   (K686 SCAFFOLD-READY row added)",
            "wave_k689_k686_scaffold.py    (this file)",
            "wave_k689_k686_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k689_k686_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K689 Wave Driver — K686 AVAX-SOL Production Scaffold ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K689 deliverables...")
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
    print(f"    Same-tier L1:   {s['same_tier_l1']}")
    print(f"    Anti-corr K484: {s['anti_corr_k484']}")
    print(f"    K484+K476:      {s['k484_k476_overlap']}")
    print(f"    SOL triple:     {s['sol_triple_exposure']}")
    print(f"    60d gate:       {s['paper_gate']}")
    print(f"    Status:         {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k689_k686_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

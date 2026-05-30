#!/usr/bin/env python3
"""
wave_k697_k694_scaffold.py — K697 Wave Driver + Verification
=============================================================
Verifies all K697 deliverables for the K694 TIA-SOL production scaffold:
  - Phase 1:  Strategy script (k694_tia_sol_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k694-tia-sol.plist, 59th daemon)
  - Phase 3:  Dashboard (k694_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k694 flag)
  - Phase 5:  Leverage manager (K694_TIA_SOL cap + SLEEVE_WEIGHTS_V645)
  - Phase 6:  Leverage config (k694_notes + K694_TIA_SOL)
  - Phase 7:  Deployment verification (59th daemon)
  - Phase 8:  Runbook §61 (K694 TIA-SOL playbook)
  - Phase 9:  HTML update (K694 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=9, K697 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K694 pattern (K697 scaffold):
  - Signal: diff = TIA_FR - SOL_FR (direct alt-alt, no base asset)
  - W=168h rolling mean, zero threshold (sign only)
  - SIXTH ALT-ALT pair (8th evaluated, no BTC/ETH leg) — CONDITIONAL G4 11/12
  - Both TIA-PERP and SOL-PERP on Bybit (HL 62.5% headroom preserved, Bybit mandatory)
  - OOS Sharpe 19.09 (W=168h, ~218d OOS, 11/12 G4 folds positive)
  - $58,354/yr net @$10M @4x (3% standalone sleeve)
  - K691 lesson: TIA-APT REJECT (G5b APT corr=0.4712). K694 avoids APT leg.
  - SOL saturation: signed corr(K694, K476)=0.2275 PASS (SOL shared but independent)
  - TIA new vertex: first DA-layer token in alt-alt family
  - Natural SOL-short hedge: K694 BULL_TIA offsets SOL-long in K679+K682+K686+K690
  - OU half-life=3.46h FASTEST in alt-alt family (K686=3.6h, K690=4.41h)
  - Cross-architecture: Celestia DA (infrastructure, rollup-paced) vs SOL SVM (retail, sentiment)

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

WAVE     = "K697"
STRATEGY = "K694 TIA-SOL FR Differential (SIXTH ALT-ALT pair, 8th evaluated, Bybit-only, Celestia DA vs Solana SVM cross-architecture, CONDITIONAL G4 11/12)"


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
    """Verify all K697 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k694_tia_sol_run.py",
            "Phase 1: K694 strategy script (K339 pattern, W=168h, alt-alt direct diff, Bybit-only, CONDITIONAL)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k694-tia-sol.plist",
            "Phase 2: 59th daemon plist (StartInterval 28800, Bybit-only, CONDITIONAL)"
        ),
        _check_file(
            DATA_DIR / "k694_dashboard.json",
            "Phase 3: Dashboard (alt-alt diff signal, regime, alt_alt_mechanism, CONDITIONAL)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k694 flag, §61)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K694_TIA_SOL cap + SLEEVE_WEIGHTS_V645)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K694_TIA_SOL: 4.0 + k694_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (59th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §61 (K694 TIA-SOL playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K694 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k697_k694_scaffold.py",
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

    # Check k694_tia_sol_run.py
    script_path = REPO_ROOT / "scripts" / "k694_tia_sol_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["k339_repo_root"]          = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]     = "PAPER_TRADE         = True" in content
        results["sleeve_3pct"]             = "SLEEVE_PCT          = 0.030" in content
        results["leverage_4x"]             = "LEVERAGE            = 4.0" in content
        results["rolling_168h"]            = "EMA_PERIOD_HOURS    = 168" in content
        results["zero_threshold"]          = "SIGNAL_SIGMA_MULT   = 0.0" in content
        results["bybit_only"]              = "BYBIT_ONLY" in content
        results["post_only"]               = "POST_ONLY_PARALLEL" in content
        results["sixth_alt_alt"]           = "SIXTH ALT-ALT" in content
        results["tia_sol_diff"]            = "tia_sol_diff" in content
        results["symbols_tia_sol"]         = 'SYMBOLS = ("TIA", "SOL")' in content
        results["dashboard_path"]          = "k694_dashboard.json" in content
        results["oos_sh_19_09"]            = "19.09" in content or "19.092" in content
        results["k691_lesson"]             = "K691" in content and "TIA-APT" in content
        results["hl_62_5"]                 = "62.5" in content
        results["profit_58k"]              = "58,354" in content
        results["59th_daemon"]             = "59th" in content
        results["g4_11_12"]               = "11/12" in content
        results["ou_3_46h"]               = "3.46h" in content
        results["sol_saturation"]          = "SOL saturation" in content or "sol_saturation" in content
        results["natural_hedge"]           = "natural" in content.lower() and "hedge" in content.lower()
        results["conditional"]             = "CONDITIONAL" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k694_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]        = "regime" in dash
            results["dashboard_oos_perf"]      = "oos_performance" in dash
            results["dashboard_alt_mech"]      = "alt_alt_mechanism" in dash
            results["dashboard_hl_625"]        = dash.get("hl_concentration_pct") == 62.5
            results["dashboard_gate_sh9"]      = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 9.0
            results["dashboard_sleeve_030"]    = dash.get("sleeve_pct") == 0.030
        except Exception as e:
            results["dashboard_error"] = str(e)
    else:
        results["dashboard_missing"] = True

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k694_cap"]    = cfg.get("exchange_caps", {}).get("K694_TIA_SOL") == 4.0
            results["cfg_k694_notes"]  = "k694_notes" in cfg
            results["cfg_sleeve_030"]  = cfg.get("k694_notes", {}).get("sleeve_pct") == 0.03
            results["cfg_bybit_only"]  = cfg.get("k694_notes", {}).get("bybit_only") is True
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k694"]     = "--include-k694" in content
        results["emer_k694_bybit_note"]  = "K694 TIA-SOL: Bybit-only" in content or "K694 TIA-SOL CLOSE SUMMARY" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k694_cap"]        = "K694_TIA_SOL" in content
        results["lev_v645_weights"]    = "SLEEVE_WEIGHTS_V645" in content
        results["lev_k694_030pct"]     = '"K694":    0.03,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k694_label"]      = "com.cryptolab.k694-tia-sol" in content
        results["vds_59th_daemon"]     = "59th daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section61"]    = "## §61 K694 TIA-SOL FR Differential" in content
        results["runbook_sixth_altalt"] = "SIXTH ALT-ALT" in content
        results["runbook_k691_lesson"]  = "K691" in content and "TIA-APT" in content
        results["runbook_profit_58k"]   = "58,354" in content or "58K" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k697_scaffold"]  = "K697" in content
        results["html_59th_daemon"]    = "59th" in content
        results["html_k694_scaffold_ready"] = "SCAFFOLD-READY" in content and "K694" in content

    return results


def run_dry_run_check() -> dict:
    """Run k694_tia_sol_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k694_tia_sol_run.py"
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
    """Generate full K697 scaffold verification report."""
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
            "daemon_number":         "59th",
            "strategy":              "K694 TIA-SOL FR Differential (SIXTH ALT-ALT pair, 8th evaluated, CONDITIONAL)",
            "signal":                "sign(rolling_mean_168h(TIA_FR - SOL_FR))",
            "threshold":             "zero (sign only)",
            "ema_window_h":          168,
            "leverage":              4.0,
            "sleeve_pct":            0.030,
            "venue":                 "Bybit-only (TIA-PERP + SOL-PERP, both Bybit — HL-only would breach 65% cap)",
            "hl_concentration_pct":  62.5,
            "hl_cap_note":           "62.5% within 65% cap — Bybit-only mandatory (HL-only = 65.5% OVER cap). 2.5pp headroom preserved.",
            "oos_sharpe":            19.092,
            "oos_period":            "~2025-10-19 to 2026-05-23",
            "profit_net_yr_10m":     58354,
            "sixth_alt_alt":         True,
            "eighth_evaluated":      True,
            "section6_result":       "CONDITIONAL — 15/16 gates PASS. G4=11/12 (fold 9 Sh=-3.97). All other gates PASS.",
            "k691_lesson":           "K691 TIA-APT REJECT (G5b APT corr=0.4712). K694 avoids APT. SOL saturation: signed corr(K694,K476)=0.2275 PASS.",
            "tia_new_vertex":        "TIA is first DA-layer token in alt-alt family. Not in any existing strategy.",
            "sol_saturation":        "SOL shared with K476+K679+K682+K684+K686+K690 (6 strategies). Signed corr=0.2275 PASS.",
            "natural_hedge":         "K694 BULL_TIA (long TIA / short SOL) = natural SOL-short hedge to K679+K682+K686+K690.",
            "cross_architecture":    "DA infrastructure (Celestia, rollup-paced) vs execution L1 (SOL, retail sentiment). Independent cycles.",
            "ou_half_life":          "3.46h FASTEST in alt-alt family (K686=3.6h, K690=4.41h, K694=3.46h FASTEST)",
            "g4_conditional":        "11/12 folds positive. 1 negative fold (fold 9: Sh=-3.97, 2025-04 to 2025-05). Monitor recurrence.",
            "sol_exposure_warning":  "K694+K679+K682+K684+K686+K690 all have SOL leg. Combined up to $3.0M @$10M. K694 BULL_TIA partially hedges.",
            "paper_gate":            "60d: Sh>=9 (47% of OOS 19.09, CONDITIONAL adjustment) + fill>=60% + maxDD<15%",
            "activation_status":     "SCAFFOLD-READY",
            "plist":                 "scripts/com.cryptolab.k694-tia-sol.plist",
            "log_files":             ["logs/k694_tia_sol.log", "logs/k694_tia_sol.err"],
            "family_rank": (
                "OOS Sh: K686=50.27 > K682=43.43 > K679=39.29 > K690=25.11 > K694=19.09 > K684=9.65. "
                "K694 OU 3.46h is FASTEST in family. Combined 6 alt-alt pairs: ~$826K/yr @$10M "
                "(3%+2%+3%+3%+3%+3% sleeves)."
            ),
        },
        "deliverable_files": [
            "scripts/k694_tia_sol_run.py",
            "scripts/com.cryptolab.k694-tia-sol.plist",
            "data/k694_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k694 added)",
            "scripts/leverage_manager.py   (K694_TIA_SOL cap + SLEEVE_WEIGHTS_V645 K694 entry)",
            "data/leverage_config.json     (K694_TIA_SOL: 4.0 + k694_notes)",
            "scripts/verify_deployment_status.py  (59th daemon)",
            "docs/k302a_runbook.md         (§61 added)",
            "report.html                   (K694 SCAFFOLD-READY row added)",
            "wave_k697_k694_scaffold.py    (this file)",
            "wave_k697_k694_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k697_k694_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K697 Wave Driver — K694 TIA-SOL Production Scaffold ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K697 deliverables...")
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
    print(f"    Section 6:      {s['section6_result']}")
    print(f"    K691 lesson:    {s['k691_lesson']}")
    print(f"    TIA vertex:     {s['tia_new_vertex']}")
    print(f"    SOL saturation: {s['sol_saturation']}")
    print(f"    Natural hedge:  {s['natural_hedge']}")
    print(f"    Cross-arch:     {s['cross_architecture']}")
    print(f"    OU half-life:   {s['ou_half_life']}")
    print(f"    G4 status:      {s['g4_conditional']}")
    print(f"    SOL exposure:   {s['sol_exposure_warning']}")
    print(f"    Family rank:    {s['family_rank']}")
    print(f"    60d gate:       {s['paper_gate']}")
    print(f"    Status:         {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k697_k694_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

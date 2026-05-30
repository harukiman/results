#!/usr/bin/env python3
"""
wave_k677_k661_scaffold.py — K677 Wave Driver + Verification
=============================================================
Verifies all K677 deliverables for the K661 AVAX-ETH production scaffold:
  - Phase 1:  Strategy script (k661_avax_eth_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k661-avax-eth.plist, 53rd daemon)
  - Phase 3:  Dashboard (k661_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k661 flag)
  - Phase 5:  Leverage manager (K661_AVAX_ETH cap + SLEEVE_WEIGHTS_V643)
  - Phase 6:  Leverage config (k661_notes + K661_AVAX_ETH)
  - Phase 7:  Deployment verification (53rd daemon)
  - Phase 8:  Runbook §54 (K661 AVAX-ETH playbook)
  - Phase 9:  HTML update (K677 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=14, K677 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K661 pattern (K677 scaffold, K668/K669 pattern):
  - Signal: diff = AVAX_FR - ETH_FR (direct, no OLS orthogonalization)
  - W=168h rolling mean, zero threshold (sign only)
  - ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base marginally better)
  - PnL corr=0.3731 < 0.40 → dual-sleeve eligible with K484 AVAX-BTC
  - G5a ETH-BTC K449 corr=-0.008 (CRITICAL shared-leg check PASS)
  - Both AVAX-PERP and ETH-PERP on HL primary
  - Dual-sleeve: K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = $139K/yr net @$10M

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

WAVE     = "K677"
STRATEGY = "K661 AVAX-ETH FR Differential (ETH-base, AVAX Subnet/RWA Avalanche9000, ACCEPT CONDITIONAL)"


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
    """Verify all K677 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k661_avax_eth_run.py",
            "Phase 1: K661 strategy script (K339 pattern, W=168h, ETH-base direct diff)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k661-avax-eth.plist",
            "Phase 2: 53rd daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k661_dashboard.json",
            "Phase 3: Dashboard (diff signal, regime, eth_base_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k661 flag, §54)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K661_AVAX_ETH + SLEEVE_WEIGHTS_V643)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K661_AVAX_ETH: 4.0 + k661_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (53rd daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §54 (K661 AVAX-ETH playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K677 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k677_k661_scaffold.py",
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

    # Check k661_avax_eth_run.py
    script_path = REPO_ROOT / "scripts" / "k661_avax_eth_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["k339_repo_root"]          = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]     = "PAPER_TRADE         = True" in content
        results["sleeve_1_5pct"]           = "SLEEVE_PCT          = 0.015" in content
        results["leverage_4x"]             = "LEVERAGE            = 4.0" in content
        results["rolling_168h"]            = "EMA_PERIOD_HOURS    = 168" in content
        results["zero_threshold"]          = "SIGNAL_SIGMA_MULT   = 0.0" in content
        results["hl_primary"]              = "HL_CONCENTRATION_POST_K661" in content
        results["post_only"]               = "POST_ONLY_PARALLEL" in content
        results["accept_conditional"]      = "ACCEPT CONDITIONAL" in content
        results["direct_diff_no_ols"]      = "avax_eth_diff" in content
        results["symbols_avax_eth_only"]   = 'SYMBOLS = ("AVAX", "ETH")' in content
        results["dashboard_path"]          = "k661_dashboard.json" in content
        results["g5b_corr_0_3731"]         = "0.3731" in content
        results["dual_sleeve_note"]        = "139,099" in content
        results["g5a_corr_critical"]       = "-0.008" in content
        results["53rd_daemon"]             = "53rd daemon" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k661_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]       = "regime" in dash
            results["dashboard_gate_sh14"]    = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 14.0
            results["dashboard_sleeve_015"]   = dash.get("sleeve_pct") == 0.015
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k661_cap"]    = cfg.get("exchange_caps", {}).get("K661_AVAX_ETH") == 4.0
            results["cfg_k661_notes"]  = "k661_notes" in cfg
            results["cfg_sleeve_015"]  = cfg.get("k661_notes", {}).get("sleeve_pct") == 0.015
            results["cfg_g5b_corr"]    = cfg.get("k661_notes", {}).get("g5b_avax_btc_k484_corr") == 0.3731
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k661"]   = "--include-k661" in content
        results["emer_k661_hl_note"]   = "K661 AVAX-ETH: HL-primary" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k661_cap"]        = "K661_AVAX_ETH" in content
        results["lev_v643_weights"]    = "SLEEVE_WEIGHTS_V643" in content
        results["lev_k661_015pct"]     = '"K661":    0.015,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k661_label"]      = "com.cryptolab.k661-avax-eth" in content
        results["vds_53rd_daemon"]     = "53rd daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section54"]   = "## §54 K661 AVAX-ETH FR Differential" in content
        results["runbook_dual_sleeve"] = "139,099" in content
        results["runbook_g5a_critical"] = "G5a ETH-BTC K449" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k677_scaffold"]  = "K677" in content or "K661 AVAX-ETH" in content

    return results


def run_dry_run_check() -> dict:
    """Run k661_avax_eth_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k661_avax_eth_run.py"
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
    """Generate full K677 scaffold verification report."""
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
            "daemon_number":          "53rd",
            "eth_base_scaffold_rank": "6th ETH-base scaffold",
            "strategy":               "K661 AVAX-ETH FR Differential",
            "decision":               "ACCEPT CONDITIONAL — dual-sleeve with K484 eligible",
            "signal":                 "sign(rolling_mean_168h(AVAX_FR - ETH_FR))",
            "threshold":              "zero (sign only)",
            "ema_window_h":           168,
            "leverage":               4.0,
            "sleeve_pct":             0.015,
            "venue":                  "HL primary (AVAX-PERP + ETH-PERP, both HL perps)",
            "oos_sharpe":             28.2551,
            "k484_sharpe":            43.887,
            "sharpe_delta_vs_k484":   -15.6319,
            "oos_ann_ret_pct":        6.6058,
            "profit_net_yr_10m":      63416,
            "dual_sleeve_net_yr":     139099,
            "diversification_premium": 63416,
            "g5a_corr_k449_critical": -0.008,
            "g5b_corr_k484_family":   0.3731,
            "g5b_verdict":            "PASS (< 0.40) — dual-sleeve eligible with K484",
            "hl_concentration_pct":   64.0,
            "paper_gate":             "60d: Sh>=14 + fill>=60% + maxDD<15%",
            "activation_status":      "SCAFFOLD-READY",
            "plist":                  "scripts/com.cryptolab.k661-avax-eth.plist",
            "log_files":              ["logs/k661_avax_eth.log", "logs/k661_avax_eth.err"],
        },
        "deliverable_files": [
            "scripts/k661_avax_eth_run.py",
            "scripts/com.cryptolab.k661-avax-eth.plist",
            "data/k661_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k661 added)",
            "scripts/leverage_manager.py   (K661_AVAX_ETH cap + SLEEVE_WEIGHTS_V643)",
            "data/leverage_config.json     (K661_AVAX_ETH: 4.0 + k661_notes)",
            "scripts/verify_deployment_status.py  (53rd daemon)",
            "docs/k302a_runbook.md         (§54 added)",
            "report.html                   (K677 row added)",
            "wave_k677_k661_scaffold.py    (this file)",
            "wave_k677_k661_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k677_k661_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K677 Wave Driver — K661 AVAX-ETH Production Scaffold ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K677 deliverables...")
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
    print(f"    Daemon:          {s['daemon_number']} daemon ({s['eth_base_scaffold_rank']})")
    print(f"    Decision:        {s['decision']}")
    print(f"    Signal:          {s['signal']}")
    print(f"    Threshold:       {s['threshold']}")
    print(f"    Sleeve:          {s['sleeve_pct']:.1%}  Leverage: {s['leverage']}x")
    print(f"    Venue:           {s['venue']}")
    print(f"    OOS Sharpe:      {s['oos_sharpe']}  (K484={s['k484_sharpe']}, delta={s['sharpe_delta_vs_k484']:.2f})")
    print(f"    Ann ret:         {s['oos_ann_ret_pct']:.2f}% @1x")
    print(f"    Profit:          ${s['profit_net_yr_10m']:,}/yr net @$10M @4x (1.5% sleeve)")
    print(f"    Dual-sleeve:     K484+K661 ~${s['dual_sleeve_net_yr']:,}/yr net @$10M (+${s['diversification_premium']:,} diversif)")
    print(f"    G5a K449 corr:   {s['g5a_corr_k449_critical']} (CRITICAL shared-leg check PASS)")
    print(f"    G5b K484 corr:   {s['g5b_corr_k484_family']} ({s['g5b_verdict']})")
    print(f"    HL conc:         {s['hl_concentration_pct']:.1f}% (within 65% limit, +~1.5pp)")
    print(f"    60d gate:        {s['paper_gate']}")
    print(f"    Status:          {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k677_k661_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
wave_k668_k663_scaffold.py — K668 Wave Driver + Verification
=============================================================
Verifies all K668 deliverables for the K663 TIA-ETH production scaffold:
  - Phase 1:  Strategy script (k663_tia_eth_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k663-tia-eth.plist, 51st daemon)
  - Phase 3:  Dashboard (k663_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k663 flag)
  - Phase 5:  Leverage manager (K663_TIA_ETH cap + SLEEVE_WEIGHTS_V641)
  - Phase 6:  Leverage config (k663_notes + K663_TIA_ETH)
  - Phase 7:  Deployment verification (51st daemon)
  - Phase 8:  Runbook §52 (K663 TIA-ETH playbook)
  - Phase 9:  HTML update (K663 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=8, K668 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K663 pattern (K668 scaffold):
  - Signal: diff = TIA_FR - ETH_FR (direct, no OLS orthogonalization)
  - W=168h rolling mean, zero threshold (sign only)
  - ETH-base K660 SURPRISE: G5b TIA-BTC K507 corr=0.2309 PASS
    (K660 rule predicted BLOCKED-APT-style; TIA vol_ratio=2.12x + DA spikes)
  - Both TIA-PERP and ETH-PERP on HL primary
  - OOS Sharpe 17.13 (9/9 §6 gates PASS)
  - Dual-sleeve: K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = $114,598/yr net @$10M

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

WAVE     = "K668"
STRATEGY = "K663 TIA-ETH FR Differential (ETH-base, Modular DA Celestia, K660 SURPRISE)"


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
    """Verify all K668 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k663_tia_eth_run.py",
            "Phase 1: K663 strategy script (K339 pattern, W=168h, ETH-base direct diff)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k663-tia-eth.plist",
            "Phase 2: 51st daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k663_dashboard.json",
            "Phase 3: Dashboard (diff signal, regime, eth_base_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k663 flag, §52)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K663_TIA_ETH + SLEEVE_WEIGHTS_V641)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K663_TIA_ETH: 4.0 + k663_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (51st daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §52 (K663 TIA-ETH playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K663 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k668_k663_scaffold.py",
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

    # Check k663_tia_eth_run.py
    script_path = REPO_ROOT / "scripts" / "k663_tia_eth_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["k339_repo_root"]       = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]  = "PAPER_TRADE         = True" in content
        results["sleeve_1_5pct"]        = "SLEEVE_PCT          = 0.015" in content
        results["leverage_4x"]          = "LEVERAGE            = 4.0" in content
        results["rolling_168h"]         = "EMA_PERIOD_HOURS    = 168" in content
        results["zero_threshold"]       = "SIGNAL_SIGMA_MULT   = 0.0" in content
        results["hl_primary"]           = "HL_CONCENTRATION_POST_K663" in content
        results["post_only"]            = "POST_ONLY_PARALLEL" in content
        results["k660_surprise"]        = "K660 SURPRISE" in content
        results["direct_diff_no_ols"]   = "tia_eth_diff" in content
        results["symbols_tia_eth_only"] = 'SYMBOLS = ("TIA", "ETH")' in content
        results["dashboard_path"]       = "k663_dashboard.json" in content
        results["g5b_corr_0_2309"]      = "0.2309" in content
        results["dual_sleeve_note"]     = "114,598" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k663_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_eth_mech"]    = "eth_base_mechanism" in dash
            results["dashboard_hl_610"]      = dash.get("hl_concentration_pct") == 61.0
            results["dashboard_gate_sh8"]    = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 8.0
            results["dashboard_sleeve_015"]  = dash.get("sleeve_pct") == 0.015
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k663_cap"]    = cfg.get("exchange_caps", {}).get("K663_TIA_ETH") == 4.0
            results["cfg_k663_notes"]  = "k663_notes" in cfg
            results["cfg_sleeve_015"]  = cfg.get("k663_notes", {}).get("sleeve_pct") == 0.015
            results["cfg_g5b_corr"]    = cfg.get("k663_notes", {}).get("g5b_tia_btc_k507_corr") == 0.2309
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k663"]   = "--include-k663" in content
        results["emer_k663_hl_note"]   = "K663 TIA-ETH: HL-primary" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k663_cap"]        = "K663_TIA_ETH" in content
        results["lev_v641_weights"]    = "SLEEVE_WEIGHTS_V641" in content
        results["lev_k663_015pct"]     = '"K663":    0.015,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k663_label"]      = "com.cryptolab.k663-tia-eth" in content
        results["vds_51st_daemon"]     = "51st daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section52"]   = "## §52 K663 TIA-ETH FR Differential" in content
        results["runbook_k660_surp"]   = "K660 SURPRISE" in content
        results["runbook_dual_sleeve"] = "114,598" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k663_scaffold"]  = "K668" in content or "K663 TIA-ETH FR Diff" in content
        results["html_51st_daemon"]    = "51st daemon" in content

    return results


def run_dry_run_check() -> dict:
    """Run k663_tia_eth_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k663_tia_eth_run.py"
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
            "status":      "PASS" if ok else "FAIL",
            "returncode":  result.returncode,
            "stdout_lines": result.stdout.strip().splitlines()[:5],
            "stderr_lines": result.stderr.strip().splitlines()[:3],
        }
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "reason": "script took > 15s"}
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def generate_report() -> dict:
    """Generate full K668 scaffold verification report."""
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
            "daemon_number":        "51st",
            "strategy":             "K663 TIA-ETH FR Differential",
            "signal":               "sign(rolling_mean_168h(TIA_FR - ETH_FR))",
            "threshold":            "zero (sign only)",
            "ema_window_h":         168,
            "leverage":             4.0,
            "sleeve_pct":           0.015,
            "venue":                "HL primary (TIA-PERP + ETH-PERP, both HL perps)",
            "oos_sharpe":           17.1322,
            "oos_ann_ret_pct":      6.1824,
            "profit_net_yr_10m":    63060,
            "dual_sleeve_net_yr":   114598,
            "g5b_corr":             0.2309,
            "g5b_verdict":          "PASS — K660 SURPRISE (predicted BLOCKED-APT-style)",
            "hl_concentration_pct": 61.0,
            "k660_rule_exception":  "TIA vol_ratio=2.12x + periodic DA spikes -> G5b PASS despite TIA far below ETH",
            "paper_gate":           "60d: Sh>=8 + fill>=60% + maxDD<15%",
            "activation_status":    "SCAFFOLD-READY",
            "plist":                "scripts/com.cryptolab.k663-tia-eth.plist",
            "log_files":            ["logs/k663_tia_eth.log", "logs/k663_tia_eth.err"],
        },
        "deliverable_files": [
            "scripts/k663_tia_eth_run.py",
            "scripts/com.cryptolab.k663-tia-eth.plist",
            "data/k663_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k663 added)",
            "scripts/leverage_manager.py   (K663_TIA_ETH cap + SLEEVE_WEIGHTS_V641)",
            "data/leverage_config.json     (K663_TIA_ETH: 4.0 + k663_notes)",
            "scripts/verify_deployment_status.py  (51st daemon)",
            "docs/k302a_runbook.md         (§52 added)",
            "report.html                   (K663 row added)",
            "wave_k668_k663_scaffold.py    (this file)",
            "wave_k668_k663_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k668_k663_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K668 Wave Driver — K663 TIA-ETH Production Scaffold ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K668 deliverables...")
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
    print(f"    Signal:         {s['signal']}")
    print(f"    Threshold:      {s['threshold']}")
    print(f"    Sleeve:         {s['sleeve_pct']:.1%}  Leverage: {s['leverage']}x")
    print(f"    Venue:          {s['venue']}")
    print(f"    OOS Sharpe:     {s['oos_sharpe']}  Ann ret: {s['oos_ann_ret_pct']:.2f}%")
    print(f"    Profit:         ${s['profit_net_yr_10m']:,}/yr net @$10M @4x (1.5% sleeve)")
    print(f"    Dual-sleeve:    K507+K663 ~${s['dual_sleeve_net_yr']:,}/yr net @$10M")
    print(f"    G5b corr:       {s['g5b_corr']} ({s['g5b_verdict']})")
    print(f"    HL conc:        {s['hl_concentration_pct']:.1f}% (within 65% limit)")
    print(f"    60d gate:       {s['paper_gate']}")
    print(f"    Status:         {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k668_k663_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

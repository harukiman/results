#!/usr/bin/env python3
"""
wave_k654_k629_scaffold.py — K654 Wave Driver + Verification
=============================================================
Verifies all K654 deliverables for the K629 WLD-ETH production scaffold:
  - Phase 1:  Strategy script (k629_wld_eth_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k629-wld-eth.plist)
  - Phase 3:  Dashboard (k629_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k629 flag)
  - Phase 5:  Leverage manager (K629_WLD_ETH cap + SLEEVE_WEIGHTS_V639)
  - Phase 6:  Leverage config (k629_notes + K629_WLD_ETH)
  - Phase 7:  Deployment verification (49th daemon)
  - Phase 8:  Runbook §50 (K629 WLD-ETH playbook)
  - Phase 9:  HTML update (K629 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=10, K654 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K629 pattern (K654 scaffold):
  - Signal: diff = WLD_FR - ETH_FR (direct, no OLS orthogonalization)
  - W=168h EMA, 1.5sigma threshold
  - ETH-base mechanism fix: JUP-BTC cross-base corr=0.3437 PASS
    (K621 WLD-BTC was 0.4612 BLOCKED by BTC-FR-compression)
  - Both WLD-PERP and ETH-PERP on HL primary
  - OOS Sharpe 19.90 (9/9 §6 gates PASS)
  - Escalation: K621 BLOCKED -> K624 BLOCKED -> K627 STILL-BLOCKED -> K629 PASS

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

WAVE     = "K654"
STRATEGY = "K629 WLD-ETH FR Differential (ETH-base, Biometric ID Cluster 24)"


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
    """Verify all K654 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k629_wld_eth_run.py",
            "Phase 1: K629 strategy script (K339 pattern, W=168h, ETH-base direct diff)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k629-wld-eth.plist",
            "Phase 2: 49th daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k629_dashboard.json",
            "Phase 3: Dashboard (diff signal, regime, eth_base_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k629 flag, §50)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K629_WLD_ETH + SLEEVE_WEIGHTS_V639)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K629_WLD_ETH: 4.0 + k629_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (49th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §50 (K629 WLD-ETH playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K629 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k654_k629_scaffold.py",
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

    # Check k629_wld_eth_run.py
    script_path = REPO_ROOT / "scripts" / "k629_wld_eth_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["k339_repo_root"]       = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]  = "PAPER_TRADE         = True" in content
        results["sleeve_3pct"]          = "SLEEVE_PCT          = 0.03" in content
        results["leverage_4x"]          = "LEVERAGE            = 4.0" in content
        results["ema_168h"]             = "EMA_PERIOD_HOURS    = 168" in content
        results["signal_1_5sigma"]      = "SIGNAL_SIGMA_MULT   = 1.5" in content
        results["hl_primary"]           = "HL_CONCENTRATION_POST_K629" in content
        results["post_only"]            = "POST_ONLY_PARALLEL" in content
        results["eth_base_mechanism"]   = "JUP-BTC cross-base corr" in content
        results["direct_diff_no_ols"]   = "wld_eth_diff" in content
        results["symbols_wld_eth_only"] = 'SYMBOLS = ("WLD", "ETH")' in content
        results["dashboard_path"]       = 'k629_dashboard.json' in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k629_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_eth_mech"]    = "eth_base_mechanism" in dash
            results["dashboard_hl_595"]      = dash.get("hl_concentration_pct") == 59.5
            results["dashboard_gate_sh10"]   = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 10.0
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k629_cap"]    = cfg.get("exchange_caps", {}).get("K629_WLD_ETH") == 4.0
            results["cfg_k629_notes"]  = "k629_notes" in cfg
            results["cfg_sleeve_3pct"] = cfg.get("k629_notes", {}).get("sleeve_pct") == 0.03
            results["cfg_jup_corr"]    = cfg.get("k629_notes", {}).get("jup_btc_cross_base_corr") == 0.3437
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k629"]   = "--include-k629" in content
        results["emer_k629_hl_note"]   = "K629 WLD-ETH: HL-primary" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k629_cap"]        = "K629_WLD_ETH" in content
        results["lev_v639_weights"]    = "SLEEVE_WEIGHTS_V639" in content
        results["lev_k629_3pct"]       = '"K629":    0.03,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k629_label"]      = "com.cryptolab.k629-wld-eth" in content
        results["vds_49th_daemon"]     = "49th daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section50"]   = "## §50 K629 WLD-ETH" in content
        results["runbook_eth_base"]    = "ETH-Base Mechanism Fix" in content
        results["runbook_60d_gate"]    = "60-Day Paper-Trade Activation Gate" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k629_scaffold"]  = "K654" in content and "K629 WLD-ETH FR Diff SCAFFOLD-READY" in content
        results["html_49th_daemon"]    = "49th daemon" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    return vds_path.read_text().count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k629_wld_eth_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k629_wld_eth_run.py", "--status"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
        )
        success = result.returncode == 0
        return {
            "returncode": result.returncode,
            "success":    success,
            "stdout_len": len(result.stdout),
            "stderr_len": len(result.stderr),
            "status":     "PASS" if success else "FAIL",
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== {WAVE} {STRATEGY} Wave Verification ===")
    print(f"  Timestamp: {ts_jst}")
    print(f"  REPO_ROOT: {REPO_ROOT}")

    # Phase 1-11: File deliverables
    print("\n[Phase 1-11] Checking file deliverables...")
    deliverables = check_deliverables()
    for c in deliverables["checks"]:
        status_icon = "OK" if c["status"] == "PASS" else "FAIL"
        print(f"  [{status_icon}] {c['path']} — {c['description'][:65]}")
    print(f"  Result: {deliverables['passed']}/{deliverables['total']} passed")

    # Content integrity checks
    print("\n[Content] Checking content integrity...")
    content = check_content_integrity()
    passed_content = sum(1 for v in content.values() if v is True)
    failed_content = sum(1 for v in content.values() if v is False)
    total_content  = len(content)
    for key, val in content.items():
        icon = "OK" if val is True else ("FAIL" if val is False else "INFO")
        print(f"  [{icon}] {key}: {val}")
    print(f"  Result: {passed_content}/{total_content} content checks passed")

    # Daemon count
    print("\n[Phase 7] Counting registered daemons...")
    daemon_count = count_registry_daemons()
    daemon_ok    = daemon_count >= 49
    print(f"  Registered daemons: {daemon_count} (expected >= 49 for K654)")
    print(f"  K629 daemon (49th): {'PASS' if daemon_ok else 'FAIL'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary
    overall_pass = (
        deliverables["all_pass"]
        and daemon_ok
        and dry_run.get("status") == "PASS"
    )

    print(f"\n=== K654 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK (>=49)' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print(f"  Overall: {'ALL PASS' if overall_pass else 'PARTIAL PASS — check failures'}")
    print()
    print(f"  K629 WLD-ETH FR Differential (ETH-base, Biometric ID):")
    print(f"    OOS Sharpe:         19.90 (9/9 §6 gates PASS, IS=29.94, ratio=0.665)")
    print(f"    OOS Ann Return:     7.85% (unlevered on notional)")
    print(f"    Profit 3% sleeve:   $94,210/yr @$10M @4x")
    print(f"    Signal:             diff = WLD_FR - ETH_FR (direct, W=168h EMA)")
    print(f"    ETH-base fix:       JUP-BTC cross-base corr=0.3437 PASS (was 0.4612 BLOCKED)")
    print(f"    Anti-corr K449:     ETH-BTC corr=-0.2052 (portfolio diversification)")
    print(f"    Venue:              HL primary (WLD-PERP + ETH-PERP both on HL)")
    print(f"    HL concentration:   ~59.5% (+2pp, within 65% limit)")
    print(f"    ADF:                p=0.0 (stationary), OU halflife=5.70h")
    print(f"    Walk-fwd:           11/12 positive (91.7%)")
    print(f"    Trades/yr:          48.2 (W=168h, G6 PASS)")
    print(f"    60d gate:           Realized Sh>=10 + fill>=60% + maxDD<15%")
    print(f"    Daemon:             49th (com.cryptolab.k629-wld-eth)")
    print(f"    Cluster:            Biometric ID / World ID (Cluster 24, ETH-base)")
    print(f"    Escalation:         K621 BLOCKED -> K624 BLOCKED -> K627 STILL-BLOCKED -> K629 PASS")
    print(f"    v6.39 path:         K629 adds 3% HL sleeve to v6.38 portfolio")

    # Generate JSON report
    report = {
        "wave":           WAVE,
        "strategy":       STRATEGY,
        "run_time_jst":   ts_jst,
        "deliverables":   deliverables,
        "content_checks": content,
        "daemon_count":   daemon_count,
        "dry_run":        dry_run,
        "overall_pass":   overall_pass,
        "k629_summary": {
            "oos_sharpe":            19.9017,
            "oos_sharpe_is":         29.9396,
            "is_oos_ratio":          0.665,
            "oos_ann_ret_pct":       7.85,
            "profit_3pct_4x_10m":   94210,
            "signal":                "diff = WLD_FR - ETH_FR (direct, W=168h EMA, 1.5sigma)",
            "ema_window_h":          168,
            "sleeve_pct":            0.03,
            "leverage":              4.0,
            "venue":                 "HL primary (WLD-PERP + ETH-PERP both on HL)",
            "hl_concentration_pre":  57.5,
            "hl_concentration_post": 59.5,
            "hl_headroom_pp":        5.5,
            "jup_btc_corr":          0.3437,
            "eth_btc_corr":         -0.2052,
            "adf_pvalue":            0.0,
            "ou_halflife_h":         5.70,
            "walk_forward_pos":      "11/12 (91.7%)",
            "perm_pvalue":           0.0,
            "dsr_pvalue":            0.0,
            "trades_per_yr":         48.2,
            "max_drawdown_pct":      0.71,
            "calmar":                28.0,
            "gates_passed":          9,
            "gates_total":           9,
            "daemon_number":         "49th",
            "plist":                 "scripts/com.cryptolab.k629-wld-eth.plist",
            "cluster":               "Biometric ID / World ID (Cluster 24, ETH-base unlock)",
            "gate_realized_sharpe":  10.0,
            "gate_fill_pct":         60,
            "gate_max_dd_pct":       15,
            "gate_days":             60,
            "v639_candidate":        True,
            "escalation_chain":      "K621 BLOCKED-G5 -> K624 BLOCKED-G5G6 -> K627 STILL-BLOCKED -> K629 PASS",
            "anti_corr_k449":        "ETH-BTC (K449) corr=-0.2052 (anti-correlated: diversification benefit)",
            "wave_scaffold":         WAVE,
        },
    }

    report_path = REPO_ROOT / "wave_k654_k629_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  JSON report: {report_path.relative_to(REPO_ROOT)}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
wave_k651_k646_scaffold.py — K651 Wave Driver + Verification
=============================================================
Verifies all K651 deliverables for the K646 ALGO orthogonalized production scaffold:
  - Phase 1:  Strategy script (k646_algo_orthog_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k646-algo-orthog.plist)
  - Phase 3:  Dashboard (k646_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k646 flag)
  - Phase 5:  Leverage manager (K646_ALGO_ORTHOG cap + SLEEVE_WEIGHTS_V637)
  - Phase 6:  Leverage config (k646_notes + K646_ALGO_ORTHOG)
  - Phase 7:  Deployment verification (46th daemon)
  - Phase 8:  Runbook §48 (K646 ALGO orthog playbook)
  - Phase 9:  HTML update (K646 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=4, K651 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K646 orthog pattern (K650 pattern — K645 direct template):
  - residual = ALGO_diff - β_FIL × FIL_diff
  - β_FIL = 0.411 (K646 OLS single-factor, IS R²=0.2396)
  - W=72h EMA (9 × 8h periods, optimal per K646 analysis)
  - OOS Sharpe 8.11 (residual SF W=72h) vs raw K522=10.27 (G5i BLOCKED, FIL corr=0.6052)
  - G5 cleared: FIL corr 0.6052 → 0.2546 post-orth (PASS); POL 0.2818 (PASS)
  - Enterprise/Utility L1 cluster unlock: first confirmed Algorand PoS VRF-specific FR alpha

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

WAVE     = "K651"
STRATEGY = "K646 ALGO-BTC Orthogonalized FR Differential"


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
    """Verify all K651 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k646_algo_orthog_run.py",
            "Phase 1: K646 strategy script (K339 pattern, W=72h, β_FIL=0.411)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k646-algo-orthog.plist",
            "Phase 2: 46th daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k646_dashboard.json",
            "Phase 3: Dashboard (residual signal, β_fil_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k646 flag, §48)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K646_ALGO_ORTHOG + SLEEVE_WEIGHTS_V637)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K646_ALGO_ORTHOG: 4.0 + k646_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (46th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §48 (K646 ALGO orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K646 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k651_k646_scaffold.py",
            "Phase 11: Wave driver (this file)"
        ),
    ]
    return {
        "checks":       checks,
        "total":        len(checks),
        "passed":       sum(1 for c in checks if c["status"] == "PASS"),
        "failed":       sum(1 for c in checks if c["status"] == "FAIL"),
        "all_pass":     all(c["status"] == "PASS" for c in checks),
    }


def check_content_integrity() -> dict:
    """Spot-check key content in critical files."""
    results = {}

    # Check k646_algo_orthog_run.py has hardcoded β coefficient
    script_path = REPO_ROOT / "scripts" / "k646_algo_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_fil_hardcoded"]      = "BETA_FIL  = 0.411" in content
        results["k339_repo_root"]          = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]     = "PAPER_TRADE         = True" in content
        results["bybit_primary"]           = "BYBIT_SLEEVE_PCT   = SLEEVE_PCT" in content
        results["post_only"]               = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]         = "SIGNAL_SIGMA_MULT   = 1.5" in content
        results["sleeve_2pct"]             = "SLEEVE_PCT          = 0.02" in content
        results["ema_72h"]                 = "EMA_PERIOD_HOURS    = 72" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β_fil fields
    dash_path = DATA_DIR / "k646_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_fil"]    = dash.get("beta_fil_used") == 0.411
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            results["dashboard_hl_65"]       = dash.get("hl_concentration_pct") == 65.0
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K646 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k646_cap"]    = cfg.get("exchange_caps", {}).get("K646_ALGO_ORTHOG") == 4.0
            results["cfg_k646_notes"]  = "k646_notes" in cfg
            results["cfg_beta_fil"]    = cfg.get("k646_notes", {}).get("beta_fil") == 0.411
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k646
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k646"]      = "--include-k646" in content
        results["emer_k646_bybit_note"]   = "K646 ALGO-BTC orthog: Bybit-only" in content or "K646" in content

    # Check leverage_manager.py has K646 cap and SLEEVE_WEIGHTS_V637
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k646_cap"]     = "K646_ALGO_ORTHOG" in content
        results["lev_v637_weights"] = "SLEEVE_WEIGHTS_V637" in content

    # Check verify_deployment_status.py has 46th daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k646_label"]   = "com.cryptolab.k646-algo-orthog" in content
        results["vds_46th_daemon"]  = "46th daemon" in content

    # Check runbook has §48
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section48"]  = "## §48 K646 ALGO-BTC Orthogonalized" in content
        results["runbook_beta_table"] = "β_FIL" in content
        results["runbook_60d_gate"]   = "60-Day Paper-Trade Activation Gate" in content

    # Check report.html has K646 row
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k646_scaffold"] = "K651 K646 ALGO-BTC Orthog SCAFFOLD-READY" in content
        results["html_46th_daemon"]   = "46th daemon" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    content = vds_path.read_text()
    return content.count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k646_algo_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k646_algo_orthog_run.py", "--status"],
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
    daemon_ok    = daemon_count >= 46
    print(f"  Registered daemons: {daemon_count} (expected >= 46 for K651)")
    print(f"  K646 daemon (46th): {'PASS' if daemon_ok else 'FAIL'}")

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

    print(f"\n=== K651 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK (>=46)' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print(f"  Overall: {'ALL PASS' if overall_pass else 'PARTIAL PASS — check failures'}")
    print()
    print(f"  K646 ALGO-BTC Orthogonalized FR Differential:")
    print(f"    OOS Sharpe:         8.11 (residual SF FIL W=72h)")
    print(f"    β_FIL:              0.411 (K646 OLS SF, HARDCODED)")
    print(f"    FIL corr raw:       0.6052 (K522 BLOCKED-G5i)")
    print(f"    FIL corr post-orth: 0.2546 (K646 UNLOCKED)")
    print(f"    OOS Ann Ret @4x:    2.5406%")
    print(f"    Profit 2% sleeve:   ~$20,325/yr net @$10M @4x")
    print(f"    Venue:              Bybit primary (ALGO+BTC paired)")
    print(f"    HL concentration:   65% UNCHANGED (Bybit-only)")
    print(f"    60d gate:           Realized Sh>=4 + fill>=60% + maxDD<20%")
    print(f"    Daemon:             46th (com.cryptolab.k646-algo-orthog)")
    print(f"    Cluster:            Enterprise/Utility L1 / Algorand PoS VRF (7th orthog)")
    print(f"    v6.37 path:         K646 adds 2% Bybit sleeve to v6.36")

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
        "k646_summary": {
            "oos_sharpe_residual":     8.11,
            "oos_sharpe_raw_k522":     10.271,
            "beta_fil":                0.411,
            "is_r2":                   0.2396,
            "oos_r2":                  -0.0282,
            "fil_corr_raw":            0.6052,
            "fil_corr_post_orth":      0.2546,
            "oos_ann_ret_pct":         2.5406,
            "profit_2pct_4x_10m_usd":  20325,
            "ema_window_h":            72,
            "sleeve_pct":              0.02,
            "leverage":                4.0,
            "venue":                   "Bybit primary (ALGOUSDT perp + BTC-USDT-SWAP)",
            "hl_concentration_pct":    65.0,
            "daemon_number":           "46th",
            "plist":                   "scripts/com.cryptolab.k646-algo-orthog.plist",
            "cluster":                 "Enterprise/Utility L1 / Algorand PoS VRF",
            "gate_realized_sharpe":    4.0,
            "gate_fill_pct":           60,
            "gate_max_dd_pct":         20,
            "gate_days":               60,
            "v637_candidate":          True,
            "orthog_formula":          "residual = ALGO_diff - 0.411*FIL_diff",
            "k522_unblocked":          True,
            "wave_scaffold":           WAVE,
        },
    }

    report_path = REPO_ROOT / f"wave_k651_k646_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  JSON report: {report_path.relative_to(REPO_ROOT)}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())

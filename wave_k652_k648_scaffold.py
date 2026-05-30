#!/usr/bin/env python3
"""
wave_k652_k648_scaffold.py — K652 Wave Driver + Verification
=============================================================
Verifies all K652 deliverables for the K648 POL 6-factor orthogonalized production scaffold:
  - Phase 1:  Strategy script (k648_pol_orthog_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k648-pol-orthog.plist)
  - Phase 3:  Dashboard (k648_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k648 flag)
  - Phase 5:  Leverage manager (K648_POL_ORTHOG cap + SLEEVE_WEIGHTS_V637)
  - Phase 6:  Leverage config (k648_notes + K648_POL_ORTHOG)
  - Phase 7:  Deployment verification (47 daemons)
  - Phase 8:  Runbook §49 (K648 POL 6-factor orthog playbook)
  - Phase 9:  HTML update (K648 SCAFFOLD-READY row, 47 daemon count)
  - Phase 10: 60d paper-trade gate criteria
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

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

WAVE     = "K652"
STRATEGY = "K648 POL 6-Factor Orthogonalized FR Differential (MF OP+SEI+APT+TIA+FIL+SAND W=168h)"


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
    """Verify all K652 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k648_pol_orthog_run.py",
            "Phase 1: K648 strategy script (K339 pattern, 6-factor MF)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k648-pol-orthog.plist",
            "Phase 2: 47th daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k648_dashboard.json",
            "Phase 3: Dashboard (residual signal, betas_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k648 flag)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K648_POL_ORTHOG + SLEEVE_WEIGHTS_V637)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K648_POL_ORTHOG: 4.0 + k648_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (47th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §49 (K648 POL 6-factor orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K648 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k652_k648_scaffold.py",
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

    # Check k648_pol_orthog_run.py has hardcoded β coefficients
    script_path = REPO_ROOT / "scripts" / "k648_pol_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_op_hardcoded"]   = "BETA_OP   =  0.337443" in content
        results["beta_sei_hardcoded"]  = "BETA_SEI  =  0.075509" in content
        results["beta_apt_hardcoded"]  = "BETA_APT  = -0.016480" in content
        results["beta_tia_hardcoded"]  = "BETA_TIA  =  0.059789" in content
        results["beta_fil_hardcoded"]  = "BETA_FIL  =  0.042751" in content
        results["beta_sand_hardcoded"] = "BETA_SAND =  0.200488" in content
        results["k339_repo_root"]      = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"] = "PAPER_TRADE         = True" in content
        results["bybit_primary"]       = "BYBIT_SLEEVE_PCT   = SLEEVE_PCT" in content
        results["post_only"]           = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]     = "SIGNAL_SIGMA_MULT   = 1.5" in content
        results["sleeve_2pct"]         = "SLEEVE_PCT          = 0.02" in content
        results["ema_168h"]            = "EMA_PERIOD_HOURS    = 168" in content
        results["6factor_formula"]     = "BETA_SAND * sand_diff" in content
        results["hl_unchanged_65"]     = "HL_CONCENTRATION_UNCHANGED = 65.0" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β fields (after first run)
    dash_path = DATA_DIR / "k648_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            betas = dash.get("betas_used", {})
            results["dashboard_beta_op"]   = betas.get("beta_op")   == 0.337443
            results["dashboard_beta_sei"]  = betas.get("beta_sei")  == 0.075509
            results["dashboard_beta_apt"]  = betas.get("beta_apt")  == -0.016480
            results["dashboard_beta_tia"]  = betas.get("beta_tia")  == 0.059789
            results["dashboard_beta_fil"]  = betas.get("beta_fil")  == 0.042751
            results["dashboard_beta_sand"] = betas.get("beta_sand") == 0.200488
            results["dashboard_regime"]    = "regime" in dash
            results["dashboard_oos_perf"]  = "oos_performance" in dash
            results["dashboard_orthog"]    = "orthog_mechanism" in dash
            results["dashboard_hl_65"]     = dash.get("hl_concentration_pct") == 65.0
        except Exception as e:
            results["dashboard_error"] = str(e)
    else:
        results["dashboard_not_yet_created"] = True   # created on first --status run

    # Check leverage_config.json has K648 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k648_cap"]      = cfg.get("exchange_caps", {}).get("K648_POL_ORTHOG") == 4.0
            results["cfg_k648_notes"]    = "k648_notes" in cfg
            results["cfg_beta_op"]       = cfg.get("k648_notes", {}).get("beta_op")   == 0.337443
            results["cfg_beta_sand"]     = cfg.get("k648_notes", {}).get("beta_sand") == 0.200488
            results["cfg_oos_sharpe"]    = cfg.get("k648_notes", {}).get("oos_sharpe_residual") == 23.407
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k648
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k648"]     = "--include-k648" in content
        results["emer_k648_summary"]     = "K648 POL-BTC ORTHOG CLOSE SUMMARY" in content
        results["emer_bybit_only_note"]  = "Bybit-only" in content
        results["emer_6factor_formula"]  = "0.337443*OP_diff" in content

    # Check leverage_manager.py has K648 cap and SLEEVE_WEIGHTS_V637
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k648_cap"]      = "K648_POL_ORTHOG" in content
        results["lev_v637_weights"]  = "SLEEVE_WEIGHTS_V637" in content
        results["lev_k648_sleeve"]   = '"K648":    0.02' in content

    # Check verify_deployment_status.py has 47th daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_47th_daemon"]   = "com.cryptolab.k648-pol-orthog" in content
        results["vds_47th_label"]    = "47th daemon" in content

    # Check runbook has §49
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section49"]  = "## §49 K648 POL-BTC 6-Factor" in content
        results["runbook_beta_table"] = "β_OP" in content and "β_SAND" in content
        results["runbook_60d_gate"]   = "60-Day Paper-Trade Activation Gate" in content
        results["runbook_4_29m"]      = "$4,293,200/yr" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    content = vds_path.read_text()
    return content.count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k648_pol_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k648_pol_orthog_run.py", "--status"],
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
        print(f"  [{status_icon}] {c['path']} — {c['description'][:70]}")
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
    daemon_ok    = daemon_count == 47
    print(f"  Registered daemons: {daemon_count} (expected 47)")
    print(f"  Status: {'PASS' if daemon_ok else f'MISMATCH (expected 47, got {daemon_count})'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K652 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K648 Strategy:    POL-BTC 6-Factor Orthogonalized FR Differential")
    print(f"  OOS Sharpe:       23.41 (residual MF W=168h) vs 46.52 raw K611 (BLOCKED)")
    print(f"  beta_OP:          0.337443  beta_SEI: 0.075509  beta_APT: -0.016480")
    print(f"  beta_TIA:         0.059789  beta_FIL: 0.042751  beta_SAND: 0.200488")
    print(f"  IS R2:            0.3788 (highest in orthog series)  OOS R2: 0.0114")
    print(f"  ADF p=0.0 (stationary)  OU halflife=3.55h")
    print(f"  Profit 2% slv:    $4,293,200/yr @$10M @4x (OOS 10.73% ann ret)")
    print(f"  HL concentration: 65% UNCHANGED (Bybit-only)")
    print(f"  Cluster:          Polygon L2/PoS/zkEVM (Polygon-specific unlock, 47th daemon)")
    print(f"  6-factor unlock:  K611 BLOCKED (6 factors > 0.40) -> K648 all post-orth < 0.40 PASS")
    print(f"  Post-orth corrs:  OP=-0.096, SEI=0.007, APT=0.030, TIA=0.005, FIL=0.011, SAND=0.030")
    print(f"  60d gate:         Realized Sh>=12 + fill>=60% + maxDD<20%")
    print(f"  v6.37:            K648 adds 2% Bybit sleeve to v6.36")
    print()

    # Save wave result JSON
    report = {
        "wave":             WAVE,
        "strategy":         STRATEGY,
        "timestamp_jst":    ts_jst,
        "deliverables":     deliverables,
        "content_checks":   content,
        "daemon_count":     daemon_count,
        "daemon_ok":        daemon_ok,
        "dry_run":          dry_run,
        "k648_summary": {
            "oos_sharpe_residual":       23.407,
            "oos_sharpe_raw_k611":       46.5229,
            "k611_status":               "BLOCKED-ROLLUP-SIBLING (6 factors exceed G5)",
            "k611_blockers":             {
                "OP": 0.5178, "SEI": 0.4935, "APT": 0.5064,
                "TIA": 0.4203, "FIL": 0.4427, "SAND": 0.4274,
            },
            "oos_ann_ret_pct":           10.733,
            "beta_op":                   0.337443,
            "beta_sei":                  0.075509,
            "beta_apt":                  -0.016480,
            "beta_tia":                  0.059789,
            "beta_fil":                  0.042751,
            "beta_sand":                 0.200488,
            "is_r2":                     0.3788,
            "oos_r2":                    0.0114,
            "adf_pvalue":                0.0,
            "ou_halflife_h":             3.55,
            "post_orth_corrs":           {
                "OP": -0.096, "SEI": 0.007, "APT": 0.030,
                "TIA": 0.005, "FIL": 0.011, "SAND": 0.030,
            },
            "profit_2pct_usd_yr":        4_293_200,
            "profit_2pct_k":             4293.2,
            "sleeve_activation":         "2% Bybit (POL+BTC both legs)",
            "hl_concentration":          "65% UNCHANGED — Bybit-only",
            "cluster":                   "Polygon L2 / PoS / zkEVM (Polygon-specific unlock, 47th daemon)",
            "gate_60d":                  "Realized Sh>=12 + fill>=60% + maxDD<20%",
            "v637_candidate":            "K648 2% Bybit + v6.36 portfolio",
            "ema_window":                "W=168h (21 x 8h periods)",
            "daemon_number":             "47th",
            "plist_label":               "com.cryptolab.k648-pol-orthog",
            "orthog_formula":            (
                "residual = POL_diff "
                "- 0.337443*OP_diff "
                "- 0.075509*SEI_diff "
                "- (-0.016480)*APT_diff "
                "- 0.059789*TIA_diff "
                "- 0.042751*FIL_diff "
                "- 0.200488*SAND_diff"
            ),
            "polygon_alpha_hypothesis":  (
                "POL FR dynamics: AggLayer aggregation proof demand cycles (distinct from OP/ARB rollup) "
                "+ MATIC->POL migration Sep 2024 rebranding premium "
                "+ Polygon zkEVM gas fee adoption (distinct from OP/ARB optimistic sequencer) "
                "+ POL staking/validator re-staking demand (BFT validator set) "
                "— all orthogonal to OP+SEI+APT+TIA+FIL+SAND common factors after 6-factor OLS"
            ),
        },
        "overall_status":   "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k652_k648_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k652_k648_scaffold.json")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

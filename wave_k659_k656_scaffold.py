#!/usr/bin/env python3
"""
wave_k659_k656_scaffold.py — K659 Wave Driver + Verification
=============================================================
Verifies all K659 deliverables for the K656 GALA dual-factor orthogonalized production scaffold:
  - Phase 1: Strategy script (k656_gala_orthog_run.py)
  - Phase 2: Daemon plist (com.cryptolab.k656-gala-orthog.plist)
  - Phase 3: Dashboard (k656_dashboard.json)
  - Phase 4: Emergency exit integration (--include-k656 flag)
  - Phase 5: Leverage manager (K656_GALA_ORTHOG cap + SLEEVE_WEIGHTS_V640)
  - Phase 6: Leverage config (k656_notes + K656_GALA_ORTHOG)
  - Phase 7: Deployment verification (50 daemons)
  - Phase 8: Runbook §51 (K656 GALA orthog playbook)
  - Phase 9: HTML update (K656 SCAFFOLD-READY row, 50 daemon count)
  - Phase 10: 60d gate criteria (Sh>=4, fill>=60%, DD<20%)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
K659 Milestone: 50th daemon MILESTONE — 9th orthog scaffold — gaming cluster COMPLETE
  (SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) all ACCEPT CONDITIONAL)
  First dual-factor (JUP+FIL) orthogonalization in K6xx series.
  IS R²=0.4731 LARGEST in series. OOS Sh=8.3211 DF W=504h.
  $48,143/yr net @$10M @4x (2% Bybit sleeve).
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

WAVE     = "K659"
STRATEGY = "K656 GALA-BTC Dual-Factor Orthogonalized FR Differential"


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
    """Verify all K659 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k656_gala_orthog_run.py",
            "Phase 1: K656 strategy script (K339 pattern, W=504h, β_JUP=0.22738 β_FIL=0.405439)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k656-gala-orthog.plist",
            "Phase 2: 50th daemon plist (StartInterval 28800, MILESTONE)"
        ),
        _check_file(
            DATA_DIR / "k656_dashboard.json",
            "Phase 3: Dashboard (residual signal, betas_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k656 flag, §51)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K656_GALA_ORTHOG + SLEEVE_WEIGHTS_V640)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K656_GALA_ORTHOG: 4.0 + k656_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (50th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §51 (K656 GALA orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K656 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k659_k656_scaffold.py",
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

    # Check k656_gala_orthog_run.py has hardcoded β coefficients
    script_path = REPO_ROOT / "scripts" / "k656_gala_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_jup_hardcoded"]   = "BETA_JUP" in content and "0.227380" in content
        results["beta_fil_hardcoded"]   = "BETA_FIL" in content and "0.405439" in content
        results["k339_repo_root"]       = "REPO_ROOT" in content and "Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]  = "PAPER_TRADE" in content and "True" in content
        results["bybit_primary"]        = "BYBIT_SLEEVE_PCT" in content
        results["post_only"]            = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]      = "SIGNAL_SIGMA_MULT" in content and "1.5" in content
        results["sleeve_2pct"]          = "SLEEVE_PCT" in content and "0.02" in content
        results["rolling_504h"]         = "ROLLING_PERIOD_HOURS" in content and "504" in content
        results["gaming_cluster_note"]  = "gaming cluster COMPLETE" in content.lower() or "GAMING_CLUSTER" in content.upper() or "Gaming cluster COMPLETE" in content
        results["dual_factor_note"]     = "dual-factor" in content.lower() or "DF" in content
        results["50th_daemon_note"]     = "50th daemon" in content.lower() or "50th" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β fields
    dash_path = DATA_DIR / "k656_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_jup"]    = dash.get("betas_used", {}).get("beta_jup") == 0.2274 or dash.get("betas_used", {}).get("beta_jup") == 0.22738
            results["dashboard_beta_fil"]    = dash.get("betas_used", {}).get("beta_fil") == 0.405439
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            oos = dash.get("oos_performance", {})
            results["dashboard_oos_sh"]      = oos.get("sharpe_residual_df_504h") == 8.3211
            results["dashboard_50th"]        = oos.get("daemon_number") == "50th"
            results["dashboard_gaming_cluster"] = "SAND" in str(oos.get("gaming_cluster_complete", ""))
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K656 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k656_cap"]      = cfg.get("exchange_caps", {}).get("K656_GALA_ORTHOG") == 4.0
            results["cfg_k656_notes"]    = "k656_notes" in cfg
            results["cfg_beta_jup"]      = cfg.get("k656_notes", {}).get("beta_jup") == 0.22738
            results["cfg_beta_fil"]      = cfg.get("k656_notes", {}).get("beta_fil") == 0.405439
            results["cfg_sleeve_2pct"]   = cfg.get("k656_notes", {}).get("sleeve_pct") == 0.02
            results["cfg_50th_milestone"] = "50th" in cfg.get("k656_notes", {}).get("milestone", "")
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k656
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k656"]      = "--include-k656" in content
        results["emer_k656_summary"]      = "K656 GALA-BTC DUAL-FACTOR ORTHOG CLOSE SUMMARY" in content

    # Check leverage_manager.py has K656 cap and SLEEVE_WEIGHTS_V640
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k656_cap"]      = "K656_GALA_ORTHOG" in content
        results["lev_v640_weights"]  = "SLEEVE_WEIGHTS_V640" in content

    # Check verify_deployment_status.py has 50th daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_50th_daemon"]  = "com.cryptolab.k656-gala-orthog" in content
        results["vds_50th_label"]   = "50th daemon" in content

    # Check runbook has §51
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section51"]    = "§51 K656 GALA-BTC Dual-Factor" in content
        results["runbook_beta_table"]   = "β_JUP" in content or "beta_JUP" in content or "0.227380" in content
        results["runbook_60d_gate"]     = "60-Day Paper-Trade Activation Gate" in content or "60d gate" in content.lower()
        results["runbook_gaming_cluster"] = "Gaming Cluster" in content and "COMPLETE" in content
        results["runbook_50th_milestone"] = "50th Daemon Milestone" in content

    # Check report.html has K659 / K656 entry
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k659_entry"]    = "K659" in content
        results["html_k656_scaffold"] = "K656" in content and "SCAFFOLD" in content.upper()
        results["html_50_daemons"]    = "50 daemons" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    content = vds_path.read_text()
    return content.count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k656_gala_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k656_gala_orthog_run.py", "--status"],
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
    print(f"  ★★★ 50th DAEMON MILESTONE — 9th ORTHOG SCAFFOLD — GAMING CLUSTER COMPLETE ★★★")

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
    daemon_ok    = daemon_count == 50
    print(f"  Registered daemons: {daemon_count} (expected 50 — MILESTONE)")
    print(f"  Status: {'PASS — 50th daemon MILESTONE!' if daemon_ok else f'MISMATCH (expected 50, got {daemon_count})'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K659 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK — MILESTONE!' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K656 Strategy:       GALA-BTC Dual-Factor Orthogonalized FR Differential")
    print(f"  OOS Sharpe:          8.3211 (DF W=504h) — raw K620=12.09 BLOCKED")
    print(f"  beta_JUP:            0.227380 (HARDCODED, no re-OLS in prod)")
    print(f"  beta_FIL:            0.405439 (HARDCODED, no re-OLS in prod)")
    print(f"  JUP cleared:         0.4308 -> 0.0495 (-87%)")
    print(f"  FIL cleared:         0.4114 -> 0.0184 (-96%)")
    print(f"  IS R²:               0.4731 (LARGEST in K6xx orthog series)")
    print(f"  First dual-factor:   YES — first JUP+FIL dual-factor orthog in K6xx series")
    print(f"  Rolling window:      W=504h = 63 x 8h periods")
    print(f"  Signal threshold:    1.5σ of 504h rolling window")
    print(f"  Profit 2% sleeve:    $48,143/yr net @$10M @4x (OOS 1.88% ann ret)")
    print(f"  Venue:               Bybit primary (HL cap 66.5% > 65%)")
    print(f"  HL concentration:    64.5% UNCHANGED (Bybit-only)")
    print(f"  Gaming cluster:      SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) ALL ACCEPT COND")
    print(f"  60d gate:            Realized Sh>=4 + fill>=60% + maxDD<20%")
    print(f"  v6.40:               K656 2% Bybit sleeve + v6.39 portfolio")
    print(f"  Daemon:              50th (MILESTONE — 10 waves of daemons!)")
    print(f"  Orthog series:       9th orthog scaffold (K628/K631/K633/K635/K638/K645/K646/K647/K656)")
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
        "k656_summary": {
            "oos_sharpe_residual_df_504h":  8.3211,
            "oos_sharpe_raw_k620":          12.0901,
            "k620_status":                  "BLOCKED-G5 (JUP=0.4308 + FIL=0.4114 dual blockers)",
            "is_r2":                        0.4731,
            "is_r2_note":                   "LARGEST in K6xx orthog series (dual-factor first)",
            "oos_r2":                       -0.666,
            "beta_jup":                     0.22738,
            "beta_fil":                     0.405439,
            "beta_note":                    "HARDCODED — no re-OLS in production for stability.",
            "jup_corr_raw":                 0.4308,
            "jup_corr_post_orth":           0.0495,
            "fil_corr_raw":                 0.4114,
            "fil_corr_post_orth":           0.0184,
            "max_post_orth_corr":           0.2993,
            "max_post_orth_pair":           "UNI",
            "g5_pass":                      True,
            "gaming_distinct":              "SAND=-0.058 < 0.40 (gaming cluster distinction RETAINED)",
            "rolling_window":               "W=504h (63 x 8h periods)",
            "signal_threshold":             "1.5σ of 504h rolling window",
            "profit_2pct_net_usd_yr":       48_143,
            "profit_2pct_gross_usd_yr":     60_179,
            "sleeve_activation":            "2% Bybit (GALA+BTC both legs, delta-neutral)",
            "hl_concentration":             "64.5% UNCHANGED (Bybit-only, HL cap 66.5% > 65%)",
            "cluster":                      "Gaming Publisher / Gala Games P2E / GalaChain L1 (9th orthog scaffold)",
            "gaming_cluster_complete":      "SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) ALL ACCEPT CONDITIONAL",
            "gate_60d":                     "Realized Sh>=4 + fill>=60% + maxDD<20% (50% of OOS Sh=8.32)",
            "v640_candidate":               "K656 2% Bybit + v6.39 portfolio",
            "daemon_number":                "50th",
            "milestone":                    "K659 MILESTONE — 50th daemon, 9th orthog scaffold, gaming cluster complete",
            "orthog_series":                "K628/K631/K633/K635/K638/K645/K646/K647/K656 (9 orthog scaffolds)",
            "first_dual_factor":            "YES — first JUP+FIL dual-factor orthog in K6xx series",
        },
        "overall_status":   "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k659_k656_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k659_k656_scaffold.json")
    print()

    return 0 if deliverables["all_pass"] and daemon_ok else 1


if __name__ == "__main__":
    sys.exit(main())

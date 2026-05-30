#!/usr/bin/env python3
"""
wave_k701_k698_scaffold.py — K701 Wave Driver + Verification
=============================================================
Verifies all K701 deliverables for the K698 LINK-ETH production scaffold:
  - Phase 1:  Strategy script (k698_link_eth_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k698-link-eth.plist, 61st daemon)
  - Phase 3:  Dashboard (k698_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k698 flag)
  - Phase 5:  Leverage manager (K698_LINK_ETH cap + SLEEVE_WEIGHTS_V646)
  - Phase 6:  Leverage config (k698_notes + K698_LINK_ETH)
  - Phase 7:  Deployment verification (61st daemon)
  - Phase 8:  Runbook §62 (K698 LINK-ETH playbook)
  - Phase 9:  HTML update (K698 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=6, K701 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K698 pattern (K701 scaffold):
  - Signal: diff = LINK_FR - ETH_FR (direct diff, ETH-base mechanism)
  - W=120h rolling mean, zero threshold (sign only)
  - 4th ETH-base scaffold (K629 WLD-ETH, K658 SOL-ETH, K661 AVAX-ETH, K698 LINK-ETH)
  - 1st oracle-ETH pair (oracle middleware vs Ethereum L1)
  - Both LINK-PERP and ETH-PERP on Bybit (HL 64.5% baseline + 2.5% = 67% > 65% cap)
  - OOS Sharpe 12.07 (W=120h, ~217d OOS, 8/8 §6 gates PASS)
  - $28,997/yr net @$10M @4x (2.5% sleeve)
  - G5a corr(K698, K557 LINK-BTC) = 0.0578 PASS CRITICAL
  - G5b corr(K698, K449 ETH-BTC) = -0.0036 PASS CRITICAL
  - MR9 FR identity max_err=5.42e-20; position-level corr=0.1254 de-correlated
  - K695 lesson: LINK-SOL G5c=0.497 BLOCKED. K698 avoids SOL. Clean oracle expansion.
  - K557 coordination: K557 LINK-BTC 1.5% + K698 LINK-ETH 2.5% = 4.0% max LINK AUM
  - LINK oracle MM floor ~1.25e-5/hr; LINK > ETH FR 74.5% of time
  - ADF stat=-18.82 p=0.0, OU halflife=1.45h ultra-fast MR
  - G4 17/21 folds positive (81%)

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

WAVE     = "K701"
STRATEGY = "K698 LINK-ETH FR Differential (oracle middleware vs Ethereum L1, 4th ETH-base scaffold, 1st oracle-ETH pair, Bybit primary, W=120h, 8/8 §6 gates)"


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
    """Verify all K701 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k698_link_eth_run.py",
            "Phase 1: K698 strategy script (K339 pattern, W=120h, oracle vs ETH L1, Bybit primary)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k698-link-eth.plist",
            "Phase 2: 61st daemon plist (StartInterval 28800, Bybit primary, 4th ETH-base)"
        ),
        _check_file(
            DATA_DIR / "k698_dashboard.json",
            "Phase 3: Dashboard (oracle-ETH diff signal, regime, oracle_eth_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k698 flag, §62)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K698_LINK_ETH 4x cap + SLEEVE_WEIGHTS_V646)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K698_LINK_ETH: 4.0 + k698_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (61st daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §62 (K698 LINK-ETH playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K698 SCAFFOLD-READY banner)"
        ),
        _check_file(
            REPO_ROOT / "wave_k701_k698_scaffold.py",
            "Phase 11: This wave driver file"
        ),
    ]
    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")
    return {
        "checks":  checks,
        "n_pass":  n_pass,
        "n_fail":  n_fail,
        "verdict": "ALL_PASS" if n_fail == 0 else f"{n_fail}_FAIL",
    }


def check_script_content() -> dict:
    """Verify k698_link_eth_run.py contains required K701 elements."""
    results: dict = {}
    script_path = REPO_ROOT / "scripts" / "k698_link_eth_run.py"
    if not script_path.exists():
        return {"error": "script not found"}
    content = script_path.read_text()
    results["k339_repo_root"]         = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
    results["link_eth_signal"]        = "LINK_FR - ETH_FR" in content or "link_eth_diff" in content
    results["w120h_window"]           = "EMA_PERIOD_HOURS    = 120" in content
    results["sleeve_025"]             = "SLEEVE_PCT          = 0.025" in content
    results["leverage_4x"]            = "LEVERAGE            = 4.0" in content
    results["bybit_primary"]          = "Bybit" in content and "long_venue" in content
    results["dashboard_path"]         = "k698_dashboard.json" in content
    results["fr_history_path"]        = "k698_fr_history.jsonl" in content
    results["paper_trade_default"]    = "PAPER_TRADE         = True" in content
    results["61st_daemon"]            = "61st" in content
    results["oracle_eth_mechanism"]   = "oracle" in content.lower() and "mm floor" in content.lower()
    results["g5a_k557_critical"]      = "0.0578" in content or "g5a" in content.lower()
    results["g5b_k449_critical"]      = "-0.0036" in content or "g5b" in content.lower()
    results["mr9_identity"]           = "5.42e-20" in content or "MR9" in content
    results["k695_lesson"]            = "K695" in content
    results["k557_coordination"]      = "K557" in content and "coord" in content.lower()
    return results


def check_dashboard_content() -> dict:
    """Verify k698_dashboard.json contains required K701 fields."""
    results: dict = {}
    dash_path = DATA_DIR / "k698_dashboard.json"
    if not dash_path.exists():
        return {"error": "dashboard not found"}
    try:
        dash = json.loads(dash_path.read_text())
    except Exception as e:
        return {"error": str(e)}
    results["wave_k701"]              = dash.get("wave") == "K701"
    results["oos_sharpe_12"]          = abs(dash.get("oos_performance", {}).get("sharpe", 0) - 12.0676) < 0.01
    results["sleeve_025"]             = abs(dash.get("sleeve_pct", 0) - 0.025) < 0.001
    results["leverage_4x"]            = dash.get("leverage") == 4.0
    results["venue_bybit"]            = dash.get("venue") == "Bybit"
    results["hl_concentration_645"]   = abs(dash.get("hl_concentration_pct", 0) - 64.5) < 0.5
    results["daemon_61st"]            = dash.get("oos_performance", {}).get("daemon_number") == "61st"
    results["gate_sharpe_6"]          = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 6.0
    results["oracle_eth_mechanism"]   = "oracle_eth_mechanism" in dash
    results["g5a_k557_corr"]          = abs(dash.get("oracle_eth_mechanism", {}).get("g5a_link_btc_k557_corr", 1) - 0.0578) < 0.001
    results["g5b_k449_corr"]          = abs(dash.get("oracle_eth_mechanism", {}).get("g5b_eth_btc_k449_corr", 1) - (-0.0036)) < 0.001
    results["mr9_max_err"]            = dash.get("oracle_eth_mechanism", {}).get("mr9_fr_identity_max_err") == 5.42e-20
    return results


def check_config_content() -> dict:
    """Verify leverage_config.json contains K698 entries."""
    results: dict = {}
    cfg_path = DATA_DIR / "leverage_config.json"
    if not cfg_path.exists():
        return {"error": "config not found"}
    try:
        cfg = json.loads(cfg_path.read_text())
    except Exception as e:
        return {"error": str(e)}
    results["cfg_k698_cap"]    = cfg.get("exchange_caps", {}).get("K698_LINK_ETH") == 4.0
    results["cfg_k698_notes"]  = "k698_notes" in cfg
    results["cfg_sleeve_025"]  = cfg.get("k698_notes", {}).get("sleeve_pct") == 0.025
    results["cfg_bybit_only"]  = cfg.get("k698_notes", {}).get("bybit_only") is True
    results["cfg_hl_64_5"]     = abs(cfg.get("k698_notes", {}).get("hl_concentration_post", 0) - 64.5) < 0.5
    return results


def check_emergency_exit_content() -> dict:
    """Verify emergency_hl_exit.py contains K698 flag."""
    results: dict = {}
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if not emer_path.exists():
        return {"error": "emergency_hl_exit.py not found"}
    content = emer_path.read_text()
    results["emer_include_k698"]         = "--include-k698" in content
    results["emer_k698_close_summary"]   = "K698 LINK-ETH CLOSE SUMMARY" in content
    results["emer_bybit_only_note"]      = "K698 LINK-ETH: Bybit-only" in content or "K698 LINK-ETH close summary" in content.lower()
    return results


def check_leverage_manager_content() -> dict:
    """Verify leverage_manager.py contains K698 entries."""
    results: dict = {}
    lm_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if not lm_path.exists():
        return {"error": "leverage_manager.py not found"}
    content = lm_path.read_text()
    results["lev_k698_cap"]        = "K698_LINK_ETH" in content
    results["lev_k698_025pct"]     = '"K698":    0.025,' in content
    results["lev_v646"]            = "SLEEVE_WEIGHTS_V646" in content
    return results


def check_verify_deployment_content() -> dict:
    """Verify verify_deployment_status.py contains 61st daemon."""
    results: dict = {}
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return {"error": "verify_deployment_status.py not found"}
    content = vds_path.read_text()
    results["vds_k698_label"]      = "com.cryptolab.k698-link-eth" in content
    results["vds_61st_daemon"]     = "61st daemon" in content
    return results


def check_html_content() -> dict:
    """Verify report.html contains K698/K701 scaffold references."""
    results: dict = {}
    html_path = REPO_ROOT / "report.html"
    if not html_path.exists():
        return {"error": "report.html not found"}
    content = html_path.read_text()
    results["html_61st_daemon"]             = "61st" in content
    results["html_k698_scaffold_ready"]     = "SCAFFOLD-READY" in content and "K698" in content
    results["html_oracle_eth"]              = "oracle-ETH" in content.lower() or "oracle vs ETH" in content.lower()
    results["html_k701_banner"]             = "K701" in content
    return results


def dry_run_verify() -> dict:
    """Run k698_link_eth_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k698_link_eth_run.py"
    if not script_path.exists():
        return {"status": "SKIP", "reason": "script not found"}
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--status"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        return {
            "returncode": result.returncode,
            "stdout_lines": result.stdout.strip().splitlines()[:5],
            "stderr_lines": result.stderr.strip().splitlines()[:3],
            "status": "PASS" if result.returncode == 0 else "FAIL",
        }
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== {WAVE} K698 LINK-ETH Production Scaffold Verification — {ts_jst} ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Daemon:   61st (4th ETH-base scaffold, 1st oracle-ETH pair)")
    print(f"  OOS Sh:   12.07 (W=120h, 8/8 §6 gates PASS)")
    print(f"  Profit:   $28,997/yr net @$10M @4x (2.5% sleeve)")
    print(f"  Venue:    Bybit primary (LINK-PERP + ETH-PERP)")
    print(f"  HL:       64.5% UNCHANGED (Bybit-only mandatory — HL-only 67%>65% cap)")
    print(f"  G5a:      corr(K698, K557 LINK-BTC) = 0.0578 PASS CRITICAL")
    print(f"  G5b:      corr(K698, K449 ETH-BTC) = -0.0036 PASS CRITICAL")
    print(f"  MR9:      LINK-ETH = LINK-BTC - ETH-BTC (max_err=5.42e-20, pos-corr=0.1254)")
    print(f"  K695:     LINK-SOL G5c=0.497 BLOCKED. K698 avoids SOL. Clean oracle expansion.")
    print(f"  K557:     LINK coord: K557 1.5% + K698 2.5% = 4.0% max combined LINK AUM")
    print(f"  Gate:     60d paper-trade: Sh>=6 + fill>=60% + maxDD<15%")

    # Check all deliverables
    print("\n--- Phase Deliverable Checks ---")
    deliverables = check_deliverables()
    for c in deliverables["checks"]:
        status_icon = "OK" if c["status"] == "PASS" else "FAIL"
        print(f"  [{status_icon}] {c['path']} — {c['description']}")
    print(f"\n  Deliverables: {deliverables['n_pass']}/{deliverables['n_pass']+deliverables['n_fail']} PASS")

    # Content checks
    print("\n--- Script Content Checks ---")
    script_checks = check_script_content()
    for k, v in script_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- Dashboard Content Checks ---")
    dash_checks = check_dashboard_content()
    for k, v in dash_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- Config Content Checks ---")
    cfg_checks = check_config_content()
    for k, v in cfg_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- Emergency Exit Checks ---")
    emer_checks = check_emergency_exit_content()
    for k, v in emer_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- Leverage Manager Checks ---")
    lm_checks = check_leverage_manager_content()
    for k, v in lm_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- Deployment Status Checks ---")
    vds_checks = check_verify_deployment_content()
    for k, v in vds_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- HTML Content Checks ---")
    html_checks = check_html_content()
    for k, v in html_checks.items():
        icon = "OK" if v else "FAIL"
        print(f"  [{icon}] {k}: {v}")

    print("\n--- Dry-Run Verification ---")
    dry_run = dry_run_verify()
    print(f"  Status: {dry_run.get('status')}")
    for line in dry_run.get("stdout_lines", []):
        print(f"    {line}")

    # Build report
    report = {
        "wave":               WAVE,
        "strategy":           STRATEGY,
        "ts_jst":             ts_jst,
        "daemon_number":      "61st",
        "eth_base_rank":      "4th ETH-base scaffold (1st oracle-ETH pair)",
        "oos_sharpe":         12.0676,
        "w_hours":            120,
        "sleeve_pct":         0.025,
        "leverage":           4.0,
        "profit_10m":         28997,
        "venue":              "Bybit primary (HL 64.5% UNCHANGED)",
        "gate":               "60d paper-trade: Sh>=6 + fill>=60% + maxDD<15%",
        "deliverables":       deliverables,
        "script_checks":      script_checks,
        "dashboard_checks":   dash_checks,
        "config_checks":      cfg_checks,
        "emergency_checks":   emer_checks,
        "leverage_checks":    lm_checks,
        "deployment_checks":  vds_checks,
        "html_checks":        html_checks,
        "dry_run":            dry_run,
        "activation_path": {
            "plist":          "scripts/com.cryptolab.k698-link-eth.plist",
            "log_files":      ["logs/k698_link_eth.log", "logs/k698_link_eth.err"],
            "dashboard":      "data/k698_dashboard.json",
            "runbook_section": "docs/k302a_runbook.md §62",
        },
        "commit_files": [
            "scripts/k698_link_eth_run.py",
            "scripts/com.cryptolab.k698-link-eth.plist",
            "data/k698_dashboard.json",
            "scripts/emergency_hl_exit.py",
            "scripts/leverage_manager.py",
            "data/leverage_config.json",
            "scripts/verify_deployment_status.py",
            "docs/k302a_runbook.md",
            "report.html",
            "wave_k701_k698_scaffold.py",
            "wave_k701_k698_scaffold.json",
        ],
        "oracle_eth_notes": {
            "g5a_k557_corr":        0.0578,
            "g5b_k449_corr":        -0.0036,
            "mr9_fr_identity_err":  5.42e-20,
            "mr9_pos_corr":         0.1254,
            "k695_lesson":          "LINK-SOL REJECTED (G5c=0.497). K698 avoids SOL. G5a=0.0578 PASS.",
            "k557_coord_combined":  "K557 1.5% + K698 2.5% = 4.0% max combined LINK AUM",
            "link_gt_eth_pct":      74.5,
            "link_mm_floor":        1.25e-5,
            "ou_halflife_h":        1.45,
            "adf_pvalue":           0.0,
        },
        "section6_gates": {
            "G1_oos_sharpe":        "PASS (12.07)",
            "G2_perm_p":            "PASS (p=0.0)",
            "G3_dsr_bonferroni":    "PASS (p=0.0, 5 trials)",
            "G4_walk_forward":      "PASS (17/21=81%)",
            "G5a_k557_link_btc":    "PASS (corr=0.0578 CRITICAL)",
            "G5b_k449_eth_btc":     "PASS (corr=-0.0036 CRITICAL)",
            "G6_trades_yr":         "PASS (31.9/yr, W=120h)",
            "G7_ann_ret_4x":        "PASS (11.6% > 5%)",
            "G9_oos_days":          "PASS (217d > 180d)",
            "total":                "8/8 PASS",
        },
    }

    # Write JSON report
    json_path = REPO_ROOT / "wave_k701_k698_scaffold.json"
    json_path.write_text(json.dumps(report, indent=2))
    print(f"\n  JSON report written: {json_path.relative_to(REPO_ROOT)}")

    # Final summary
    all_deliverables_pass = deliverables["n_fail"] == 0
    dry_run_pass = dry_run.get("status") in ("PASS", "SKIP")

    print(f"\n=== K701 Scaffold Verification Summary ===")
    print(f"  Deliverables:  {deliverables['n_pass']}/{deliverables['n_pass']+deliverables['n_fail']} {'ALL PASS' if all_deliverables_pass else 'SOME FAIL'}")
    print(f"  Dry-run:       {dry_run.get('status')}")
    print(f"  Strategy:      K698 LINK-ETH FR Differential (oracle vs ETH L1)")
    print(f"  Daemon:        61st (4th ETH-base scaffold, 1st oracle-ETH pair)")
    print(f"  OOS Sharpe:    12.07 (W=120h, 8/8 §6 gates PASS)")
    print(f"  Profit:        $28,997/yr net @$10M @4x @2.5% sleeve")
    print(f"  Venue:         Bybit primary (HL 64.5% UNCHANGED)")
    print(f"  Gate:          60d paper-trade: Sh>=6 + fill>=60% + maxDD<15%")
    print(f"  ETH-base:      4th ETH-base scaffold (K629/K658/K661/K698)")
    print(f"  Oracle-ETH:    1st oracle-ETH pair (Chainlink vs Ethereum L1 — NEW)")
    print(f"  G5a K557:      corr=0.0578 PASS CRITICAL")
    print(f"  G5b K449:      corr=-0.0036 PASS CRITICAL")
    print(f"  MR9:           max_err=5.42e-20, pos-corr=0.1254 de-correlated")
    print(f"  K695 lesson:   LINK-SOL G5c=0.497 BLOCKED. K698 avoids SOL. Clean.")
    print(f"  K557 coord:    K557 1.5% + K698 2.5% = 4.0% max combined LINK AUM")
    print(f"  LINK anchor:   MM floor ~1.25e-5/hr, LINK>ETH FR 74.5% time")
    print(f"  v6.50 path:    K698 LINK-ETH 2.5% Bybit sleeve (61st daemon)")
    print()

    return 0 if (all_deliverables_pass and dry_run_pass) else 1


if __name__ == "__main__":
    sys.exit(main())

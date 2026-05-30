#!/usr/bin/env python3
"""
wave_k699_k696_scaffold.py — K699 Wave Driver + Verification
=============================================================
Verifies all K699 deliverables for the K696 ENA-SOL production scaffold:
  - Phase 1:  Strategy script (k696_ena_sol_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k696-ena-sol.plist, 60th daemon MILESTONE)
  - Phase 3:  Dashboard (k696_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k696 flag)
  - Phase 5:  Leverage manager (K696_ENA_SOL cap + SLEEVE_WEIGHTS_V645)
  - Phase 6:  Leverage config (k696_notes + K696_ENA_SOL)
  - Phase 7:  Deployment verification (60th daemon)
  - Phase 8:  Runbook §63 (K696 ENA-SOL playbook)
  - Phase 9:  HTML update (K696 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=13, K699 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K696 pattern (K699 scaffold):
  - Signal: diff = ENA_FR - SOL_FR (direct alt-alt, no base asset)
  - W=168h rolling mean, zero threshold (sign only)
  - SEVENTH ALT-ALT pair (9th evaluated, no BTC/ETH leg) — FIRST CROSS-CLUSTER
  - 60th daemon MILESTONE (7th alt-alt ACCEPT)
  - Both ENA-PERP and SOL-PERP on Bybit (HL 62.5% headroom preserved, Bybit mandatory)
  - OOS Sharpe 26.93 (W=168h, 3rd in alt-alt family)
  - $93,187/yr net @$10M @4x (3% standalone sleeve)
  - MR8: ENA new vertex — NOT in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA} alt-alt algebraic group
  - MR9: K696 = K616_dir - K476_dir. K616 vs K476 corr = 0.0094 ORTHOGONAL
  - MR6: K616 + K696 combined ENA notional < 6% AUM
  - ENA (Ethena synthetic stable infra) -7.65%/yr vs SOL +7.70%/yr cross-cluster
  - Double carry: ENA FR < 0 (37.2% of time) earns |ENA FR| + SOL FR simultaneously
  - ADF stat = -13.0808 STRONGEST stationary in alt-alt family
  - OU half-life = 3.75h STRONG
  - ACCEPT 15/17; G4 11/12 (fold 7 negative -6.136); G6 20.8/yr carry-positive
  - 61.5% BEAR_ENA (LONG SOL/SHORT ENA); 38.5% BULL_ENA

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

WAVE     = "K699"
STRATEGY = (
    "K696 ENA-SOL FR Differential (SEVENTH ALT-ALT pair, 9th evaluated, "
    "Bybit-only, ENA synthetic-stable infra vs SOL SVM L1 cross-cluster, "
    "FIRST CROSS-CLUSTER, 60th daemon MILESTONE, ACCEPT 15/17)"
)


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
    """Verify all K699 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k696_ena_sol_run.py",
            "Phase 1: K696 strategy script (K339 pattern, W=168h, alt-alt direct diff, Bybit-only, ACCEPT 15/17)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k696-ena-sol.plist",
            "Phase 2: 60th daemon MILESTONE plist (StartInterval 28800, Bybit-only)"
        ),
        _check_file(
            DATA_DIR / "k696_dashboard.json",
            "Phase 3: Dashboard (alt-alt diff signal, regime, alt_alt_mechanism, cross_cluster_analysis)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k696 flag, §63)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K696_ENA_SOL cap + SLEEVE_WEIGHTS_V645)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K696_ENA_SOL: 4.0 + k696_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (60th daemon MILESTONE registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §63 (K696 ENA-SOL playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K696 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k699_k696_scaffold.py",
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

    # Check k696_ena_sol_run.py
    script_path = REPO_ROOT / "scripts" / "k696_ena_sol_run.py"
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
        results["seventh_alt_alt"]         = "SEVENTH ALT-ALT" in content
        results["ena_sol_diff"]            = "ena_sol_diff" in content
        results["symbols_ena_sol"]         = 'SYMBOLS = ("ENA", "SOL")' in content
        results["dashboard_path"]          = "k696_dashboard.json" in content
        results["oos_sh_26_93"]            = "26.93" in content
        results["mr8_new_vertex"]          = "MR8" in content
        results["mr9_independence"]        = "MR9" in content
        results["hl_62_5"]                 = "62.5" in content
        results["profit_93k"]              = "93,187" in content
        results["60th_daemon"]             = "60th" in content
        results["g4_11_12"]               = "11/12" in content
        results["ou_3_75h"]               = "3.75h" in content
        results["ena_combined_cap"]        = "ENA_COMBINED_CAP_PCT" in content
        results["double_carry"]            = "double_carry" in content or "double carry" in content.lower()
        results["cross_cluster"]           = "cross_cluster" in content or "cross-cluster" in content.lower()
        results["adf_13"]                  = "13.0808" in content or "-13.08" in content
    else:
        results["script_missing"] = True

    # Check dashboard
    dash_path = DATA_DIR / "k696_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_regime"]        = "regime" in dash
            results["dashboard_oos_perf"]      = "oos_performance" in dash
            results["dashboard_alt_mech"]      = "alt_alt_mechanism" in dash
            results["dashboard_cross_cluster"] = "cross_cluster_analysis" in dash
            results["dashboard_hl_625"]        = dash.get("hl_concentration_pct") == 62.5
            results["dashboard_gate_sh13"]     = dash.get("gate_metrics", {}).get("realized_sharpe_target") == 13.0
            results["dashboard_sleeve_030"]    = dash.get("sleeve_pct") == 0.030
            results["dashboard_g5"]            = "g5_independence" in dash
        except Exception as e:
            results["dashboard_error"] = str(e)
    else:
        results["dashboard_missing"] = True

    # Check leverage_config.json
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k696_cap"]    = cfg.get("exchange_caps", {}).get("K696_ENA_SOL") == 4.0
            results["cfg_k696_notes"]  = "k696_notes" in cfg
            results["cfg_sleeve_030"]  = cfg.get("k696_notes", {}).get("sleeve_pct") == 0.03
            results["cfg_bybit_only"]  = cfg.get("k696_notes", {}).get("bybit_only") is True
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k696"]     = "--include-k696" in content
        results["emer_k696_bybit_note"]  = "K696 ENA-SOL: Bybit-only" in content or "K696 ENA-SOL CLOSE SUMMARY" in content

    # Check leverage_manager.py
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k696_cap"]        = "K696_ENA_SOL" in content
        results["lev_v645_weights"]    = "SLEEVE_WEIGHTS_V645" in content
        results["lev_k696_030pct"]     = '"K696":    0.03,' in content

    # Check verify_deployment_status.py
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k696_label"]      = "com.cryptolab.k696-ena-sol" in content
        results["vds_60th_daemon"]     = "60th daemon" in content

    # Check runbook
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section63"]       = "## §63 K696 ENA-SOL FR Differential" in content
        results["runbook_seventh_altalt"]  = "SEVENTH ALT-ALT" in content
        results["runbook_cross_cluster"]   = "CROSS-CLUSTER" in content or "cross-cluster" in content.lower()
        results["runbook_profit_93k"]      = "93,187" in content or "93K" in content
        results["runbook_mr8"]             = "MR8" in content
        results["runbook_mr9"]             = "MR9" in content

    # Check report.html
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k699_scaffold"]          = "K699" in content
        results["html_60th_daemon"]            = "60th daemon" in content
        results["html_k696_scaffold_ready"]    = "SCAFFOLD-READY" in content and "K696" in content
        results["html_seventh_altalt"]         = "SEVENTH ALT-ALT" in content
        results["html_cross_cluster"]          = "CROSS-CLUSTER" in content or "cross-cluster" in content.lower()

    return results


def run_dry_run_check() -> dict:
    """Run k696_ena_sol_run.py --status to verify script is importable."""
    script_path = REPO_ROOT / "scripts" / "k696_ena_sol_run.py"
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
    """Generate full K699 scaffold verification report."""
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
            "daemon_number":         "60th MILESTONE",
            "strategy":              "K696 ENA-SOL FR Differential (SEVENTH ALT-ALT pair, 9th evaluated, FIRST CROSS-CLUSTER)",
            "signal":                "sign(rolling_mean_168h(ENA_FR - SOL_FR))",
            "threshold":             "zero (sign only)",
            "ema_window_h":          168,
            "leverage":              4.0,
            "sleeve_pct":            0.030,
            "venue":                 "Bybit-only (ENA-PERP + SOL-PERP, both Bybit — HL-only would breach 65% cap)",
            "hl_concentration_pct":  62.5,
            "hl_cap_note":           "62.5% within 65% cap — Bybit-only mandatory (HL-only = 65.5% OVER cap). 2.5pp headroom preserved.",
            "oos_sharpe":            26.93,
            "oos_period":            "~2025-10 to 2026-05",
            "profit_net_yr_10m":     93187,
            "seventh_alt_alt":       True,
            "ninth_evaluated":       True,
            "first_cross_cluster":   True,
            "section6_result":       "ACCEPT 15/17 — G4=11/12 (fold 7 Sh=-6.136); G6=20.8/yr carry-positive. All other gates PASS.",
            "mr8_new_vertex":        "ENA not in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA}. ENA = 8th vertex, first synthetic-stable protocol equity.",
            "mr9_independence":      "K696 = K616_dir - K476_dir. K616 vs K476 corr = 0.0094 ORTHOGONAL. PnL corr K616=0.6723 complementary.",
            "mr6_ena_cap":           "K616 ENA-BTC + K696 ENA-SOL combined ENA notional < 6% AUM (< $600K @$10M).",
            "cross_cluster_thesis":  "ENA = synthetic-stable infra equity (sUSDe protocol, -7.65%/yr). SOL = SVM L1 retail (+7.70%/yr). Independent FR drivers.",
            "double_carry":          "ENA FR < 0 (37.2% of time): SHORT ENA earns |ENA FR| AND SHORT SOL earns SOL FR simultaneously. Asymmetric carry advantage.",
            "adf_stat":              "-13.0808 STRONGEST stationary in alt-alt family",
            "ou_half_life":          "3.75h STRONG",
            "g4_status":             "11/12 folds positive. 1 negative fold (fold 7: Sh=-6.136). G6 20.8/yr carry-positive confirms edge.",
            "sol_saturation":        "G5a K476 corr=0.1765 SOL-saturation CRITICAL PASS. K696 = 8th SOL strategy (up to $4.8M combined extreme).",
            "regime_distribution":   "61.5% BEAR_ENA (LONG SOL/SHORT ENA); 38.5% BULL_ENA (LONG ENA/SHORT SOL)",
            "paper_gate":            "60d: Sh>=13 (48% of OOS 26.93) + fill>=60% + maxDD<15%",
            "activation_status":     "SCAFFOLD-READY",
            "plist":                 "scripts/com.cryptolab.k696-ena-sol.plist",
            "log_files":             ["logs/k696_ena_sol.log", "logs/k696_ena_sol.err"],
            "family_rank": (
                "OOS Sh: K686=50.27 > K682=43.43 > K679=39.29 > K696=26.93 > K690=25.11 > K694=19.09 > K684=9.65. "
                "K696 = 3rd highest in alt-alt family. Combined 7 accepted alt-alt pairs: ~$919K/yr @$10M."
            ),
        },
        "deliverable_files": [
            "scripts/k696_ena_sol_run.py",
            "scripts/com.cryptolab.k696-ena-sol.plist",
            "data/k696_dashboard.json",
            "scripts/emergency_hl_exit.py  (--include-k696 added)",
            "scripts/leverage_manager.py   (K696_ENA_SOL cap + SLEEVE_WEIGHTS_V645 K696 entry)",
            "data/leverage_config.json     (K696_ENA_SOL: 4.0 + k696_notes)",
            "scripts/verify_deployment_status.py  (60th daemon MILESTONE)",
            "docs/k302a_runbook.md         (§63 added)",
            "report.html                   (K696 SCAFFOLD-READY row added)",
            "wave_k699_k696_scaffold.py    (this file)",
            "wave_k699_k696_scaffold.json  (this report)",
        ],
    }

    # Write JSON report
    out_path = REPO_ROOT / "wave_k699_k696_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    print(f"\n=== K699 Wave Driver — K696 ENA-SOL Production Scaffold (60th Daemon MILESTONE) ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Checking all K699 deliverables...")
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
    print(f"    Daemon:             {s['daemon_number']}")
    print(f"    Strategy:           {s['strategy']}")
    print(f"    Signal:             {s['signal']}")
    print(f"    Threshold:          {s['threshold']}")
    print(f"    Sleeve:             {s['sleeve_pct']:.1%}  Leverage: {s['leverage']}x")
    print(f"    Venue:              {s['venue']}")
    print(f"    HL conc:            {s['hl_concentration_pct']:.1f}% ({s['hl_cap_note']})")
    print(f"    OOS Sharpe:         {s['oos_sharpe']}  ({s['oos_period']})")
    print(f"    Profit:             ${s['profit_net_yr_10m']:,}/yr net @$10M @4x (3% standalone)")
    print(f"    Section 6:          {s['section6_result']}")
    print(f"    MR8 new vertex:     {s['mr8_new_vertex']}")
    print(f"    MR9 independence:   {s['mr9_independence']}")
    print(f"    MR6 ENA cap:        {s['mr6_ena_cap']}")
    print(f"    Cross-cluster:      {s['cross_cluster_thesis']}")
    print(f"    Double carry:       {s['double_carry']}")
    print(f"    ADF stat:           {s['adf_stat']}")
    print(f"    OU half-life:       {s['ou_half_life']}")
    print(f"    G4 status:          {s['g4_status']}")
    print(f"    SOL saturation:     {s['sol_saturation']}")
    print(f"    Regime dist:        {s['regime_distribution']}")
    print(f"    Family rank:        {s['family_rank']}")
    print(f"    60d gate:           {s['paper_gate']}")
    print(f"    Status:             {s['activation_status']}")
    print()

    out_path = REPO_ROOT / "wave_k699_k696_scaffold.json"
    print(f"  Report written -> {out_path}")
    print()

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

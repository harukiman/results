#!/usr/bin/env python3
"""
wave_k669_k658_scaffold.py — K669 Wave Driver + Verification
=============================================================
Verifies all K669 deliverables for the K658 SOL-ETH production scaffold:
  - Phase 1:  Strategy script (k658_sol_eth_run.py)
  - Phase 2:  Daemon plist (com.cryptolab.k658-sol-eth.plist)
  - Phase 3:  Dashboard (k658_dashboard.json)
  - Phase 4:  Emergency exit integration (--include-k658 flag)
  - Phase 5:  Leverage manager (K658_SOL_ETH cap + SLEEVE_WEIGHTS_V642)
  - Phase 6:  Leverage config (k658_notes + K658_SOL_ETH)
  - Phase 7:  Deployment verification (52nd daemon)
  - Phase 8:  Runbook §53 (K658 SOL-ETH playbook)
  - Phase 9:  HTML update (K658/K669 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=15, K669 spec)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K658 pattern (K669 scaffold):
  - Signal: diff = SOL_FR - ETH_FR (direct, no OLS orthogonalization)
  - W=168h EMA, sign threshold (threshold=0)
  - ETH-base mechanism wins: SOL-BTC K476 PnL corr=0.2131 PASS
    (dual sleeve: K476 SOL-BTC 1.5% + K658 SOL-ETH 1.5% = 3% combined)
  - Both SOL-PERP and ETH-PERP on HL primary
  - OOS Sharpe 29.66 (ACCEPT, ETH-base wins vs K476 Sh=16.30 +13.36)
  - HL neutral: K476 reduced 4%->1.5%, K658 adds 1.5% = net unchanged

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

WAVE     = "K669"
STRATEGY = "K658 SOL-ETH FR Differential (ETH-base, SOL L1 SVM DePIN-Retail, dual K476)"


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
    """Verify all K669 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k658_sol_eth_run.py",
            "Phase 1: K658 strategy script (K339 pattern, W=168h, ETH-base direct diff)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k658-sol-eth.plist",
            "Phase 2: 52nd daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k658_dashboard.json",
            "Phase 3: Dashboard (diff signal, regime, eth_base_mechanism)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k658 flag, §53)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K658_SOL_ETH + SLEEVE_WEIGHTS_V642)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K658_SOL_ETH: 4.0 + k658_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (52nd daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §53 (K658 SOL-ETH playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K658/K669 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k669_k658_scaffold.py",
            "Phase 11: Wave driver (this file)"
        ),
    ]
    total  = len(checks)
    passed = sum(1 for c in checks if c["status"] == "PASS")
    return {
        "checks":   checks,
        "total":    total,
        "passed":   passed,
        "failed":   total - passed,
        "all_pass": passed == total,
    }


def check_content() -> dict:
    """Spot-check key content in deliverable files."""
    results = {}

    # Phase 1: strategy script
    script = (REPO_ROOT / "scripts" / "k658_sol_eth_run.py").read_text()
    results["k339_repo_root"]        = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in script
    results["paper_trade_default"]   = "PAPER_TRADE         = True" in script
    results["sleeve_1_5pct"]         = "SLEEVE_PCT          = 0.015" in script
    results["leverage_4x"]           = "LEVERAGE            = 4.0" in script
    results["ema_168h"]              = "EMA_PERIOD_HOURS    = 168" in script
    results["sign_threshold"]        = "SIGNAL_SIGMA_MULT   = 0.0" in script
    results["hl_primary"]            = 'SYMBOLS = ("SOL", "ETH")' in script
    results["post_only"]             = "POST_ONLY_PARALLEL" in script
    results["eth_base_mechanism"]    = "ETH-base mechanism" in script
    results["direct_diff_no_ols"]    = "no OLS orthogonalization" in script or "no orthogonalization" in script
    results["symbols_sol_eth_only"]  = "SOL" in script and "ETH" in script
    results["dashboard_path"]        = 'DASHBOARD_PATH  = DATA_DIR  / "k658_dashboard.json"' in script
    results["dashboard_regime"]      = "BULL_SOL" in script or "BEAR_SOL" in script

    # Phase 3: dashboard
    dash = json.loads((DATA_DIR / "k658_dashboard.json").read_text())
    results["dashboard_oos_sh"]      = dash.get("oos_performance", {}).get("sharpe", 0) > 29.0
    results["dashboard_sleeve_1_5"]  = dash.get("sleeve_pct", 0) == 0.015
    results["dashboard_gate_sh15"]   = dash.get("gate_metrics", {}).get("realized_sharpe_target", 0) >= 15.0
    results["dashboard_daemon_52"]   = dash.get("oos_performance", {}).get("daemon_number") == "52nd"

    # Phase 5: leverage manager
    lev_mgr = (REPO_ROOT / "scripts" / "leverage_manager.py").read_text()
    results["lev_k658_cap"]          = '"K658_SOL_ETH"' in lev_mgr or '"K658":' in lev_mgr
    results["lev_v642_weights"]      = "SLEEVE_WEIGHTS_V642" in lev_mgr
    results["lev_k658_1_5pct"]       = '"K658":    0.015' in lev_mgr

    # Phase 6: leverage config
    lev_cfg = json.loads((DATA_DIR / "leverage_config.json").read_text())
    results["cfg_k658_cap"]          = lev_cfg.get("exchange_caps", {}).get("K658_SOL_ETH") == 4.0
    results["cfg_k658_notes"]        = "k658_notes" in lev_cfg
    results["cfg_sol_btc_corr"]      = (
        lev_cfg.get("k658_notes", {}).get("sol_btc_k476_pnl_corr", 0) > 0.2
    )

    # Phase 4: emergency exit
    emer = (REPO_ROOT / "scripts" / "emergency_hl_exit.py").read_text()
    results["emer_include_k658"]     = "--include-k658" in emer
    results["emer_k658_hl_note"]     = "K658 SOL-ETH" in emer

    # Phase 7: verify_deployment_status
    vds = (REPO_ROOT / "scripts" / "verify_deployment_status.py").read_text()
    results["vds_k658_label"]        = "com.cryptolab.k658-sol-eth" in vds
    results["vds_52nd_daemon"]       = "52nd daemon" in vds

    # Phase 8: runbook
    runbook = (REPO_ROOT / "docs" / "k302a_runbook.md").read_text()
    results["runbook_section53"]     = "§53" in runbook
    results["runbook_eth_base"]      = "ETH-base mechanism" in runbook
    results["runbook_60d_gate"]      = "Sh>=15" in runbook

    # Phase 9: HTML
    html = (REPO_ROOT / "report.html").read_text()
    results["html_k658_scaffold"]    = "K658 SOL-ETH" in html or "k658" in html
    results["html_52nd_daemon"]      = "52nd daemon" in html or "52nd" in html

    return results


def run_dry_run() -> dict:
    """Run the K658 script with --dry-run and capture result."""
    cmd    = [sys.executable, str(REPO_ROOT / "scripts" / "k658_sol_eth_run.py"), "--dry-run"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {
        "returncode": result.returncode,
        "success":    result.returncode == 0,
        "stdout_len": len(result.stdout),
        "stderr_len": len(result.stderr),
        "status":     "PASS" if result.returncode == 0 else "FAIL",
        "stdout_preview": result.stdout[:500] if result.stdout else "",
        "stderr_preview": result.stderr[:200] if result.stderr else "",
    }


def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== {WAVE} Wave Driver — {STRATEGY} ===")
    print(f"  Timestamp: {ts_jst}")

    print("\n[Phase 1-11] Checking deliverables...")
    deliverables = check_deliverables()
    for c in deliverables["checks"]:
        status_icon = "✓" if c["status"] == "PASS" else "✗"
        print(f"  {status_icon} {c['status']:4s}  {c['path']:55s}  ({c['size_bytes']:,} bytes)")
    print(f"\n  Deliverables: {deliverables['passed']}/{deliverables['total']} PASS")

    print("\n[Content checks] Verifying key content...")
    content = check_content()
    fails   = [k for k, v in content.items() if not v]
    passes  = [k for k, v in content.items() if v]
    print(f"  Content: {len(passes)}/{len(content)} PASS")
    if fails:
        print(f"  FAIL: {', '.join(fails)}")

    print("\n[Phase 12] Running dry-run...")
    dry_run = run_dry_run()
    print(f"  Dry-run: {'PASS' if dry_run['success'] else 'FAIL'} (returncode={dry_run['returncode']})")
    if dry_run['stdout_preview']:
        print(f"  stdout: {dry_run['stdout_preview'][:200]}")
    if dry_run['stderr_preview']:
        print(f"  stderr: {dry_run['stderr_preview'][:200]}", file=sys.stderr)

    # Write JSON report
    overall = (
        deliverables["all_pass"]
        and len(fails) == 0
        and dry_run["success"]
    )

    report = {
        "wave":     WAVE,
        "strategy": STRATEGY,
        "run_time_jst": ts_jst,
        "deliverables": deliverables,
        "content_checks": content,
        "daemon_count": 52,
        "dry_run":  dry_run,
        "overall_pass": overall,
        "k658_summary": {
            "oos_sharpe":               29.6613,
            "oos_sharpe_k476_btc":      16.298,
            "eth_base_sharpe_delta":    13.3633,
            "oos_ann_ret_pct":          7.0553,
            "oos_ann_ret_4x_pct":       28.221,
            "profit_1_5pct_4x_10m":     42_332,
            "profit_3pct_dual_10m_est":  85_000,
            "signal":                   "diff = SOL_FR - ETH_FR (direct, W=168h EMA, sign threshold)",
            "ema_window_h":             168,
            "threshold":                0.0,
            "sleeve_pct":               0.015,
            "leverage":                 4.0,
            "venue":                    "HL primary (SOL-PERP + ETH-PERP both on HL)",
            "hl_concentration_impact":  "Neutral (K476 reduced 4%->1.5%, K658 adds 1.5% = net unchanged)",
            "k476_pnl_corr":            0.2131,
            "k449_pnl_corr_critical":   0.0488,
            "k629_pnl_corr":            0.08,
            "adf_pvalue":               0.0,
            "ou_halflife_h":            2.4,
            "ou_theta":                 0.290,
            "vol_ratio":                1.63,
            "walk_forward_pos":         "4/4 (100%)",
            "perm_pvalue":              0.0,
            "dsr_pvalue":               1.56e-109,
            "entries_yr":               20.3,
            "max_drawdown_pct":         0.2833,
            "gates_passed":             9,
            "gates_total":              9,
            "daemon_number":            "52nd",
            "plist":                    "scripts/com.cryptolab.k658-sol-eth.plist",
            "cluster":                  "SOL L1 Monolithic SVM / DePIN-Retail (ETH-base unlock)",
            "cluster_rationale":        (
                "SOL (Solana) FR driven by DePIN/memecoin retail cycles, Raydium/Orca DEX dominance, "
                "Jito MEV + jitoSOL demand, validator yield compression. "
                "ETH-base wins: Sh 16.30->29.66 (+13.36). "
                "Dual sleeve K476: corr=0.2131 diversified."
            ),
            "gate_realized_sharpe":     15.0,
            "gate_fill_pct":            60,
            "gate_max_dd_pct":          15,
            "gate_days":                60,
            "eth_base_family": {
                "K629_WLD_ETH": "ACCEPT — ETH-base unlocks WLD (Sh=19.9)",
                "K658_SOL_ETH": "ACCEPT — ETH-base wins for SOL (+13.36 Sh vs K476)",
                "K663_TIA_ETH": "ACCEPT — ETH-base K660 SURPRISE (Sh=17.13)",
                "K632_HYPE_ETH": "WORSE — distinct cluster (Sh drops 24.49->12.99)",
                "K660_APT_ETH": "BLOCKED-G5b — APT FR negative vs ALL bases",
                "K661_AVAX_ETH": "CONDITIONAL — BTC wins, corr=0.373 borderline",
            },
            "v642_candidate":           True,
            "wave_scaffold":            "K669",
        }
    }

    out_path = REPO_ROOT / "wave_k669_k658_scaffold.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\n  JSON report written -> {out_path}")

    result_str = "PASS" if overall else "FAIL"
    print(f"\n=== K669 Wave Result: {result_str} ===")
    print(f"  Strategy: {STRATEGY}")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']}")
    print(f"  Content checks: {len(passes)}/{len(content)}")
    print(f"  Dry-run: {'PASS' if dry_run['success'] else 'FAIL'}")
    print(f"  52nd daemon: com.cryptolab.k658-sol-eth")
    print(f"  OOS Sharpe: 29.66 (ETH-base wins vs K476 Sh=16.30 +13.36)")
    print(f"  Profit: $42,332/yr @$10M @4x @1.5% sleeve")
    print(f"  Dual: K476 1.5% + K658 1.5% = $85K/yr est combined")
    print(f"  Gate: Realized Sh>=15 + fill>=60% + maxDD<15%")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())

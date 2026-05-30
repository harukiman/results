#!/usr/bin/env python3
"""
wave_k771_k769_scaffold.py — K771 K769 AXS-SOL Alt-Alt Scaffold
=================================================================
Wave K771: Production scaffold for K769 AXS-SOL FR Differential (CLEAN ACCEPT).
76th daemon, 19th alt-alt scaffold, 16th vertex AXS (Gaming P2E).

Scaffold tasks:
  Phase 1:  Verify scripts/k769_axs_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k769-axs-sol.plist (76th daemon, 8h/28800s)
  Phase 3:  Add K769 entry to data/leverage_config.json
  Phase 4:  Add K769 DaemonSpec to scripts/verify_deployment_status.py
  Phase 5:  Add --include-k769 flag to scripts/emergency_hl_exit.py
  Phase 6:  Add §73 section to docs/k302a_runbook.md
  Phase 7:  Initialize data/k769_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Update report.html (K771 K769 AXS-SOL scaffold entry)
  Phase 10: Generate wave_k771_k769_scaffold.json

K769 CLEAN ACCEPT parameters:
  OOS Sharpe:      16.0543 (W=168h, zero threshold, ~211d OOS)
  G4 Walk-Forward: 12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423)
  G5 max corr:     -0.2796 (G5n ENA-SOL) — all 23 gates PASS
  Sleeve:          1.5% (long-tail liquidity — AXS HIP-3 HL listing)
  K523 central:    $123,689/yr @$10M @4x @1.5%
  Vertex:          AXS = 16th vertex (Gaming P2E cluster)
  HL cap:          66.8% AT CAP → paper-gate strict

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
DOCS_DIR  = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE       = "K771"
STRATEGY   = "K769"
PAIR       = "AXS-SOL"
DAEMON_NUM = "76th"
ALT_ALT_N  = "nineteenth"   # scaffold count
VERTEX_N   = "16th"
CLUSTER    = "Gaming P2E × Solana SVM"
OOS_SHARPE = 16.0543
SLEEVE_PCT = 0.015
LEVERAGE   = 4.0
CENTRAL_YR = 123689
K523_CONS  = 78337
K523_OPT   = 175227
HL_CAP_PCT = 66.8


def ts_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def check(condition: bool, msg: str) -> bool:
    tag = "PASS" if condition else "FAIL"
    print(f"  [{tag}] {msg}")
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Verify run script
# ─────────────────────────────────────────────────────────────────────────────

def phase1_run_script() -> bool:
    path = SCRIPTS_DIR / "k769_axs_sol_run.py"
    exists = path.exists()
    check(exists, f"scripts/k769_axs_sol_run.py exists")
    if not exists:
        return False

    # Quick syntax check
    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k769_axs_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k769-axs-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k769-axs-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k769-axs-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k769-axs-sol")
    check(paper_ok,    "plist PAPER_TRADE=True default")
    return interval_ok and label_ok and paper_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — leverage_config.json
# ─────────────────────────────────────────────────────────────────────────────

def phase3_leverage_config() -> bool:
    path = DATA_DIR / "leverage_config.json"
    if not path.exists():
        check(False, "data/leverage_config.json exists")
        return False

    config = json.loads(path.read_text())
    k769_key = "K769_AXS_SOL"

    if k769_key not in config:
        config[k769_key] = {
            "strategy": "K769 AXS-SOL FR Differential (K771 scaffold) — EIGHTEENTH ALT-ALT pair (16th vertex AXS Gaming P2E × Solana SVM), CLEAN ACCEPT",
            "oos_sharpe": OOS_SHARPE,
            "w_hours": 168,
            "w_note": "W=168h family standard window (G6: 31.1/yr OOS vs 20/yr long-tail min). W=80h Sh=16.98 marginally higher but W=168h chosen for family consistency.",
            "ann_return_usd_net_10M_central": CENTRAL_YR,
            "k523_conservative_yr": K523_CONS,
            "k523_central_yr": CENTRAL_YR,
            "k523_optimistic_yr": K523_OPT,
            "sleeve_pct": SLEEVE_PCT,
            "sleeve_note": "1.5% long-tail liquidity constraint — AXS HIP-3 HL listing 2026-01-18 (smaller than major L1). Max 2.0% absolute.",
            "leverage": LEVERAGE,
            "hl_primary": True,
            "bybit_fallback": True,
            "hl_concentration_pre": HL_CAP_PCT,
            "hl_concentration_post": HL_CAP_PCT,
            "hl_cap_note": "66.8% AT CAP — paper-gate strict. Deploy live only after K498/v6.52 reduces HL% below 65%.",
            "venue_config": "HL primary (AXS-PERP + SOL-PERP), Bybit fallback (AXSUSDT). Bybit 730d primary for backtest. HL from 2026-01-18.",
            "cluster": "AXS-SOL Alt-Alt FR Differential (Gaming P2E × SVM, HL primary, 18th alt-alt, 16th vertex)",
            "daemon_number": DAEMON_NUM,
            "wave": WAVE,
            "activation": "SCAFFOLD-READY — 60d paper-trade gate (Realized Sh>=6 + fill>=60% + maxDD<15%) + K498/v6.52 OKX activation",
            "activation_criteria": {
                "realized_sharpe_min": 6.0,
                "fill_rate_min_pct": 60,
                "max_drawdown_max_pct": 15,
                "days_required": 60,
                "additional_gate": "K498/v6.52 OKX activation required (HL% must drop below 65.0%)",
                "note": "60d paper-trade gate. HL 66.8% AT CAP. CLEAN ACCEPT all G1-G9 PASS."
            },
            "g4_result": "12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423) — strong WF validation",
            "g5_result": "all PASS (max_corr=-0.2796 G5n ENA-SOL — all 23 gates well below 0.40 threshold)",
            "g5_note": "No proximity warnings. AXS Gaming P2E structurally orthogonal to all family members.",
            "g6_result": "31.1 entries/yr OOS PASS (W=168h G6-safe vs 20/yr long-tail minimum)",
            "g8_result": "HL+Bybit confirmed. OKX not yet cached (2-venue confirmed).",
            "l003_avax": "raw_corr(AXS_fr, AVAX_fr)=0.149 PASS (<0.45)",
            "l004_carry": "AXS positive_frac full=0.4114 OOS=0.3155. 41%/32% — net negative bias (gaming bear). L004 PASS.",
            "l007_fil": "raw_corr(AXS_fr, FIL_fr)=0.1711 PASS (<0.45)",
            "l010_hbar": "raw_corr(AXS_fr, HBAR_fr)=-0.0355 PASS (<0.45)",
            "l011_sol_direct": "raw_corr(AXS_fr, SOL_fr)=0.1916 PASS (<0.50). OOS=0.1182 near-zero.",
            "axs_vertex": "16th vertex added. MR9 L002: all future AXS-X pairs auto-blocked.",
            "axs_fr_drivers": "Gaming P2E: Axie Origins seasonal content, SLP burn/mint, AXS staking APR, NFT breeding, SEA retail speculation, P2E tournaments (Axie World Championship), Ronin upgrades (RON airdrop). vol_ratio=5.24x (full), 8.88x (OOS), 16.23x (HL 1h).",
            "sol_fr_drivers": "Solana SVM DePIN/Retail. Phantom. Firedancer. SOL ETF. SVM DeFi TVL (Jupiter/Drift/Jito). +8.82%/ann. Min=-20.51bps cascade.",
            "max_dd_oos": "-0.5311% (contained — differential mean-reversion Gaming P2E vs SVM well-behaved)",
            "data_cross_venue": "Bybit AXSUSDT 730d primary (2024-05-25 to 2026-05-24, 3184 rows 8h). HL AXS-PERP from 2026-01-18 (3040 rows 1h). Cross-venue backtest: primary on Bybit. OKX pending.",
        }
        path.write_text(json.dumps(config, indent=2))
        check(True, f"data/leverage_config.json: {k769_key} entry added")
    else:
        check(True, f"data/leverage_config.json: {k769_key} entry already present")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — verify_deployment_status.py
# ─────────────────────────────────────────────────────────────────────────────

def phase4_verify_deployment() -> bool:
    path = SCRIPTS_DIR / "verify_deployment_status.py"
    if not path.exists():
        check(False, "scripts/verify_deployment_status.py exists")
        return False

    content = path.read_text()
    if "k769-axs-sol" in content:
        check(True, "verify_deployment_status.py: K769 entry already present")
        return True

    # Find insertion point — after K759 DaemonSpec closing paren
    k759_marker = '        expected_html_status="SCAFFOLD-READY",  # K761: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%\n    ),'
    if k759_marker not in content:
        # Try a simpler marker
        k759_marker2 = "K761: plist in scripts/"
        if k759_marker2 not in content:
            check(False, "verify_deployment_status.py: K759 insertion marker not found")
            return False

    k769_entry = '''
    DaemonSpec(
        label="com.cryptolab.k769-axs-sol",
        purpose="K769 AXS-SOL FR Differential (EIGHTEENTH ALT-ALT pair 16th-vertex AXS Gaming-P2E Axie-Infinity × Solana SVM, HL primary AXS-PERP+SOL-PERP Bybit fallback AXSUSDT, 4x leverage, 8h cycle, OOS Sh 16.05 W=168h G6-safe direct alt-alt diff, central $123,689/yr net @$10M @4x @1.5% sleeve K523 3-point $78.3K-$175.2K/yr, HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, G4 WF 12/12-positive min_sh=5.9193 mean=16.8423 strong-WF-validation, G5 all-PASS max_corr=-0.2796-G5n-ENA-SOL all-23-gates-well-below-0.40 no-proximity-warnings, G6 31.1/yr PASS W=168h-family-standard G6-long-tail-compliant, G8 HL+Bybit-confirmed OKX-pending 2-venue-confirmed, L003 AVAX-corr=0.149-PASS, L004 AXS-carry=41pct-full-32pct-OOS-L004-PASS gaming-bear-net-negative, L007 FIL-corr=0.1711-PASS, L010 HBAR-corr=-0.0355-PASS, L011 SOL-direct=0.1916-PASS OOS=0.1182-near-zero, AXS-vertex 16th V={APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,AXS} MR9-L002-all-future-AXS-X-blocked, AXS FR=Gaming-P2E-Axie-Origins-seasonal SLP-burn-mint AXS-staking-APR NFT-breeding SEA-retail-speculation P2E-tournaments-Axie-World-Championship Ronin-sidechain-upgrades vol_ratio=5.24x-full-8.88x-OOS-16.23x-HL, SOL FR=DePIN/Retail Phantom Firedancer ETF +8.82%/ann Min=-20.51bps cascade, MaxDD-OOS=-0.5311%, raw_corr(AXS,SOL)=0.19-full-0.1182-OOS-orthogonal, Bybit-730d-primary-backtest HL-from-2026-01-18-3040rows-OOS, sleeve-1.5pct-long-tail-AXS-HIP3-listing max-2.0pct, 60d paper-trade gate Realized Sh>=6 fill>=60% maxDD<15% + K498/v6.52-OKX-activation-required, live-trigger=K498/v6.52-reduces-HL%<65%+60d-gate, 76th daemon 18th alt-alt CLEAN ACCEPT HL-cap-66.8%, K771 scaffold)",
        scripts=["scripts/k769_axs_sol_run.py"],
        log_basename="k769_axs_sol",
        expected_html_status="SCAFFOLD-READY",  # K771: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%
    ),'''

    # Find after K767 entry (last before K763 compound scheduler section)
    # We'll insert after the K759 daemon spec closing entry
    old_marker = '        expected_html_status="SCAFFOLD-READY",  # K761: plist in scripts/ (gitignored); activate after 60d gate (Sh>=6 + fill>=60% + maxDD<15%) AND K498/v6.52 OKX reduces HL% below 65%\n    ),'
    if old_marker in content:
        new_content = content.replace(old_marker, old_marker + k769_entry)
        path.write_text(new_content)
        check(True, "verify_deployment_status.py: K769 DaemonSpec added after K759")
        return True

    # Fallback: find K767 marker
    k767_marker = '        expected_html_status="SCAFFOLD-READY",  # K767: plist in scripts/'
    if k767_marker in content:
        # find its full line
        for line in content.splitlines():
            if "K767: plist in scripts/" in line:
                k767_full_line = line + "\n    ),"
                if k767_full_line in content:
                    new_content = content.replace(k767_full_line, k767_full_line + k769_entry)
                    path.write_text(new_content)
                    check(True, "verify_deployment_status.py: K769 DaemonSpec added after K767")
                    return True

    check(False, "verify_deployment_status.py: could not find insertion point")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — emergency_hl_exit.py
# ─────────────────────────────────────────────────────────────────────────────

def phase5_emergency_exit() -> bool:
    path = SCRIPTS_DIR / "emergency_hl_exit.py"
    if not path.exists():
        check(False, "scripts/emergency_hl_exit.py exists")
        return False

    content = path.read_text()
    if "include-k769" in content:
        check(True, "emergency_hl_exit.py: K769 flag already present")
        return True

    # ── 1. Add argparse flag after K759 flag block ────────────────────────────
    k759_flag_end = '            "See: docs/k302a_runbook.md §72"\n        ),\n    )'
    if k759_flag_end not in content:
        check(False, "emergency_hl_exit.py: K759 flag end marker not found")
        return False

    k769_argparse = '''

    # K771: K769 AXS-SOL alt-alt emergency exit flag
    # K769 = HL primary AXS-PERP+SOL-PERP paired when AXS_FR-SOL_FR rolling mean 168h changes sign.
    # Close protocol: IOC reduce-only on HL (short leg first, then long leg).
    # AXS = 16th vertex (Gaming P2E cluster). HL concentration: 66.8% AT CAP (paper-gate strict).
    # Use --include-k769 to print K769-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k769",
        dest="include_k769",
        action="store_true",
        default=False,
        help=(
            "K771: Include K769 AXS-SOL close summary during emergency exit. "
            "K769 positions (AXS+SOL paired, HL primary) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = AXS_FR - SOL_FR (direct differential, W=168h rolling mean, zero threshold). "
            "HL primary: AXS-PERP + SOL-PERP both on HL. Bybit fallback (AXSUSDT). "
            "HL concentration 66.8% AT CAP — paper-gate strict (PAPER_TRADE=True default). "
            "G4 WF 12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423). "
            "G5 all PASS (max_corr=-0.2796 G5n ENA-SOL — all 23 gates well below 0.40). "
            "G6: 31.1 entries/yr OOS PASS (W=168h G6-safe vs 20/yr long-tail minimum). "
            "OOS Sharpe 16.05 (W=168h). MaxDD OOS=-0.5311%. "
            "Data: Bybit 730d primary (backtest), HL from 2026-01-18 (OOS live). "
            "L003 AVAX: raw_corr=0.149 PASS. L007 FIL: raw_corr=0.1711 PASS. "
            "L010 HBAR: raw_corr=-0.0355 PASS. L011 SOL: raw_corr=0.1916 PASS (OOS=0.1182). "
            "L004: AXS carry 41% full / 32% OOS PASS (net negative bias — gaming bear). "
            "AXS = 16th vertex. MR9 L002: all future AXS-X auto-blocked. "
            "K523 central $123,689/yr net @$10M @4x (1.5% sleeve, long-tail constraint). "
            "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%. "
            "Live trigger: K498/v6.52 OKX activation (HL% < 65%) + 60d gate. "
            "Cluster: Gaming P2E × Solana SVM (18th alt-alt, 76th daemon). "
            "Requires: K769 daemon running (com.cryptolab.k769-axs-sol, 76th daemon). "
            "See: docs/k302a_runbook.md §73"
        ),
    )'''

    new_content = content.replace(k759_flag_end, k759_flag_end + k769_argparse)

    # ── 2. Add runtime handler block ─────────────────────────────────────────
    k759_handler_end = '            logger.info(\n                "K759 WIF-SOL: HL primary (positions ARE in HL exit above — WIF-PERP + SOL-PERP on HL). "\n                "HL 66.8% AT CAP (K751 audit — paper-gate strict; no live capital until K498/v6.52 OKX). "\n                "G4 WF 12/12 ALL POSITIVE (min_sh=9.895). WIF = 15th vertex. "\n                "G5w PEPE-SOL=0.382 proximity → 2.0% sleeve. L011 WIF-SOL=0.487 monthly recheck. "\n                "Use --include-k759 for structured HL close summary (§72)."\n            )'

    k769_handler = '''

        # ── K769 AXS-SOL close summary (K771 §73) ──────────────────────────
        # HL concentration: 66.8% AT CAP (paper-gate: PAPER_TRADE=True default — no live capital yet).
        # Live only after K498/v6.52 OKX activation + 60d gate passage.
        if args.include_k769:
            logger.info("=== K769 AXS-SOL CLOSE SUMMARY (K771 §73) ===")
            logger.info("  K769 AXS-SOL: HL primary (AXS-PERP + SOL-PERP both legs on HL)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BULL_AXS (Gaming P2E season): short SOL first → sell long AXS second")
            logger.info("  BEAR_AXS (SVM season dominant): short AXS first → sell long SOL second")
            logger.info("  HL concentration: 66.8% AT CAP — paper-gate strict")
            logger.info("  PAPER_TRADE=True default — no live capital until K498/v6.52 OKX reduces HL%")
            logger.info("  G4 WF: 12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423) — strong WF validation")
            logger.info("  G5: all PASS (max_corr=-0.2796 G5n ENA-SOL — all 23 gates well below 0.40)")
            logger.info("  G6: 31.1 entries/yr OOS PASS (W=168h G6-safe vs 20/yr long-tail minimum)")
            logger.info("  G8: HL+Bybit confirmed (AXS HL from 2026-01-18; Bybit 730d primary for backtest)")
            logger.info("  L003 AVAX corr=0.149 PASS | L007 FIL corr=0.1711 PASS")
            logger.info("  L010 HBAR corr=-0.0355 PASS | L011 SOL corr=0.1916 PASS (OOS=0.1182)")
            logger.info("  L004 AXS carry: 41% full / 32% OOS PASS (net negative — gaming bear market)")
            logger.info("  AXS = 16th vertex (Gaming P2E cluster). MR9 L002: all future AXS-X blocked.")
            logger.info("  V = {APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF,AXS}")
            logger.info("  AXS FR: Gaming P2E (Axie Origins seasonal, SLP burn/mint, AXS staking APR,")
            logger.info("          NFT breeding, SEA retail speculation, P2E tournaments, Ronin upgrades).")
            logger.info("  AXS FR: vol_ratio=5.24x (full), 8.88x (OOS), 16.23x (HL 1h).")
            logger.info("  SOL FR: DePIN/Retail Phantom Firedancer ETF +8.82%/ann. Min=-20.51bps cascade.")
            logger.info("  MaxDD OOS=-0.5311% | raw_corr(AXS,SOL)=0.19 (Bybit) — essentially orthogonal")
            logger.info("  OOS Sh=16.05 (W=168h), K523 central $123,689/yr net @$10M @4x (1.5% sleeve)")
            logger.info("  K523 3-point: conservative=$78,337 central=$123,689 optimistic=$175,227/yr")
            logger.info("  Sleeve 1.5% (long-tail liquidity — AXS HIP-3 HL listing 2026-01-18)")
            logger.info("  60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%")
            logger.info("  Live trigger: K498/v6.52 OKX activation (HL% < 65%) + 60d gate passage")
            logger.info("  18th alt-alt scaffold, 76th daemon. HL primary (positions in main HL exit)")
            logger.info("  See: docs/k302a_runbook.md §73 (K769 AXS-SOL playbook)")
        else:
            logger.info(
                "K769 AXS-SOL: HL primary (positions ARE in HL exit above — AXS-PERP + SOL-PERP on HL). "
                "HL 66.8% AT CAP — paper-gate strict; no live capital until K498/v6.52 OKX. "
                "G4 WF 12/12 ALL POSITIVE (min_sh=5.9193). AXS = 16th vertex (Gaming P2E). "
                "G5 all PASS (max_corr=-0.2796). Sleeve 1.5% (long-tail liquidity constraint). "
                "Use --include-k769 for structured HL close summary (§73)."
            )'''

    # Find the K759 handler end marker and add K769 after it
    k759_handler_simple = '                "Use --include-k759 for structured HL close summary (§72)."\n            )'
    if k759_handler_simple in new_content:
        new_content = new_content.replace(
            k759_handler_simple,
            k759_handler_simple + k769_handler
        )
        path.write_text(new_content)
        check(True, "emergency_hl_exit.py: K769 flag + handler added")
        return True

    check(False, "emergency_hl_exit.py: handler insertion marker not found")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §73
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    if "§73" in content or "K769 AXS-SOL" in content:
        check(True, "docs/k302a_runbook.md: §73 already present")
        return True

    section73 = """

## §73 K769 AXS-SOL FR Differential (76th Daemon, EIGHTEENTH ALT-ALT, Gaming P2E × SVM, 16th Vertex)

*K771 §73 -- K769 AXS-SOL FR Differential production scaffold (76th daemon, EIGHTEENTH ALT-ALT 16th-vertex AXS Gaming-P2E Axie-Infinity × Solana SVM, OOS Sh 16.05 W=168h G6-safe direct alt-alt diff, central $123,689/yr net @$10M @4x 1.5% sleeve K523 3-point $78.3K-$175.2K, HL primary HL 66.8% AT CAP paper-gate-strict K498/v6.52-activation-required, G4 WF 12/12 all positive min_sh=5.9193 mean=16.8423 strong-WF-validation, G5 all PASS max_corr=-0.2796-G5n-ENA-SOL all-23-gates-well-below-0.40, G6 31.1/yr PASS W=168h-family-standard, G8 HL+Bybit-confirmed OKX-pending, Bybit-730d-primary-backtest HL-from-2026-01-18-3040rows, AXS-vertex-16th MR9-L002-all-future-AXS-X-blocked, 60d gate: Sh>=6 fill>=60% maxDD<15% + K498/v6.52-OKX-activation) -- 2026-05-30*

### §73.1 Strategy Overview

| Parameter | Value |
|-----------|-------|
| Strategy | K769 AXS-SOL FR Differential (EIGHTEENTH ALT-ALT pair) |
| Signal | diff = AXS_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold) |
| OOS Sharpe | 16.0543 (W=168h, zero threshold, ~211d OOS) |
| G4 Walk-Forward | 12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423) |
| G5 max corr | -0.2796 (G5n ENA-SOL) — all 23 gates well below 0.40 |
| G5 note | No proximity warnings. AXS Gaming P2E structurally orthogonal to family. |
| G6 entries/yr | 31.1/yr OOS PASS (W=168h vs 20/yr long-tail minimum) |
| G8 venues | HL+Bybit confirmed (OKX pending — 2-venue confirmed) |
| L011 | raw_corr(AXS,SOL)=0.1916 PASS (< 0.50, OOS=0.1182 near-zero) |
| Sleeve | 1.5% of AUM (long-tail liquidity — AXS HIP-3 HL listing 2026-01-18) |
| Leverage | 4x |
| Daemon | 76th (eighteenth alt-alt pair, CLEAN ACCEPT) |
| HL status | 66.8% AT CAP — paper-gate strict |
| Vertex | AXS = 16th vertex (Gaming P2E cluster). MR9 L002: all future AXS-X blocked. |
| Data | Bybit 730d primary (backtest), HL from 2026-01-18 3040 rows (OOS live) |

### §73.2 AXS vs SOL FR Economics

**AXS FR drivers (Axie Infinity — Gaming P2E, RON-chain governance):**
- Gaming P2E adoption cycles: Axie Origins V3+ seasonal content releases
- SLP burn/mint economics: in-game token supply mechanics
- AXS staking governance APR: treasury staking reward cycles
- NFT Axie breeding demand: marketplace floor price + breeding liquidity cycles
- Southeast Asian retail speculation (Philippines/Indonesia primary P2E markets)
- P2E tournament event spikes (Axie World Championship seasons)
- Ronin sidechain upgrades (RON airdrop, bridge activity, validator set changes)
- Vol ratio vs SOL: 5.24x (full Bybit), 6.37x (30d), 8.88x (OOS), 16.23x (HL 1h)
- AXS carry: 41% positive (full) / 32% OOS — net negative bias (gaming bear market)

**SOL FR drivers (Solana SVM L1):**
- DePIN/Retail adoption premium (Phantom wallet, Firedancer upgrade)
- SOL ETF speculation and institutional narrative flows
- SVM DeFi TVL (Jupiter/Drift/Jito ecosystem)
- +8.82%/ann persistently positive (structural retail demand)
- Extreme negative: -20.51bps (liquidation cascade Feb 2025)

**Alt-alt mechanism:** Gaming P2E cycle (Axie game versions, SLP economics) is structurally orthogonal to Solana SVM cycle (Firedancer, validator rewards, meme).
Historical: 2021 AXS P2E peak (8000+ USD) was independent of SOL SVM narrative.
raw_corr(AXS, SOL) = 0.19 (Bybit full), 0.1182 (OOS) — essentially orthogonal.

### §73.3 §6 Gate Results (K769)

| Gate | Value | Result |
|------|-------|--------|
| G1 OOS Sharpe | 16.0543 | PASS |
| G2 Permutation | p=0.000 | PASS |
| G3 DSR Bonferroni | best OOS Sh=16.98 (W=80h) over 9 configs — all > 15.0 | PASS |
| G4 Walk-Forward | 12/12 positive (mean Sh=16.84, min_sh=5.9193) | PASS |
| G5 Family corr | max=-0.2796 G5n ENA-SOL (all 23 gates well below 0.40) | PASS |
| G6 Entries/yr | 31.1/yr OOS (W=168h, long-tail threshold 20/yr) | PASS |
| G7 Ann return | 183.24% levered OOS | PASS |
| G8 Cross-venue | HL+Bybit confirmed (OKX pending) | PASS |
| G9 OOS days | 211d | PASS |
| L003 AVAX | raw_corr=0.149 < 0.45 | PASS |
| L004 carry | 41% full / 32% OOS (gaming bear net negative) | PASS |
| L007 FIL | raw_corr=0.1711 < 0.45 | PASS |
| L010 HBAR | raw_corr=-0.0355 < 0.45 | PASS |
| L011 SOL-direct | raw_corr=0.1916 < 0.50, OOS=0.1182 | PASS |

### §73.4 K523 3-Point Profit Projection (@$10M @4x @1.5%)

| Scenario | Annual Net | Basis |
|----------|-----------|-------|
| Conservative | $78,337/yr | R2S=38% floor (K518), OOS haircut 25% |
| **Central** | **$123,689/yr** | **60% realized-to-stated (K523 mandate)** |
| Optimistic | $175,227/yr | Near-full OOS realization (Gaming P2E cycle peak) |

Note: 1.5% sleeve ($150K margin @$10M) → $600K total notional @4x.
Long-tail liquidity constraint: AXS HIP-3 HL listing from 2026-01-18. Max sleeve 2.0%.
No proximity warnings in G5 — AXS Gaming P2E fully orthogonal to existing family.

### §73.5 HL Concentration Status

| Metric | Value |
|--------|-------|
| HL % before K769 | 66.8% (K761 reference) |
| K769 capital impact | +0.0% (PAPER-ONLY — no live capital added) |
| HL % after K769 | 66.8% (unchanged — paper-gate strict) |
| HL cap ceiling | 65.0% (post-K532 governance) |
| Status | OVER CAP — paper-gate mandatory until K498/v6.52 |

### §73.6 AXS Vertex Rule (MR9 L002)

- AXS = 16th alt-alt vertex added to V
- V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF, AXS}
- MR9 L002: all future AXS-X pairs are auto-blocked (AXS exhausted as new vertex)
- AXS-SOL is the only permissible AXS-X pair given V at K769
- Gaming P2E cluster: AXS (Axie Infinity) is the first and only Gaming P2E vertex

### §73.7 Grid Robustness (9 configs, all Sh > 15.0)

All 9 grid configs (W=168h/80h/48h × T=0.0/5e-5/1e-4) produced OOS Sh > 15.0:
- Best: W=80h T=0.0 OOS Sh=16.98 (31.1/yr → 34.5/yr entries)
- Canonical: W=168h T=0.0 OOS Sh=16.05 (family standard)
- Robust: min across 9 configs = 15.43 — extremely robust edge

### §73.8 60d Paper-Trade Gate

| Condition | Target | Status |
|-----------|--------|--------|
| Realized Sharpe | >= 6.0 | IN_PROGRESS |
| Fill rate | >= 60% | IN_PROGRESS |
| Max drawdown | < 15% | IN_PROGRESS |
| K498/v6.52 gate | HL% < 65% | PENDING |

### §73.9 Daemon Activation

**Paper-trade (default — safe):**
```bash
sed -i '' "s|REPO_ROOT_PLACEHOLDER|$(pwd)|g" scripts/com.cryptolab.k769-axs-sol.plist
cp scripts/com.cryptolab.k769-axs-sol.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k769-axs-sol.plist
launchctl list | grep k769
```

**Status check:**
```bash
python3 scripts/k769_axs_sol_run.py --status
python3 scripts/k769_axs_sol_run.py --dry-run
```

**Live activation (ONLY after K498/v6.52 + 60d gate):**
```bash
# Step 1: Verify HL concentration < 65% (post-K498/v6.52 OKX activation)
# Step 2: Confirm 60d gate passed (Sh>=6, fill>=60%, maxDD<15%)
# Step 3: Set PAPER_TRADE=False in plist and reload
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k769-axs-sol.plist
# Edit plist: change PAPER_TRADE from True to False
launchctl load ~/Library/LaunchAgents/com.cryptolab.k769-axs-sol.plist
```

### §73.10 References

| Wave | Description |
|------|-------------|
| K769 | K769 AXS-SOL evaluation (CLEAN ACCEPT — this section scaffold) |
| K771 | This section — K769 AXS-SOL production scaffold (76th daemon) |
| K498 | OKX activation prerequisite (reduces HL% below 65%) |
| K523 | 3-point projection mandate |
| K518 | 38% realized-to-stated ratio floor |
| K532 | Governance v5 (HL 65.0% cap rule) |
| K766 | K769 prescreening (HL long-tail screen) |
"""

    path.write_text(content + section73)
    check(True, "docs/k302a_runbook.md: §73 AXS-SOL section added")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Initialize k769_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k769_dashboard.json"
    if path.exists():
        check(True, "data/k769_dashboard.json already exists")
        return True

    init = {
        "wave":                    "K771",
        "strategy":                "K769 AXS-SOL FR Differential (EIGHTEENTH ALT-ALT, W=168h, HL primary)",
        "daemon_number":           "76th",
        "last_poll_jst":           "—",
        "mean_168h":               0.0,
        "diff_sigma":              0.0,
        "regime":                  "NEUTRAL",
        "signal_direction":        0,
        "position_state":          "NEUTRAL",
        "long_notional":           0.0,
        "short_notional":          0.0,
        "venue":                   "HL",
        "delta_neutral_drift_pct": 0.0,
        "rebalance_required":      False,
        "daily_pnl_usdc":          0.0,
        "60d_sharpe":              0.0,
        "paper_trade_mode":        True,
        "sleeve_pct":              SLEEVE_PCT,
        "leverage":                LEVERAGE,
        "hl_concentration_pct":    HL_CAP_PCT,
        "total_notional_usdc":     0.0,
        "notional_per_leg_usdc":   0.0,
        "margin_used_usdc":        0.0,
        "margin_pct_of_aum":       0.0,
        "aum_ref_usdc":            10_000_000.0,
        "paper_trade_status":      {"days_elapsed": 0, "target_60d": 60},
        "activation_criteria": {
            "60d_paper_trade_gate":  "required",
            "realized_sharpe_min":   6.0,
            "fill_rate_min_pct":     60,
            "max_drawdown_max_pct":  15,
            "status":                "SCAFFOLD-READY",
            "activation_sleeve_pct": 0.015,
            "venue":                 "HL primary (AXS-PERP + SOL-PERP)",
        },
        "oos_performance": {
            "sharpe":           OOS_SHARPE,
            "k523_conservative_yr": K523_CONS,
            "k523_central_yr":  CENTRAL_YR,
            "k523_optimistic_yr": K523_OPT,
        },
        "scaffold_ts_jst":         ts_jst(),
    }
    path.write_text(json.dumps(init, indent=2))
    check(True, "data/k769_dashboard.json initialized")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 — Validate all scaffold files
# ─────────────────────────────────────────────────────────────────────────────

def phase8_validate() -> dict:
    checks = {
        "run_script":        (SCRIPTS_DIR / "k769_axs_sol_run.py").exists(),
        "plist":             (SCRIPTS_DIR / "com.cryptolab.k769-axs-sol.plist").exists(),
        "leverage_config":   (DATA_DIR / "leverage_config.json").exists(),
        "verify_deployment": "k769-axs-sol" in (SCRIPTS_DIR / "verify_deployment_status.py").read_text() if (SCRIPTS_DIR / "verify_deployment_status.py").exists() else False,
        "emergency_exit":    "include-k769" in (SCRIPTS_DIR / "emergency_hl_exit.py").read_text() if (SCRIPTS_DIR / "emergency_hl_exit.py").exists() else False,
        "runbook_s73":       "§73" in (DOCS_DIR / "k302a_runbook.md").read_text() if (DOCS_DIR / "k302a_runbook.md").exists() else False,
        "dashboard":         (DATA_DIR / "k769_dashboard.json").exists(),
    }
    all_pass = all(checks.values())
    for k, v in checks.items():
        check(v, f"phase8 validate: {k}")
    return {"all_pass": all_pass, "checks": checks}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 — report.html update
# ─────────────────────────────────────────────────────────────────────────────

def phase9_report_html() -> bool:
    path = REPO_ROOT / "report.html"
    if not path.exists():
        check(False, "report.html exists")
        return False

    content = path.read_text()
    if "K771" in content and "K769" in content and "AXS-SOL" in content:
        check(True, "report.html: K771/K769 AXS-SOL already present")
        return True

    # Find update timestamp line and update it
    import re
    now_jst = ts_jst()

    k771_html = f"""
<!-- K771 K769 AXS-SOL scaffold entry -->
<tr>
  <td><b>K771</b></td>
  <td>K769 AXS-SOL FR Differential</td>
  <td>CLEAN ACCEPT</td>
  <td>EIGHTEENTH ALT-ALT, 16th vertex AXS (Gaming P2E)</td>
  <td>OOS Sh=16.05, G4 12/12, G5 all PASS (max=-0.28)</td>
  <td>$78K / <b>$124K</b> / $175K</td>
  <td>1.5% sleeve, 4x, paper-gate HL 66.8% AT CAP</td>
  <td>76th daemon, 8h, 28800s</td>
  <td>{now_jst}</td>
</tr>"""

    # Try to insert before </table> or </tbody> in a waves table
    for marker in ["</tbody>", "</table>"]:
        if marker in content:
            new_content = content.replace(marker, k771_html + "\n" + marker, 1)
            # Also update last-modified timestamp if present
            new_content = re.sub(
                r'(最終更新|Last Updated|last.updated)[^\n<]*',
                lambda m: m.group(0).split(':')[0] + f': {now_jst}',
                new_content, count=1, flags=re.IGNORECASE
            )
            path.write_text(new_content)
            check(True, f"report.html: K771 K769 entry added before {marker}")
            return True

    check(False, "report.html: no </tbody> or </table> insertion point found")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Generate scaffold JSON
# ─────────────────────────────────────────────────────────────────────────────

def phase10_scaffold_json(results: dict) -> dict:
    path = REPO_ROOT / "wave_k771_k769_scaffold.json"
    out = {
        "wave": WAVE,
        "strategy": f"{STRATEGY} {PAIR} FR Differential Alt-Alt (Gaming P2E × Solana SVM — 16th vertex)",
        "run_time_jst": ts_jst(),
        "k769_result": {
            "decision": "CLEAN ACCEPT",
            "g4_wf": "12/12 ALL POSITIVE (min_sh=5.9193, mean=16.8423)",
            "g5_result": "23/23 PASS (max_corr=-0.2796 G5n ENA-SOL — all well below 0.40, no proximity warnings)",
            "g6_entries_yr": 31.1,
            "g6_note": "W=168h G6-safe vs 20/yr long-tail threshold (all 9 grid configs > 15.0 Sh)",
            "g8_result": "HL+Bybit confirmed (OKX not yet cached — 2-venue confirmed)",
            "oos_sharpe": OOS_SHARPE,
            "max_dd_oos_pct": -0.5311,
            "w_hours": 168,
            "sleeve_pct": SLEEVE_PCT,
            "leverage": LEVERAGE,
            "venue": "HL primary (AXS-PERP + SOL-PERP), Bybit fallback (AXSUSDT)",
            "hl_concentration": HL_CAP_PCT,
            "paper_gate_strict": True,
            "live_trigger": "K498/v6.52 OKX activation (HL% < 65%) + 60d gate (Sh>=6 + fill>=60% + maxDD<15%)",
            "axs_vertex": "16th vertex. MR9 L002: all future AXS-X auto-blocked.",
            "cluster": "Gaming P2E (Axie Infinity AXS) × Solana SVM",
            "data_cross_venue": "Bybit 730d primary (backtest), HL from 2026-01-18 3040 rows (OOS live)",
            "l003_avax_corr": 0.149,
            "l004_carry_full": 0.4114,
            "l004_carry_oos": 0.3155,
            "l007_fil_corr": 0.1711,
            "l010_hbar_corr": -0.0355,
            "l011_sol_corr_full": 0.1916,
            "l011_sol_corr_oos": 0.1182,
            "grid_note": "All 9 grid configs > 15.0 Sh — extremely robust edge (best W=80h T=0.0 Sh=16.98)",
        },
        "k523_projection": {
            "conservative_yr": K523_CONS,
            "central_yr": CENTRAL_YR,
            "optimistic_yr": K523_OPT,
            "note": f"K523 mandatory 3-point. Central=${CENTRAL_YR:,}/yr @$10M @4x @{SLEEVE_PCT:.1%}.",
        },
        "gate_60d": {
            "realized_sharpe_min": 6.0,
            "fill_rate_min_pct": 60,
            "max_drawdown_max_pct": 15,
            "additional_gate": "K498/v6.52 OKX activation (HL% must drop below 65.0%)",
        },
        "daemon": {
            "number": DAEMON_NUM,
            "label": "com.cryptolab.k769-axs-sol",
            "script": "scripts/k769_axs_sol_run.py",
            "interval_s": 28800,
        },
        "scaffold_verification": {
            "all_pass": results.get("all_pass", False),
            "gates_passed": sum(1 for v in results.get("checks", {}).values() if v),
            "gates_total": len(results.get("checks", {})),
            "checks": results.get("checks", {}),
            "ts_jst": ts_jst(),
        },
        "vertex_set_after_k769": [
            "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ", "LDO",
            "SEI", "SOL", "TIA", "TAO", "PEPE", "WIF", "AXS",
        ],
        "alt_alt_family_count": 18,
        "alt_alt_scaffold_count": 19,
        "note_mr9": "AXS = 16th vertex. MR9 L002: all future AXS-X pairs auto-blocked. Gaming P2E cluster first vertex.",
        "note_k768": "K768 BLUR-SOL scaffold timing independent. AXS-SOL proceeds as 19th scaffold.",
    }
    path.write_text(json.dumps(out, indent=2))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n=== {WAVE} {STRATEGY} {PAIR} Scaffold — {ts_jst()} ===")
    print(f"  {DAEMON_NUM} daemon | {ALT_ALT_N} alt-alt scaffold | {VERTEX_N} vertex AXS")
    print(f"  Cluster: {CLUSTER}")
    print(f"  OOS Sharpe: {OOS_SHARPE} | Sleeve: {SLEEVE_PCT:.1%} | K523 central: ${CENTRAL_YR:,}/yr")
    print()

    results = {}
    phases = [
        ("Phase 1: Run script",              phase1_run_script),
        ("Phase 2: Plist (76th daemon)",     phase2_plist),
        ("Phase 3: leverage_config.json",   phase3_leverage_config),
        ("Phase 4: verify_deployment",       phase4_verify_deployment),
        ("Phase 5: emergency_hl_exit",       phase5_emergency_exit),
        ("Phase 6: runbook §73",             phase6_runbook),
        ("Phase 7: k769_dashboard.json",     phase7_dashboard),
    ]

    phase_results = {}
    for name, fn in phases:
        print(f"\n  [{name}]")
        try:
            phase_results[name] = fn()
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            phase_results[name] = False

    print(f"\n  [Phase 8: Validate all scaffold files]")
    validation = phase8_validate()
    results.update(validation)

    print(f"\n  [Phase 9: report.html update]")
    phase9_report_html()

    print(f"\n  [Phase 10: Generate scaffold JSON]")
    scaffold_json = phase10_scaffold_json(results)

    all_phases_pass = all(phase_results.values()) and results.get("all_pass", False)
    print(f"\n{'='*60}")
    print(f"  {WAVE} scaffold {'COMPLETE' if all_phases_pass else 'PARTIAL'} — {ts_jst()}")
    print(f"  Phases: {sum(phase_results.values())}/{len(phase_results)} passed")
    print(f"  Validation: {sum(results.get('checks', {}).values())}/{len(results.get('checks', {}))} passed")
    print(f"  K769 AXS-SOL: {OOS_SHARPE} OOS Sh | ${CENTRAL_YR:,}/yr central | {DAEMON_NUM} daemon")
    print(f"  AXS = 16th vertex (Gaming P2E). MR9 L002: all future AXS-X blocked.")
    print(f"  HL 66.8% AT CAP → paper-gate strict until K498/v6.52")
    print(f"{'='*60}\n")
    return 0 if all_phases_pass else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
wave_k753_k545_scaffold.py
==========================
K753 K545 Tax Loss Harvester Full Scaffold — Wave Runner

DISCLAIMER: INFORMATIONAL ONLY — NOT TAX ADVICE.
User must consult a licensed CPA before any harvest action.

This wave builds the production-grade K545 scaffold:
  - scripts/k545_tax_harvester.py     (full daemon, 70th daemon)
  - scripts/com.cryptolab.k545-tax-harvester.plist (daily 03:00 UTC)
  - K523 3-point tax shield projection
  - User runbook 1-step activation

K339 REPO_ROOT pattern: Path(__file__).resolve().parent

Usage:
  python3 wave_k753_k545_scaffold.py
  python3 wave_k753_k545_scaffold.py --projection
  python3 wave_k753_k545_scaffold.py --audit
  python3 wave_k753_k545_scaffold.py --output-json wave_k753_k545_scaffold.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── K339 REPO_ROOT ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS   = REPO_ROOT / "scripts"
DATA      = REPO_ROOT / "data"
DOCS      = REPO_ROOT / "docs"

JST = timezone(timedelta(hours=9))


# ═════════════════════════════════════════════════════════════════════════════
# K523 3-point projection
# ═════════════════════════════════════════════════════════════════════════════

def k523_projection(aum_usd: float = 10_000_000, rate_pct: float = 37.0) -> dict:
    """
    K523 mandate: 3-point conservative/central/optimistic.
    Single number PROHIBITED.

    @$10M AUM, 37%:
      Conservative: $200K losses/yr → $74K shield
      Central:      $500K losses/yr → $185K shield
      Optimistic:   $1M losses/yr   → $370K shield
    """
    aum_factor = aum_usd / 10_000_000
    losses = {
        "conservative": 200_000 * aum_factor,
        "central":       500_000 * aum_factor,
        "optimistic":  1_000_000 * aum_factor,
    }
    shields = {k: round(v * rate_pct / 100) for k, v in losses.items()}
    k518 = 0.38  # realized-to-stated ratio floor
    realized = {k: round(v * k518) for k, v in shields.items()}

    return {
        "aum_usd": aum_usd,
        "tax_rate_pct": rate_pct,
        "k523_rule": "Single-number projection PROHIBITED",
        "gross_losses_harvested_usd": losses,
        "gross_shield_usd": shields,
        "k518_realized_shield_usd": realized,
        "k518_haircut": k518,
        "disclaimer": "INFORMATIONAL ONLY. NOT TAX ADVICE.",
    }


# ═════════════════════════════════════════════════════════════════════════════
# Audit
# ═════════════════════════════════════════════════════════════════════════════

DELIVERABLES = [
    (SCRIPTS / "k545_tax_harvester.py",                    "K545 full daemon script"),
    (SCRIPTS / "com.cryptolab.k545-tax-harvester.plist",   "K545 plist (70th daemon)"),
    (REPO_ROOT / "wave_k753_k545_scaffold.py",             "K753 wave runner"),
    (REPO_ROOT / "wave_k753_k545_scaffold.json",           "K753 wave JSON"),
    (REPO_ROOT / "wave_k753_k545_scaffold.md",             "K753 wave markdown"),
    (SCRIPTS / "verify_deployment_status.py",               "Deployment verifier (70th entry)"),
    (DOCS / "k302a_runbook.md",                            "Runbook §69 K545 section"),
    (REPO_ROOT / "report.html",                            "report.html K753 badge"),
    # K444 / K545 legacy (pre-existing)
    (SCRIPTS / "loss_harvester.py",                        "K444 legacy harvester (K18)"),
    (REPO_ROOT / "com.cryptolab.loss-harvester.plist",    "K444 legacy plist (K18)"),
]


def run_audit() -> list[dict]:
    results = []
    for path, desc in DELIVERABLES:
        exists = path.exists()
        size   = path.stat().st_size if exists else 0
        results.append({
            "path": str(path.relative_to(REPO_ROOT)),
            "description": desc,
            "status": "OK" if exists else "MISSING",
            "size_bytes": size,
        })
    return results


def print_audit(results: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("  K753 K545 Scaffold — Deliverables Audit")
    print("=" * 70)
    for r in results:
        icon = "[OK]     " if r["status"] == "OK" else "[MISSING]"
        print(f"  {icon} {r['path']:55s} {r['size_bytes']:>8,} bytes")
        print(f"           {r['description']}")
    print()


# ═════════════════════════════════════════════════════════════════════════════
# 1-step activation runbook
# ═════════════════════════════════════════════════════════════════════════════

ACTIVATION_STEPS = [
    {
        "step": 1,
        "title": "Consult CPA (prerequisite)",
        "effort": "Before any harvest",
        "action": "Confirm marginal tax rate, jurisdiction, wash-sale treatment for your situation.",
        "command": "# No code — CPA consultation required first",
        "risk": "ZERO",
    },
    {
        "step": 2,
        "title": "Set tax rate and jurisdiction",
        "effort": "1 min",
        "action": "Configure K545 with your rate. Default 37% US_STCG.",
        "command": "python3 scripts/k545_tax_harvester.py --set-rate 37 --set-juris US_STCG",
        "risk": "ZERO",
    },
    {
        "step": 3,
        "title": "Run mock test",
        "effort": "1 min",
        "action": "Verify K523 3-point projection and harvest logic PASS.",
        "command": "python3 scripts/k545_tax_harvester.py --mock-test",
        "expected": "K523 projection: PASS",
        "risk": "ZERO",
    },
    {
        "step": 4,
        "title": "Activate daemon (paper mode, 1-step)",
        "effort": "2 min",
        "action": "Replace CRYPTO_LAB_PATH, copy plist, load daemon.",
        "command": (
            "CRYPTO_LAB=$(python3 -c \"from pathlib import Path; print(Path('scripts/k545_tax_harvester.py').resolve().parent.parent)\") && "
            "sed -i '' \"s|CRYPTO_LAB_PATH|${CRYPTO_LAB}|g\" scripts/com.cryptolab.k545-tax-harvester.plist && "
            "cp scripts/com.cryptolab.k545-tax-harvester.plist ~/Library/LaunchAgents/ && "
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k545-tax-harvester.plist"
        ),
        "verify": "launchctl list | grep k545-tax-harvester",
        "risk": "LOW (paper mode, no orders submitted)",
    },
    {
        "step": 5,
        "title": "Upgrade to LIVE (CPA approval required)",
        "effort": "5 min + CPA sign-off",
        "action": (
            "Edit PAPER_TRADE=False in plist + add --live to ProgramArguments. "
            "launchctl unload/reload. "
            "LIVE auto-change PROHIBITED — manual edit required each time."
        ),
        "command": "# Manual: edit ~/Library/LaunchAgents/com.cryptolab.k545-tax-harvester.plist",
        "risk": "MEDIUM (live order submission when harvest conditions met)",
    },
]


def print_activation() -> None:
    print("\n" + "=" * 70)
    print("  K545 Tax Harvester — 1-Step Activation Runbook")
    print("  INFORMATIONAL ONLY. NOT TAX ADVICE.")
    print("=" * 70)
    for step in ACTIVATION_STEPS:
        print(f"\n  Step {step['step']}: {step['title']}")
        print(f"    Effort: {step['effort']} | Risk: {step['risk']}")
        print(f"    Action: {step['action']}")
        print(f"    Command: {step['command'][:100]}...")
    print()
    print("  Reversibility: Set PAPER_TRADE=True + launchctl reload -> SAFE")
    print("=" * 70 + "\n")


# ═════════════════════════════════════════════════════════════════════════════
# Main output
# ═════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K753 K545 Tax Loss Harvester Scaffold — INFORMATIONAL ONLY"
    )
    parser.add_argument("--audit",       action="store_true", help="Audit deliverables only")
    parser.add_argument("--projection",  action="store_true", help="Print K523 3-point projection")
    parser.add_argument("--activation",  action="store_true", help="Print 1-step activation runbook")
    parser.add_argument("--output-json", type=str, default=None, help="Write JSON to path")
    parser.add_argument("--aum",         type=float, default=10_000_000, help="AUM in USD")
    parser.add_argument("--rate",        type=float, default=37.0, help="Tax rate %")
    args = parser.parse_args()

    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    print("\n" + "=" * 70)
    print("  K753 K545 Tax Loss Harvester Full Scaffold")
    print("  INFORMATIONAL ONLY — NOT TAX ADVICE")
    print("=" * 70)
    print(f"  Generated: {now_jst}")
    print()

    audit_results = run_audit()
    if args.audit or not (args.projection or args.activation):
        print_audit(audit_results)

    proj = k523_projection(args.aum, args.rate)
    if args.projection or not (args.audit or args.activation):
        print("\n  K523 3-Point Tax Shield Projection (INFORMATIONAL ONLY):")
        print(f"  @${args.aum/1_000_000:.0f}M AUM, {args.rate:.0f}% rate")
        g = proj["gross_shield_usd"]
        r = proj["k518_realized_shield_usd"]
        print(f"    Gross Conservative: ${g['conservative']:>10,.0f}/yr")
        print(f"    Gross Central:      ${g['central']:>10,.0f}/yr (primary estimate)")
        print(f"    Gross Optimistic:   ${g['optimistic']:>10,.0f}/yr")
        print(f"    K518 Realized Conservative: ${r['conservative']:>7,.0f}/yr")
        print(f"    K518 Realized Central:      ${r['central']:>7,.0f}/yr")
        print(f"    K518 Realized Optimistic:   ${r['optimistic']:>7,.0f}/yr")
        print(f"    (K518 realized-to-stated haircut: {proj['k518_haircut']*100:.0f}%)")
        print()

    if args.activation or not (args.audit or args.projection):
        print_activation()

    if args.output_json:
        output = {
            "wave": "K753",
            "generated_jst": now_jst,
            "disclaimer": "INFORMATIONAL ONLY. NOT TAX ADVICE.",
            "audit": audit_results,
            "k523_projection": proj,
            "activation_steps": ACTIVATION_STEPS,
            "deliverables": [r["path"] for r in audit_results if r["status"] == "OK"],
            "missing": [r["path"] for r in audit_results if r["status"] == "MISSING"],
        }
        Path(args.output_json).write_text(json.dumps(output, indent=2))
        print(f"  JSON output: {args.output_json}")

    print("─" * 70)
    print(f"  Key: 70th daemon | Daily 03:00 UTC | PAPER default")
    print(f"  K523 central shield: ${proj['gross_shield_usd']['central']:,.0f}/yr @$10M 37%")
    print(f"  1-step activation: python3 wave_k753_k545_scaffold.py --activation")
    print("  DISCLAIMER: INFORMATIONAL ONLY. NOT TAX ADVICE.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

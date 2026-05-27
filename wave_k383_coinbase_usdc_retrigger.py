"""
wave_k383_coinbase_usdc_retrigger.py
=====================================
K383 — K362 Coinbase USDC Retrigger (R13 Finding 1, Governance Realized)

Purpose:
    Re-evaluate K362 REJECT verdict in light of R13 micro-scraper finding:
    "Coinbase USDC yield governance realized — 90% revenue share to HL protocol,
    $135-160M estimated annual, rolling out Q3 2026."

    Investigates whether the realized revenue share creates:
      1) A direct claimable USDC yield product (sUSDe-equivalent)
      2) A materially higher HYPE staking APY (AQAv2 → staking boost)
      3) Any passthrough mechanism that qualifies as K344 sleeve candidate

Decision logic mirrors K362 gates (K266-derived) plus new Q3 2026 evidence.

Author: CT Lab / K383
Date: 2026-05-27
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root pattern (consistent with all wave scripts)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent

JST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------------------
# Evidence gathered via WebFetch (3-5 URLs, K383 Phase 1)
# ---------------------------------------------------------------------------

EVIDENCE = {
    "sources_fetched": [
        "https://www.coindesk.com/markets/2026/05/18/hyperliquid-s-usdc-deal-could-supercharge-hype-pressure-circle-coinbase-margins-analysts-say",
        "https://www.coinbase.com/blog/coinbase-and-hyperliquid-aligning-markets-on-hyperliquid-to-usdc",  # 403
        "https://www.kucoin.com/blog/coinbase-and-circle-partner-with-hyperliquid-usdc-treasury-role-hype-staking-and-usdh-transition-explained",
        "https://coincentral.com/hyperliquid-usdc-yield-deal-could-route-up-to-90-to-hype-buybacks/",
        "https://stabledash.com/news/everything-you-need-to-know-about-hyperliquid-s-usdh",  # 404
    ],
    "r13_finding": {
        "id": "R13-01",
        "wave": "K382",
        "title": "Coinbase/Circle USDC Yield Sharing on Hyperliquid (May 2026) — 90% Revenue to HL Protocol",
        "note": "R13 micro-scraper flagged as K362 retrigger. actionable_for_k383=True.",
    },
    "governance_facts": {
        "aqav2_announced": "2026-05-14",
        "parties": ["Hyperliquid", "Coinbase", "Circle"],
        "usdc_supply_on_hl_b": 5.1,
        "yield_share_pct_upper_bound": 90,
        "yield_share_disclosure": "undisclosed exact; 'vast majority' per Coinbase; 90% per CoinDesk analyst",
        "annual_estimated_mm": {"low": 135, "high": 160},
        "routing_vehicle": "Hyperliquid Assistance Fund",
        "routing_mechanism_confirmed": "HYPE_buyback_only",
        "claimable_usdc_yield_product_found": False,
        "sUSDC_equivalent_launched": False,
        "hype_staking_apy_change": "NO — AQAv2 yield does NOT feed HYPE staking rewards",
        "hlp_vault_apy_change": "NO — AQAv2 yield does NOT feed HLP vault",
        "rollout_timeline": "phases through Q3 2026",
        "governance_vote_for_passthrough": "NOT FOUND — no governance vote to redirect yield to USDC holders",
        "kucoin_additional_detail": (
            "Yield from USDC reserves flows to Hyperliquid Assistance Fund for: "
            "HYPE buybacks, market-maker rebates, protocol insurance. "
            "No individual depositor yield distribution mentioned."
        ),
        "coincentral_confirmation": (
            "Revenue routed through Assistance Fund → HYPE buybacks confirmed. "
            "No proposals for USDC holder yield found."
        ),
    },
}


# ---------------------------------------------------------------------------
# K266 Gate evaluation (modified for stablecoin sleeve)
# ---------------------------------------------------------------------------

def evaluate_k266_gates(product: dict) -> dict:
    """
    Apply K266 strict gates to a stablecoin yield product candidate.

    Gates (K362 / K266 standard):
        G1  net APY >= 5%
        G2  audit + counterparty grade
        G3  peg stability
        G4  orthogonal to HL ecosystem (rho < 0.3)
        G5  holder-claimable (NOT buyback-only)
    """
    gates = {}

    # G1 — net APY
    apy = product.get("net_apy_pct")
    gates["G1_apy"] = {
        "threshold_pct": 5.0,
        "actual_pct": apy,
        "pass": apy is not None and apy >= 5.0,
        "note": "N/A — product does not exist" if apy is None else f"{apy:.2f}% vs 5.0% threshold",
    }

    # G2 — counterparty audit
    gates["G2_audit"] = {
        "counterparty": product.get("counterparty"),
        "audit": product.get("audit"),
        "pass": product.get("audit_pass", False),
        "note": product.get("audit_note", ""),
    }

    # G3 — peg stability
    gates["G3_peg"] = {
        "asset": product.get("peg_asset"),
        "stability_grade": product.get("peg_grade"),
        "pass": product.get("peg_pass", False),
        "note": product.get("peg_note", ""),
    }

    # G4 — orthogonality
    rho = product.get("corr_vs_hl", None)
    gates["G4_orthogonal"] = {
        "threshold_rho": 0.3,
        "actual_rho": rho,
        "pass": rho is not None and rho < 0.3,
        "note": product.get("orthogonal_note", ""),
    }

    # G5 — claimability
    gates["G5_claimable"] = {
        "holder_claimable": product.get("holder_claimable", False),
        "pass": product.get("holder_claimable", False),
        "note": product.get("claimable_note", ""),
    }

    all_pass = all(g["pass"] for g in gates.values())
    gates["all_pass"] = all_pass
    gates["gates_passed"] = sum(1 for k, g in gates.items() if k not in ("all_pass", "gates_passed") and g.get("pass"))
    gates["gates_total"] = 5

    return gates


# ---------------------------------------------------------------------------
# Product definitions
# ---------------------------------------------------------------------------

PRODUCTS = {
    "aqav2_direct_usdc_yield": {
        "name": "AQAv2 Direct USDC Reserve Yield Passthrough (Hypothetical)",
        "status": "NOT_LAUNCHED",
        "net_apy_pct": None,
        "counterparty": "Coinbase + Hyperliquid",
        "audit": None,
        "audit_pass": False,
        "audit_note": "Product does not exist — no audit possible",
        "peg_asset": "USDC",
        "peg_grade": "N/A",
        "peg_pass": False,
        "peg_note": "Product does not exist",
        "corr_vs_hl": None,
        "orthogonal_note": "If launched: HL-native → correlated with HL ecosystem risk",
        "holder_claimable": False,
        "claimable_note": "AQAv2 yield routes exclusively to Assistance Fund → HYPE buybacks. Zero passthrough to USDC holders.",
        "k344_candidate": False,
    },
    "hype_staking": {
        "name": "HYPE Native Staking (AQAv2 boosted? — REJECTED)",
        "status": "EXISTS_NOT_BOOSTED",
        "net_apy_pct": 2.37,
        "counterparty": "Hyperliquid PoS validators",
        "audit": "Native L1 (low risk)",
        "audit_pass": True,
        "audit_note": "Native HL L1 staking — low smart contract risk",
        "peg_asset": "HYPE (volatile token)",
        "peg_grade": "FAIL — HYPE is not a stablecoin",
        "peg_pass": False,
        "peg_note": "HYPE carries full price exposure. Not a capital-stable sleeve.",
        "corr_vs_hl": 0.85,
        "orthogonal_note": "HYPE staking is highly correlated with HL ecosystem performance (rho ~0.85)",
        "holder_claimable": False,
        "claimable_note": "Auto-compound, no manual claim. 7-day unstake queue. AQAv2 yield does NOT boost staking rewards.",
        "k344_candidate": False,
    },
    "susde_k344_baseline": {
        "name": "Ethena sUSDe (K344 active sleeve)",
        "status": "ACTIVE_BASELINE",
        "net_apy_pct": 4.01,
        "counterparty": "Ethena Labs",
        "audit": "Multiple independent audits",
        "audit_pass": True,
        "audit_note": "Audited. Delta-neutral hedging complexity acknowledged.",
        "peg_asset": "USDC (synthetic, delta-neutral)",
        "peg_grade": "GOOD — historically stable peg",
        "peg_pass": True,
        "peg_note": "MDD 0.11% (K344 live). Near-perfect peg historically.",
        "corr_vs_hl": 0.05,
        "orthogonal_note": "Ethereum-native. Near-zero correlation with HL ecosystem (rho 0.05, K344).",
        "holder_claimable": True,
        "claimable_note": "sUSDe redeemable anytime. Standard 7d cooldown.",
        "k344_candidate": True,
    },
}


# ---------------------------------------------------------------------------
# Architecture candidates (v6.14a/b/c)
# ---------------------------------------------------------------------------

ARCHITECTURE_CANDIDATES = {
    "v6.14a": {
        "description": "Keep sUSDe 5% sleeve (K344 confirmed). No USDC HL sleeve. HYPE buyback benefit captured passively via existing HYPE exposure in HL trading strategies.",
        "susde_alloc_pct": 5.0,
        "usdc_hl_alloc_pct": 0.0,
        "hl_concentration_delta_pp": 0.0,
        "total_hl_exposure_pct": 57.5,
        "rationale": "No actionable claimable yield from AQAv2. sUSDe remains best available stablecoin sleeve. HYPE buyback benefit is passive and already captured.",
        "verdict": "RECOMMENDED",
    },
    "v6.14b": {
        "description": "Split sleeve: sUSDe 3% + USDC HL 2% (only if claimable yield >= 3%).",
        "susde_alloc_pct": 3.0,
        "usdc_hl_alloc_pct": 2.0,
        "hl_concentration_delta_pp": 2.0,
        "total_hl_exposure_pct": 59.5,
        "rationale": "Gate condition NOT MET — no USDC HL claimable yield product exists. Architecture candidate remains theoretical.",
        "verdict": "BLOCKED — G5 claimability gate fails",
    },
    "v6.14c": {
        "description": "Full replace: sUSDe 0% + USDC HL 5% (only if claimable yield > sUSDe + advantages).",
        "susde_alloc_pct": 0.0,
        "usdc_hl_alloc_pct": 5.0,
        "hl_concentration_delta_pp": 5.0,
        "total_hl_exposure_pct": 62.5,
        "rationale": "Multiple gate failures. No product. G1/G4/G5 all fail. Additionally loses sUSDe Ethereum-native orthogonality.",
        "verdict": "BLOCKED — G1/G4/G5 fail",
    },
}


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_k383_analysis() -> dict:
    """Execute K383 retrigger analysis and return full results dict."""

    now = datetime.now(JST).isoformat()

    # Evaluate gates for each product
    gate_results = {}
    for prod_id, prod in PRODUCTS.items():
        gate_results[prod_id] = evaluate_k266_gates(prod)

    # Decision logic
    # AQAv2 direct yield: product does NOT exist → G5 fail alone is sufficient REJECT
    aqav2_direct_gates = gate_results["aqav2_direct_usdc_yield"]
    hype_staking_gates = gate_results["hype_staking"]
    susde_gates = gate_results["susde_k344_baseline"]

    # K383 verdict
    if not EVIDENCE["governance_facts"]["claimable_usdc_yield_product_found"]:
        k383_verdict = "CONFIRM_REJECT"
        k383_rationale = [
            "R13-01 described 'governance realized' = AQAv2 framework activated (Coinbase as treasury deployer confirmed).",
            "However, 'governance realized' does NOT mean a claimable USDC yield product was launched.",
            "All $135-160M annual AQAv2 revenue routes exclusively to Hyperliquid Assistance Fund → HYPE buybacks.",
            "No sUSDC, yield-bearing USDC token, or direct USDC holder yield product exists or was announced.",
            "HYPE staking APY (2.37%) unchanged — AQAv2 yield does NOT feed staking rewards.",
            "HLP vault yield unchanged — AQAv2 yield does NOT feed HLP.",
            "No governance vote found to redirect AQAv2 yield toward USDC holder distribution.",
            "G5 (claimability) fails — buyback-only mechanism is NOT a sleeve candidate.",
            "K362 REJECT logic stands unchanged: mechanism mismatch, not product deprecation.",
        ]
        monitor_trigger = (
            "HL governance proposal published that explicitly routes a portion of AQAv2 "
            "reserve yield to a claimable USDC yield token (sUSDC-equivalent). "
            "Watch: hyperliquid.gitbook.io governance, HL Discord #governance, "
            "Hyper Foundation Twitter. Re-trigger K384 on such event."
        )
        recheck_days = 30
    else:
        # Hypothetical: if product launches, check G1
        k383_verdict = "ACCEPT_PENDING_DETAILS"
        k383_rationale = ["Claimable yield product found — details required for full acceptance."]
        monitor_trigger = "N/A"
        recheck_days = 0

    # Concentration impact summary
    concentration = {
        "current_hl_exposure_pct": 57.5,
        "cap_pct": 65.0,
        "headroom_pct": 7.5,
        "v6_14a_impact_pp": 0.0,
        "v6_14b_impact_pp": 2.0,
        "v6_14c_impact_pp": 5.0,
        "note": (
            "sUSDe (Ethereum-native) adds ZERO HL concentration. "
            "Any HL-native yield product would consume HL headroom. "
            "v6.14a preserves full 7.5pp headroom buffer."
        ),
    }

    # Implementation effort (ACCEPT path — not triggered)
    implementation_note = (
        "K383 verdict is CONFIRM_REJECT. No implementation required. "
        "If future K384 re-triggers on governance proposal, implementation would include: "
        "(1) USDC HL yield monitoring daemon similar to k344_susde_oc_daily_run.py, "
        "(2) Architecture re-balance K386 v6.14 weighting update, "
        "(3) HTML/runbook updates. Estimated effort: 4-6h."
    )

    result = {
        "wave": "K383",
        "task": "K362 Coinbase USDC Retrigger (R13 Finding 1 — Governance Realized)",
        "generated_at": now,
        "k362_original_verdict": "REJECT",
        "k383_verdict": k383_verdict,
        "k383_rationale": k383_rationale,
        "evidence": EVIDENCE,
        "product_evaluations": {
            prod_id: {
                "product": PRODUCTS[prod_id],
                "gates": gate_results[prod_id],
            }
            for prod_id in PRODUCTS
        },
        "architecture_candidates": ARCHITECTURE_CANDIDATES,
        "concentration_analysis": concentration,
        "k344_sleeve_status": "UNCHANGED — sUSDe remains K344 active sleeve. No replacement or addition warranted.",
        "monitor_trigger": monitor_trigger,
        "recheck_days": recheck_days,
        "implementation_note": implementation_note,
        "phases_completed": [
            "Phase 1: R13-01 evidence extraction + governance proposal investigation (WebSearch + WebFetch 3 URLs)",
            "Phase 2: Revenue distribution channel analysis (AQAv2 → HYPE buyback confirmed, no new mechanisms)",
            "Phase 3: K344 sUSDe comparison refreshed (sUSDe 4.01% APY current, Sh 8.39, MDD 0.11%)",
            "Phase 4: v6.14a/b/c architecture candidate evaluation",
            "Phase 5: K266 strict gate evaluation (G1-G5) for all candidates",
            "Phase 6: HL concentration impact (v6.14a = 0pp delta, recommended)",
            "Phase 7: Decision matrix → CONFIRM_REJECT",
            "Phase 8: Monitor trigger definition for future K384 retrigger",
        ],
    }

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def main():
    result = run_k383_analysis()

    out_json = REPO_ROOT / "wave_k383_coinbase_usdc_retrigger.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"K383 analysis complete.")
    print(f"Verdict: {result['k383_verdict']}")
    print(f"K362 status: {result['k362_original_verdict']} → CONFIRMED")
    print(f"K344 sleeve: {result['k344_sleeve_status']}")
    print(f"Output: {out_json}")
    return result


if __name__ == "__main__":
    main()

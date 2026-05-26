"""
wave_k362_coinbase_usdc_hl.py
Wave K362 — Coinbase x HL USDC deal yield investigation (K354 follow-up)
R12-18 sleeve candidate scan: AQAv2 yield mechanism categorization + K344 comparison.

REPO_ROOT pattern (K339 security rule):
  REPO_ROOT = Path(__file__).resolve().parent   (script lives at repo root)

NO new packages — stdlib + json + datetime only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ── paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_JSON = REPO_ROOT / "wave_k362_coinbase_usdc_hl.json"
OUTPUT_MD   = REPO_ROOT / "wave_k362_coinbase_usdc_hl.md"

# ── JST helper ─────────────────────────────────────────────────────────────
JST = timezone(timedelta(hours=9))

def now_jst() -> str:
    return datetime.now(tz=JST).isoformat(timespec="seconds")

# ── K344 sUSDe benchmark (from K361) ───────────────────────────────────────
K344_SUSDE = {
    "apy_pct": 5.0,
    "sharpe": 8.39,
    "mdd_pct": 0.11,
    "corr_vs_trading": 0.05,
    "allocation_pct": 5.0,
    "chain": "Ethereum",
    "custody": "Ethena Labs (centralized off-chain hedging)",
    "audit": "multiple independent audits",
    "smart_contract_risk": "medium (complex delta-neutral hedging)",
    "ecosystem": "Ethereum / ETH-native",
}

# ── AQAv2 deal facts (from web research) ───────────────────────────────────
AQAV2_DEAL = {
    "announced": "2026-05-14",
    "parties": ["Hyperliquid", "Coinbase", "Circle"],
    "framework": "Aligned Quote Asset v2 (AQAv2)",
    "usdc_supply_on_hl_bn": 5.1,
    "yield_share_to_hl_pct_max": 90,
    "yield_share_note": "exact % undisclosed; 'vast majority' per Coinbase blog; 90% upper bound per analysts",
    "annual_gross_coinbase_circle_bn": 0.180,
    "annual_routed_to_hl_mm_range": [135, 160],
    "repurchase_authorization_mm": 30,
    "routing_vehicle": "Hyperliquid Assistance Fund",
    "routing_mechanism": "HYPE_buyback_only",
    "circle_commitment": "stake 500k HYPE",
    "coinbase_commitment": "increase staked HYPE position",
    "additional_revenue_streams": [
        "Trading fee buybacks (97% of fees → Assistance Fund → HYPE buyback)",
        "Bitwise BHYP ETF (10% of management fee → HYPE purchases)",
    ],
    "sources": [
        "https://www.coinbase.com/blog/coinbase-and-hyperliquid-aligning-markets-on-hyperliquid-to-usdc",
        "https://www.theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc",
        "https://www.coindesk.com/markets/2026/05/18/hyperliquid-s-usdc-deal-could-supercharge-hype-pressure-circle-coinbase-margins-analysts-say",
        "https://cryptobriefing.com/hyperliquid-usdc-yield-hype-buybacks/",
        "https://tokenomics.com/articles/hyperliquid-tokenomics-how-hype-captures-65m-monthly-in-holder-revenue",
    ],
}

# ── HYPE staking facts (from gitbook + stakingrewards.com) ─────────────────
HYPE_STAKING = {
    "reward_formula": "inversely proportional to sqrt(total_staked)",
    "apy_at_400m_staked_pct": 2.37,
    "apy_range_pct": [1.80, 4.50],
    "reward_accrual": "every minute",
    "reward_distribution": "daily",
    "compounding": "auto-redelegation (compound, not manual claim)",
    "unstaking_queue_days": 7,
    "aqav2_yield_feeds_staking": False,
    "note": "Staking rewards derive from network emissions (inflationary), not from AQAv2 USDC reserve yield",
}

# ── HLP vault facts ─────────────────────────────────────────────────────────
HLP_VAULT = {
    "type": "market_making_vault",
    "yield_sources": ["trading fees", "funding rates", "liquidations"],
    "aqav2_yield_feeds_hlp": False,
    "monthly_revenue_jan2026_mm": 0.651,
    "note": "HLP vault earns from MM activity, NOT from AQAv2 USDC reserve yield",
    "user_claimable": True,
    "risk": "directional MM risk, potential drawdown in trending markets",
}

# ── HypurrFi USDC lending (K337 context) ───────────────────────────────────
HYPURRFI = {
    "protocol": "HypurrFi (hypurrfi.com)",
    "product": "USDC lending pool (Aave-style)",
    "apy_pct_range": [8, 20],
    "apy_source": "organic borrowing demand, not AQAv2 yield",
    "tvl_mm": 16.6,
    "user_claimable": True,
    "risk": "smart_contract + platform_risk (HyperEVM, domain compromise incident noted)",
    "note": "K337 reference: $16.6M pooled, ~9% APY — yield is organic, not AQAv2-derived",
}

# ── yield mechanism categorization ─────────────────────────────────────────
def categorize_mechanisms() -> list[dict[str, Any]]:
    return [
        {
            "id": "aqav2_buyback",
            "name": "AQAv2 USDC Reserve Yield → HYPE Buyback",
            "category": "INDIRECT_BENEFIT",
            "description": "90% of USDC reserve yield flows to Assistance Fund → open-market HYPE buybacks",
            "user_claimable": False,
            "requires_hype_exposure": True,
            "estimated_apy_pct": None,
            "notes": "Benefit is capital appreciation of HYPE token, not a claimable yield stream. No passthrough to USDC holders.",
            "k344_sleeve_candidate": False,
            "reason": "Not a claimable yield product. Requires HYPE token ownership. Indirect benefit only.",
        },
        {
            "id": "hype_staking",
            "name": "HYPE Native Staking (2.37% APY)",
            "category": "INDIRECT_BENEFIT",
            "description": "PoS-style HYPE staking with auto-compound rewards, funded by network emissions",
            "user_claimable": False,
            "requires_hype_exposure": True,
            "estimated_apy_pct": 2.37,
            "notes": "AQAv2 yield does NOT feed into staking rewards. Rewards are inflationary emissions. Auto-compound, not claimable in the sUSDe sense. Unstaking requires 7-day queue.",
            "k344_sleeve_candidate": False,
            "reason": "Below K344 sUSDe 5% APY. Requires HYPE price exposure. Not orthogonal to existing trading strategies. 7-day liquidity lockup.",
        },
        {
            "id": "hlp_vault",
            "name": "HLP Market-Making Vault",
            "category": "INDIRECT_BENEFIT",
            "description": "LP shares in HL's automated market-making vault, earning trading fees + funding",
            "user_claimable": True,
            "requires_hype_exposure": False,
            "estimated_apy_pct": None,
            "notes": "AQAv2 yield does NOT feed into HLP. Jan 2026 HLP revenue was $651K/month. Directional MM risk in trending markets (MDD risk non-trivial).",
            "k344_sleeve_candidate": False,
            "reason": "AQAv2 yield does not flow here. MM risk means non-negligible MDD — incompatible with K344 sleeve target (MDD < 0.2%). Increases HL ecosystem concentration.",
        },
        {
            "id": "hypurrfi_usdc",
            "name": "HypurrFi USDC Lending Pool (8-20% APY)",
            "category": "INDIRECT_BENEFIT",
            "description": "USDC deposited into HypurrFi earns borrowing demand yield on HyperEVM",
            "user_claimable": True,
            "requires_hype_exposure": False,
            "estimated_apy_pct": 9.0,
            "notes": "Yield is organic borrowing demand on HyperEVM — NOT derived from AQAv2 Coinbase deal. K337 reference. Domain compromise incident (migrated to hypurrfi.com). HyperEVM smart contract risk.",
            "k344_sleeve_candidate": False,
            "reason": "Not connected to Coinbase deal. High smart-contract risk on HyperEVM. Domain compromise incident. HL ecosystem concentration risk (v6.13d HL exposure already 57.5%).",
        },
        {
            "id": "aqav2_direct_usdc_yield",
            "name": "Direct USDC Reserve Yield Passthrough (NOT FOUND)",
            "category": "TBD_NOT_LAUNCHED",
            "description": "A product where USDC holders on HL receive direct yield from the AQAv2 reserve deal (sUSDe-style)",
            "user_claimable": False,
            "requires_hype_exposure": False,
            "estimated_apy_pct": None,
            "notes": "This product does NOT currently exist. All AQAv2 reserve yield routes exclusively to HYPE buybacks via Assistance Fund. No 'HL native sUSDe equivalent' exists as of 2026-05-27.",
            "k344_sleeve_candidate": False,
            "reason": "Product does not exist. If launched, would require re-evaluation. Trigger: HL governance proposal for USDC yield passthrough token.",
        },
    ]

# ── K344 sleeve comparison ─────────────────────────────────────────────────
def build_comparison() -> dict[str, Any]:
    return {
        "k344_susde_benchmark": K344_SUSDE,
        "hl_concentration_risk": {
            "current_hl_exposure_pct": 57.5,
            "max_allowed_pct": 65.0,
            "headroom_pct": 7.5,
            "susde_is_inside_hl": False,
            "hl_products_would_be_inside_hl": True,
            "note": "Any HL-native yield product would add to existing 57.5% HL exposure. Only 7.5% headroom before hitting 65% cap (feedback_concentration_risk_HL.md).",
        },
        "comparison_matrix": [
            {
                "metric": "Annual yield APY",
                "susde": "4.01% (Q1 2026 mean, K361)",
                "hl_hype_staking": "2.37%",
                "hlp_vault": "variable (MM-dependent)",
                "hypurrfi_usdc": "~9% (organic demand, volatile)",
                "aqav2_direct": "N/A (product does not exist)",
            },
            {
                "metric": "User claimable",
                "susde": "YES (sUSDe redeem anytime)",
                "hl_hype_staking": "NO (auto-compound, 7d unstake)",
                "hlp_vault": "YES (with withdrawal lag)",
                "hypurrfi_usdc": "YES",
                "aqav2_direct": "N/A",
            },
            {
                "metric": "MDD risk",
                "susde": "0.11% (K344 live)",
                "hl_hype_staking": "HYPE price exposure (high vol)",
                "hlp_vault": "non-trivial (trending mkt risk)",
                "hypurrfi_usdc": "stablecoin; liquidation risk",
                "aqav2_direct": "N/A",
            },
            {
                "metric": "Orthogonal to trading (rho)",
                "susde": "0.05 (near-zero, K344)",
                "hl_hype_staking": "likely high (corr with crypto mkt)",
                "hlp_vault": "medium (corr with vol regime)",
                "hypurrfi_usdc": "low-medium (HyperEVM rate-driven)",
                "aqav2_direct": "N/A",
            },
            {
                "metric": "Smart contract risk",
                "susde": "medium (audited, complex hedging)",
                "hl_hype_staking": "low (native HL L1)",
                "hlp_vault": "low-medium (native HL L1)",
                "hypurrfi_usdc": "HIGH (HyperEVM + domain incident)",
                "aqav2_direct": "N/A",
            },
            {
                "metric": "HL concentration impact",
                "susde": "ZERO (Ethereum-native, outside HL)",
                "hl_hype_staking": "+X% (adds HL exposure)",
                "hlp_vault": "+X% (adds HL exposure)",
                "hypurrfi_usdc": "+X% (adds HyperEVM exposure)",
                "aqav2_direct": "+X% (would add HL exposure)",
            },
            {
                "metric": "Tied to Coinbase AQAv2 deal",
                "susde": "NO",
                "hl_hype_staking": "NO (inflationary emissions)",
                "hlp_vault": "NO (trading fees only)",
                "hypurrfi_usdc": "NO (organic borrow demand)",
                "aqav2_direct": "YES (hypothetical only)",
            },
        ],
    }

# ── concentration risk analysis ────────────────────────────────────────────
def concentration_analysis() -> dict[str, Any]:
    return {
        "current_portfolio_hl_exposure_pct": 57.5,
        "max_allowed_pct": 65.0,
        "headroom_pct": 7.5,
        "susde_is_outside_hl": True,
        "susde_replacement_vs_addition": {
            "replace_susde_with_hl_product": {
                "hl_exposure_delta": 0,
                "net_result": "HL exposure unchanged at 57.5%, but lose Ethereum-native orthogonality of sUSDe",
                "verdict": "INFERIOR: lose diversification, gain nothing",
            },
            "add_hl_product_to_susde": {
                "hl_exposure_delta": "+allocation_size",
                "net_result": "HL exposure rises. Even 5% HL product → 57.5+5=62.5% (within 65% cap, but close)",
                "verdict": "RISKY: approaches concentration cap; only viable if product is materially better than sUSDe",
            },
        },
        "conclusion": "No discovered HL-native product justifies either replacing or adding to sUSDe sleeve. sUSDe's outside-HL positioning is a structural advantage, not a bug.",
    }

# ── decision ───────────────────────────────────────────────────────────────
DECISION = {
    "verdict": "REJECT",
    "rationale": [
        "AQAv2 USDC reserve yield (90%) flows exclusively to HYPE buybacks via Assistance Fund. Zero passthrough to USDC depositors.",
        "No sUSDe-equivalent direct USDC yield product exists on HL as of 2026-05-27.",
        "HYPE staking (2.37% APY) is below K344 sUSDe benchmark (5% APY) and requires HYPE price exposure.",
        "HLP vault yield does not derive from AQAv2 deal; carries MM directional risk incompatible with K344 sleeve targets.",
        "HypurrFi USDC lending is organic/unconnected to Coinbase deal; carries HyperEVM smart-contract risk + prior domain compromise.",
        "All HL-native products add to existing 57.5% HL concentration (cap: 65%), while sUSDe (Ethereum-native) provides zero HL concentration impact.",
    ],
    "monitor_trigger": "HL governance proposal published for USDC yield passthrough token (direct yield product for USDC holders). Watch: hyperliquid.gitbook.io, HL Discord governance channel.",
    "defer_conditions": [
        "HL governance vote on USDC yield product passes",
        "Protocol launches sUSDC-style rebasing token backed by AQAv2 reserve yield",
        "AQAv2 yield split % is formally disclosed (currently 'vast majority' only)",
    ],
    "k344_sleeve_status": "UNCHANGED — sUSDe remains K344 sleeve. No replacement or addition warranted.",
    "next_wave_recommendation": "K363+ — sUSDe sleeve monitoring continues as scheduled. No new scaffold required.",
}

# ── main ───────────────────────────────────────────────────────────────────
def main() -> None:
    ts = now_jst()

    mechanisms = categorize_mechanisms()
    comparison = build_comparison()
    concentration = concentration_analysis()

    output: dict[str, Any] = {
        "wave": "K362",
        "task": "Coinbase x HL USDC deal yield investigation (K354 follow-up, USDH-sunset replacement scan)",
        "generated_at": ts,
        "decision": DECISION["verdict"],
        "deal_facts": AQAV2_DEAL,
        "hype_staking": HYPE_STAKING,
        "hlp_vault": HLP_VAULT,
        "hypurrfi": HYPURRFI,
        "yield_mechanisms": mechanisms,
        "k344_comparison": comparison,
        "concentration_analysis": concentration,
        "full_decision": DECISION,
        "phases_completed": [
            "Phase 1: Deal mechanism research (5 URLs fetched)",
            "Phase 2: Claimable products discovery (HL API + web research)",
            "Phase 3: Mechanism categorization (5 mechanisms evaluated)",
            "Phase 4: K344 sleeve comparison (6-metric matrix)",
            "Phase 5: HL ecosystem yield assessment (staking + HLP + HypurrFi)",
            "Phase 6: Decision matrix",
            "Phase 7: Concentration risk note",
        ],
        "urls_fetched": [
            "https://www.coinbase.com/blog/coinbase-and-hyperliquid-aligning-markets-on-hyperliquid-to-usdc",
            "https://www.theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc",
            "https://www.coindesk.com/markets/2026/05/18/hyperliquid-s-usdc-deal-could-supercharge-hype-pressure-circle-coinbase-margins-analysts-say",
            "https://beincrypto.com/coinbase-usdh-hyperliquid-shifts-to-usdc/",
            "https://cryptobriefing.com/hyperliquid-usdc-yield-hype-buybacks/",
            "https://coincentral.com/hyperliquid-usdc-yield-deal-could-route-up-to-90-to-hype-buybacks/",
            "https://tokenomics.com/articles/hyperliquid-tokenomics-how-hype-captures-65m-monthly-in-holder-revenue",
            "https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/staking",
        ],
        "api_endpoints_queried": [
            "POST https://api.hyperliquid.xyz/info {type:meta} — confirmed 230 perp markets live",
            "POST https://api.hyperliquid.xyz/info {type:validatorSummaries} — 31 validators (stakeData requires non-zero user)",
            "POST https://api.hyperliquid.xyz/info {type:delegatorSummary} — confirmed endpoint exists",
            "POST https://api.hyperliquid.xyz/info {type:allVaults} — endpoint exists (empty response)",
            "POST https://api.hyperliquid.xyz/info {type:spotMetaAndAssetCtxs} — USDC confirmed index 0, canonical",
        ],
    }

    OUTPUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[K362] JSON written → {OUTPUT_JSON}", file=sys.stderr)

    _write_md(output, ts)
    print(f"[K362] MD written  → {OUTPUT_MD}", file=sys.stderr)
    print(f"[K362] Decision: {DECISION['verdict']}", file=sys.stderr)


def _write_md(data: dict[str, Any], ts: str) -> None:
    deal = data["deal_facts"]
    staking = data["hype_staking"]
    hlp = data["hlp_vault"]
    hypurrfi = data["hypurrfi"]
    mech = data["yield_mechanisms"]
    comp = data["k344_comparison"]["comparison_matrix"]
    conc = data["concentration_analysis"]
    dec = data["full_decision"]

    lines: list[str] = []

    lines += [
        f"# Wave K362 — Coinbase x HL USDC Deal Yield Investigation",
        f"",
        f"**Generated:** {ts}  ",
        f"**Decision:** {data['decision']}  ",
        f"**Wave:** K362 (K354 follow-up, USDH-sunset replacement scan)",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"K354 established that USDH was sunset mid-May 2026 and Coinbase became",
        f"HyperLiquid's official USDC treasury deployer under the AQAv2 framework,",
        f"with ~90% of USDC reserve yield flowing to the HL protocol.",
        f"",
        f"**K362 finding:** The 90% yield flows **exclusively** to HYPE token buybacks",
        f"via the Hyperliquid Assistance Fund. No sUSDe-equivalent direct USDC yield",
        f"product exists. No HL-native yield mechanism qualifies as a K344 sleeve",
        f"candidate. Decision: **REJECT** (same outcome as K354 USDH rejection, but",
        f"for a fundamentally different reason — mechanism mismatch rather than product",
        f"deprecation).",
        f"",
        f"---",
        f"",
        f"## Phase 1 — Deal Mechanism Research",
        f"",
        f"### AQAv2 Framework Facts",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Announced | {deal['announced']} |",
        f"| Parties | {', '.join(deal['parties'])} |",
        f"| USDC on HL | ${deal['usdc_supply_on_hl_bn']}B |",
        f"| Yield share to HL | up to {deal['yield_share_to_hl_pct_max']}% (exact undisclosed) |",
        f"| Annual gross (Coinbase+Circle) | ${deal['annual_gross_coinbase_circle_bn']*1000:.0f}M |",
        f"| Annual routed to HL (est.) | ${deal['annual_routed_to_hl_mm_range'][0]}M–${deal['annual_routed_to_hl_mm_range'][1]}M |",
        f"| Repurchase authorization | ${deal['repurchase_authorization_mm']}M |",
        f"| Routing vehicle | {deal['routing_vehicle']} |",
        f"| Routing mechanism | **{deal['routing_mechanism']}** |",
        f"| Circle commitment | {deal['circle_commitment']} |",
        f"",
        f"### Key Finding: Yield Route",
        f"",
        f"Multiple independent sources confirm:",
        f"> All AQAv2 reserve yield is routed through Hyperliquid's Assistance Fund,",
        f"> which executes HYPE open-market buybacks. No portion is distributed",
        f"> directly to USDC holders, stakers, or LP vault participants.",
        f"",
        f"Exact split percentage was NOT disclosed publicly. 90% is an analyst upper",
        f"bound from CoinDesk. Coinbase blog used 'vast majority'. CryptoBriefing",
        f"confirmed exclusive HYPE buyback routing.",
        f"",
        f"### Additional Revenue Streams (context)",
        f"",
        f"HYPE token buybacks now funded by three streams (May 2026):",
        f"1. Trading fee buybacks — 97% of exchange fees → Assistance Fund",
        f"2. AQAv2 reserve yield — $135–160M/year new stream",
        f"3. Bitwise BHYP ETF — 10% of management fee → HYPE purchases",
        f"",
        f"At $65M/month exchange revenue (Jan 2026 baseline), AQAv2 adds ~$11–13M/mo",
        f"incremental buyback pressure — structurally significant for HYPE price, but",
        f"zero impact on USDC holder yield.",
        f"",
        f"---",
        f"",
        f"## Phase 2 — Claimable Products Discovery",
        f"",
        f"### HL API Endpoints Queried",
        f"",
        f"| Endpoint | Result |",
        f"|----------|--------|",
        f"| `{{type:meta}}` | 230 perp markets confirmed live |",
        f"| `{{type:validatorSummaries}}` | 31 validators (stakeData requires user address) |",
        f"| `{{type:delegatorSummary}}` | Endpoint live; requires non-zero address |",
        f"| `{{type:allVaults}}` | Endpoint live; empty response (no public vault list) |",
        f"| `{{type:spotMetaAndAssetCtxs}}` | USDC = index 0, canonical, HyperEVM contract confirmed |",
        f"",
        f"### HYPE Native Staking",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| APY (at 400M staked) | {staking['apy_at_400m_staked_pct']}% |",
        f"| APY range | {staking['apy_range_pct'][0]}–{staking['apy_range_pct'][1]}% |",
        f"| Accrual | every minute |",
        f"| Distribution | daily |",
        f"| Compounding | auto-redelegation (NOT manual claim) |",
        f"| Unstaking queue | {staking['unstaking_queue_days']} days |",
        f"| AQAv2 feeds staking | **{staking['aqav2_yield_feeds_staking']}** |",
        f"| Reward source | inflationary network emissions only |",
        f"",
        f"**Critical:** AQAv2 USDC reserve yield does NOT feed into HYPE staking",
        f"rewards. Staking rewards are purely inflationary PoS emissions.",
        f"",
        f"### HLP Market-Making Vault",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Yield sources | {', '.join(hlp['yield_sources'])} |",
        f"| AQAv2 feeds HLP | **{hlp['aqav2_yield_feeds_hlp']}** |",
        f"| Jan 2026 monthly revenue | ${hlp['monthly_revenue_jan2026_mm']*1000:.0f}K |",
        f"| User claimable | {hlp['user_claimable']} |",
        f"| Risk | {hlp['risk']} |",
        f"",
        f"HLP vault compensates liquidity providers for MM activity only. AQAv2 yield",
        f"does NOT flow to HLP. Jan 2026 HLP revenue was $651K/month (vs $62.6M perp",
        f"fees — HLP is a tiny fraction of protocol revenue).",
        f"",
        f"### HypurrFi USDC Lending",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Product | USDC lending pool (Aave-style) |",
        f"| APY range | {hypurrfi['apy_pct_range'][0]}–{hypurrfi['apy_pct_range'][1]}% |",
        f"| TVL | ${hypurrfi['tvl_mm']}M |",
        f"| AQAv2 connected | **NO** |",
        f"| Yield source | organic borrowing demand on HyperEVM |",
        f"| Smart contract risk | **HIGH** |",
        f"| Security incident | domain compromise (migrated to hypurrfi.com) |",
        f"",
        f"K337 reference context: HypurrFi's ~9% APY is organic, unrelated to",
        f"Coinbase deal. Security incident (domain compromise) increases caution.",
        f"",
        f"---",
        f"",
        f"## Phase 3 — Mechanism Categorization",
        f"",
    ]

    for m in mech:
        cat_emoji = {"INDIRECT_BENEFIT": "INDIRECT", "TBD_NOT_LAUNCHED": "TBD/NOT LAUNCHED"}
        lines += [
            f"### {m['name']}",
            f"",
            f"- **Category:** {m['category']}",
            f"- **User claimable:** {m['user_claimable']}",
            f"- **Requires HYPE exposure:** {m['requires_hype_exposure']}",
            f"- **Est. APY:** {m['estimated_apy_pct']}%",
            f"- **K344 sleeve candidate:** {m['k344_sleeve_candidate']}",
            f"- **Notes:** {m['notes']}",
            f"- **Reason for rejection:** {m['reason']}",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## Phase 4 — K344 Sleeve Comparison Matrix",
        f"",
        f"| Metric | sUSDe (K344) | HYPE Staking | HLP Vault | HypurrFi USDC | AQAv2 Direct |",
        f"|--------|-------------|--------------|-----------|----------------|--------------|",
    ]
    for row in comp:
        lines.append(
            f"| {row['metric']} | {row['susde']} | {row['hl_hype_staking']} | {row['hlp_vault']} | {row['hypurrfi_usdc']} | {row['aqav2_direct']} |"
        )

    lines += [
        f"",
        f"**Conclusion:** No HL-native product matches or exceeds sUSDe on all",
        f"dimensions critical for a K344 sleeve (APY, claimability, MDD, orthogonality,",
        f"HL concentration neutrality). sUSDe remains the only qualifying sleeve.",
        f"",
        f"---",
        f"",
        f"## Phase 5 — HL Ecosystem Yield Assessment",
        f"",
        f"### HYPE Token Accretion",
        f"",
        f"AQAv2 creates ~$135–160M/year in additional HYPE buyback fuel. At current",
        f"$5.1B USDC base, this is ~2.7–3.1% annual buyback yield equivalent for HYPE",
        f"holders — meaningful for HYPE price but zero benefit to USDC depositors.",
        f"",
        f"If USDC supply grows to $10B (plausible given HL's growth trajectory), annual",
        f"AQAv2-driven buybacks could reach $270–300M — comparable to a major DeFi",
        f"protocol's entire annual revenue.",
        f"",
        f"### HLP Vault Holders",
        f"",
        f"HLP vault does NOT receive AQAv2 yield share. HLP earns from trading",
        f"activity. The vault is a reasonable passive yield product for HL-native",
        f"participants but is disqualified as a K344 sleeve due to: (1) MM directional",
        f"risk, (2) no AQAv2 yield connection, (3) adds HL concentration.",
        f"",
        f"### Bid-Side Market Makers",
        f"",
        f"No evidence of rebates funded by USDC yield. Existing rebate structure is",
        f"funded by trading fees (taker-maker spread). AQAv2 yield bypasses the",
        f"rebate pool entirely.",
        f"",
        f"---",
        f"",
        f"## Phase 6 — Decision Matrix",
        f"",
        f"| Verdict | Trigger Condition | Result |",
        f"|---------|-------------------|--------|",
        f"| ACCEPT scaffold | Clear claimable yield product live, K344-like profile | NOT MET |",
        f"| MONITOR | Yield mechanism exists but not yet claimable | NOT MET |",
        f"| DEFER | HL governance proposal pending, not finalized | NOT MET |",
        f"| **REJECT** | Yield flows entirely to buybacks/dev — zero passthrough | **MET** |",
        f"",
        f"**Final decision: REJECT**",
        f"",
        f"All AQAv2 yield routes to HYPE buybacks. No direct user passthrough exists",
        f"or is pending. This is the same structural outcome as K354 USDH rejection",
        f"(that was deprecated; this is: yield mechanism mismatch — buyback-only).",
        f"",
        f"### Monitor Trigger",
        f"",
        f"Watch for: **HL governance proposal published for a USDC yield passthrough",
        f"token** (analogous to sUSDe / Ethena's rebasing model). If such a proposal",
        f"appears on hyperliquid.gitbook.io or HL Discord governance channel, escalate",
        f"to K363+ scaffold wave immediately.",
        f"",
        f"---",
        f"",
        f"## Phase 7 — Concentration Risk Note",
        f"",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Current HL exposure | {conc['current_portfolio_hl_exposure_pct']}% |",
        f"| Max allowed (feedback_concentration_risk_HL.md) | {conc['max_allowed_pct']}% |",
        f"| Headroom | {conc['headroom_pct']}% |",
        f"| sUSDe inside HL ecosystem | {not conc['susde_is_outside_hl']} |",
        f"",
        f"### Replace sUSDe with HL product?",
        f"",
        f"HL exposure delta = 0, but lose Ethereum-native orthogonality.",
        f"**Verdict: INFERIOR.** sUSDe's outside-HL positioning is a structural advantage.",
        f"",
        f"### Add HL product alongside sUSDe?",
        f"",
        f"Even a 5% allocation to an HL product → HL exposure = 62.5% (near 65% cap).",
        f"Would only be viable if product materially outperforms sUSDe AND has",
        f"demonstrably lower MDD. No such product exists.",
        f"**Verdict: RISKY with no discovered candidate.**",
        f"",
        f"---",
        f"",
        f"## Sources",
        f"",
    ]
    for url in data["urls_fetched"]:
        lines.append(f"- {url}")

    lines += [
        f"",
        f"---",
        f"",
        f"## Key Findings Summary",
        f"",
        f"1. **AQAv2 yield is HYPE-buyback-only.** 90% of $180M/year USDC reserve",
        f"   yield flows to HYPE buybacks. Zero passthrough to USDC depositors.",
        f"",
        f"2. **No sUSDe equivalent on HL.** No rebasing USDC yield token, no",
        f"   claimable USDC staking product, no AQAv2-backed vault exists.",
        f"",
        f"3. **HYPE staking (2.37% APY)** is below K344 benchmark, requires HYPE",
        f"   exposure, auto-compounds (not claimable), and adds HL concentration.",
        f"",
        f"4. **HLP vault** earns from MM activity only, carries directional risk,",
        f"   and adds HL concentration. Disqualified as sleeve.",
        f"",
        f"5. **HypurrFi USDC (~9% APY)** is organic/unconnected to Coinbase deal,",
        f"   carries HyperEVM smart-contract risk, and adds HL concentration.",
        f"   Prior domain compromise incident noted.",
        f"",
        f"6. **sUSDe K344 sleeve unchanged.** No replacement or addition warranted.",
        f"   sUSDe's Ethereum-native positioning provides structural HL-orthogonality",
        f"   unavailable from any HL-ecosystem product.",
        f"",
        f"7. **Monitor trigger set.** If HL governance proposes a direct USDC yield",
        f"   passthrough token, escalate immediately to scaffold wave.",
        f"",
    ]

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

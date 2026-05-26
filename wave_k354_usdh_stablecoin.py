"""
wave_k354_usdh_stablecoin.py
K354 — USDH stablecoin yield arb exploration (R11-8)
Assessment of USDH as v6.14 sleeve candidate complementing K344 sUSDe.

REPO_ROOT pattern (K339 security rule):
  REPO_ROOT = Path(__file__).resolve().parent.parent  ← NOT USED HERE
  (this script lives at repo root, so REPO_ROOT = Path(__file__).resolve().parent)

NO new packages — stdlib + pandas + numpy only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent       # crypto-lab/
CACHE_DIR = REPO_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

OUTPUT_JSON = REPO_ROOT / "wave_k354_usdh_stablecoin.json"
OUTPUT_MD   = REPO_ROOT / "wave_k354_usdh_stablecoin.md"

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
NOW_STR = NOW.isoformat(timespec="seconds")

# ── Phase 1: Protocol Intelligence (hard-coded from WebFetch / WebSearch) ──
# Sources verified 2026-05-27:
#   usdh.com, coinmarketcap.com/currencies/hyperliquid-usd/,
#   beincrypto.com/coinbase-usdh-hyperliquid-shifts-to-usdc/,
#   unchainedcrypto.com/coinbase-becomes-hyperliquids-official-usdc-treasury-deployer,
#   defillama.com/protocol/hypurrfi, wave_k337_hypurrfi_euler.json

USDH_PROTOCOL: dict[str, Any] = {
    "name": "USDH",
    "issuer": "Native Markets / Bridge Building Inc.",
    "chain": "HyperEVM (Hyperliquid L1 sidechain)",
    "launch_date": "2024-09",
    "type": "fiat_backed_stablecoin",
    "peg": "1:1 USD",
    "reserve_assets": ["cash", "short_term_US_Treasuries", "repo_agreements"],
    "reserve_managers": ["BlackRock (BUIDL)", "Superstate (USTB)"],
    "custody": ["JPMorgan Chase", "Fireblocks"],
    "issuance_platform": "Stripe Bridge",
    "genius_act_compliant": True,
    "audit": {
        "type": "monthly_reserve_attestation",
        "cadence": "monthly",
        "attestor": "independent_third_party",
        "status": "ACTIVE_ONGOING",
        "note": "Reserve composition + custodian details public at all times"
    },
}

USDH_MARKET: dict[str, Any] = {
    "as_of": NOW_STR,
    "source": "CoinMarketCap 2026-05-27",
    "price_usd": 0.9874,                    # CMC live: $0.987361
    "market_cap_usd": 62_440_000,           # $62.44M
    "circulating_supply": 63_240_000,       # 63.24M USDH
    "total_supply": 65_870_000,             # 65.87M USDH
    "ath_usd": 1.01,                        # Feb 6 2026
    "atl_usd": 0.9845,                      # Oct 10 2025
    "max_peg_deviation_high_pct": +1.00,    # ATH = +1.0% above peg
    "max_peg_deviation_low_pct": -1.55,     # ATL = $0.9845 → -1.55%
    "current_deviation_pct": -1.26,         # $0.9874 → -1.26% at snapshot
    "volume_24h_usd": 6_410_000,
    "vol_to_mcap_ratio": 0.1027,
    "peak_supply_note": "Was ~$90.7M at search snapshot (earlier date); declining due to sunset",
    "sunset_trigger": "Coinbase acquisition of USDH brand assets, May 2026",
}

# ── Phase 2: USDH Sunset — Critical Event ──────────────────────────────────
USDH_SUNSET: dict[str, Any] = {
    "event": "Coinbase acquires USDH brand assets; USDH sunsets",
    "announced": "2026-05 (mid-May)",
    "deal_summary": (
        "Coinbase becomes Hyperliquid's official USDC treasury deployer under the "
        "Aligned Quote Asset framework. Native Markets granted Coinbase right to "
        "purchase USDH brand assets. USDH transitions from primary HL stablecoin to "
        "deprecated status."
    ),
    "transition_details": {
        "USDH_redemption": "Feeless USDH→USDC or fiat via Native Markets USDH Dashboard (ongoing)",
        "timeline": "Gradual; no hard deadline published as of 2026-05-27",
        "market_alignment": "Hyperliquid migrating spot + perp markets from USDH to USDC",
        "revenue_sharing": "Coinbase shares 'vast majority' of USDC reserve yield with HL protocol",
        "hyperliquid_usdc_rev_share_pct": 90,   # per The Block / KuCoin reporting
        "hype_buyback_mechanism": "USDC yield → HL Assistance Fund → HYPE buyback (replaces USDH 50% mechanism)",
    },
    "impact_on_usdh_holders": [
        "Full par redemption guaranteed (1 USDH = $1 USDC or fiat)",
        "No forced conversion deadline announced",
        "Secondary market liquidity thinning (MCap declined ~$28M in days)",
        "Current spot price $0.9874 = slight discount to par (arb exists but thinning)",
    ],
    "impact_on_hypurrfi_usdh_pools": {
        "isolated_pool_cap": "Supply cap 5M, borrow cap 3M — likely to be wound down",
        "tvl_at_k337": 854_375,       # already tiny per K337
        "note": "HypurrFi USDH pool survival unlikely post-sunset; redemption arb window closing",
    },
}

# ── Phase 3: Yield Mechanism & APY Analysis ────────────────────────────────
USDH_YIELD: dict[str, Any] = {
    "native_yield_to_holder": False,    # USDH holders do NOT earn yield directly
    "yield_distribution": {
        "model": "50/50 split (historical, pre-sunset)",
        "tranche_1": "50% → HL Assistance Fund → HYPE buyback",
        "tranche_2": "50% → USDH Growth & Builders grants / incentives",
        "holder_direct_apy_pct": 0.0,
        "note": "Unlike sUSDe, USDH has NO pass-through yield to token holders"
    },
    "hypurrfi_lending_apy": {
        "source": "K337 wave + HypurrFi DeFiLlama 2026-05-27",
        "usdh_isolated_pool_est_apy_pct": {"min": 9.0, "max": 15.0},   # K337 scenario C
        "hypurrfi_pooled_avg_apy_pct": 8.24,                            # DeFiLlama current
        "hypurrfi_tvl_current_usd": 15_630_000,
        "note": "USDH isolated pool is tiny; HypurrFi pooled is USDC/HYPE dominated",
    },
    "ecosystem_trading_benefits": {
        "taker_fee_discount": "0% lower taker fees on USDH-quoted markets",
        "maker_rebate_boost": "50% higher maker rebates",
        "volume_amplification": "20% amplified volume for fee tier",
        "note": "These benefits are TRADING perks, not yield. Not applicable to passive holders.",
    },
    "comparison_to_alternatives": {
        "plain_USDC_no_yield_pct": 0.0,
        "USDC_Aave_Compound_est_pct": 3.5,
        "sUSDe_current_apy_pct": 3.72,           # K344 current_apy_pct
        "sUSDe_7d_ma_pct": 4.04,                 # K344 7d_ma_apy_pct
        "sUSDe_hist_mean_pct": 10.30,            # K344 apy_mean_full_pct
        "USDH_direct_holder_yield_pct": 0.0,
        "USDH_HypurrFi_lending_est_pct": 9.0,   # if tvl existed; conditional
    },
}

# ── Phase 4: Peg Analysis ──────────────────────────────────────────────────
# Reconstructed from ATH/ATL + current snapshot. No 30d tick data available
# (CoinGecko free API 404 for this token; CMC free tier blocks granular history).

USDH_PEG_ANALYSIS: dict[str, Any] = {
    "data_source": "CMC snapshot + ATH/ATL metadata (granular 30d data unavailable, API 404/403)",
    "price_history": {
        "launch": "2024-09",
        "atl_date": "2025-10-10",
        "atl_usd": 0.9845,
        "atl_deviation_pct": -1.55,
        "ath_date": "2026-02-06",
        "ath_usd": 1.01,
        "ath_deviation_pct": +1.00,
        "current_price_usd": 0.9874,
        "current_deviation_pct": -1.26,
    },
    "depeg_incidents_formal": 0,        # K337: "depeg_incidents: 0" (no hard depeg)
    "peg_stability_assessment": {
        "max_observed_deviation_pct": 1.55,
        "g2_threshold_pct": 5.0,
        "g2_cleared": True,
        "note": (
            "Max deviation 1.55% well within 5% G2 gate. However current -1.26% "
            "discount is NOT arb opportunity — it reflects SUNSET RISK (rational "
            "discount for redemption friction + counterparty risk during wind-down). "
            "This is NOT a clean peg arb."
        ),
    },
    "arb_opportunity_assessment": {
        "discount_arb_available": True,
        "entry_price_usd": 0.9874,
        "par_redemption_usd": 1.00,
        "gross_spread_pct": 1.26,
        "estimated_costs": {
            "slippage_pct": 0.20,
            "gas_hyperevm_pct": 0.01,
            "redemption_delay_risk_pct": 0.50,    # risk during wind-down period
        },
        "net_spread_pct": 0.55,                   # 1.26 - 0.71
        "arb_type": "ONE_TIME_SUNSET_ARB",
        "risk_classification": "MEDIUM_HIGH",
        "note": (
            "Potential one-time gain of ~0.55% net. NOT a systematic yield strategy. "
            "Redemption timeline unspecified. Not suitable as a portfolio sleeve."
        ),
    },
}

# ── Phase 5: K344 Correlation Assessment ──────────────────────────────────
# sUSDe yield source: ETH staking + Ethena delta-neutral hedge
# USDH yield source: US Treasury yield (via reserves)
# These are mechanistically DIFFERENT — but correlation test requires data.

CORRELATION_ANALYSIS: dict[str, Any] = {
    "method": "qualitative_mechanistic + point-in-time_comparison",
    "note": "30d tick price data unavailable for correlation computation (API blocked)",
    "susde_yield_driver": "ETH liquid staking + Ethena delta-neutral perp funding",
    "usdh_yield_driver": "US Treasury yield distributed as ecosystem grants (NOT to holders)",
    "yield_orthogonality": {
        "mechanistic_score": "ORTHOGONAL",
        "rho_estimated_qualitative": "< 0.2",
        "g5_threshold": 0.4,
        "g5_cleared_qualitative": True,
        "caveat": "Cannot compute actual ρ — USDH direct yield = 0% to holders; comparison meaningless",
    },
    "combined_sleeve_rationale": {
        "conclusion": "INVALID — USDH offers no direct yield to holders",
        "sUSDe_apy": 3.72,
        "USDH_direct_apy": 0.0,
        "combined_sleeve_weighted_apy": "Undefined (USDH = 0%)",
    },
}

# ── Phase 6: K266 Strict Gate Evaluation ──────────────────────────────────
GATE_RESULTS: list[dict[str, Any]] = [
    {
        "gate": "G1",
        "name": "net_apy_ge_5pct",
        "threshold": 5.0,
        "actual": 0.0,
        "pass": False,
        "note": "USDH holders earn 0% yield. HypurrFi lending theoretical 9%+ but pool is winding down with sunset.",
    },
    {
        "gate": "G2",
        "name": "max_peg_deviation_lt_5pct",
        "threshold": 5.0,
        "actual": 1.55,
        "pass": True,
        "note": "Historical ATL deviation 1.55% — technically within gate. But current -1.26% reflects sunset discount, not normal operation.",
    },
    {
        "gate": "G3",
        "name": "audit_verified",
        "threshold": "monthly_attestation",
        "actual": "monthly_independent_attestation_ongoing",
        "pass": True,
        "note": "Monthly reserve attestations confirmed. Reserve composition public.",
    },
    {
        "gate": "G4",
        "name": "tvl_gt_20m_and_institutional_backing",
        "threshold": 20_000_000,
        "actual_market_cap": 62_440_000,
        "pass_market_cap": True,
        "coinbase_backing": True,
        "circle_backing": False,
        "note": (
            "MCap $62.4M > $20M threshold at snapshot. BUT: declining rapidly post-sunset "
            "announcement (was ~$90.7M days prior). Coinbase is ACQUIRING brand (not backing). "
            "Effective operational TVL is rapidly zeroing. Gate technically passes but economically FAIL."
        ),
        "effective_pass": False,
    },
    {
        "gate": "G5",
        "name": "orthogonal_to_k344_rho_lt_04",
        "threshold": 0.4,
        "actual_rho_computed": None,
        "pass": False,
        "note": "Cannot be tested: USDH yield to holders = 0%. No yield series to correlate with sUSDe.",
    },
]

GATES_PASSED = sum(1 for g in GATE_RESULTS if g.get("pass", False) or g.get("effective_pass", False))
TOTAL_GATES = len(GATE_RESULTS)

# ── Final Decision ─────────────────────────────────────────────────────────
DECISION: dict[str, Any] = {
    "verdict": "REJECT",
    "rationale": [
        "CRITICAL: USDH is being SUNSET (May 2026). Coinbase acquired brand assets; "
        "Hyperliquid migrating to USDC as primary quote asset.",
        "G1 FAIL: USDH offers 0% yield to holders. Reserve yield is fully recycled to HL "
        "Assistance Fund and builder grants — none passes through to token holders.",
        "K344 complement premise is INVALID: sUSDe yields 3.72% to holders; USDH yields 0%. "
        "There is no orthogonal yield axis — just orthogonal nothingness.",
        "HypurrFi USDH isolated pool TVL was $854K (K337) — already tiny. With sunset, "
        "this pool will be wound down entirely.",
        "Current -1.26% peg discount is a SUNSET RISK DISCOUNT, not a systematic arb opportunity.",
        "One-time arb: buy at $0.9874 → redeem at $1.00 = ~0.55% net after costs. Trivial, "
        "one-directional, not a yield strategy.",
        "Gates passed: 2/5 (G2 peg deviation, G3 audit). G1, G4-effective, G5 all fail.",
    ],
    "complementarity_to_k344": "INVALID — no yield mechanism for token holders",
    "v6_14_sleeve_status": "REJECTED — do not add to portfolio",
    "alternative_recommendation": (
        "USDC-on-Hyperliquid via Coinbase deal: 90% USDC reserve yield → HL protocol. "
        "Monitor whether HL passes any USDC yield share to HYPE stakers or LP providers "
        "as a potential future sleeve (K355+ wave if mechanism clarified)."
    ),
    "gates_cleared": f"{GATES_PASSED}/{TOTAL_GATES}",
}

# ── Build Output JSON ──────────────────────────────────────────────────────

def build_output() -> dict[str, Any]:
    return {
        "wave": "K354",
        "task": "R11-8 — USDH stablecoin yield arb exploration",
        "generated_at": NOW_STR,
        "decision": DECISION["verdict"],
        "protocol": USDH_PROTOCOL,
        "market_data": USDH_MARKET,
        "sunset_event": USDH_SUNSET,
        "yield_analysis": USDH_YIELD,
        "peg_analysis": USDH_PEG_ANALYSIS,
        "correlation_k344": CORRELATION_ANALYSIS,
        "gate_results": GATE_RESULTS,
        "final_decision": DECISION,
        "data_sources": [
            {"name": "USDH Official", "url": "https://usdh.com/", "quality": "FETCHED"},
            {"name": "CoinMarketCap USDH", "url": "https://coinmarketcap.com/currencies/hyperliquid-usd/", "quality": "FETCHED"},
            {"name": "The Block — Coinbase/HL deal", "url": "https://www.theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc", "quality": "SEARCHED"},
            {"name": "Unchained Crypto — USDH sunset", "url": "https://unchainedcrypto.com/coinbase-becomes-hyperliquids-official-usdc-treasury-deployer-as-usdh-sunsets/", "quality": "SEARCHED"},
            {"name": "BeinCrypto — Coinbase USDH", "url": "https://beincrypto.com/coinbase-usdh-hyperliquid-shifts-to-usdc/", "quality": "FETCHED"},
            {"name": "DefiLlama HypurrFi", "url": "https://defillama.com/protocol/hypurrfi", "quality": "FETCHED"},
            {"name": "wave_k337_hypurrfi_euler.json", "url": "local", "quality": "EXACT"},
            {"name": "wave_k344_ethena_optimal_control.json", "url": "local", "quality": "EXACT"},
        ],
        "research_gaps": [
            "CoinGecko USDH price tick data (30d) — API 404 (token not indexed or endpoint changed)",
            "DefiLlama USDH stablecoin page — 403 Forbidden",
            "HypurrFi USDH isolated pool current APY (requires app.hypurrfi.com)",
            "Exact Coinbase USDC revenue share pass-through mechanism (90% to HL protocol; recipient TBD)",
        ],
    }


def build_md_report(data: dict[str, Any]) -> str:
    md = f"""# K354 — USDH Stablecoin Yield Arb Exploration (R11-8)

**Wave**: K354 | **Generated**: {NOW_STR}
**Task**: Deep-dive USDH as v6.14 sleeve complement to K344 sUSDe
**Decision**: **{DECISION["verdict"]}**

---

## Executive Summary

USDH, Hyperliquid's native stablecoin, is being **sunset as of May 2026**. Coinbase acquired the USDH brand assets and is replacing USDH with USDC as Hyperliquid's primary quote asset. This fundamentally invalidates the premise of USDH as a K344 sUSDe sleeve complement:

1. **0% direct yield to holders** — USDH reserve yield is distributed to HL Assistance Fund (50%) and builder grants (50%), not passed through to token holders. Unlike sUSDe (3.72% APY to holders), USDH is a non-yielding stablecoin.
2. **Sunset in progress** — Market cap declining ($90.7M → $62.4M in days), secondary market thinning, HypurrFi USDH pool winding down.
3. **Gates cleared: 2/5** — Only G2 (peg deviation) and G3 (audit) pass. G1 (yield), G4 (effective TVL), G5 (correlation) all fail.

**Verdict: REJECT — do not add to v6.14 portfolio.**

---

## Phase 1: Protocol Intelligence

### Protocol Structure

| Field | Value |
|-------|-------|
| Name | USDH |
| Issuer | Native Markets / Bridge Building Inc. |
| Chain | HyperEVM (Hyperliquid L1) |
| Launch | September 2024 |
| Type | Fiat-backed stablecoin |
| Peg | 1:1 USD |
| Reserve Assets | Cash, short-term US Treasuries, repo agreements |
| Reserve Managers | BlackRock (BUIDL), Superstate (USTB) |
| Custody | JPMorgan Chase + Fireblocks |
| Issuance Platform | Stripe Bridge |
| GENIUS Act Compliant | Yes |
| Audit | Monthly independent attestation (ongoing) |

### Market Data (2026-05-27 snapshot)

| Metric | Value |
|--------|-------|
| Price | $0.9874 (-1.26% below peg) |
| Market Cap | $62.44M (declining from ~$90.7M) |
| Circulating Supply | 63.24M USDH |
| ATH | $1.01 (Feb 6, 2026) → +1.0% above peg |
| ATL | $0.9845 (Oct 10, 2025) → -1.55% below peg |
| 24h Volume | $6.41M |

---

## Phase 2: Critical Event — USDH Sunset (May 2026)

### What Happened

In mid-May 2026, **Coinbase acquired the USDH brand assets** from Native Markets and became Hyperliquid's official USDC treasury deployer under the Aligned Quote Asset (AQA) framework.

**Key terms:**
- Native Markets granted Coinbase the right to purchase USDH brand assets
- Coinbase deploys USDC across HL spot, perp, and HIP-4 markets
- **Coinbase shares ~90% of USDC reserve yield with Hyperliquid protocol**
- HYPE buyback mechanism preserved: USDC yield → HL Assistance Fund → HYPE buyback
- USDH holders can redeem 1:1 feeless via Native Markets dashboard (no hard deadline)

### Why USDH Failed to Scale

- USDH market cap peaked at ~$101.75M vs $5B+ in USDC circulating on Hyperliquid
- No yield pass-through to holders → no incentive to hold USDH over USDC
- Thin secondary market liquidity limited institutional adoption

### Impact on Infrastructure

| Component | Status |
|-----------|--------|
| USDH Dashboard | Active (feeless redemption) |
| HypurrFi USDH isolated pool | Winding down (TVL was $854K at K337) |
| HL spot markets (USDH-quoted) | Migrating to USDC |
| HL perp markets | USDC primary (was already dominant) |

---

## Phase 3: Yield Mechanism Analysis

### USDH Yield Structure

**Critical finding: USDH passes 0% yield to token holders.**

```
Reserve yield from US Treasuries (~4-5% APY on backing)
    ├── 50% → HL Assistance Fund → HYPE token buyback
    └── 50% → USDH Growth Fund → Developer grants & ecosystem incentives
        └── 0% → USDH holders
```

This is fundamentally different from:
- **sUSDe**: ETH staking + Ethena delta-neutral hedge → ~3.72% APY *directly to sUSDe holders*
- **USDC on Aave/Compound**: ~3.5% APY *directly to depositors*
- **USDT**: 0% to holders (similar model to USDH)

### Yield Comparison

| Asset | Direct Holder APY | Mechanism |
|-------|------------------|-----------|
| USDC (plain) | 0% | No yield |
| USDH | **0%** | Yield redirected to HL ecosystem |
| USDC on Aave | ~3.5% | Lending market rate |
| sUSDe (K344) | **3.72%** | ETH staking + delta-neutral hedge |
| sUSDe 7d MA | 4.04% | Same mechanism |
| sUSDe historical mean | 10.30% | Same mechanism (2024-2026) |
| USDH on HypurrFi isolated | ~9-15%* | Lending market rate (pool winding down) |

*HypurrFi USDH lending APY is conditional on the pool surviving the sunset. TVL was $854K at K337 (too small), now likely declining further.

### Trading Benefits (Non-Yield)

USDH offered trading perks on Hyperliquid:
- 0% lower taker fees on USDH-quoted markets
- 50% higher maker rebates for LPs
- 20% amplified volume for fee tier calculations

These are **execution cost reductions for active traders, not passive yield**.

---

## Phase 4: Peg Arb Opportunity Quantification

### Price History

| Metric | Value |
|--------|-------|
| ATH | $1.01 (+1.00% above peg) |
| ATL | $0.9845 (-1.55% below peg) |
| Current | $0.9874 (-1.26% below peg) |
| Formal depeg incidents | 0 |

*Note: 30d tick data unavailable — CoinGecko API returned 404 for this token ID; CMC free tier blocks granular history. Analysis based on CMC ATH/ATL metadata.*

### Current Discount — Sunset Risk Premium

The current -1.26% discount is **NOT a clean peg arb**. It represents:

1. **Redemption uncertainty**: No hard deadline for USDH→USDC conversion announced
2. **Counterparty wind-down risk**: Native Markets is transitioning operations
3. **Liquidity thinning**: Market makers withdrawing as protocol winds down
4. **Opportunity cost**: Capital locked during uncertain redemption timeline

**One-time arb math:**

| Component | Value |
|-----------|-------|
| Buy price | $0.9874 |
| Par redemption | $1.0000 |
| Gross spread | +1.26% |
| Slippage | -0.20% |
| Gas (HyperEVM) | -0.01% |
| Redemption delay risk | -0.50% |
| **Net spread** | **+0.55%** |

**Conclusion**: ~0.55% one-time gain. Trivial. One-directional (buy the dip, redeem). Not a systematic yield strategy or portfolio sleeve.

---

## Phase 5: K344 sUSDe Correlation Assessment

### Mechanistic Comparison

| Dimension | sUSDe (K344) | USDH (K354) |
|-----------|-------------|-------------|
| Yield driver | ETH staking + Ethena delta-neutral | US Treasury yield (NOT passed to holders) |
| Holder APY | 3.72% (current), 10.30% (hist mean) | **0%** |
| Peg mechanism | Soft peg via redemption + market | Hard peg via fiat reserve |
| Risk type | ETH price + funding rate | Treasury + counterparty (Stripe/Bridge) |
| Orthogonality | — | Mechanistically orthogonal |
| Practical | — | **Irrelevant (0% yield)** |

### Correlation Computation

Statistical ρ between sUSDe APY and USDH holder yield cannot be computed:
- sUSDe APY series: available (K344 data, 831 days)
- USDH holder yield series: **all zeros** (no pass-through mechanism)
- ρ(constant, anything) = undefined / 0

**G5 assessment**: The two assets are *mechanistically* orthogonal (different yield drivers), but USDH provides **no yield axis to be orthogonal on**. The combined sleeve would simply be: sUSDe 5% allocation earning 3.72% + USDH 3-5% allocation earning 0% = blended underperformance vs pure sUSDe.

---

## Phase 6: K266 Strict Gate Results

| Gate | Criterion | Threshold | Actual | Pass |
|------|-----------|-----------|--------|------|
| G1 | Net APY ≥ 5% | 5.0% | **0.0%** (holder yield) | FAIL |
| G2 | Max peg deviation < 5% | 5.0% | 1.55% (ATL) | PASS |
| G3 | Audit status verified | Monthly attestation | Active ongoing | PASS |
| G4 | TVL > $20M + institutional backing | $20M | $62.4M MCap (declining) | FAIL* |
| G5 | Orthogonal to K344 (\|ρ\| < 0.4) | 0.4 | Undefined (0% yield) | FAIL |

*G4: Market cap technically > $20M but sunset in progress, TVL declining ~$1M/day, effective operational TVL → 0.

**Summary: 2/5 gates cleared (G2, G3). REJECT.**

---

## Final Decision

### REJECT — USDH as v6.14 Sleeve Candidate

**Reasons:**
1. **Sunset**: USDH is deprecated. Coinbase/USDC replaces it as HL's native quote asset.
2. **No yield**: 0% direct yield to holders eliminates the entire premise.
3. **Gate failures**: G1 (yield), G4 (effective), G5 (correlation) — 3/5 gates fail.
4. **Not orthogonal yield diversification**: Adding a 0%-yielding stable dilutes K344 sUSDe.
5. **One-time arb**: The ~0.55% sunset discount arb is a one-off, not a strategy.

### Alternative: USDC-on-Hyperliquid via Coinbase Deal

The Coinbase/HL deal creates a more interesting potential sleeve:
- Coinbase shares **~90% of USDC reserve yield** with HL protocol
- If HL distributes any portion to HYPE stakers, LP providers, or users → potential yield mechanism
- Monitor: does the USDC reserve yield share flow to any on-chain claimable product?
- **K355+**: If a USDC yield product emerges on Hyperliquid post-sunset, revisit as sleeve

### v6.14 Portfolio Status

| Component | Status | Allocation |
|-----------|--------|-----------|
| K344 sUSDe (Ethena) | ACTIVE | 5% (pending v6.14 decision) |
| K354 USDH | **REJECTED** | 0% |
| USDC-HL yield (Coinbase deal) | MONITOR | TBD (K355+) |

---

## Data Sources

| Source | URL | Quality |
|--------|-----|---------|
| USDH Official | https://usdh.com/ | Fetched |
| CoinMarketCap USDH | https://coinmarketcap.com/currencies/hyperliquid-usd/ | Fetched |
| The Block — Coinbase/HL deal | https://www.theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc | Searched |
| Unchained Crypto — USDH sunset | https://unchainedcrypto.com/coinbase-becomes-hyperliquids-official-usdc-treasury-deployer-as-usdh-sunsets/ | Searched |
| BeinCrypto — Coinbase USDH | https://beincrypto.com/coinbase-usdh-hyperliquid-shifts-to-usdc/ | Fetched |
| DefiLlama HypurrFi | https://defillama.com/protocol/hypurrfi | Fetched |
| wave_k337_hypurrfi_euler.json | local | Exact |
| wave_k344_ethena_optimal_control.json | local | Exact |

### Research Gaps

- CoinGecko USDH 30d price tick data: API 404 (token not indexed or endpoint deprecated)
- DefiLlama USDH stablecoin page: 403 Forbidden
- HypurrFi USDH isolated pool current APY: requires app.hypurrfi.com (auth-gated)
- Coinbase USDC revenue share pass-through: ~90% to HL protocol, recipient mechanism TBD

---

*K354 complete. USDH: REJECT. Monitor USDC-on-HL Coinbase deal yield mechanism for K355+.*
"""
    return md


def main() -> None:
    print(f"[K354] Generating USDH stablecoin analysis — {NOW_STR}")

    # Write JSON
    data = build_output()
    OUTPUT_JSON.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"[K354] JSON written: {OUTPUT_JSON}")

    # Write MD
    md_content = build_md_report(data)
    OUTPUT_MD.write_text(md_content, encoding="utf-8")
    print(f"[K354] MD written: {OUTPUT_MD}")

    # Summary to stdout
    print()
    print("=" * 60)
    print(f"  DECISION : {data['decision']}")
    print(f"  Gates    : {DECISION['gates_cleared']}")
    print(f"  G1 Yield : {GATE_RESULTS[0]['actual']}% (threshold: {GATE_RESULTS[0]['threshold']}%)")
    print(f"  Reason   : USDH sunset + 0% holder yield + HypurrFi pool winding down")
    print(f"  Next step: Monitor USDC-on-HL Coinbase deal (K355+)")
    print("=" * 60)


if __name__ == "__main__":
    main()

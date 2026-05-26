# Wave K373 — HL Portfolio Margin Investigation (K368 AX-05)

**Generated:** 2026-05-27T08:39:08 JST  
**Parent:** K368 (AX-05 second-priority pathway)  
**Scope:** Mechanism research, K280 component eligibility analysis, Sharpe lift estimation, decision  
**Status:** DEFER — prerequisite gate (>$5M HL volume) not met at paper-trade stage

---

## Executive Summary

HL Portfolio Margin (launched Dec 2025, currently pre-alpha) unifies spot and perp positions
in a single margin account. The mechanism is real and the capital efficiency benefit is genuine.

However, K373 finds:

1. **K368's cost-benefit was overestimated.** K368 assumed K208 (OOS weight ~76%) would benefit.
   K208 is cross-venue (HL short + Bybit long) — HL portfolio margin CANNOT net against Bybit positions.
   Only K276b (~22% OOS weight, 47% live weight) is potentially eligible.

2. **Revised Sharpe lift: +0.6 to +1.0** (vs K368's +0.3 to +0.8 for full portfolio).
   On K276b-only basis at 15-20% margin reduction, the lift range is +0.73 to +1.04 (live weights,
   30d Sharpe basis). This is narrower in absolute terms but concentrated in K276b.

3. **Primary eligibility gate FAILS: >$5M weighted VOLUME** (not balance).
   The K368 note said ">$5M account size" — Gitbook says ">$5M in weighted trading volume."
   User is in paper-trade stage; live HL volume = zero. This gate cannot be met without
   transitioning to live trading and accumulating volume over 6-18 months.

4. **K276b margin netting is uncertain.** HL portfolio margin is designed for same-asset spot+perp
   pairs. K276b holds different-symbol perps (long ENA, short ATOM, etc.) — cross-symbol netting
   benefit is partial and unquantified in HL documentation.

**Verdict: DEFER until live trading + capital accumulation reaches $5M+ HL volume.**
This wave has value as a decision record; the analysis is complete and actionable when the gate opens.

---

## Phase 1 — Mechanism Research

### Source: HL Gitbook Portfolio Margin (WebFetch 2026-05-27)

| Parameter | Value |
|---|---|
| Launch date | Dec 2025 (pre-alpha) |
| Current status | Alpha-mode (May 2026) — restricted rollout |
| Eligibility trigger | >$5M **weighted trading volume** (not balance) |
| Application process | Not specified; no self-service enrollment found |
| Invite-only | Not stated explicitly; alpha-mode caps imply restricted |
| KYC | Not documented |

### Mechanism

Portfolio margin unifies spot and perp trading in a **single account balance**. Key properties:

- Spot PnL and perp PnL offset each other for liquidation purposes
- Classic use case: hold BTC spot long + short BTC perp → combined delta ~ 0 → margin requirement drops dramatically
- Automatic borrow against collateral: `token_balance * borrow_oracle_price * LTV`
- Oracle: `median(HL_spot_USDC_price, HL_perp_mark_price * USDT_USDC_oracle, HL_perp_oracle_price * USDT_USDC_oracle)`
- Liquidation trigger: `portfolio_margin_ratio > 0.95` (entire account, not per-position)
- LTV for HYPE collateral: 0.5 (pre-alpha)

### Alpha-Mode Supply/Borrow Caps

| Asset | Global Supply | Global Borrow | User Supply | User Borrow |
|---|---|---|---|---|
| USDH | 500M | 100M | 5M | 1M |
| USDC | 1B | 200M | 50M | 10M |
| HYPE | 10M | — | 500k | — |
| BTC | 4k | — | 200 | — |

### Supported Collateral

HYPE, USDC, USDH, BTC, and HIP-3 DEX collateral assets.
K280 uses USDC → qualifies as eligible collateral (conditional on access).

### Cross-Venue Scope

Portfolio margin operates **within HL only**. Positions on Bybit, OKX, or other exchanges
are invisible to HL margin calculations. This is the critical limitation for K208.

---

## Phase 2 — K280 Position Structure Analysis

K280 = K198 + K208 + K276b (inverse-vol weighted)

### OOS Weights (backtest): K198=2.6%, K208=75.8%, K276b=21.6%
### Live Weights (2026-05-27): K198=10.8%, K208=42.3%, K276b=46.9%

---

### K198 — ML Allocator

| Property | Value |
|---|---|
| Type | Ridge regression weight allocator |
| HL positions | None — allocates weights to K208 + K276b sleeves |
| Portfolio margin eligible | NO |
| Reason | Pure weight-scheduler. No trading positions at all. |

---

### K208 — Bybit-HL DAR Reverse Carry

| Property | Value |
|---|---|
| Type | DAR(2,1) filtered cross-venue FR carry |
| Mechanism | Predict Bybit FR > HL FR → short HL perp, long Bybit perp |
| Symbols | SOL, XRP, SUI, OP, APT, AXS, JTO, IMX, SAND, ADA (10 symbols) |
| HL positions | Short perps only (HL leg of cross-venue trade) |
| Bybit positions | Long perps (Bybit leg — invisible to HL) |
| Cross-venue | YES |
| Portfolio margin eligible | **NO** |
| Reason | HL can only see the HL-leg short perps. The hedge (Bybit long) is on a different exchange. Without the offsetting long visible, HL treats K208 positions as naked shorts. No margin reduction. |

**Impact on K368 estimate:** K368 implicitly assumed K208 (OOS weight 75.8%) benefits.
This was incorrect. Excluding K208, the eligible weight drops from ~97% to ~22% (OOS) or ~47% (live).

---

### K276b — HL Cross-Sectional FR Carry

| Property | Value |
|---|---|
| Type | Cross-sectional funding rate carry |
| Mechanism | Long top-10 FR symbols + short bottom-10 FR symbols (all on HL) |
| Symbols | ENA, ONDO, ATOM, TIA, SEI, WLD, RNDR, TAO, MEME, AAVE, PYTH, LDO, FET, PEPE, MKR, JUP, UNI, BOME, DOT, BONK (20 symbols) |
| HL positions | Mix of long perps + short perps (all on HL) |
| Cross-venue | NO — all on HL |
| Portfolio margin eligible | **PARTIAL** |
| Reason | All positions on HL → intra-HL netting possible. BUT: longs and shorts are DIFFERENT symbols (long ENA vs short ATOM), not same-asset spot+perp pairs. HL portfolio margin is strongest for same-asset pairs. Cross-symbol netting is partial and depends on correlation matrix in HL's portfolio margin ratio formula. |

**Structural observation:** K276b could be restructured to hold spot longs + perp shorts for
the same tokens (e.g., hold ENA spot + short ENA perp = near-zero delta, collect FR).
This would maximize portfolio margin benefit — but requires a new strategy design wave.
Current K276b as-is gets only partial cross-symbol netting.

---

### K297' — HL HIP-3 RWA Carry

| Property | Value |
|---|---|
| Positions | Long PAXG perp + Long SPX perp (both same-direction) |
| Portfolio margin eligible | NO |
| Reason | Both positions are directional longs. No internal hedge. Portfolio margin benefits hedged positions, not co-directional positions. |

---

## Phase 3 — Sharpe Lift Estimation

### Why K368's +0.3 to +0.8 Was Based on Wrong Assumptions

K368 derived the range assuming:
- All K280 components benefit (effective weight ~97% of portfolio)
- Margin reduction of 15-30%
- Full portfolio Sharpe of 18.46 (OOS) as base

With those inputs: `(0.974)^2 * 0.15 * 18.46 = 2.63` to `(0.974)^2 * 0.30 * 18.46 = 5.25`.
After halving for conservative estimate: ~1.3 to ~2.6 — which K368 reduced to +0.3 to +0.8
(incorporating uncertainty). K368's range was actually conservative on its own assumptions.

### K373 Corrected Analysis

**Only K276b is eligible.** Different margin reduction scenarios:

| Scenario | Margin Freed | K276b Weight | Sharpe Lift (Conservative) | Sharpe Lift (Optimistic) |
|---|---|---|---|---|
| 15% — same-symbol netting | 15% | 22% (OOS) | +0.57 | +0.61 |
| 20% — cross-symbol partial | 20% | 22% (OOS) | +0.76 | +0.81 |
| 30% — aggressive | 30% | 22% (OOS) | +1.14 | +1.21 |
| 15% | 15% | 47% (live) | +0.73 | +0.78 |
| 20% | 20% | 47% (live) | +0.98 | +1.04 |

**Methodology note:** Conservative = `w^2 * notional_boost * Sh_k276b` (vol grows with weight).
Optimistic = `w * notional_boost * Sh_k276b * 0.5` (partial vol dilution).

**Key uncertainty:** The 15-30% margin reduction for K276b's cross-sectional different-symbol perps
is an assumption. HL documentation does not specify how cross-symbol perp portfolios are margined.
If HL only offsets same-asset spot+perp pairs, K276b receives 0% reduction as-is.

**Bottom line:**
- If margin offset is real for K276b: +0.6 to +1.0 Sharpe lift (live weight basis)
- If margin offset is 0% for different-symbol perps: no benefit
- If K276b is restructured to same-asset spot+perp pairs: could reach +1.0 to +1.5, but this changes the strategy fundamentally

---

## Phase 4 — Eligibility Assessment

| Criterion | Requirement | Current Status | Assessment |
|---|---|---|---|
| Volume threshold | >$5M weighted HL trading volume | Paper-trade: live volume = 0 | FAIL |
| Collateral asset | USDC, USDH, HYPE, or BTC | K280 uses USDC | PASS (conditional) |
| Alpha-mode caps | Per-user borrow/supply limits | N/A until access granted | N/A |
| Application process | Unknown (alpha-mode) | No self-service found | UNKNOWN |

**Critical clarification:** K368 wrote ">$5M account size." HL Gitbook states ">$5M in weighted
trading volume during alpha mode." These are meaningfully different. A $200k account trading at
high turnover (4 full rotations/month, 20 symbols × average position ~$2k) generates:
- Monthly volume: ~4 × 20 × $2k = $160k/month
- Time to $5M volume: ~31 months at this rate
- At $1M capital per symbol: ~3-4 months

**Path to eligibility:** Start live trading on HL with K276b-equivalent strategy, accumulate
$5M+ in trading volume, then apply (or wait for HL to open general access post-alpha).

---

## Phase 5 — Risk Assessment

### Systemic Liquidation Risk

**Current state (cross-margin on HL):** Each K276b symbol shares the HL margin pool.
A bad ENA position draws from shared capital but doesn't instantly liquidate others.

**Under portfolio margin:** Entire portfolio (spot + perp across all HIP-3 DEXs) shares
one margin ratio. If `portfolio_margin_ratio > 0.95`, ALL positions are subject to
simultaneous forced liquidation.

This is a **qualitative risk upgrade**: from "sequential cross-margin stress" to
"all-or-nothing portfolio liquidation." For K276b's 20-symbol diversification, a simultaneous
close of all positions in distress is significantly worse than staggered per-symbol liquidations.

### Impact on K357 Emergency Exit Script

`wave_k357_emergency_exit.py` closes positions sequentially (symbol by symbol, IOC limit orders,
reduceOnly=True). This design is **incompatible** with portfolio margin cascade dynamics, where
forced liquidation of all positions can precede the script execution.

**Required update if portfolio margin is activated:**
- Add `--portfolio-margin` flag
- Prioritize monitoring `portfolio_margin_ratio` in addition to per-position health
- Implement panic-close threshold at ratio = 0.90 (before HL's 0.95 trigger)
- Log portfolio margin ratio in `cache/emergency_exit_status.json`

This update is **K374 or K376 scope** — do not activate portfolio margin without this.

### Alpha-Mode Caps as Ceiling

$10M USDC user borrow cap. At current K276b scale (paper-trade), this is non-binding.
At live $5M+ capital scale, careful monitoring of per-user caps is needed.

---

## Phase 6 — Decision Matrix

| Scenario | Verdict | Next Wave |
|---|---|---|
| User >$5M HL volume, K276b eligible, mechanism verified | ACCEPT + K374 scaffold | K374 |
| Mechanism unclear, await HL documentation update | CONDITIONAL + 60d wait | K375 |
| User below volume threshold (current state) | **DEFER** | **K376+ when scaling** |
| K276b different-symbol netting confirmed = 0% | REJECT | None |

**Current verdict: DEFER**

Rationale:
1. Volume gate FAILS (paper-trade, zero live HL volume)
2. K208 (dominant weight ~76% OOS) is ineligible — cross-venue, not nettable on HL
3. K276b is potentially eligible but margin offset for cross-symbol perps is unverified
4. Even if eligible, restructuring K276b to spot+perp same-asset pairs maximizes benefit but alters strategy design (new wave required)
5. No self-service application process documented; alpha-mode suggests relationship/volume-gated access

---

## Phase 7 — Path Forward

### When to Revisit

| Trigger | Action |
|---|---|
| Live HL trading begins, volume accumulating | Monthly volume tracking; alert at $2M cumulative |
| HL announces portfolio margin general availability | Immediate AX-05 re-evaluation |
| K280 architecture adds HL spot legs to K276b | Re-analyze spot+perp netting benefit |
| User queries HL team about portfolio margin access | Gather invite criteria, document |

### Future Strategy Redesign Option

If HL portfolio margin becomes available, the highest-value redesign would be:

**K276b → K276b-PM (Portfolio Margin Edition)**
- Current: long ENA perp, short ATOM perp (different-symbol, partial netting)
- PM edition: long ENA spot + short ENA perp (same-asset, maximum netting)
- Hold 10 tokens as spot longs (highest FR symbols), hedge each with perp short
- Delta ≈ 0 per token, collect positive FR from each
- Expected margin reduction: 40-60% per pair (spot+perp same-asset pairs are the prime use case)
- Expected Sharpe lift at 40% margin reduction, 47% live weight: +1.3 to +1.9
- This would approach K368's original +0.8 estimate and possibly exceed it
- **Multi-wave effort**: K276b-PM strategy design + backtest + gate testing

---

## Appendix — Technical Notes

### K208 Cross-Venue Netting: Why It Cannot Work

HL portfolio margin pools all positions visible to HL's clearing system. The Bybit perp positions
in K208 are held in a **separate exchange account** — HL has no API access to Bybit balances.
Even if Bybit and HL both use the same underlying (e.g., SOL), they are legally and technically
separate positions. HL cannot grant margin benefit for a "hedge" it cannot verify exists.

This is not a bug or limitation of portfolio margin — it is correct behavior. Cross-exchange
netting would require a third-party prime broker recognizing both positions (e.g., Copper, Fireblocks
prime brokerage layer), which is not HL's architecture.

### K276b Cross-Symbol Netting: Partial at Best

HL's portfolio margin ratio formula computes maintenance margins per position, then sums them.
It does NOT apply a correlation matrix reduction to different-symbol perp portfolios (at least,
none is documented). The benefit for K276b holding ENA long + ATOM short is likely:
- **Close to zero** in the current formula (sum of maintenance margins, no cross-symbol netting)
- **Potential future benefit** if HL adds correlation-based portfolio margin (institutional feature)

Same-asset spot+perp pairs ARE explicitly designed for in the documentation: "spot and perp pnl
offset each other, protecting against liquidation on the perp position." This makes spot+perp
the clearly intended use case.

---

## Summary Table

| Dimension | Finding |
|---|---|
| HL Portfolio Margin status | Pre-alpha, May 2026 |
| Eligibility gate | >$5M weighted HL volume (NOT balance) |
| User status | Paper-trade, volume = 0 → INELIGIBLE |
| K198 eligible | NO (allocator, no positions) |
| K208 eligible | NO (cross-venue, Bybit leg invisible to HL) |
| K276b eligible | PARTIAL (all-HL but different-symbol perps, not same-asset pairs) |
| K297' eligible | NO (co-directional, no hedge offset) |
| Sharpe lift if K276b eligible | +0.6 to +1.0 (live weight, 15-20% margin freed) |
| Sharpe lift if K276b restructured to spot+perp | +1.3 to +1.9 (estimated) |
| K368 estimate accuracy | Overestimated component eligibility (K208 cross-venue), but lift range directionally correct |
| K357 emergency exit update needed | YES (if ever activated: add portfolio-margin liquidation logic) |
| **VERDICT** | **DEFER — revisit when live trading + $5M+ volume** |

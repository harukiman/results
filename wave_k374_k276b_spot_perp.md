# K374: K276b Spot+Perp Restructure Feasibility

**Wave:** K374  
**Last Updated:** 2026-05-27T08:51:41+0900 (JST)  
**Preceded by:** K373 (HL Portfolio Margin Investigation — DEFER verdict)  
**Task origin:** K373 identified restructuring K276b to same-asset spot+perp pairs as the "highest-value future option" with estimated Sharpe lift +1.3 to +1.9.  
**This wave:** Feasibility check only. Determine if multi-wave investment is warranted.

---

## Executive Summary

**VERDICT: REJECT**

The K276b spot+perp restructure is **not feasible today** and does not warrant multi-wave investment. Three independent blockers each independently disqualify the option:

1. **Coverage failure (35%, need 50%+):** Only 7 of 20 K276b symbols have any HL spot counterpart. The remaining 13 — ONDO, ATOM, TIA, RNDR, MEME, PYTH, LDO, FET, MKR, JUP, UNI, BOME, DOT — have no HL spot listing whatsoever.

2. **Wrapper token price mismatch (0/7 viable):** All 7 spot "matches" are wrapper tokens with drastically non-1:1 price ratios vs their perp counterparts (UENA/ENA = 0.000257:1, HSEI/SEI = 2.57:1, HTAO/TAO = 0.00287:1, PEPE/kPEPE = 0.154:1). These cannot form delta-neutral pairs without custom hedge ratios, and HL portfolio margin almost certainly will not recognize wrapper-to-perp as the same underlying for margin offset purposes.

3. **Liquidity failure (0/20 GOOD):** No K276b symbol achieves the $1M/day minimum spot liquidity. The single best candidate (HTAO) has $78K/day — well below even the "marginal" $100K threshold.

**K373's Sharpe lift estimate of +1.3 to +1.9 was wrong.** The estimate assumed clean same-asset pairs (ENA spot vs ENA perp). The reality is HL spot does not natively list the major DeFi/L1 tokens in K276b's universe.

**Sharpe lift achievable today: +0.0.**

**Multi-wave investment: Not warranted.** These are structural limitations outside CT Lab's control. Keep K276b as-is (cross-sectional perp-only).

---

## Phase 1: HL Spot Market Discovery

**API:** `POST https://api.hyperliquid.xyz/info {"type":"spotMetaAndAssetCtxs"}`  
**Fetched:** 2026-05-27T08:49:30 JST (live data)

### Universe Statistics

| Metric | Count |
|--------|-------|
| Total spot pairs (all quotes) | 300 |
| USDC-quoted pairs | 283 |
| Pairs with nonzero 24h volume | 107 |
| Pairs with ≥$1M/day volume | 9 |
| Pairs with $100K–$1M/day | 14 |
| Pairs with $10K–$100K/day | 14 |
| Pairs with $1–$10K/day | 70 |
| Pairs with zero volume | 176 |

**Key observation:** HL spot market is dominated by native/meme tokens (WOW, NEKO, PURR, HFUN, HYENA). The top 9 by volume ($1M+/day) are: WOW, NEKO, QQQ, QUANT, NBT, BUDDY, PURR, RUB, GLD. None of these are DeFi/L1 tokens that overlap with K276b's universe.

### Top 10 HL Spot Pairs by 24h Volume

| Pair | 24h USD Volume | Mark Price |
|------|---------------|------------|
| WOW/USDC | $178,778,461 | $59.49 |
| NEKO/USDC | $33,055,174 | $75,866 |
| QQQ/USDC | $9,387,281 | $570.91 |
| QUANT/USDC | $5,854,743 | $2,074 |
| NBT/USDC | $4,575,496 | $1.00 |
| BUDDY/USDC | $3,526,635 | $83.69 |
| PURR/USDC | $3,226,920 | $0.098 |
| RUB/USDC | $3,110,700 | $0.999 |
| GLD/USDC | $1,004,222 | $380.64 |
| USDT0/USDC | $486,751 | $0.174 |

---

## Phase 2: K276b Universe Alignment

**K276b_top20 symbols** (from wave_k276_curves.json, wave_k280_k272a_k276b.py):
```
ENA, ONDO, ATOM, TIA, SEI, WLD, RNDR, TAO, MEME, AAVE,
PYTH, LDO, FET, PEPE, MKR, JUP, UNI, BOME, DOT, BONK
```

**Perp note:** Two K276b symbols use k-prefix on HL perps:
- PEPE → `kPEPE` perp (1000x price scaling)
- BONK → `kBONK` perp (1000x price scaling)

### Symbol Coverage Check

| Symbol | Spot Token | Status | Spot Vol 24h | Perp Token | Perp Vol 24h |
|--------|-----------|--------|-------------|-----------|-------------|
| ENA | UENA | MATCH | $0 | ENA | $3,941,054 |
| ONDO | — | NO_MATCH | — | ONDO | $14,940,541 |
| ATOM | — | NO_MATCH | — | ATOM | $845,586 |
| TIA | — | NO_MATCH | — | TIA | $4,127,715 |
| SEI | HSEI | MATCH | $0 | SEI | $2,319,419 |
| WLD | UWLD | MATCH | $0 | WLD | $65,973,659 |
| RNDR | — | NO_MATCH | — | RNDR | $0 (dead) |
| TAO | HTAO | MATCH | $78,273 | TAO | $24,773,523 |
| MEME | — | NO_MATCH | — | MEME | $115,086 |
| AAVE | AAVE0 | MATCH | $719 | AAVE | $9,634,476 |
| PYTH | — | NO_MATCH | — | PYTH | $427,819 |
| LDO | — | NO_MATCH | — | LDO | $969,380 |
| FET | — | NO_MATCH | — | FET | $9,840,988 |
| PEPE | PEPE | MATCH | $0 | kPEPE | $2,076,506 |
| MKR | — | NO_MATCH | — | MKR | $0 (dead) |
| JUP | — | NO_MATCH | — | JUP | $2,632,879 |
| UNI | — | NO_MATCH | — | UNI | $2,158,324 |
| BOME | — | NO_MATCH | — | BOME | $58,860 |
| DOT | — | NO_MATCH | — | DOT | $1,463,105 |
| BONK | UBONK | MATCH | $0 | kBONK | $1,491,215 |

**Coverage rate: 7/20 = 35% (FAILS 50% threshold)**

---

## Phase 3: Spot Liquidity Assessment

### Wrapper Token Price Ratio Analysis

This is the critical sub-finding. Every "matching" spot token is a **wrapper** with a non-trivial price ratio to its perp:

| Symbol | Spot Token | Perp Token | Spot Price | Perp Price | Ratio | 1:1 Viable? |
|--------|-----------|-----------|-----------|-----------|-------|-------------|
| ENA | UENA | ENA | $0.0000250 | $0.09710 | 0.000257 | NO |
| SEI | HSEI | SEI | $0.17005 | $0.06608 | 2.573 | NO |
| WLD | UWLD | WLD | $0.000300 | $0.37810 | 0.000793 | NO |
| TAO | HTAO | TAO | $0.80042 | $279.06 | 0.002868 | NO |
| PEPE | PEPE | kPEPE | $0.000541 | $0.003518 | 0.1538 | NO (kPEPE=1000x) |
| AAVE | AAVE0 | AAVE | $0.6376 | $85.90 | 0.007422 | NO |
| BONK | UBONK | kBONK | $0.002750 | $0.005968 | 0.4608 | NO (kBONK=1000x) |

**0/7 matched pairs are 1:1 price-ratio viable.**

### Liquidity Tier Classification

| Symbol | Spot Vol 24h | Tier |
|--------|-------------|------|
| TAO (HTAO) | $78,273 | UNVIABLE (<$100K) |
| AAVE (AAVE0) | $719 | UNVIABLE (<$100K) |
| ENA (UENA) | $0 | UNVIABLE (zero) |
| SEI (HSEI) | $0 | UNVIABLE (zero) |
| WLD (UWLD) | $0 | UNVIABLE (zero) |
| PEPE (PEPE) | $0 | UNVIABLE (zero) |
| BONK (UBONK) | $0 | UNVIABLE (zero) |

**0/20 K276b symbols in GOOD tier (≥$1M/day). 0/20 in MARGINAL tier (≥$100K/day).**

---

## Phase 4: Pair Construction Logic

### Current K276b Architecture

```
K276b (cross-sectional FR carry, all HL perps):
  - Rank 20 symbols by HL 8h funding rate
  - Long perp: top 10 symbols by FR (collect positive FR)
  - Short perp: bottom 10 symbols by FR (collect negative FR)
  - Net: 10 long + 10 short perp positions, all on HL
  - FR capture on both sides (long AND short carry)
```

### Proposed Restructured K276b (Long-Only-Carry)

```
K276b_restructured (same-asset spot+perp, per-symbol):
  - For each symbol with FR > 0: long spot + short perp
  - Delta-neutral per pair (spot position cancels perp delta)
  - Net carry = FR collection on short perp + financing cost
  - CANNOT replicate: no short-side carry (no spot shorting on HL)
```

**Critical alpha loss:** The restructured version can only capture the long-carry side. Current K276b profits from both high-FR (long) and low-FR (short) symbols. Restructured K276b would lose ~50% of the FR alpha surface.

### The Wrapper Hedge Problem

Even if liquidity existed, the non-1:1 wrapper ratios create a **structural mismatch:**

- To delta-neutral hedge 1 ENA perp (price $0.097): need 1 ENA perp worth of spot, but UENA costs $0.000025. Hedge ratio = 0.097/0.000025 = ~3,880 UENA per 1 ENA perp.
- This is a non-trivial computation, different for each pair, and the ratio is **not constant** — UENA/ENA ratio can drift, creating residual unhedged delta.
- HL portfolio margin treats positions by their USD notional, not by wrapper conversion ratio. If it recognizes UENA-long vs ENA-perp-short as "same underlying," great. If not, **no margin offset at all**.

---

## Phase 5: Portfolio Margin Offset Estimate

### K373 Claim vs K374 Reality

| Scenario | Sharpe Lift | Basis |
|----------|------------|-------|
| K373 claim | +1.3 to +1.9 | Clean same-asset pairs (ENA spot + ENA perp) — assumed |
| K374 actual (today) | **+0.0** | Zero viable pairs |
| K374 hypothetical B | ~+0.47 | 10 clean pairs, 40% offset, 50% alpha retention |
| K374 hypothetical C | ~+1.17 | 15 clean pairs, 50% offset, 60% alpha retention |

### Why K373's Estimate Was Wrong

K373 stated: "long ENA spot + short ENA perp." This assumes:
1. ENA is listed as ENA/USDC spot on HL — **FALSE** (only UENA exists)
2. ENA spot has adequate liquidity — **FALSE** (UENA vol = $0/day)
3. Spot and perp are price-equivalent for delta-neutral — **FALSE** (UENA/ENA ratio = 0.000257)
4. HL portfolio margin recognizes the wrapper-to-perp offset — **UNVERIFIED, likely false**

All four assumptions fail simultaneously for all K276b symbols.

### What Portfolio Margin Actually Needs

For K276b to benefit from HL portfolio margin:
- **G1:** Native spot listing (e.g. ENA/USDC directly, not UENA wrapper)
- **G2:** Price equivalence (spot price ≈ perp price, within 5%)
- **G3:** Spot liquidity ≥ $1M/day per symbol
- **G4:** HL PM explicitly recognizes spot-perp pairs as offsetting

Current score: G1=FAIL, G2=FAIL, G3=FAIL, G4=UNKNOWN.

---

## Phase 6: K266 Strict Gates Feasibility (Qualitative)

| Gate | Status | Comment |
|------|--------|---------|
| G1: OOS Sharpe ≥ 1.0 | FAIL (hypothetical) | Zero viable pairs; long-only-carry loses ~50% alpha vs K276b |
| G5: Orthogonal vs K208 | PASS | K208 is cross-venue; restructured K276b would be intra-HL same-asset — still orthogonal |
| G7: Ann return > 5% | UNKNOWN | Cannot evaluate without viable pairs |
| G10 (new): Spot liq > $1M/day | FAIL | 0/20 K276b symbols meet threshold |

---

## Phase 7: Decision

### REJECT

**Rationale:** The restructuring is not feasible today. The structural blockers are:

1. **35% coverage, all wrappers with non-1:1 ratios** — HL spot market does not natively list K276b's DeFi/L1 token universe. All 7 "matches" require complex hedge ratio computation that undermines the delta-neutral assumption.

2. **Zero adequate liquidity** — Best candidate HTAO ($78K/day) is 13x below the minimum viable threshold. Most K276b matched tokens have $0 spot volume.

3. **Long-only-carry alpha loss ~50%** — Cannot replicate K276b's short-side FR capture without spot shorting, which HL spot does not support.

4. **PM eligibility still blocked** — K373 established that the $5M trading volume threshold for HL portfolio margin is unmet (paper-trade stage). Even if all spot issues were resolved, PM remains inaccessible.

5. **Wrapper basis risk** — Non-1:1 ratios mean residual delta exposure even after "hedging." If UENA/ENA ratio drifts 5%, a $500K ENA perp position with UENA spot hedge has $25K unhedged delta — violating delta-neutral assumption.

### Not Worth Multi-Wave Investment

A multi-wave investment (3–5 waves minimum per task description) requires:
- K375: spot liquidity analysis + PM recognition testing
- K376: hybrid architecture design
- K377+: backtesting restructured strategy

**None of these are worthwhile given the fundamental blockers.** The issues are not "needs more research" — they are observable market facts:
- HL spot does not list ONDO/ATOM/TIA/RNDR/MEME/PYTH/LDO/FET/MKR/JUP/UNI/BOME/DOT
- HTAO spot volume is $78K/day vs $24M/day for TAO perp (300x gap)
- Wrapper ratios are not 1:1 and drift over time

### Recommended Action

Keep K276b as-is (cross-sectional perp-only HL carry strategy). No architecture change.

### Revisit Triggers (future)

1. HL natively lists 10+ K276b symbols as direct USDC spot (e.g. ENA/USDC, ONDO/USDC, ATOM/USDC)
2. Any 10+ K276b symbols achieve >$1M/day spot volume on HL
3. HL portfolio margin exits alpha-mode to general availability (removes $5M volume gate)
4. K276b universe evolves to include tokens already native to HL spot (WOW, NEKO, PURR, etc.)

---

## Phase 8: Concentration Impact

### HL Concentration Analysis

| Aspect | Assessment |
|--------|-----------|
| New HL concentration | Zero — restructure stays entirely within HL |
| Ecosystem shift | From perp-only HL → spot+perp HL (more HL dependency) |
| Operational complexity | 2 legs per pair vs 1 leg; wrapper conversion adds state |
| Verdict | Concentration impact manageable IF feasibility existed — moot given REJECT |

Current K280 HL allocation (from K373): K276b live weight 46.9%. Adding K276b spot legs would increase HL capital deployment, but this is not the binding constraint — the binding constraints are spot market structure and liquidity.

---

## Phase 9: K357 Emergency Exit Implications

**Impact: None (REJECT verdict).**

If REJECT: No portfolio margin activation → K357 emergency exit script requires no changes.

If future ACCEPT (per revisit triggers): K357 would need `--portfolio-margin` flag to handle:
- All-or-nothing portfolio liquidation (PM ratio > 0.95 triggers simultaneous forced close)
- Current K357 closes positions sequentially per-symbol — incompatible with PM cascade dynamics
- Wrapper token unwinding: each symbol needs correct hedge ratio to determine spot quantity to close

**K357 enhancement scope:** Deferred to the hypothetical K375+/K376 wave if and when revisit triggers are met.

---

## Summary Table

| Dimension | Threshold | Actual | Pass/Fail |
|-----------|-----------|--------|-----------|
| Symbol coverage | ≥50% | 35% (7/20) | FAIL |
| Price ratio viable (1:1) | ≥50% | 0% (0/20) | FAIL |
| Spot liquidity GOOD (≥$1M) | ≥1 symbol | 0 symbols | FAIL |
| Spot liquidity MARGINAL (≥$100K) | ≥1 symbol | 0 symbols | FAIL |
| Best spot vol (HTAO) | ≥$100K/day | $78K/day | FAIL |
| HL PM eligibility | $5M vol | paper-trade (K373) | FAIL |
| Long-only alpha retention | ~80%+ | ~50% | FAIL |
| Multi-wave investment | STRONG feasibility | REJECT | N/A |

**All 7 dimensions fail. REJECT is the only defensible verdict.**

---

## Deliverables

| File | Description |
|------|-------------|
| `wave_k374_k276b_spot_perp.py` | Feasibility script with live API calls |
| `wave_k374_k276b_spot_perp.json` | Structured output (coverage table, liquidity table, decision) |
| `wave_k374_k276b_spot_perp.md` | This document (300–500 lines) |

---

## Appendix: Wrapper Token Glossary

| Spot Token | Perp Token | Wrapper Type | Ratio | Notes |
|-----------|-----------|-------------|-------|-------|
| UENA | ENA | U-prefix (unified) | ~0.000257 | Likely fractional unit |
| HSEI | SEI | H-prefix (HL-native) | ~2.573 | Different denomination |
| UWLD | WLD | U-prefix (unified) | ~0.000793 | Fractional unit |
| HTAO | TAO | H-prefix (HL-native) | ~0.00287 | 1 TAO ≈ 348 HTAO |
| PEPE | kPEPE | Direct spot | ~0.154 | kPEPE perp = 1000x PEPE |
| AAVE0 | AAVE | 0-suffix | ~0.00742 | Fractional unit |
| UBONK | kBONK | U+k prefix | ~0.461 | Both scaled, not 1:1 |

Note: "H" prefix tokens (HTAO, HSEI, HWAVE, HPEPE) appear to be HyperLiquid-native wrapped versions with non-trivial conversion ratios. "U" prefix tokens (UENA, UWLD, UBONK) appear to be unified/bridged assets with micro-denomination pricing. None of these form clean delta-neutral pairs with their perp counterparts.

---

*Wave K374 — Feasibility only. No production scripts modified.*  
*Decision: REJECT — keep K276b as cross-sectional perp-only carry strategy.*

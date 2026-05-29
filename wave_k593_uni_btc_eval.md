# K593 UNI-BTC FR Differential Paired-Trade Evaluation

**Wave:** K593  
**Date:** 2026-05-30 07:38 JST  
**Strategy:** UNI-BTC FR Differential Paired-Trade  
**Candidate:** Uniswap (UNI) — DeFi/DEX governance token, 10th cluster candidate  
**Decision:** **REJECT (Phase 0 vol ratio fail)**

---

## Executive Summary

K593 evaluates UNI (Uniswap AMM governance token) as the first DeFi/DEX cluster candidate. The hypothesis: Uniswap, as the largest DEX by TVL, would exhibit FR differential edge vs BTC driven by DeFi-specific demand cycles. The evaluation produces a **REJECT** decision at Phase 0 on vol ratio grounds (1.012x vs 1.5x threshold), with the full statistical analysis run for DeFi cluster documentation. The critical insight: **DeFi governance tokens are FR-undifferentiated from BTC** — a structural finding with implications for the entire DeFi cluster hypothesis.

| Metric | Value | Status |
|--------|-------|--------|
| Decision | REJECT | Phase 0 vol fail |
| Phase 0 vol ratio 6M | 1.012x | FAIL (< 1.5x) |
| Phase 0 vol ratio 365d | 1.240x | FAIL (< 1.5x) |
| Phase 0 vol ratio full | 1.191x | FAIL (< 1.5x) |
| Venues | HL + Bybit + OKX | PASS |
| OOS Sharpe (indicative) | 9.30 | n/a (Phase 0 blocked) |
| OOS Ann Return (indicative) | 2.89% | n/a |
| Gates passed (indicative) | 7/9 | n/a |
| G5 family corr (indicative) | 16/16 PASS | n/a |
| G8 cross-venue (indicative) | 0.051 FAIL | Structural |
| DeFi/DEX cluster status | NOT CONFIRMED | UNI vol fail |
| HL concentration delta | 0% | REJECT unchanged |
| Family rank | Unchanged (16 members) | UNI not added |

---

## Phase 0: Pre-screen

### Venue Check

| Venue | Status | Max Leverage | Note |
|-------|--------|-------------|------|
| HL | LISTED | 10x | marginTableId=52, 17,519 rows (May 2024–May 2026) |
| Bybit | Trading | 50x | UNIUSDT, 8h FR, 2,190 rows cached |
| OKX | live | 50x | UNI-USDT-SWAP confirmed |

Venue PASS — all three venues confirmed.

### Vol Ratio Analysis: FAIL

| Window | Vol Ratio | Threshold | Status |
|--------|-----------|-----------|--------|
| 6M (180d) | **1.012x** | 1.5x | **FAIL** |
| 365d | 1.240x | 1.5x | FAIL |
| Full (730d) | 1.191x | 1.5x | FAIL |

**Critical finding:** UNI vol ratio 6M = 1.012x — the **lowest of any token evaluated in the family history** (K449+). This is the structural signal: UNI FR tracks BTC FR almost perfectly.

**Why UNI vol ratio is this low:**
1. UNI is deployed on Ethereum — its demand is synchronized with the ETH/DeFi macro cycle, which itself tracks BTC
2. Uniswap governance token FR is driven by broad DeFi sentiment, not protocol-specific yield demand
3. Contrast with tokens that PASS phase 0: AXS (P2E yield cycles, 49.5x), SAND (metaverse narrative, 3.0x), FIL (storage market, ~4x), LINK (oracle middleware, 1.32x — barely passed)
4. DeFi governance tokens (UNI, AAVE at governance level, MKR) derive their FR from the same macro crypto cycle that drives BTC FR — no independent signal

**UNI FR statistics:**
- Mean: 0.00001492/hr (+1.49e-5) — slightly positive carry, near BTC level
- Std: 0.00002105/hr — close to BTC std (1.76e-5 full window)
- Range: [-0.000152, +0.000527] — narrow vs AXS [-0.001+], SAND [±0.003+]

**Phase 0 verdict: REJECT (vol ratio 1.012x < 1.5x)**

---

## Full Statistical Analysis (For DeFi Cluster Documentation)

Despite Phase 0 rejection, full analysis is run to characterize the DeFi cluster.

### Data

- **UNI FR:** 17,519 rows, 2024-05-24 to 2026-05-24 (730d full history)
- **BTC FR:** 17,512 rows, 2024-05-23 to 2026-05-23
- **Aligned:** 17,484 rows (~724.5 trading days)
- **OOS window:** 218.5 days (30.2% of total)

### ADF / OU Analysis

| Test | Value | Status |
|------|-------|--------|
| ADF stat | -12.391 | — |
| ADF p-value | 0.000000 | Stationary ✓ |
| OU half-life | 3.32h (0.14d) | Fast mean reversion |
| OU theta | 0.2087 | Strong mean reversion |
| OU R² | — | — |

The differential is stationary (ADF p < 0.001) with ultra-fast mean reversion (3.32h). This is the shortest OU half-life in the family. The rapid reversion confirms UNI and BTC FR are tightly coupled — deviations from their near-zero differential correct almost immediately.

### Grid Search (Best Windows)

| Window | OOS Sharpe | Ann Return | Trades/yr |
|--------|-----------|------------|-----------|
| 336h (14d) | 12.38 | 2.66% | 16.7 |
| 240h (10d) | 10.73 | 2.56% | 23.4 |
| 720h (30d) | 10.71 | 2.22% | 13.4 |
| **96h (4d)** | **9.30** | **2.89%** | **48.4** |
| 168h (7d) | 8.21 | 2.26% | 35.1 |

Best G6-compliant (≥30 trades/yr): **w=96h**, OOS Sh=9.30, trades=48.4/yr.

### IS/OOS Metrics (w=96h, indicative)

| Period | Days | Sharpe | Ann Return | Max DD | Trades/yr |
|--------|------|--------|------------|--------|-----------|
| IS | 506.0 | 11.79 | 4.07% | -0.49% | 50.5 |
| OOS | 218.5 | 9.30 | 2.89% | -0.39% | 48.4 |
| Full | 724.5 | 11.08 | 3.72% | -0.49% | 49.9 |

Note: OOS Sharpe of 9.30 is solid statistically, but the economic edge is thin — 2.89% OOS Ann Return at 1x leverage = 11.58% at 4x. This is below most family members despite the good Sharpe (low absolute return, very low volatility signal).

### Permutation & DSR Tests

| Test | Value | Threshold | Status |
|------|-------|-----------|--------|
| Perm p-value | 0.000000 | ≤0.05 | PASS |
| Real OOS Sharpe | 9.2966 | — | — |
| Perm mean Sharpe | -0.064 | — | — |
| DSR t-stat | 7.194 | — | — |
| DSR p-value | 0.000000 | <0.0056 | PASS |

Statistical quality is real — but the signal exists in a very small return space.

---

## §6 Gates (Indicative — Phase 0 Blocked)

| Gate | Value | Status |
|------|-------|--------|
| G1 OOS Sharpe ≥ 1.0 | 9.30 | PASS |
| G2 Perm p ≤ 0.05 | 0.000 | PASS |
| G3 DSR Bonferroni | p=0.000 | PASS |
| G4 Walk-forward | 10/12 pos | **FAIL** |
| G5 Family corr | 16/16 PASS | PASS |
| G6 Trades/yr ≥ 30 | 48.4 | PASS |
| G7 Ann return 4x > 5% | 11.58% | PASS |
| G8 Cross-venue | 0.051 | **FAIL** |
| G9 Data sufficiency | 218.5d | PASS |

**7/9 PASS** (G4, G8 fail). Even setting aside Phase 0, G8 FAIL is significant:
- HL vs Bybit signal corr = 0.051 — near-zero correlation
- This confirms HL 1h FR and Bybit 8h FR for UNI have divergent settlement mechanics
- The edge may be HL-venue-specific, not cross-venue robust

### Walk-Forward Detail (12-fold IS=90d/OOS=30d)

| Fold | OOS Period | Sharpe | Result |
|------|-----------|--------|--------|
| 1 | 2025-05-28 | 8.74 | PASS |
| 2 | 2025-06-27 | 8.30 | PASS |
| 3 | 2025-07-27 | -8.25 | **FAIL** |
| 4 | 2025-08-26 | 36.56 | PASS |
| 5 | 2025-09-25 | 20.21 | PASS |
| 6 | 2025-10-25 | 4.22 | PASS |
| 7 | 2025-11-24 | 18.42 | PASS |
| 8 | 2025-12-24 | -7.98 | **FAIL** |
| 9 | 2026-01-23 | 11.48 | PASS |
| 10 | 2026-02-22 | 13.21 | PASS |
| 11 | 2026-03-24 | 28.97 | PASS |
| 12 | 2026-04-23 | 29.67 | PASS |

10/12 positive. Negative folds: Jul-Aug 2025 (BTC bull regime spike, UNI FR briefly elevated with BTC), Dec 2025 (BTC bull peak, DeFi FR convergence to BTC).

---

## G5 Family Cross-Correlations (Indicative)

All 16/16 PASS. ETH G5a = +0.0445 (critical test — UNI on ETH, but FR signals distinct). LINK G5m = +0.1662 (DeFi adjacency, PASS).

| Gate | Pair | Corr | Status | Note |
|------|------|------|--------|------|
| G5a | ETH-BTC | +0.045 | PASS | CRITICAL: DeFi DEX vs ETH L1 — distinct |
| G5b | SOL-BTC | -0.003 | PASS | — |
| G5c | AVAX-BTC | +0.052 | PASS | — |
| G5d | ATOM-BTC | -0.036 | PASS | — |
| G5e | INJ-BTC | +0.040 | PASS | INJ DEX vs UNI AMM |
| G5f | SEI-BTC | -0.010 | PASS | — |
| G5g | TIA-BTC | -0.059 | PASS | — |
| G5h | APT-BTC | -0.037 | PASS | — |
| G5i | FIL-BTC | -0.015 | PASS | — |
| G5j | K280 BTC-carry | -0.061 | PASS | — |
| G5k | RENDER-BTC | -0.061 | PASS | — |
| G5l | TAO-BTC | +0.014 | PASS | — |
| G5m | LINK-BTC K557 | +0.166 | PASS | DeFi infra adjacent but distinct |
| G5n | TON-BTC K571 | +0.033 | PASS | — |
| G5o | SAND-BTC K583 | -0.022 | PASS | — |
| G5p | AXS-BTC K591 | -0.030 | PASS | — |

Key finding: ETH G5a = 0.045 (well below 0.40). This suggests UNI and ETH FR signals are orthogonal despite UNI being deployed on Ethereum. The UNI FR differential signal operates independently of the ETH-BTC FR differential signal — but this is moot given Phase 0 failure.

LINK G5m = 0.166 — highest correlation in the family, reflecting DeFi infra adjacency. Still well below 0.40 threshold.

---

## Cross-Venue G8 (Indicative)

- HL vs Bybit signal corr: **0.051** (FAIL, threshold=0.55)
- HL vs Bybit diff corr: 0.140
- Bybit UNI rows: 2,190 (8h settlements)
- Overlap: 17,389h (~725d)

G8 FAIL is structural: HL 1h settlement vs Bybit 8h settlement creates divergent signals. Unlike AXS (G8=0.627 PASS), UNI's near-BTC vol ratio means the HL-Bybit signal divergence dominates. This suggests the UNI FR edge (if any) is venue-specific to HL's 1h settlement mechanism.

---

## Profit Projection (Indicative — BLOCKED)

| Scenario | Annual Return | USDC/yr |
|----------|--------------|---------|
| 4x leverage | 11.58% | — |
| $10M, 1% alloc | — | **$11,577/yr** |
| $10M, 2% alloc | — | $23,154/yr |
| $100M, 1% alloc | — | $115,769/yr |

**These are blocked** — Phase 0 REJECT prevents deployment. For comparison, this is the lowest profit projection in the family, reflecting the thin absolute return from the compressed UNI-BTC FR differential.

---

## HL Concentration Impact

**UNI REJECT → HL concentration unchanged at 65.0%.**

No allocation change. Baseline (with AXS + SAND paper allocs):
- v6.28+ HL: 64-65%
- + UNI: N/A (rejected)

---

## DeFi Cluster Analysis

### Status: NOT CONFIRMED

The DeFi/DEX cluster hypothesis is **not confirmed** via UNI. This is the primary deliverable of K593.

### Why DeFi Governance Tokens Fail Phase 0

| Token Type | FR Driver | Vol Ratio (6M) | Result |
|------------|-----------|----------------|--------|
| AXS (P2E game) | P2E yield cycle, SEA retail | 49.5x | PASS |
| SAND (Metaverse) | Land speculation, NFT cycles | 3.01x | PASS |
| FIL (Storage) | Storage market, retrieval demand | ~4x | PASS |
| LINK (Oracle) | Oracle request cycles, DeFi infra | 1.32x | PASS (marginal) |
| **UNI (DEX gov)** | **Broad DeFi sentiment (=BTC)** | **1.012x** | **FAIL** |

DeFi governance tokens are **narrative-synchronized** with BTC because:
1. DeFi "season" cycles align with BTC bull runs (DeFi TVL grows with BTC price)
2. UNI governance voters are also BTC/ETH holders → same demand profile
3. AMM protocol revenue (which UNI governs) scales with total crypto market activity
4. No independent yield mechanism: UNI holders don't earn protocol fees directly

### DeFi Cluster Next Candidates

In order of expected independence from BTC FR:

1. **AAVE-BTC**: Lending protocol — borrow rates driven by liquidation cycles independent of BTC FR? Variable interest rates create distinct demand spikes (forced liquidation events).
2. **CRV-BTC**: veCRV yield locking — the "curve wars" bribe economy may create distinct FR patterns from AMM governance.
3. **MKR-BTC**: DAI stability module — DAI peg maintenance creates collateral demand cycles distinct from BTC FR.
4. **SUSHI-BTC**: DEX v2 alternative — same category as UNI, likely same vol ratio profile.
5. **JUP-BTC** (Solana DEX): If listed on HL, Solana ecosystem DeFi may show SOL-correlated FR rather than BTC-correlated.

### Structural Insight

The DeFi cluster may not be valid at the **governance token** level. Protocol utility tokens (which pay actual yield to holders) might show distinct FR:
- Compare: UNI (governance only) vs hypothetical UNI-v4 fee switch (direct yield)
- The Uniswap fee switch debate is precisely about this: does UNI governance = protocol yield?
- Currently: UNI ≈ BTC FR (no fee switch) → governance premium insufficient for FR signal

---

## Family Rank (Unchanged)

| Rank | Pair | OOS Sharpe | Ecosystem | Status |
|------|------|-----------|-----------|--------|
| 1 | APT-BTC | 51.10 | Move-VM | ACCEPT |
| 2 | ATOM-BTC | 50.79 | Cosmos | ACCEPT |
| 3 | SEI-BTC | 48.10 | Cosmos | ACCEPT |
| 4 | AVAX-BTC | 43.89 | Avalanche | ACCEPT |
| 5 | SAND-BTC | 33.63 | Gaming/UGC | ACCEPT COND |
| 6 | FIL-BTC | 21.77 | Storage | ACCEPT COND |
| 7 | AXS-BTC | 17.82 | Gaming/P2E | ACCEPT COND ★ NEW |
| 8 | SOL-BTC | 16.30 | Solana | ACCEPT |
| 9 | RENDER-BTC | 15.30 | AI/GPU | ACCEPT COND |
| 10 | TIA-BTC | 14.44 | Cosmos | ACCEPT |
| 11 | LINK-BTC | 13.78 | Oracle | ACCEPT COND |
| 12 | ICP-BTC | 12.53 | Compute/Cloud | ACCEPT COND |
| 13 | INJ-BTC | 11.23 | Cosmos | ACCEPT |
| 14 | TON-BTC | 8.40 | Social/Messaging | ACCEPT COND |
| 15 | ETH-BTC | 5.66 | Ethereum | ACCEPT |
| 16 | TAO-BTC | 5.27 | AI/Training | ACCEPT COND |

UNI rejected — family remains 16 members. DeFi/DEX cluster not added.

---

## Confirmed Cluster Taxonomy (Post-K593)

| # | Cluster | Members | Status |
|---|---------|---------|--------|
| 1 | L1 (EVM) | APT, SOL, AVAX, ETH | Confirmed |
| 2 | Cosmos | ATOM, INJ, TIA, SEI | Confirmed |
| 3 | Storage | FIL | Confirmed |
| 4 | AI/GPU | RENDER | Confirmed |
| 5 | AI/Training | TAO | Confirmed |
| 6 | Oracle | LINK | Confirmed |
| 7 | Social/Messaging | TON | Confirmed |
| 8 | Gaming/UGC | SAND | Confirmed |
| 9 | Gaming/P2E | AXS | Confirmed |
| 10 | PoW/BlockDAG | KAS | Confirmed |
| 11 | Compute/Cloud | ICP | Confirmed |
| — | DeFi/DEX | UNI (REJECTED) | NOT CONFIRMED |

11 confirmed clusters. DeFi remains a hypothesis.

---

## Next Pivot

**Primary:** AAVE-BTC — Lending protocol evaluation. Hypothesis: borrow rate cycles driven by forced liquidation events may be less correlated with BTC FR than AMM governance.

**Alternative pivots:**
- CRV-BTC: veCRV yield mechanics (gauge voting → distinct bribe cycles)
- MKR-BTC: DAI collateral demand (stability module → distinct from BTC FR)
- ARB-BTC / OP-BTC: L2 rollup cluster (distinct from L1 FR?)

**DeFi cluster status:** Open hypothesis. UNI is the worst-case DeFi token for FR independence. AAVE may show lending-specific cycles.

---

## Files

- `wave_k593_uni_btc_eval.py` — K339 REPO_ROOT pattern, full evaluation
- `wave_k593_uni_btc_eval.json` — Machine-readable results
- `wave_k593_uni_btc_eval.md` — This report
- `report.html` — Badge updated (K593 REJECT, DeFi DEX cluster status)

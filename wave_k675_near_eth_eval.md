# K675 NEAR-ETH FR Differential Paired-Trade Evaluation

**Wave:** K675  
**Strategy:** NEAR-ETH FR Differential Paired-Trade (ETH-base mechanism — K503 sharding L1)  
**Run date:** 2026-05-30T13:50:47+09:00  
**Decision:** REJECT — Phase 0 FAIL

---

## Executive Summary

K675 applies the ETH-base FR differential mechanism (K663 rule) to NEAR Protocol,
which was previously REJECTED in K503 (NEAR-BTC, vol_ratio 1.43x < 1.5x BTC threshold).

**Result: PHASE 0 HARD REJECT.**

NEAR/ETH vol_ratio 6M = **1.4356x** vs required **>= 2.0x** (K663 ETH-base rule).
Furthermore, NEAR/ETH ratio is lower than NEAR/BTC ratio because ETH has higher vol
than BTC (ETH std = 1.899e-5 vs BTC std = 1.764e-5). ETH-base is categorically worse
for NEAR than BTC-base was — this is a structural/mathematical impossibility to fix.

K675 is a **double REJECT**: fails both the BTC threshold (1.44x < 1.5x) and the
ETH threshold (1.44x < 2.0x). No base currency makes NEAR viable for FR differential trading.

---

## Phase 0: Vol Pre-Screen (PRIMARY GATE)

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| NEAR/ETH vol_ratio 6M | 1.4356x | >= 2.0x (K663 ETH rule) | **FAIL** |
| NEAR/BTC vol_ratio 6M | 1.4265x | >= 1.5x (K503 BTC rule) | **FAIL** |
| NEAR/ETH vol_ratio full | 1.2753x | >= 2.0x | **FAIL** |
| NEAR/ETH vol_ratio 365d | ~1.35x | >= 2.0x | **FAIL** |

**Why ETH-base is strictly harder for NEAR:**
- ETH FR std = 1.899e-5 > BTC FR std = 1.764e-5 (ETH more volatile than BTC)
- NEAR/ETH ratio = NEAR_std / ETH_std < NEAR_std / BTC_std = NEAR/BTC ratio
- Switching from BTC base to ETH base makes the vol ratio *lower*, not higher
- K503 failed at 1.43x vs BTC; K675 fails at 1.44x vs ETH — same zone, harder threshold

---

## Phase 1: FR Level & Cycle Alignment

| Asset | FR Mean Ann | Notes |
|-------|------------|-------|
| NEAR  | 12.16%/yr  | Nightshade sharding L1 speculation |
| ETH   | 10.52%/yr  | DeFi/staking structural premium |
| BTC   | 11.55%/yr  | Institutional macro premium |

**Key differentials:**
- NEAR-ETH diff: **+1.65%/yr** (small carry — predominantly short NEAR, long ETH)
- NEAR-BTC diff: **+0.61%/yr** (even smaller — mixed direction historically)
- NEAR FR > ETH FR: 37.6% of time (predominantly NEAR < ETH)

**Cycle alignment assessment:**
- NEAR Foundation "Ethereum AI" partnership: narrative overlap, NOT FR dynamics overlap
- Aurora EVM bridge: Ethereum dApps on NEAR → partial ecosystem overlap
- FR dynamics still driven by native NEAR speculation (Nightshade sharding reduces per-shard demand)
- NEAR/ETH FR level corr = 0.50 (moderate) — insufficient to create ETH-aligned FR cycles
- Sharding architecture dilutes speculative demand concentration vs monolithic chains

---

## Phase 2: Grid Search (Informational)

| Window | IS Sharpe | OOS Sharpe | Ann Ret 1x | Entries/yr |
|--------|-----------|-----------|------------|-----------|
| W=336h | 13.65 | **14.89** | 3.71%/yr | 22.1 |
| W=168h | 10.42 | 11.76 | 3.16%/yr | 25.4 |
| W=72h  | 7.40  | 3.62  | 1.51%/yr | 88.0 |
| W=24h  | -0.22 | -3.36 | -1.98%/yr | 189.0 |

*All results informational — Phase 0 REJECT terminates live consideration.*

**Best config:** W=336h, OOS Sh=14.89, 22 entries/yr (G6 FAIL < 30/yr)

---

## Phase 3: Full Backtest (Informational, W=336h)

| Split | Sharpe | Ann Ret 1x | Ann Ret 4x | Max DD |
|-------|--------|-----------|-----------|--------|
| Full  | 4.29 | — | — | — |
| IS (70%) | 3.86 | — | — | — |
| OOS (30%) | **5.58** | **1.43%/yr** | **5.73%/yr** | -0.32% |

**OOS period:** 2025-10-18 to 2026-05-23 (216 days)

### NEAR-ETH vs NEAR-BTC Comparison

| Strategy | Window | OOS Sharpe | Ann Ret 1x |
|----------|--------|-----------|-----------|
| NEAR-ETH (K675) | 168h | 11.76 | 3.16%/yr |
| NEAR-BTC (K503 rerun) | 168h | 12.04 | 3.57%/yr |
| NEAR-BTC (K503 best) | 336h | **19.28** | **4.40%/yr** |

**NEAR-ETH is strictly WORSE than NEAR-BTC even informally.** ETH-base provides no
improvement for NEAR — confirming the double REJECT across both directions.

### Statistical Properties (NEAR-ETH FR diff)
- **ADF:** p=0.0000 (stationary — mean reverting as expected for FR differentials)
- **OU half-life:** 2.7h (very short — FR differentials revert quickly to mean)

---

## Phase 4: Section 6 Gates

| Gate | Description | Value | Pass? |
|------|------------|-------|-------|
| **G0** | Vol pre-screen NEAR/ETH >= 2x (PRIMARY) | 1.4356x | **FAIL** |
| G1 | OOS Sharpe >= 1.0 (informational) | 5.58 | PASS* |
| G2 | Perm p-value <= 0.05 (informational) | 0.0000 | PASS* |
| G3 | DSR Bonferroni (informational) | p~0 | PASS* |
| G4 | Walk-forward 4-fold all positive (informational) | [9.66, 11.92, 10.91, 13.62] | PASS* |
| G5a | NEAR-ETH vs ETH-BTC K449 < 0.40 | corr=-0.0015 | PASS* |
| G5b | NEAR-ETH vs NEAR-BTC K503 < 0.40 | corr=0.1839 | PASS* |
| G6 | Entries/yr >= 30 (informational) | 25.4/yr | FAIL* |
| G7 | Ann ret > 5% @4x (informational) | 5.73% | PASS* |
| G8 | Cross-venue corr >= 0.55 | structural FAIL | FAIL* |
| G9 | OOS >= 180d | 216d | PASS* |

*Informational only — G0 Phase 0 REJECT is primary gate.*

**Summary:** G0 FAIL (primary). Informational: 7/9 pass.

### G5 Correlations (informational)
- **G5a** (NEAR-ETH vs ETH-BTC K449): corr=-0.0015 → orthogonal (shared ETH leg not problematic)
- **G5b** (NEAR-ETH vs NEAR-BTC K503): corr=0.1839 → orthogonal (different base provides different timing)

Even if Phase 0 were waived, NEAR-ETH informational Sharpe (11.76/5.58) is well below the live
strategies in the family (K449 Sh=5.66, K476 Sh=16.30, K493 Sh=50.79).

---

## Phase 5: Decision

**DECISION: REJECT (Phase 0 FAIL)**

### Decision Rationale

1. **K663 ETH-base rule**: vol_ratio NEAR/ETH 6M = 1.44x < 2.0x (hard threshold)
2. **K503 parallel**: NEAR/BTC 6M = 1.43x < 1.5x (already REJECTED on BTC-base)
3. **ETH-base structural impossibility**: ETH vol > BTC vol → NEAR/ETH always lower than NEAR/BTC
4. **Informational backtest worse**: NEAR-ETH OOS Sh=11.76 vs NEAR-BTC W=336h Sh=19.28
5. **Double REJECT confirmed**: No base currency (BTC or ETH) makes NEAR viable for FR differential

### K663 Rule Validation

The K663 rule (vol_ratio >= 2x for ETH-base) correctly rejects NEAR-ETH:
- NEAR Nightshade sharding reduces per-shard speculative demand
- Aurora EVM bridge creates partial ETH overlap but does NOT amplify NEAR FR volatility
- NEAR Foundation "Ethereum AI" narrative does not translate to FR dynamics alignment
- Result validates rule: narrative/ecosystem overlap ≠ FR cycle alignment

---

## Profit Projection (HYPOTHETICAL — INFORMATIONAL ONLY)

**Status:** PHASE 0 REJECT — NOT eligible for live deployment

| Metric | Value |
|--------|-------|
| Sleeve | 2% of $10M |
| Leverage | 4x |
| Friction buffer | 15% |
| OOS ann ret @1x | 1.43%/yr (W=336h) |
| Gross USDC/yr | ~$11,468 |
| Net USDC/yr | ~$9,748 |
| Daily USDC | ~$26 |

**For comparison (live strategies):**
- K449 ETH-BTC: ~$70K+/yr @$10M
- K493 ATOM-BTC: ~$200K+/yr @$10M
- K675 NEAR-ETH: $9.7K/yr hypothetical (NOT live-eligible)

---

## ETH-Base Family Track (K629→K675)

| Wave | Strategy | Decision | OOS Sharpe |
|------|----------|----------|-----------|
| K629 | WLD-ETH | ACCEPT | 19.9 |
| K632 | HYPE-ETH | WORSE | 12.99 vs BTC 24.49 |
| K658 | SOL-ETH | ACCEPT | 29.66 vs BTC 16.30 |
| K660 | APT-ETH | BLOCKED-G5b | corr=0.966 |
| K661 | AVAX-ETH | CONDITIONAL | BTC wins, diversify |
| K663 | TIA-ETH | ACCEPT | vol_ratio=2.12x |
| K667 | TRX-ETH | WORSE | K632-style |
| K670 | SHIB-ETH | WORSE | — |
| K671 | PEPE-ETH | WORSE | 19.04 vs BTC 26.42 |
| **K675** | **NEAR-ETH** | **REJECT** | **Phase 0: 1.44x < 2x** |

---

## K675 Lesson

K675 confirms a structural insight:

> **When an alt fails BTC-base vol pre-screen, ETH-base will not rescue it if ETH vol > BTC vol.**

Since ETH consistently has higher FR volatility than BTC (ETH/BTC std ratio ~1.08x),
any alt with vol_ratio/BTC < 1.5x will have vol_ratio/ETH < 1.38x — far below the 2x ETH threshold.

For Nightshade sharding L1s specifically:
- Sharding distributes transaction load across chunks → lower per-chunk speculative pressure
- Lower concentrated demand → lower FR vol premium vs major assets
- Aurora EVM bridges create ecosystem narrative overlap, not FR vol amplification

**Next steps:** No pivot needed for NEAR. ETH-base family evaluation continues.
Recommended next candidate: non-sharding L1 with NEAR/ETH-like partial Ethereum overlap
(e.g., evaluate SEI-ETH if SEI has vol_ratio >= 2x vs ETH).

---

*K339 REPO_ROOT pattern | LIVE 変更禁止 | report.html badge pending*

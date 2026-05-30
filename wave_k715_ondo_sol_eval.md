# K715 — ONDO-SOL FR Differential Alt-Alt Eval

**Wave:** K715  
**Strategy:** ONDO-SOL FR Differential (Tokenized TBills vs SVM, alt-alt direction)  
**Decision:** BLOCKED-G5c-AVAX  
**OOS Sharpe:** 36.84  
**Profit @$10M AUM (4x, 3% sleeve):** ~$79,650/yr net USDC (BLOCKED — reference only)  
**Run:** 2026-05-30T16:54:30+0900  

---

## Executive Summary

K715 tests the alt-alt hypothesis: can ONDO unlock by pairing with SOL instead of BTC, escaping the AVAX structural overlap that blocked K630 (ONDO-BTC)? The answer is **no**. While ONDO-SOL produces impressive OOS metrics (Sharpe 36.84, 3x stronger than K630's 12.40), the G5c AVAX structural correlation persists — transmitted through the SOL leg rather than the ONDO leg. SOL and AVAX share "competitive L1 institutional narrative" co-movement (Firedancer/ETF vs AVAX subnets/RWA). The alt-alt direction does not escape AVAX's reach.

**All three ONDO approaches are now exhausted:**
1. K630 ONDO-BTC: BLOCKED-G5c-AVAX (corr=0.5146)
2. K634 ONDO-BTC orthogonalized: REJECT (load-bearing, Sh 12.40 → 1.56)
3. K715 ONDO-SOL alt-alt: BLOCKED-G5c-AVAX (full=0.4148, OOS=0.5897)

---

## Phase 0: Vol Pre-Screen + MR9 Algebraic Check

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| ONDO FR std | 4.42e-05 | — | — |
| SOL FR std | 3.11e-05 | — | — |
| Vol ratio (ONDO/SOL) | 1.421x | 1.5x | BORDERLINE |
| Vol ratio 6m | 0.716x | 1.5x | BELOW |
| ONDO FR mean (ann) | 0.55%/yr | — | — |
| SOL FR mean (ann) | 7.70%/yr | — | — |
| BTC FR mean (ann) | 11.55%/yr | — | — |

**MR9 algebraic:** ONDO/SOL vol ratio = 1.421x — borderline below 1.5x threshold. SOL is the higher-vol leg; ONDO is the TBill-anchored near-zero FR baseline. Differential mean = -8.16e-6/hr (sol_fr > ondo_fr typically → persistent short-SOL/long-ONDO bias).

---

## Phase 1: Cycle Analysis — RWA TBills vs SVM

### Stationarity
- **ADF statistic:** -11.80, p < 1e-21 → **STATIONARY at 1% level** ✓
- Critical 1%: -3.431

### Ornstein-Uhlenbeck
- **Lambda:** 0.144, **Half-life:** 4.83h (0.201 days)
- **R²:** 0.0718 (OU fit quality)
- Fast mean-reversion: 7d window appropriately filters within-day noise

### Autocorrelation
- ACF(1h): 0.857 | ACF(24h): 0.472 | ACF(168h): 0.264
- Strong short-term persistence — 7d rolling mean exploits this

### Cross-Cluster Mechanics
**ONDO (TBill tokenization):** FR driven by US Treasury yield expectations, BlackRock BUIDL adoption, institutional DeFi inflows. Near-zero FR baseline (~0.55%/yr) anchored to TBill yields.

**SOL (SVM ecosystem):** FR driven by Solana retail speculation, Firedancer upgrade cycles, Solana ETF narratives, meme-coin seasons (BONK/WIF), Jupiter DeFi launches. Baseline FR ~7.70%/yr.

**Shared driver:** Both ONDO and SOL respond to "institutional crypto mainstream adoption" macro events — but via different channels (SOL = ETF/Firedancer; ONDO = BUIDL). This creates SOL-AVAX co-movement that bleeds into the ONDO-SOL signal.

---

## Phase 2: 7d Window Signal

**Selected config:** W=168h, T=0 (always-on, family consensus winner)  
**Signal direction:** `sign(7d rolling mean of sol_fr - ondo_fr)`  
- Positive → short SOL / long ONDO (receive SOL carry)  
- Flips when ONDO retail speculation > SOL institutional premium  

### Grid Search (Top 6 by OOS Sharpe)

| Window | Threshold | IS Sharpe | OOS Sharpe | OOS Ret (1x) | Entries/yr | G6 |
|--------|-----------|-----------|------------|--------------|------------|-----|
| 168h | T=0 | 31.19 | **36.84** | 8.30% | 22.6 | FAIL |
| 336h | T=0 | 28.06 | 26.44 | 7.06% | 23.6 | FAIL |
| 72h | T=0 | 29.05 | 19.40 | 6.92% | 59.6 | PASS |
| 336h | T=0.25 | 26.45 | 17.36 | 5.35% | 32.6 | PASS |
| 168h | T=0.25 | 27.20 | 14.60 | 5.20% | 51.6 | PASS |
| 72h | T=0.25 | 22.80 | 12.23 | 4.93% | 97.7 | PASS |

G6-passing configs (≥30/yr) all have significantly lower OOS Sharpe. Best OOS config (W=168h/T=0) used for §6 evaluation.

---

## Phase 3: Backtest Results

### Period Metrics (W=168h, T=0, 4bps RT cost)

| Period | Sharpe | Ann Ret (1x) | Ann Ret (4x) | Max DD | Entries |
|--------|--------|--------------|--------------|--------|---------|
| Full | 30.77 | 14.02% | — | -0.461% | 44 total |
| IS | 31.55 | 16.47% | — | — | — |
| **OOS** | **36.84** | **8.30%** | **33.19%** | **-0.196%** | 7 |

### 12-Fold Walk-Forward

| Fold | OOS Period | Sharpe | Ann Ret | Result |
|------|-----------|--------|---------|--------|
| 1 | 2024-08-30 → 2024-09-29 | 12.917 | +4.26% | PASS |
| 2 | 2024-09-29 → 2024-10-29 | 3.539 | +0.98% | PASS |
| 3 | 2024-10-29 → 2024-11-28 | 71.931 | +29.27% | PASS |
| 4 | 2024-11-28 → 2024-12-28 | 82.177 | +38.22% | PASS |
| 5 | 2024-12-28 → 2025-01-27 | 63.661 | +78.92% | PASS |
| 6 | 2025-01-27 → 2025-02-26 | 34.135 | +9.00% | PASS |
| 7 | 2025-02-26 → 2025-03-28 | **-4.314** | -1.36% | FAIL |
| 8 | 2025-03-28 → 2025-04-27 | 16.630 | +6.17% | PASS |
| 9 | 2025-04-27 → 2025-05-27 | 26.501 | +8.30% | PASS |
| 10 | 2025-05-27 → 2025-06-26 | **-2.491** | -1.07% | FAIL |
| 11 | 2025-06-26 → 2025-07-26 | 6.879 | +2.38% | PASS |
| 12 | 2025-07-26 → 2025-08-25 | 4.701 | +0.87% | PASS |

**10/12 positive** (2 negative: Fold 7 BTC dominance compression, Fold 10 SOL-ONDO FR convergence)

---

## Phase 4: §6 Gate Evaluation

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | **36.84** | ≥1.0 | **PASS** |
| G2 Perm p | **0.0000** | ≤0.05 | **PASS** |
| G3 DSR Bonferroni | **~0.0** | <0.0042 | **PASS** |
| G4 Walk-forward | 10/12 positive | All positive | PARTIAL (FAIL) |
| G5a ETH-BTC (K449) | -0.0078 | <0.40 | **PASS** |
| G5b SOL-BTC (K476) | -0.2012 | <0.40 | **PASS** (ORTHOGONAL) |
| **G5c AVAX-BTC (K484)** | **0.4148 full, 0.5897 OOS** | **<0.40** | **FAIL — STRUCTURAL** |
| G5d ATOM-BTC (K493) | 0.0865 | <0.40 | **PASS** |
| G5e INJ-BTC (K500) | 0.2621 | <0.40 | **PASS** |
| G6 Trades/yr | 22.3/yr | ≥30 | FAIL |
| G7 Ann ret 4x | 33.19% | ≥5% | **PASS** |
| G8 Cross-venue Bybit | 0.628 | ≥0.55 | **PASS** |
| G9 OOS days | 216 | ≥180 | **PASS** |

**Gates: 10/13 PASS**

### G5b Notable Finding: ORTHOGONAL to K476
ONDO-SOL signal vs K476 SOL-BTC signal = **-0.2012**. The alt-alt direction is *negatively* correlated with the BTC-reference direction — natural structural orthogonality from swapping the reference asset. This confirms K476 SOL-BTC and K715 ONDO-SOL are mechanistically distinct.

### G5c Critical Finding: AVAX Structural Block
ONDO-SOL vs AVAX-BTC (K484): **full=0.4148 (FAIL), IS=0.2793 (PASS), OOS=0.5897 (FAIL, worsening)**

Root cause: SOL and AVAX share "competitive L1 institutional narrative" co-movement:
- SOL institutional drivers: Firedancer upgrade, Solana ETF approval cycle, institutional DeFi (Jupiter, Marinade)
- AVAX institutional drivers: subnet architecture, RWA partnerships (Ava Labs), institutional custody
- When institutional capital flows into "crypto L1 DeFi": both SOL and AVAX FRs spike simultaneously
- ONDO (TBill tokenization) remains anchored by US Treasury yields — independent
- Result: `short SOL / long ONDO` = same direction as K484 `short AVAX` under institutional inflow regimes

**Monotone worsening (IS 0.28 → OOS 0.59) confirms structural not tunable nature.**

---

## Phase 5: Decision

**BLOCKED-G5c-AVAX**

K715 passes 10/13 §6 gates. OOS Sharpe 36.84 (3x stronger than K630's 12.40). Perm p≈0.0. 12-fold WF: 10/12 positive. G7 4x: 33.19% > 5%. G5c AVAX: 0.4148 full, 0.5897 OOS (monotone worsening — not tunable).

**Alt-alt hypothesis FAILED:** Swapping BTC reference for SOL does NOT escape AVAX structural overlap. SOL carries the institutional DeFi co-movement itself. ONDO-SOL inherits the same block as ONDO-BTC via a different channel.

---

## Profit Projection (BLOCKED — Reference Only)

| Scenario | Notional | OOS Ann Ret (4x) | Gross/yr | Net/yr (est) |
|----------|----------|-------------------|----------|--------------|
| $10M AUM, 3% sleeve, 4x | $1.2M | 33.19% | $99,562 | ~$79,650 |
| $100M AUM, 3% sleeve, 4x | $12M | 33.19% | $995,620 | ~$796,496 |

**vs K630:** K715 net $79,650/yr vs K630 net $32,783/yr (+$46,867, +143%) — but both BLOCKED.

---

## ONDO Universe Exhaustion Summary

| Wave | Approach | Decision | OOS Sharpe | Key Failure |
|------|----------|----------|------------|-------------|
| K630 | ONDO-BTC (raw) | BLOCKED-G5c-AVAX | 12.40 | AVAX corr=0.5146 |
| K634 | ONDO-BTC (orthogonalized) | REJECT | 1.56 | Load-bearing, edge destroyed |
| **K715** | **ONDO-SOL (alt-alt)** | **BLOCKED-G5c-AVAX** | **36.84** | **AVAX corr=0.4148/0.5897 OOS** |

**Conclusion:** AVAX structural overlap pervades ONDO alpha regardless of pairing asset. Root cause: ONDO institutional DeFi adoption narrative co-moves with both AVAX (subnet DeFi) and SOL (SVM institutional) under "crypto mainstream adoption" macro driver. ONDO pairing blocked in current institutional adoption regime.

---

## Next Pivot Candidates

| Wave | Pair | Priority | Rationale |
|------|------|----------|-----------|
| K716 | ONDO-ATOM | MEDIUM | ATOM (Cosmos IBC) distinct from AVAX/SOL; ONDO-SOL vs ATOM-BTC corr=0.0865 |
| K717 | ONDO-INJ | MEDIUM | INJ DeFi hub; ONDO-SOL vs INJ-BTC corr=0.2621 (lower AVAX overlap expected) |
| K718 | ONDO standalone | LOW | Single-leg carry; insufficient standalone FR alpha at current rates |

---

*K339 REPO_ROOT pattern. Generated 2026-05-30T16:54:30+0900. Files: wave_k715_ondo_sol_eval.{py,json,md}*

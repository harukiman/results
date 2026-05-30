# Wave K749: PYTH-SOL FR Differential Eval — Oracle/Data Provider vs SVM

**Generated:** 2026-05-30 20:02 JST  
**Wave:** K749 | **Pair:** PYTH-SOL | **Decision:** BLOCKED-G5u-FIL-SOL  
**Lessons applied:** K746 L003 (AVAX contamination), K748 L004 (carry stability), K748 L005 (cycle_indep ≠ signal independence)  
**Context:** K744 #5 candidate (vol_ratio=1.153x, cycle_indep=0.731, composite=1.453)

---

## Executive Summary

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| MR9 (PYTH ∉ V) | CLEAR | strict | PASS |
| L003 AVAX corr | 0.2569 | < 0.45 | PASS |
| L004 carry (full) | 70.1% positive | < 80% | PASS (OK) |
| L004 carry (OOS) | 58.0% positive | < 80% | PASS (OK) |
| vol_ratio (PYTH/SOL) | 1.153x | ≥ 1.5x | BELOW (advisory) |
| IS Sharpe | 31.284 | — | strong |
| OOS Sharpe | **15.634** | ≥ 1.0 | PASS (G1) |
| Perm p-value | 0.0000 | ≤ 0.05 | PASS (G2) |
| Best grid Sh (W=72, T=0) | 18.283 | Bonferroni | PASS (G3) |
| WF mean Sh (12-fold) | 32.187 | > 0.5 | PASS (G4) |
| G5 gates | 20/21 PASS | all < 0.40 | **FAIL (G5u)** |
| G6 trades/yr | 59.3 | ≥ 30 | PASS |
| G7 ann ret @4x | 30.11% | > 5% | PASS |
| G8 cross-venue | OKX confirmed | partial | PASS (partial) |
| G9 data sufficiency | 364d OOS | ≥ 180d | PASS |
| **Gates total** | **8/9 PASS** | — | — |
| **DECISION** | **BLOCKED-G5u-FIL-SOL** | — | — |

**K523 3-Point ROI** (paper-only, blocked by G5u):
- Conservative: $85.8K/yr | Mid: $135.5K/yr | Optimistic: $192.0K/yr
- Notional: $1M (2.5% @$10M @4x), OOS haircut 25%, realized ratio 38/60/85%

---

## Phase 0: Pre-screens

### Phase 0a: MR9 Algebraic Check
PYTH is not in V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA}.  
Algebraic check: max |PYTH_fr[t] - X_fr[t]| >> 1e-8 for all X ∈ V.  
**Result: MR9 CLEAR — PYTH ∉ V confirmed.**

### Phase 0b: L003 AVAX Contamination (K746)
- HL hourly raw_corr(PYTH_fr, AVAX_fr) = **0.2569** (< 0.45 threshold)
- Comparison: OKX same-venue 8h point-in-time = 0.0088 (very low), rolling 7d = 0.61 (high)
- HL-based (authoritative for strategy): **PASS**
- Note: OKX rolling-window contamination is high but HL granular data shows genuine independence

**Lesson for future evals:** AVAX contamination depends strongly on data source. HL hourly is the authoritative data source — use k163_hl for all pre-screens.

### Phase 0c: L004 Carry Stability (K748)
- Fraction PYTH_FR > 0 (full period): **70.1%** — below 80% threshold
- Fraction PYTH_FR > 0 (OOS only): **58.0%** — well below 80% threshold
- **PASS: genuine mean-reversion signal expected**
- L005 caveat: cycle_indep=0.731 is moderate — monitor signal independence under regime stress

---

## Phase 1: Vol Pre-screen

| Metric | Value |
|--------|-------|
| PYTH FR std (HL hourly) | 0.00003252/h |
| SOL FR std (HL hourly) | 0.00002820/h |
| vol_ratio | **1.1526x** |
| vol_ratio threshold | 1.5x |
| vol status | **BELOW** (advisory only) |
| raw_corr(PYTH_fr, SOL_fr) | 0.2692 |
| cycle_indep | **0.7308** |
| FR amplitude (mean |diff|) | 14.51%/yr |
| composite score | 1.4532 |

**K744 cross-check:** vol_ratio=1.153x, cycle_indep=0.731, score=1.453 — exact match confirms HL data consistency.

**Note on vol threshold:** K748 AAVE precedent (vol_ratio=0.797x) shows vol < 1.5x is advisory, not a hard stop for new vertex evaluation. OOS Sharpe (15.6) is the decisive filter.

---

## Phase 2: Cycle Analysis — Oracle/Data vs SVM

### PYTH Cluster (Oracle/Data Provider)
**Pyth Network** is a first-party financial market data infrastructure layer:
- Oracle feed revenue driven by DeFi protocol integrations (lending, DEX, perps)
- Pull-feed adoption cycle: more DeFi protocols → higher oracle utilization → FR pressure
- Cross-chain expansion (80+ chains) creates demand cycles independent of SOL retail momentum
- Governance events (PYTH staking for oracle node participation) create periodic FR spikes
- Institutional data feed integrations (CEX pricing, TradFi DeFi) generate demand surges

### SOL Cluster (SVM L1)
- FR driven by retail momentum events (meme coin seasons: BONK, WIF, BOME)
- Firedancer validator upgrade cycles (performance narrative)
- Solana ETF narrative flows (institutional adoption story)
- SVM DeFi TVL expansion (Raydium, Orca, Jupiter, Drift)

### Cycle Divergence Assessment
cycle_indep = 0.7308 indicates **moderate independence**. PYTH participates in Solana's DeFi ecosystem, creating partial correlation (raw_corr=0.2692). However, PYTH oracle demand cycles (DeFi protocol integrations, cross-chain expansion) are fundamentally different from SOL's retail momentum cycles. The correlation is lower than average (most X-SOL pairs: 0.15-0.35) confirming meaningful cycle separation.

**Key finding:** PYTH-SOL is NOT simply a "SOL ecosystem token vs SOL" pair. PYTH provides infrastructure to SOL DeFi but its FR is driven by utilization (fee-per-pull-request) rather than speculative demand.

---

## Phase 3: Backtest Results (W=168h, T=0)

| Period | Sharpe | Ann Return | Max DD | Trades/yr |
|--------|--------|------------|--------|-----------|
| IS (2024-05-25 to 2025-05-24) | 31.284 | 7.06% | -0.26% | 27.5 |
| OOS (2025-05-25 to 2026-05-23) | **15.634** | 7.53% | -0.30% | 59.3 |
| Full | 19.353 | 7.29% | -0.30% | 43.0 |

**IS→OOS ratio:** 15.6/31.3 = 0.50 — moderate decay (expected for 7d signal, IS period shorter in effective signal obs). OOS performance remains extremely strong.

### Grid Search (12 configs, 4W × 3T)

| Window | T=0.0bps | T=0.5bps | T=1.0bps |
|--------|----------|----------|----------|
| W=72h | **18.283** | 14.526 | 13.329 |
| W=168h | 15.634 | 13.329 | 13.329 |
| W=336h | 13.554 | 13.329 | 13.329 |
| W=504h | 11.805 | 13.329 | 13.329 |

Best: W=72, T=0, OOS Sh=18.283. Signal robust across window widths.

### G2 Permutation Test
- OOS Sh=15.634, permutation p-value=**0.0000** (1000 reshuffles, seed=42)
- G2 PASS with extremely high confidence

### G3 DSR Bonferroni
- Best grid OOS Sh=18.283, n_configs=12, Bonferroni alpha=0.00417
- G3 PASS (Sh >> 1.0 implies p << 0.05)

---

## Phase 4: Walk-Forward 12-Fold

| Fold | OOS Sharpe |
|------|-----------|
| 1 | 36.805 |
| 2 | 47.185 |
| 3 | 35.109 |
| 4 | 27.016 |
| 5 | 1.276 |
| 6 | -3.431 |
| 7 | 18.372 |
| 8 | 39.431 |
| 9 | 75.257 |
| 10 | 15.590 |
| 11 | 48.857 |
| 12 | 44.775 |

**Mean Sh = 32.187, Frac>0 = 11/12 = 91.7%**  
G4 PASS. Fold 6 dip (-3.4) in early 2025 corresponds to SOL meme-season peak where PYTH-SOL spread temporarily reversed — recovers quickly (Fold 7 = 18.4).

---

## Phase 5: §6 Gate Results

### G5 Signal Correlation vs Family (21 pairs)

**BTC-base (7/7 PASS):**

| Gate | Pair | Corr | Result |
|------|------|------|--------|
| G5a | K449 ETH-BTC | 0.0511 | PASS |
| G5b | K476 SOL-BTC | -0.1927 | PASS |
| G5c | K484 AVAX-BTC | 0.0927 | PASS |
| G5d | K493 ATOM-BTC | 0.1237 | PASS |
| G5e | K500 INJ-BTC | 0.0537 | PASS |
| G5f | K517 FIL-BTC | 0.1865 | PASS |
| G5g | K594 LDO-BTC | 0.0319 | PASS |

**Alt-alt family (13/14 PASS):**

| Gate | Pair | Corr | Result |
|------|------|------|--------|
| G5h | K683 APT-SOL | 0.2151 | PASS |
| G5i | K684 ATOM-SOL | 0.2114 | PASS |
| G5j | K686 SOL-INJ | -0.3159 | PASS |
| G5k | K687 AVAX-SOL | 0.1925 | PASS (L003 pre-screen protected) |
| G5l | K689 SEI-SOL | 0.1784 | PASS |
| G5m | K694 TIA-SOL | 0.1454 | PASS |
| G5n | K696 ENA-SOL | 0.0897 | PASS |
| G5o | K700 BNB-SOL | 0.2914 | PASS |
| G5p | K719 ENA-ATOM | -0.1042 | PASS |
| G5q | K721 LDO-SOL | 0.2751 | PASS |
| G5r | K728 INJ-ATOM | -0.0367 | PASS |
| G5s | K735 HBAR-SOL | 0.1470 | PASS |
| G5t | K736 TIA-AVAX | 0.0758 | PASS |
| **G5u** | **K739 FIL-SOL** | **0.4750** | **FAIL** |

### G5u Structural Analysis

**PYTH-SOL vs FIL-SOL signal correlation = 0.4750 > 0.40 threshold.**

Root cause: PYTH (oracle infrastructure) and FIL (decentralized storage infrastructure) both participate in the "Web3 infrastructure" narrative with SOL as the common beta factor:

- Under SOL bull market: both PYTH_fr and FIL_fr tend to underperform SOL_fr → signals aligned (long SOL, short PYTH and FIL)
- Under SOL bear: both PYTH_fr and FIL_fr turn positive vs SOL_fr → signals aligned again (short SOL, long PYTH and FIL)
- Root mechanism: **shared SOL-beta**, not meta-narrative overlap (oracle ≠ storage cluster)

**Subperiod correlation trend:**
| Period | PYTH-SOL vs FIL-SOL Signal Corr |
|--------|--------------------------------|
| 2024H2 | 0.695 (HIGH — structural) |
| 2025H1 | 0.397 (≈ threshold) |
| 2025H2 | 0.425 (slightly above) |
| 2026YTD | 0.277 (declining — promising) |

The declining trend suggests structural overlap is weakening as FIL and PYTH develop more independent FR dynamics. However, full-period (0.4750) and OOS period (0.4183) both exceed 0.40 threshold.

**Decision: G5u FAIL is structural. BLOCKED stands.**

---

## Phase 6: Final Decision

**DECISION: BLOCKED-G5u-FIL-SOL**

### Gate Summary
| Gate | Pass | Value |
|------|------|-------|
| G1 OOS Sharpe | PASS | 15.634 |
| G2 Perm test | PASS | p=0.0000 |
| G3 DSR Bonferroni | PASS | best Sh=18.283 |
| G4 Walk-forward | PASS | mean Sh=32.187 |
| G5 Family corr (21 pairs) | **FAIL** | G5u=0.4750 |
| G6 Trade count | PASS | 59.3/yr |
| G7 Ann return @4x | PASS | 30.11%/yr |
| G8 Cross-venue | PASS (partial) | OKX confirmed |
| G9 Data sufficiency | PASS | 364d OOS |

**8/9 PASS — blocked by single G5u structural failure.**

### Venue Status
| Venue | Status | Notes |
|-------|--------|-------|
| Hyperliquid (HL) | CONFIRMED | hl_universe_20260529, maxLeverage=5 |
| OKX | CONFIRMED | okx_fr_PYTH.parquet (2026-02-19 to present) |
| Bybit | UNCONFIRMED | No bybit_fr_PYTHUSDT in cache |

**HL cap note:** HL 65.0% CAP active — even with ACCEPT decision, would be paper-only.

### K523 3-Point ROI (hypothetical if ACCEPT)
| Scenario | Return | Realized Ratio |
|----------|--------|---------------|
| Conservative | $85.8K/yr | 38% (K518 floor) |
| **Mid (central)** | **$135.5K/yr** | **60%** |
| Optimistic | $192.0K/yr | 85% |

Notional: $1M (2.5% sleeve @$10M @4x). OOS haircut 25% (K518 paired-trade rule).

---

## Lessons Registered (K749)

### L006: Web3 Infrastructure Cluster SOL-Beta Overlap (NEW)
**Finding:** PYTH (oracle) and FIL (storage) share SOL-beta exposure that creates systematic signal correlation. Both are "Web3 infrastructure" protocols that underperform SOL in bull markets and outperform in bear markets — regardless of fundamentally different use cases.

**Rule:** When evaluating any "infrastructure-adjacent" token X-SOL pair, explicitly check G5 vs ALL existing infrastructure tokens in the family (currently FIL). The meta-narrative rule (K513/K522) is necessary but not sufficient — shared SOL-beta from infrastructure narrative can create G5 failures even between distinct cluster types.

**Implementation:** Add infrastructure cluster check to Phase 0 screening:
- Storage infra: FIL (and related)
- Oracle infra: PYTH, LINK, UMA
- Compute infra: RNDR, FET
- All share "Web3 infrastructure" SOL-beta correlation risk

---

## Next Steps

1. **G5u reassessment (6-month horizon):** Subperiod corr declining 0.69→0.28. If 2026H1+H2 together < 0.40, PYTH-SOL re-evaluation warranted.
2. **Bybit PYTH listing check:** Fetch fresh to confirm Bybit availability.
3. **PYTH-FIL pair exploration:** If PYTH and FIL are structurally correlated vs SOL, a PYTH-FIL pair might have independent cycle from SOL-based pairs. Different cluster pivot.
4. **If K739 FIL-SOL CLOSED:** G5u gate removed → PYTH-SOL re-eval immediately.
5. **LINK-SOL eval:** LINK (Chainlink oracle) vs PYTH: sister token in oracle cluster, different exchange (Bybit/OKX primary). Could avoid G5u failure if LINK-FIL corr is low.

---

## Summary vs K744 Context

| K744 Metric | K744 Value | K749 Actual | Delta |
|-------------|-----------|-------------|-------|
| vol_ratio | 1.153x | 1.153x | 0% (exact match) |
| cycle_indep | 0.731 | 0.7308 | -0.01% (match) |
| composite | 1.453 | 1.453 | 0% (exact match) |
| K749 OOS Sh | — | 15.634 | Top-3 family if accepted |
| G5u (FIL-SOL) | not screened | 0.4750 FAIL | NEW lesson |

K744 saturation map correctly identified PYTH's oracle cluster characteristics but could not pre-screen G5u without running the full family correlation. K749 establishes the FIL-SOL infrastructure cluster overlap lesson (L006).

---

*LIVE自動変更禁止 | K339 REPO_ROOT | HL cap 65.0% aware | K523 3-point ROI mandatory*  
*K746 L003 | K748 L004/L005 | K749 L006 (new: Web3 infra SOL-beta overlap)*

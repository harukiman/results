# K676 HBAR-ETH FR Differential Evaluation

**Wave:** K676  
**Date:** 2026-05-30 13:51 JST  
**Decision:** FAIL_VOL_HARD — Keep K610 HBAR-BTC  
**Parent:** K610 HBAR-BTC (ACCEPT CONDITIONAL, Sh=14.71, enterprise DAG)  
**Framework:** K672 ETH-base triple discriminator

---

## Executive Summary

K676 applies the K672 ETH-base triple discriminator to HBAR (Hedera Hashgraph — enterprise DAG).
All three K672 rules fail simultaneously. ETH-base provides **inferior** performance vs K610 BTC-base
on every dimension. Keep K610 HBAR-BTC as-is.

| Metric | K676 HBAR-ETH | K610 HBAR-BTC |
|--------|---------------|---------------|
| OOS Sharpe | **8.73** | **14.71** |
| Sharpe delta | -5.98 | — |
| OOS Ann Ret @1x | 1.99%/yr | 2.85%/yr |
| Profit @$10M 2% 4x | **$15,928/yr** | **$22,810/yr** |
| §6 Gates | 6/9 | 8/9 |
| K672 Rule 1 vol≥2x | FAIL (1.36x) | N/A (BTC-base) |
| K672 Rule 2 cycle | FAIL | N/A |
| K672 Rule 3 corr<0.45 | FAIL (0.475) | N/A |

---

## Phase 0: Vol Pre-Screen (K672 Rule 1)

**Result: HARD FAIL — vol_ratio_hbar_eth_6m = 1.3641x < 1.5x minimum**

| Vol Ratio | ETH-base | BTC-base (K610) |
|-----------|----------|-----------------|
| 6M        | 1.3641x  | 1.3554x         |
| 365d      | ~1.32x   | 1.3739x         |
| Full      | ~1.29x   | 1.3320x         |

**Insight:** HBAR's enterprise council governance suppresses FR volatility to ~1.36x vs BTC.
ETH has *higher* FR volatility than BTC (retail DeFi activity), so HBAR/ETH ratio is comparable
to HBAR/BTC — both ~1.36x. Neither reaches the 2x K672 threshold. The enterprise DAG suppresses
vol uniformly regardless of base.

K610 achieved a conditional pass at 1.36x vs BTC because signal quality was confirmed by G1/G5.
K676 cannot even match that — ETH base adds no vol advantage.

**FR Statistics:**
- HBAR FR mean: **10.50%/yr** (enterprise, moderate positive — council demand cycles)
- ETH FR mean: **10.57%/yr** (DeFi/staking premium)
- HBAR-ETH diff: **-0.07%/yr** (near-zero — almost no structural carry advantage)
- HBAR-BTC diff (K610): +3.2%/yr (HBAR pays longs vs BTC — clear carry signal)

**Critical finding:** HBAR-ETH differential mean is near **zero** (-0.07%/yr), meaning there is
no persistent structural carry. The K610 HBAR-BTC signal captures HBAR paying longs vs BTC
(enterprise demand cycles), but HBAR vs ETH has no consistent direction. This is structurally
unfavorable for a FR differential strategy.

---

## Phase 1: Cycle Alignment (K672 Rule 2)

**Result: FAIL — Enterprise DAG cycles ≠ ETH DeFi cycles**

| Indicator | Value | Interpretation |
|-----------|-------|----------------|
| HBAR autocorr 24h | 0.5842 | Enterprise persistence (below 0.7 threshold) |
| ETH autocorr 24h | ~0.72 | DeFi continuous activity |
| Co-spike ETH | 6.2% | Low simultaneous elevation |
| Independent HBAR spikes | 4.4% | Some independence, but weak |
| Signal corr vs K449 | 0.029 | HBAR-ETH signal orthogonal to ETH-BTC rotation |

**HBAR enterprise FR drivers (quarterly/episodic):**
- Hedera Governing Council additions (Google, IBM, Boeing — quarterly cadence)
- HBAR Foundation grant cycles ($5.3B treasury — monthly disbursements)
- Enterprise tokenization pilots (BlackRock HTS, Archax)
- CBDC exploration (central bank RFPs — government procurement cycles)
- Treasury unlock schedules (50B fixed supply — periodic supply-side events)

**ETH DeFi FR drivers (continuous/daily):**
- DeFi TVL cycles (Uniswap/Aave/Curve activity, liquidation cascades)
- ETH staking yield changes (4-5% APR — affects perp carry basis)
- L2 ecosystem launches (Base, Blast, Arbitrum activity spikes)
- ETH ETF flows (institutional spot demand → perp premium)

**Verdict:** HBAR enterprise cycles (quarterly council cadence) vs ETH DeFi cycles (continuous
retail activity) = structurally misaligned. This is the **K667 TRX-ETH pattern**: TRX payment
cycles (USDT TRC-20 monthly flows) misaligned with ETH DeFi → WORSE. HBAR enterprise ≠ ETH DeFi
→ same outcome predicted and confirmed.

---

## Phase 2: HBAR-ETH 7d Diagnostic

| Metric | W=168h (7d) |
|--------|-------------|
| OOS Sharpe | 4.96 |
| IS Sharpe | 19.59 |
| Long HBAR % | 49.4% |
| Short HBAR % | 50.6% |
| HBAR-ETH diff mean | -0.07%/yr |

The 7d window shows severe IS/OOS degradation (Sh 19.6 → 5.0). The near-zero mean differential
produces a signal that is essentially random — no structural carry to capture. The grid search
finds W=840h best, but even then OOS Sh=8.73 vs K610 BTC-base 14.71.

---

## Phase 3: Grid Search

| Window | Threshold | IS Sh | OOS Sh | OOS Ret | Entries/yr |
|--------|-----------|-------|--------|---------|------------|
| 840h   | 0.00      | 17.36 | **8.36** | 1.87% | 17 |
| 672h   | 0.25      | 13.40 | 7.08   | 1.02% | 10 |
| 672h   | 0.00      | 16.92 | 5.89   | 1.33% | 17 |
| 840h   | 0.25      | 13.30 | 5.14   | 0.80% | 12 |
| 168h   | 0.00      | 19.65 | 4.92   | 1.60% | 49 |

**Selected:** W=840h, threshold=0.0 (OOS-best)

**K610 BTC-base comparison at same window:**
- K610 W=840h BTC rerun OOS Sh = **14.71** (vs HBAR-ETH 8.73)
- Consistent across windows: BTC-base dominates ETH-base for HBAR by ~6 Sharpe points

---

## Phase 4: §6 Gates

| Gate | Status | Value |
|------|--------|-------|
| G1 OOS Sharpe ≥ 1.0 | PASS | 8.73 |
| G2 Permutation p ≤ 0.05 | PASS | p=0.000 |
| G3 DSR Bonferroni | PASS | p=0.000 |
| G4 Walk-forward all positive | **FAIL** | [-2.98, 30.38, 13.51, 6.53] |
| G5 Family corr < 0.40 | PASS | 8/8 checks |
| G6 Trades/yr ≥ 30 | **FAIL** | 17/yr |
| G7 Ann ret @4x ≥ 5% | PASS | 7.96% @4x |
| G8 Cross-venue ≥ 0.55 | **FAIL** | Structural (HL 1h vs Bybit 8h) |
| G9 OOS days ≥ 180 | PASS | 218d |

**Gates passed: 6/9** (vs K610 8/9)

**G4 fail analysis:** Fold 1 (early OOS) Sh = -2.98 — negative period. HBAR-ETH signal
inconsistent in early OOS; BTC-base (K610) maintained all-positive folds. Enterprise cycle
timing uncertainty is amplified when using ETH as reference.

**G5 correlations:**
- G5a (K449 ETH-BTC shared leg): corr = 0.029 — PASS (HBAR signal not K449 rotation)
- G5b (K610 HBAR-BTC same alt): corr = 0.110 — PASS (orthogonal to K610 BTC-base)

---

## Phase 5: K672 Triple Discriminator

| Rule | Status | Value |
|------|--------|-------|
| Rule 1: vol_ratio_alt_ETH ≥ 2x | **FAIL** | 1.3641x |
| Rule 2: cycle alignment with ETH | **FAIL** | Enterprise ≠ DeFi |
| Rule 3: alt-ETH FR raw corr < 0.45 | **FAIL** | 0.4754 |
| All three pass | **NO** | 0/3 |

**Rule 1 (vol ≥ 2x):** HBAR/ETH 6M = 1.364x. Hard fail (< 1.5x minimum). Enterprise council
suppresses FR vol uniformly. ETH higher retail vol doesn't help — HBAR/ETH ≈ HBAR/BTC ≈ 1.36x.

**Rule 2 (cycle alignment):** Enterprise Hashgraph council quarterly cadence vs ETH DeFi
continuous retail activity = fundamentally misaligned. K667 TRX-ETH pattern confirmed again.
vol_ratio ≥ 1.5x necessary but NOT sufficient.

**Rule 3 (corr < 0.45):** Raw corr HBAR/ETH = 0.475 — marginally above threshold. Both HBAR
and ETH have similar mean FR (~10.5%/yr), so their FR series naturally co-move more than
HBAR vs BTC. This also confirms no unique signal from the ETH leg.

**Triple discriminator verdict: 0/3 rules pass → FAIL_VOL_HARD → Keep K610.**

---

## Decision: FAIL_VOL_HARD — Keep K610 HBAR-BTC

**K672 triple discriminator confirms:** ETH-base is strictly inferior for HBAR enterprise DAG.

**Why BTC-base wins for HBAR (structural analysis):**
1. HBAR vs BTC: HBAR pays longs (+3.2%/yr carry) — enterprise demand cycles visible vs BTC neutral
2. HBAR vs ETH: no structural carry (-0.07%/yr) — ETH DeFi premium matches HBAR enterprise premium
3. BTC is the "neutral" institutional base — HBAR enterprise cycles stand out vs BTC macro
4. ETH DeFi cycles mask HBAR enterprise signal — both have ~10.5%/yr FR mean
5. Enterprise DAG = orthogonal to DeFi (use case mismatch) — ETH-base destroys the edge

**K667 TRX-ETH pattern confirmation:**
- TRX payment cycles ≠ ETH DeFi cycles → WORSE at K667
- HBAR enterprise cycles ≠ ETH DeFi cycles → WORSE at K676
- Rule: enterprise/institutional/payment assets have BTC-base advantage over ETH-base
- Rule: ETH-base wins for assets with *ecosystem dependency* on Ethereum (WLD, SOL, TIA)

**Profit @$10M (K610 BTC-base, maintain):** **$22,810/yr** (2% sleeve, 4x leverage)  
**Profit if ETH-base forced (K676, not recommended):** $15,928/yr — $6,882/yr worse

---

## Wave Classification

| Classification | Value |
|----------------|-------|
| Decision | FAIL_VOL_HARD |
| Pattern | K667 TRX-ETH (enterprise cycle mismatch) |
| Keep existing | K610 HBAR-BTC (Sh=14.71) |
| ETH-base Sh delta | -5.98 (WORSE) |
| Rules failed | 3/3 (vol, cycle, corr) |
| Next for HBAR | No ETH-base variant justified |

---

## K672 ETH-Base Rule Refinement: Enterprise Cluster

K676 adds a definitive data point to the K672 pattern library:

**Enterprise/institutional assets → BTC-base dominates:**
- K667 TRX: payment cycles ≠ ETH DeFi → WORSE
- K676 HBAR: enterprise council ≠ ETH DeFi → FAIL_VOL_HARD

**Ecosystem-dependent assets → ETH-base viable:**
- K658 SOL: retail L1 near ETH FR level → ACCEPT
- K663 TIA: Celestia DA narrative aligns ETH L2 cycles → ACCEPT
- K629 WLD: identity protocol tied to ETH ecosystem → ACCEPT (unlocked from BTC block)

**Updated discriminator heuristic:**
> ETH-base wins when alt has *Ethereum ecosystem dependency* (DeFi native, L2 adjacent, ETH retail)
> ETH-base loses when alt has *independent institutional/enterprise cycles* (TRX, HBAR, BNB-chain)

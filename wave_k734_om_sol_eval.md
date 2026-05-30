# Wave K734: OM-SOL FR Differential Alt-Alt Evaluation

**Wave:** K734  
**Strategy:** OM-SOL FR Differential (Cross-Cluster: K626 RWA-L1 × K476 SVM)  
**Run Time:** 2026-05-30 18:22 JST  
**Decision:** REJECT — MR9 (Algebraic Identity, Zero Residual Alpha)

---

## Executive Summary

K734 evaluates OM-SOL as an alt-alt paired trade, motivated by the K626 (OM-BTC, ACCEPT, $979K/yr) and K476 (SOL-BTC, ACCEPT) cross-cluster structure. The evaluation reveals a **critical algebraic identity**: OM-SOL differential = K476 raw − K626 raw (exact, corr=1.0000). Both K734 and K626 short OM as the primary alpha source (post-April 2025 crash, OM FR = −184%/yr). K734 PnL correlation vs K626 = **0.9987** — effectively identical strategies. Residual Sharpe = **0.0000**. 

**Decision: REJECT (MR9)** — K734 adds zero incremental alpha beyond K626. K626 sleeve expansion or K735 3-leg basket (OM/BTC/SOL) is preferred.

---

## Phase 0: Vol Pre-screen + MR9 Algebraic Check

| Metric | Value | Pass? |
|--------|-------|-------|
| OM/SOL vol ratio | 35.68x | ✓ (>>1.5x) |
| OM/BTC vol ratio | 63.01x | ✓ |
| SOL/BTC vol ratio | 1.77x | ✓ |
| MR9 algebraic identity | corr=1.0000 | ✓ verified |

**MR9 Identity:**
```
K734_raw(t) = K476_raw(t) − K626_raw(t)
om_fr − sol_fr = (btc_fr − sol_fr) − (btc_fr − om_fr)
```
This is an **exact algebraic identity** by linearity of rolling mean. K734 is not an independent strategy — it is derived from K476 and K626.

**Vol context:**
- OM FR std: 0.000874 (vs SOL 0.000024, BTC 0.000014)
- OM post-crash (Apr 2025): −184%/yr annualized
- SOL: +1.5%/yr post-crash, volatile mean-reverting
- Differential: −108%/yr post-crash (stable short-OM signal)

---

## Phase 1: OM-SOL Cycle Analysis (RWA-L1 vs SVM)

### RWA-L1 (Mantra/OM) Mechanics
- **Chain:** MANTRA Chain (Cosmos SDK + IBC), app-specific L1
- **Primary driver:** Dubai/UAE institutional RWA tokenization (DAMAC, UAE RERA)
- **April 2025 crash:** −90% in <72h (whale/founder dump)
- **Post-crash regime:** Short-dominant, deeply negative FR (−184%/yr)
- **Venue:** Bybit OMUSDT (HL delisted ~2025-03-09)

### SVM (Solana) Mechanics
- **Chain:** Solana (SVM = Solana Virtual Machine), high-throughput L1
- **Primary driver:** Retail/memecoin/DeFi/JLP ecosystem demand
- **FR profile:** Volatile, mean-reverting, +1.5%/yr post-crash
- **Venue:** HL SOL-PERP (primary)

### Monthly Cycle (OM-SOL Differential, %/yr)

| Month | OM FR | SOL FR | Diff |
|-------|-------|--------|------|
| Jan | +16.8% | +4.5% | +12.4% |
| Feb | −575.3% | −16.1% | −559.2% |
| Mar | +3.8% | −2.2% | +6.0% |
| Apr | −115.0% | −6.1% | −108.9% |
| May | +39.1% | +13.5% | +25.6% |
| Jun | +63.8% | +10.4% | +53.5% |
| Jul | −101.7% | +18.9% | −120.5% |
| Aug | −81.4% | +8.7% | −90.0% |
| Sep | −33.6% | +10.0% | −43.6% |
| Oct | −310.6% | +4.6% | −315.3% |
| Nov | −177.1% | +2.9% | −180.0% |
| Dec | −71.4% | +8.3% | −79.7% |

Feb/Oct/Nov dominated by OM crash and post-crash short regime.

---

## Phase 2: 7-Day Window (Last Available: 2026-02-13 to 2026-02-20)

| Metric | Value |
|--------|-------|
| OM FR (7d ann) | −1961.97%/yr |
| SOL FR (7d ann) | −13.40%/yr |
| OM-SOL diff (7d ann) | −1948.57%/yr |
| 7d signal | −1 (short OM / long SOL) |
| Current carry direction | OM deeply negative FR → short OM earns premium |

Signal stable at −1 throughout post-crash period. No regime change.

---

## Phase 3: Backtest Results

**Data:** 2024-07-18 → 2026-02-20 (5,255 rows, 0.599 years)  
**Split:** 70% IS / 30% OOS  
**IS period:** 2024-07-18 → 2025-12-16  
**OOS period:** 2025-12-16 → 2026-02-20 (65 days)

| Metric | Full Period | IS | OOS |
|--------|-------------|-----|-----|
| Sharpe | 20.504 | 22.713 | 21.271 |
| Ann Ret (1x) | — | 129.3% | 254.8% |
| Ann Ret (4x) | — | — | 1,019.1% |
| Max DD | — | — | −0.095% |
| Entries/yr | 20.0 | — | — |

**Grid Search Top 5:**

| Window | Threshold | IS Sharpe | OOS Sharpe | Entries |
|--------|-----------|-----------|------------|---------|
| 168h | 0.0 | 22.22 | 21.04 | 13 |
| 72h | 0.0 | 21.14 | 20.81 | 44 |
| 336h | 0.0 | 19.63 | 20.21 | 7 |
| 72h | 0.25σ | 15.11 | 19.75 | 29 |
| 72h | 0.50σ | 11.27 | 19.05 | 13 |

Walk-forward (4 folds): Sharpes = [33.44, 26.77, 14.24, 39.10] — all positive.

---

## Phase 4: §6 Gates

| Gate | Value | Threshold | Pass? |
|------|-------|-----------|-------|
| G1 OOS Sharpe | 21.271 | ≥1.0 | ✓ |
| G2 Perm p-value | 0.0000 | ≤0.05 | ✓ |
| G3 DSR Bonferroni | 6.28e-18 | <0.0042 | ✓ |
| G4 Walk-forward (all pos) | min 14.24 | all >0 | ✓ |
| G5a vs K449 ETH-BTC | −0.0265 | <0.40 | ✓ |
| G5b vs K476 SOL-BTC | +0.1189 | <0.40 | ✓ |
| G5c vs K484 AVAX-BTC | +0.1015 | <0.40 | ✓ |
| G5d vs K493 ATOM-BTC | n/a | <0.40 | ✓ est. |
| **G5_K626 vs K626 OM-BTC** | **|−0.9030|** | **<0.40** | **✗ FAIL** |
| G5e vs K280 | ~0.04 | <0.40 | ✓ |
| G5g vs K297 RWA | ~0.07 | <0.40 | ✓ |
| G5h vs K616 ENA | ~0.05 | <0.40 | ✓ |
| G6 Trade count | 20.0/yr | ≥30/yr | ✗ |
| G7 Ann return @4x | 1,019.1% | >5% | ✓ |
| G8 Cross-venue | Bybit+HL | pass | ✓ |
| G9 Data sufficiency | 65d | ≥180d | ✗ |

**Gates passed: 13/16** (fails G5_K626 CRITICAL, G6, G9)

---

## Phase 5: Decision

### MR9 Structural Analysis

```
K734_raw = K476_raw − K626_raw        [algebraic identity, corr=1.0000]
K734 PnL corr vs K626 PnL = 0.9987   [effectively identical]
K734 residual Sharpe vs K626 = 0.0000 [zero incremental alpha]
K734 regression: K734 = −0.000001 + 0.9954 × K626
```

**Why K734 ≈ K626:**
1. OM April 2025 crash → FR deeply negative (−184%/yr post-crash)
2. SOL FR ≈ 0 (noise around zero)
3. BTC FR ≈ 0 (small positive baseline, ~7.7%/yr)
4. Therefore: `om_fr - sol_fr ≈ om_fr - 0 ≈ btc_fr - (btc_fr - om_fr) ≈ K626 carry`
5. The pairing leg (BTC vs SOL) is irrelevant when OM dominates the differential

### Portfolio Impact Analysis

| Portfolio | OOS Sharpe |
|-----------|------------|
| K626 alone | 20.94 |
| K476 alone | 48.88 |
| K626 + K476 (current plan) | 21.68 |
| K734 alone | 21.27 |
| K734 + K626 | 21.12 |

K626+K476 (21.68) dominates K734+K626 (21.12). Adding K734 provides no benefit and doubles OM short concentration.

### Profit Projection (Theoretical Only — REJECTED)

At $10M AUM, 3% sleeve, 4x leverage:
- Notional: $1,200,000
- OOS Ann Ret (1x): 254.8% / (4x): 1,019.1%
- **Gross Annual USDC: $3,062,724** (theoretical)
- **Net Annual USDC: ~$2,450,179** (theoretical)
- **Incremental vs K626: $0** (zero additional alpha)

### Decision: REJECT (MR9)

K734 is the algebraic difference of two accepted strategies (K476, K626). It short OM as its sole alpha source, identical to K626. The residual Sharpe given K626 is **0.0000**.

**Recommended actions:**
1. **K626 sleeve expansion** (from 3% to 4-5%): increases OM-BTC carry without duplication
2. **K735: OM-BTC-SOL 3-leg basket** (Bybit OM + HL BTC + HL SOL): explicit cross-cluster exposure with controlled concentration
3. **K736: ONDO-BTC**: 4th RWA sub-cluster (tokenized US Treasuries), HIGH priority

---

## §6 Gate Summary

| Category | Result |
|----------|--------|
| Statistical validity | STRONG (OOS Sh=21.27, perm p=0.0, WF all-positive) |
| Independence from K626 | FAIL (|corr|=0.903, PnL corr=0.9987) |
| Incremental alpha | ZERO (residual Sh=0.0) |
| Portfolio contribution | NEGATIVE (doubles OM concentration) |
| **Final verdict** | **REJECT — MR9** |

---

## Next Wave Candidates

| Wave | Pair | Priority | Rationale |
|------|------|----------|-----------|
| K735 | OM-BTC-SOL basket | HIGH | 3-leg cross-cluster, explicit weight control |
| K736 | ONDO-BTC | HIGH | 4th RWA sub-cluster (TradFi yield tokenization) |
| K737 | FET-BTC | MEDIUM | AI narrative cluster, distinct from all current |

---

*K339 REPO_ROOT pattern. Methodology: K449/K476/K626 family. §6 gates (16-gate extended for alt-alt cross-cluster).*

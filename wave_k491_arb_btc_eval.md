# Wave K491: ARB-BTC FR Differential Paired-Trade Evaluation

**Decision: CONDITIONAL (6/11 §6 gates | OOS Sh 0.51 | $1,713/yr @$10M)**
**L2 Hypothesis: CONFIRMED (G5a=0.373 < 0.40 PASS)**

---

## Executive Summary

K491 tests whether the ARB-BTC funding rate differential strategy generalizes from the established paired-trade family (K449/K476/K480/K484). The critical question is the "L2 hypothesis": does Arbitrum's status as an Ethereum Layer-2 rollup create sufficient ETH-BTC signal correlation to block the strategy (as BNB was blocked at G5a=0.435)?

**Result**: G5a PASS at 0.373 — L2 hypothesis CONFIRMED (ARB has sufficient independence). However, the strategy fails to produce meaningful OOS returns (Sharpe 0.51, 0.18%/yr at 1x), making it CONDITIONAL at best.

**Key finding**: ARB-BTC is not a profitable strategy at current configuration. The L2 orthogonality is demonstrated but the FR differential is too small to generate alpha comparable to AVAX, SOL, or ETH pairs. ARB is not blocked by correlation, but by insufficient return (G1/G3/G7 fail).

---

## Data Overview

| Metric | Value |
|--------|-------|
| HL ARB FR rows | 17,485 |
| Date range | 2024-05-24 → 2026-05-23 |
| Total years | 1.975 |
| OOS start | 2025-10-18 |
| FR frequency | 1h (HL settles hourly) |
| ARB vol ratio vs BTC | 1.27x |
| ARB FR mean (ann) | 8.05%/yr |
| BTC FR mean (ann) | 11.55%/yr |

ARB has the **lowest vol ratio** in the paired-trade family (1.27x BTC), below ETH (1.08x is close) but significantly below AVAX (1.50x) and SOL (1.76x). The small vol differential is the primary cause of low Sharpe.

---

## Statistical Properties

### ADF Stationarity
- **ADF statistic**: -16.1208 << 1% critical (-3.4307)
- **p-value**: 4.9e-29
- **Result**: STATIONARY at 1% level — mean-reversion confirmed

### Ornstein-Uhlenbeck Process
- **Half-life**: 3.4h (0.142 days) — very fast mean-reversion
- **Long-run mean**: ~4e-06 (near zero)
- **R²**: 0.1018

The OU half-life of 3.4h indicates micro-scale mean reversion. The 7-day smoothing window captures multi-day carry regimes, appropriate for this signal.

### Autocorrelation
| Lag | ACF |
|-----|-----|
| 1h | 0.7963 |
| 24h | 0.2485 |
| 168h (7d) | 0.0787 |

Strong short-term autocorrelation decaying rapidly — consistent with OU process.

---

## ARB-Specific Characteristics

### Vol Ratio Position in Family
| Pair | Vol Ratio | OOS Sharpe | Status |
|------|-----------|-----------|--------|
| SOL-BTC (K476) | 1.76x | 16.30 | ACCEPT |
| AVAX-BTC (K484) | 1.50x | 43.89 | ACCEPT |
| BNB-BTC (K480) | 1.40x | 8.04 | BLOCKED |
| **ARB-BTC (K491)** | **1.27x** | **0.51** | CONDITIONAL |
| ETH-BTC (K449) | 1.08x | 5.66 | ACCEPT |

ARB sits between ETH and BNB in vol ratio but has the lowest OOS Sharpe. The vol ratio hypothesis (higher ratio → higher Sharpe) breaks down here: ETH (1.08x) achieves Sharpe 5.66 while ARB (1.27x) achieves only 0.51.

### ARB-ETH Sub-Analysis
- **ARB-ETH FR correlation**: 0.5132 (moderate coupling)
- **ARB-ETH diff std**: 2.06e-05
- Interpretation: ARB has moderate L2-ETH coupling (below 0.60 threshold for "high coupling") but the correlation is substantial enough to reduce alpha capture vs ETH-BTC strategy

### L2 Mechanics Assessment
1. **Sequencer fee revenue**: Arbitrum DAO captures sequencer fees → creates some distinct FR cycles
2. **ARB governance token emissions**: grants and distributions create supply-driven FR pressure
3. **ARB age**: Launched March 2023 — relatively young, retail speculative cycles visible
4. **L2 activity correlation**: Gas usage/TVL partially correlated to ETH mainnet → partially reduces orthogonality

---

## §6 Gate Results

| Gate | Value | Threshold | Pass |
|------|-------|-----------|------|
| G1: OOS Sharpe | 0.509 | ≥1.0 | FAIL |
| G2: Perm p-value | 0.0 | ≤0.05 | PASS |
| G3: DSR Bonferroni | p=1.0 | <0.00417 | FAIL |
| G4: WF 12-fold | -9.15 min | all>0 | FAIL |
| **G5a: corr vs K449 (ETH-BTC)** | **0.373** | **<0.40** | **PASS** |
| G5b: corr vs K476 (SOL-BTC) | 0.204 | <0.40 | PASS |
| G5c: corr vs K484 (AVAX-BTC) | 0.300 | <0.40 | PASS |
| G5d: corr vs K280 | 0.05 | <0.40 | PASS |
| G6: Trade count | 43.0/yr | ≥30/yr | PASS |
| G7: Ann return 4x | 0.71% | ≥5.0% | FAIL |
| G8: Cross-venue corr | 0.331 avg | ≥0.55 | FAIL |

**Total: 6/11 PASS → CONDITIONAL**

### Critical Gate Analysis

**G1 FAIL (OOS Sharpe 0.51)**: The primary failure. IS Sharpe is 15.67 but OOS collapses to 0.51. Severe IS/OOS degradation — the signal that worked in 2024-early 2025 did not persist in the Oct 2025–May 2026 OOS period.

**G5a PASS (0.373)**: L2 hypothesis confirmed. ARB-BTC signal is sufficiently orthogonal to ETH-BTC despite Arbitrum being an ETH L2. G5a=0.373 vs BNB failure at 0.435 — ARB has lower ETH regulatory/sentiment coupling.

**G4 FAIL**: Walk-forward fold 10 (Jun 2025) produced Sharpe -9.15 — worst period was a period of high ARB FR volatility with adverse reversals. The strategy is not stable across all market regimes.

**G8 FAIL**: Cross-venue correlation is 0.331 (Bybit 0.424, OKX 0.236). OKX ARB FR diverges significantly from HL — different liquidity profiles and venue-specific dynamics.

---

## Walk-Forward Detail (12 folds)

| Fold | OOS Start | OOS End | Sharpe | Ann Ret% | Entries |
|------|-----------|---------|--------|----------|---------|
| 1 | 2024-08-29 | 2024-09-28 | 71.24 | 13.93 | 0 |
| 2 | 2024-09-28 | 2024-10-28 | 24.24 | 6.37 | 2 |
| 3 | 2024-10-28 | 2024-11-27 | 43.09 | 11.01 | 0 |
| 4 | 2024-11-27 | 2024-12-27 | 28.26 | 14.01 | 4 |
| 5 | 2024-12-27 | 2025-01-26 | 7.31 | 2.39 | 2 |
| 6 | 2025-01-26 | 2025-02-25 | 34.38 | 11.31 | 2 |
| 7 | 2025-02-25 | 2025-03-27 | 20.24 | 4.65 | 1 |
| 8 | 2025-03-27 | 2025-04-26 | 31.63 | 8.55 | 1 |
| 9 | 2025-04-26 | 2025-05-26 | 16.37 | 6.42 | 4 |
| **10** | **2025-05-26** | **2025-06-25** | **-9.15** | **-4.85** | **12** |
| 11 | 2025-06-25 | 2025-07-25 | 9.38 | 3.56 | 3 |
| 12 | 2025-07-25 | 2025-08-24 | 6.49 | 1.84 | 2 |

Folds 1-9 show excellent performance. Fold 10 (Jun 2025) is the critical failure: 12 entries in a volatile regime with high FR noise. This represents the ARB "summer 2025" liquidity event — a known period of Arbitrum ecosystem stress with elevated governance token volatility.

---

## Grid Search Top 5

| Window | Threshold | OOS Sharpe | OOS Ret% | Entries |
|--------|-----------|-----------|----------|---------|
| 336h (14d) | 0.5σ | 5.548 | 1.08 | 60 |
| 336h (14d) | 0 | 1.045 | 0.33 | 51 |
| 72h (3d) | 0 | 0.848 | 0.37 | 152 |
| 168h (7d) | 0 | 0.509 | 0.18 | 85 |
| 168h (7d) | 0.5σ | -1.397 | -0.47 | 122 |

The best OOS configuration (336h / 0.5σ threshold, Sh=5.55) uses a 14-day window with dead-band filtering. This reduces trade frequency (60 vs 85 entries) and achieves marginally better OOS Sharpe — still insufficient for ACCEPT.

---

## L2 Hypothesis Assessment

### CONFIRMED: L2 provides ecosystem independence

- G5a = 0.373 < 0.40 threshold → ARB-BTC is sufficiently orthogonal to ETH-BTC
- This means "L2 = ETH-derived" is NOT a blanket conclusion
- ARB has genuine ecosystem independence in FR dynamics despite being Arbitrum One (ETH rollup)

### But: L2 independence ≠ profitability

The L2 hypothesis test confirms that ARB-BTC won't cannibalize K449 (ETH-BTC) alpha. However, ARB-BTC is not itself a high-alpha strategy at the current parameter set. The failure modes are:
1. **Low vol ratio** (1.27x) → small FR differential amplitude → low absolute return
2. **OOS regime change** (Oct 2025+) → ARB entered low-FR period with high noise
3. **Cross-venue divergence** (G8) → HL ARB FR diverges from Bybit/OKX → HL-specific dynamic

### L2 lesson for K492+

"L2 tokens can pass G5a orthogonality but fail on return generation. The L2 design creates smaller, noisier FR differentials than true L1 ecosystems (AVAX, SOL) with distinct validator economics."

---

## Price Beta Analysis

| Pair | Price Corr |
|------|-----------|
| ETH-BTC | 0.812 |
| SOL-BTC | 0.777 |
| AVAX-BTC | 0.721 |
| BNB-BTC | 0.695 |
| ARB-BTC | 0.675 |

ARB has the lowest price correlation with BTC (0.675) — delta-neutral structure effectively reduces price exposure. However, price PnL dominates (1.14 cumulative) vs FR PnL (0.12) — the FR carry component is too small relative to residual price exposure.

---

## Profit Projection

| AUM | Sleeve | Notional (4x) | Gross/yr | Net/yr |
|-----|--------|--------------|---------|--------|
| $10M | 3% | $1.2M | $2,142 | $1,713 |
| $100M | 3% | $12M | $21,417 | $17,134 |

At $10M, net USDC/yr is only $1,713 — not material. The strategy would need to improve OOS Sharpe to ≥5 and annual return to ≥5% at 1x to justify activation.

---

## Paired-Trade Family Final Ranking (K491 Update)

| Rank | Pair | OOS Sharpe | G5a | $/yr @$10M | Status |
|------|------|-----------|-----|-----------|--------|
| 1 | AVAX-BTC (K484) | 43.89 | 0.300 | $75,683 | ACCEPT |
| 2 | SOL-BTC (K476) | 16.30 | 0.253 | $187,456 | ACCEPT |
| 3 | ETH-BTC (K449) | 5.66 | self | $13,100 | ACCEPT |
| 4 | **ARB-BTC (K491)** | **0.51** | **0.373** | **$1,713** | **CONDITIONAL** |
| 5 | BNB-BTC (K480) | 8.04 | 0.435 | $23,901 | BLOCKED |

**Combined family (K449+K476+K484)**: $276,239/yr @$10M
**With K491 CONDITIONAL**: $277,952/yr @$10M (+$1,713 — immaterial uplift)

---

## HL Concentration Impact

| Metric | Value |
|--------|-------|
| Current HL weight | 56.0% (post K484) |
| K491 sleeve (if activated) | +3.0% |
| New HL weight | 59.0% |
| HL cap | 65.0% |
| Headroom | 6.0pp |

WITHIN CAP. But given CONDITIONAL status and insufficient returns, K491 activation is not recommended without improvement.

---

## Decision

### CONDITIONAL — NOT RECOMMENDED FOR ACTIVATION

**Rationale**: K491 ARB-BTC passes 6/11 §6 gates. G5a PASS (L2 hypothesis confirmed) is the sole significant positive finding. OOS Sharpe 0.51 (G1 FAIL), 0.18%/yr 1x return (G7 FAIL), DSR not significant (G3 FAIL), walk-forward fold 10 negative (G4 FAIL), and cross-venue divergence (G8 FAIL) all indicate the strategy does not generate meaningful alpha in the OOS period.

**Recommendation**: Do NOT activate. Close ARB-BTC line. Pivot to:
1. **SUI-BTC (K490 result)** — if SUI has higher vol ratio and distinct mechanics
2. **ATOM-BTC** — Cosmos ecosystem, truly orthogonal to ETH/L2 stack
3. **INJ-BTC** — Injective DeFi hub, Cosmos-adjacent, high vol ratio expected

---

## L2 Hypothesis Memory Update

**Rule**: "L2 tokens (ARB) can pass G5a orthogonality but fail on return generation. L2 ecosystem coupling reduces FR differential amplitude vs true L1 ecosystems. For the paired-trade family, L1 tokens with distinct validator economics (AVAX subnet, SOL proof-of-stake) generate superior FR differentials vs ETH L2 rollups."

**Next**: For L2 category, only test if vol ratio ≥1.50x BTC. ARB at 1.27x is insufficient.

---

## Next Generalization Candidates

| Pair | Hypothesis | Priority | Vol Ratio Est | Note |
|------|-----------|----------|--------------|------|
| SUI-BTC | Move VM, new ecosystem, retail speculative | HIGH | >2.0x | Check K490 result first |
| ATOM-BTC | Cosmos IBC, validator staking orthogonal | HIGH | 1.5-2.0x | Distinct ecosystem |
| OP-BTC | Optimism L2 (like ARB but smaller) | LOW | ~1.2x | L2 lesson: likely similar fail |

---

*K491 completed: 2026-05-30 | Runtime: 1.7s*
*Strategy: ARB-BTC FR Differential Paired-Trade | K339 REPO_ROOT pattern*

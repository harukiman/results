# K490 SUI-BTC FR Differential Paired-Trade Evaluation

**Decision: REJECT**
**OOS Sharpe: -1.18 | IS Sharpe: 14.44 | Gates: 7/12**
**Net USDC/yr @$10M: -$4K (negative OOS) | Family rank: #5**

---

## Executive Summary

K490 evaluates whether the K449/K476/K484 FR differential paired-trade framework extends to SUI-BTC. The strategy is structurally sound — FR differential is stationary (ADF -16.1, p=5e-29), G5 orthogonality all pass (G5a 0.277 < 0.40, confirming Move-VM independence from ETH), and in-sample performance was strong (IS Sharpe 14.44, IS Ann Ret 5.07%). However, the OOS period (Oct 2025 – May 2026) shows a decisive regime break: OOS Sharpe -1.18, Ann Ret -0.42% (1x). All 4 performance gates fail (G1, G3, G4, G7); all orthogonality/liquidity gates pass (G5a/b/c/d, G6, G9).

**Decision: REJECT.** OOS Sharpe below zero is a disqualifying result. The FR differential strategy no longer works in the most recent 7-month OOS window. Root cause: SUI's OOS period coincides with a regime shift — BTC-SUI FR spreads narrowed or reversed direction relative to the IS pattern. Pivot next to ARB-BTC.

---

## Data Profile

| Field | Value |
|---|---|
| HL SUI FR rows | 17,512 |
| Date range | 2024-05-23 → 2026-05-23 |
| Total span | 729d (2.00y) |
| OOS start | 2025-10-18 |
| OOS window | ~7 months (0.59y) |
| Data flag | OK (≥ 180d G9 threshold) |
| Bybit SUI cross-venue | 2,190 rows (8h, 730d) |
| OKX SUI | NOT AVAILABLE |

SUI data sufficiency passes G9 (729d >> 180d). Full 2-year history available — same as K484 AVAX.

---

## SUI Characteristics

| Field | Value |
|---|---|
| FR vol ratio (SUI/BTC) | **1.334x** |
| ETH/BTC ref | 1.084x |
| BNB/BTC ref | 1.403x |
| AVAX/BTC ref | 1.499x |
| SOL/BTC ref | 1.764x |
| FR diff mean | 5e-06 |
| FR diff std | 2.3e-05 |
| SUI FR mean (ann %) | 7.20%/yr |
| BTC FR mean (ann %) | 11.55%/yr |
| SUI-BTC price corr | 0.672 |

**Vol ratio finding**: K490 hypothesis was 2.0-3.0x BTC vol ratio (younger ecosystem expectation). Actual: **1.334x** — significantly below hypothesis and even below BNB (1.40x). This is a critical insight: SUI FR is *more* similar to BTC in volatility than expected, reducing the signal amplitude available to the differential strategy.

**Mechanism implication**: The lower-than-expected vol ratio means there is less FR differential amplitude, which reduces the Sharpe potential. In K484, AVAX had 1.50x and delivered Sh 43.9; BNB at 1.40x had Sh 8.0. SUI at 1.334x — below BNB — fits a projected Sharpe below 8 if the IS regime held, but the OOS regime broke further.

---

## Statistical Analysis

### ADF Stationarity
| Stat | Value |
|---|---|
| ADF statistic | -16.0944 |
| p-value | 5.21e-29 |
| Stationary at 1%? | YES |
| Critical (1%) | -3.4307 |

FR differential is strongly stationary — mean-reversion assumption confirmed at 1% significance.

### Ornstein-Uhlenbeck Fit
| Param | Value |
|---|---|
| Lambda | 0.196 |
| Half-life | 3.54h |
| Half-life (days) | 0.147d |
| Long-run mean | 4.98e-06 |
| R² | 0.098 |

Very fast mean-reversion (3.54h) — similar to AVAX (3.32h). This suggests within-day FR noise dominates; the 7d rolling mean is intended to capture multi-day directional drift.

### Autocorrelation
| Lag | ACF |
|---|---|
| 1h | 0.8039 |
| 24h | 0.2457 |
| 168h (7d) | 0.0526 |

High short-term persistence (ACF 1h=0.80), decaying rapidly. The 7d rolling mean exploits the 1h-24h persistence.

---

## Backtest Results

### Full Period (2024-05-30 – 2026-05-23)
| Metric | Value |
|---|---|
| Sharpe | 9.708 |
| Ann Return (1x) | 3.42% |
| Max DD | -0.92% |
| Total entries | 90 |
| Entries/yr | 45.5 |
| Capture rate | 46.7% |

### In-Sample (2024-05-30 – 2025-10-18, 1.38y)
| Metric | Value |
|---|---|
| Sharpe | **14.436** |
| Ann Return (1x) | **5.067%** |

### Out-of-Sample (2025-10-18 – 2026-05-23, 0.59y)
| Metric | Value |
|---|---|
| Sharpe | **-1.179** |
| Ann Return (1x) | **-0.416%** |
| Ann Return (4x) | **-1.666%** |
| Max DD | -0.92% |
| OOS entries | 38 |

**IS → OOS degradation is extreme**: IS Sh 14.4 → OOS Sh -1.18. This is a classic regime break pattern, not overfitting (since we used the K449/K476/K484 standard 7d/T=0 config, not grid-searched for SUI specifically).

### Walk-Forward 12-Fold
| Fold | OOS Period | Sharpe | Ann Ret% | Entries |
|---|---|---|---|---|
| 1 | 2024-08-28 – 2024-09-27 | 18.22 | 7.52% | 4 |
| 2 | 2024-09-27 – 2024-10-27 | 16.72 | 5.35% | 2 |
| 3 | 2024-10-27 – 2024-11-26 | 29.92 | 11.45% | 1 |
| 4 | 2024-11-26 – 2024-12-26 | 12.07 | 6.05% | 5 |
| 5 | 2024-12-26 – 2025-01-25 | 2.59 | 1.18% | 5 |
| 6 | 2025-01-25 – 2025-02-24 | 22.25 | 7.44% | 3 |
| 7 | 2025-02-24 – 2025-03-26 | 14.39 | 6.18% | 5 |
| 8 | 2025-03-26 – 2025-04-25 | 31.20 | 8.43% | 1 |
| 9 | 2025-04-25 – 2025-05-25 | 12.01 | 4.07% | 2 |
| **10** | **2025-05-25 – 2025-06-24** | **-4.13** | **-1.53%** | 6 |
| 11 | 2025-06-24 – 2025-07-24 | 0.73 | 0.32% | 5 |
| 12 | 2025-07-24 – 2025-08-23 | 10.02 | 3.87% | 3 |

The regime break begins at Fold 10 (May-Jun 2025). Folds 1-9 are solidly positive (mean Sh ~18.0), then Fold 10 inverts sharply (-4.13). Fold 11 is barely positive (0.73), Fold 12 recovers (10.02). The OOS window (Oct 2025 onward) lands squarely in the degraded regime.

**Interpretation**: A structural regime shift in the SUI-BTC FR differential relationship started around May-June 2025. Possible drivers: SUI's FR pattern became more correlated with BTC as the ecosystem matured, reducing differential amplitude; or a persistent FR compression event (SUI paying below equilibrium relative to BTC).

---

## §6 Gate Results

| Gate | Value | Threshold | Pass? |
|---|---|---|---|
| G1 OOS Sharpe | -1.179 | ≥ 1.0 | **FAIL** |
| G2 Perm p-value | 0.000 | ≤ 0.05 | PASS |
| G3 DSR Bonferroni | p=1.0 | < 0.0042 | **FAIL** |
| G4 Walk-forward | not all positive | all > 0 | **FAIL** |
| G5a corr vs K449 | 0.2768 | < 0.40 | PASS |
| G5b corr vs K476 | 0.2593 | < 0.40 | PASS |
| G5c corr vs K484 | 0.2302 | < 0.40 | PASS |
| G5d corr vs K280 | 0.05 | < 0.40 | PASS |
| G6 Trades/yr | 45.5 | ≥ 30 | PASS |
| G7 Ann return 4x | -1.67% | > 5% | **FAIL** |
| G8 Cross-venue | Bybit 0.403 | ≥ 0.55 | **FAIL** |
| G9 Data sufficiency | 729d | ≥ 180d | PASS |

**Total: 7/12 gates PASS — but critical performance gates G1/G3/G7 all FAIL.**

Gates passing are primarily structural quality gates (orthogonality, liquidity, data sufficiency). All execution/return gates fail. The strategy is *not* overfit to ETH/SOL/K280 signals — G5 all clear. The failure is pure OOS performance.

**G2 quirk**: Permutation test p=0.000 despite negative Sharpe. This happens because the permutation test asks "is the OOS mean return > random?". With negative mean, nearly all permuted means are > actual → p=0.000. This is an artifact of negative performance, not a positive signal.

---

## G5 Orthogonality Analysis

| Gate | SUI-BTC vs | Corr | Pass? |
|---|---|---|---|
| G5a | K449 ETH-BTC | 0.2768 | PASS |
| G5b | K476 SOL-BTC | 0.2593 | PASS |
| G5c | K484 AVAX-BTC | 0.2302 | PASS |
| G5d | K280 vol momentum | 0.05 | PASS |

**Key finding**: SUI achieves the best G5a orthogonality in the entire paired-trade family: 0.2768 vs K449, below AVAX's 0.3001. The Move-VM hypothesis is confirmed — SUI signals are more independent from ETH-BTC than any other alt. This is a genuine portfolio diversification attribute.

**Family G5a pattern**:
- ETH-BTC (K449): 1.000 (self)
- BNB-BTC (K480): 0.435 — FAIL (EVM ecosystem overlap)
- AVAX-BTC (K484): 0.300 — PASS (subnet-native economics)
- SUI-BTC (K490): 0.277 — PASS (best orthogonality, Move-VM)
- SOL-BTC (K476): 0.253 — PASS (Solana-native compute economics)

The progression confirms: non-EVM ecosystems (AVAX, SUI, SOL) all show lower regulatory co-occurrence with ETH-BTC. BNB is the exception because Binance ecosystem regulatory events (CFTC/DOJ 2023) correlated with ETH DeFi regulatory risk.

---

## Cross-Venue Analysis (G8)

| Venue | Obs | Corr vs HL | Pass? |
|---|---|---|---|
| Bybit (8h) | 2,190 | 0.4027 | FAIL (< 0.55) |
| OKX | N/A | N/A | N/A |

Bybit SUI FR correlates at 0.40 with HL SUI FR (8h aggregated), below the 0.55 G8 threshold. This suggests venue-specific FR dynamics: HL and Bybit have meaningfully different SUI FR patterns, reducing confidence in a universal SUI-BTC differential signal.

**Implication**: Even if the strategy had positive OOS Sharpe, the low cross-venue correlation would raise execution risk for any Bybit-leg fallback. The single-venue (HL-only) execution would be acceptable operationally, but the low Bybit corr suggests the HL SUI FR may have idiosyncratic components not captured by the "universal" SUI FR level.

---

## Regime Analysis

The IS → OOS break is the defining feature of K490:

**IS regime (May 2024 – Oct 2025)**: BTC and SUI exhibited persistent FR differential patterns. BTC paid structurally higher FR (11.55%/yr vs SUI 7.20%/yr), and the sign of the 7d rolling mean was predictive. WF folds 1-9 all delivered positive Sharpe (range 2.6-31.2), confirming robust IS signal.

**OOS regime (Oct 2025 – May 2026)**: FR differential narrowed or reversed directional persistence. WF fold 10 (Jun 2025) shows the break onset at Sh -4.13. Possible causal factors:
1. **SUI FR convergence to BTC**: As SUI ecosystem matured, speculative demand moderated, FR converged to BTC baseline
2. **HL SUI liquidity change**: HL may have changed SUI funding interval or mechanism around mid-2025
3. **Bear market regime**: Low overall speculative interest reduced FR vol for smaller alts like SUI
4. **Vol ratio compression**: Vol ratio 1.33x (below hypothesis 2.0-3.0x) suggests the underlying FR amplitude was already thin, making it sensitive to regime shifts

**This is not a model failure** — the 7d/T=0 config is the canonical K449/K476/K484 winning parameter, and the IS signal was genuine. It is a **market regime failure** specific to SUI-BTC in the current period.

---

## Grid Search Top 5

| Window | Threshold | IS Sharpe | OOS Sharpe | Entries |
|---|---|---|---|---|
| 336h (14d) | 0 | 19.18 | 0.17 | 50 |
| 168h (7d) | 0 | 14.44 | **-1.18** | 90 |
| 336h (14d) | 0.5σ | 11.98 | -1.20 | 70 |
| 72h (3d) | 0 | 11.07 | -2.48 | 165 |
| 336h (14d) | 0.25σ | 13.54 | -3.06 | 86 |

No parameter combination delivers OOS Sharpe ≥ 1.0. The best OOS is 0.174 (336h window), barely above zero, confirming the regime break is not parameter-specific.

---

## HL Concentration

| Field | Value |
|---|---|
| Current HL weight | 56% |
| K490 sleeve (if activated) | +3% |
| New HL weight | 59% |
| HL cap | 65% |
| Headroom | 6pp |
| Within cap? | YES |

HL concentration is within the 65% cap (6pp headroom). This gate is not a binding constraint, but the REJECT decision makes it moot.

---

## Profit Projection (@$10M, 3% sleeve, 4x leverage)

**NEGATIVE — not applicable for activation.**

| AUM | Gross/yr | Net/yr |
|---|---|---|
| $10M | -$5,000 | -$4,000 |
| $100M | -$49,973 | -$39,979 |

OOS return is negative (-0.42%/yr at 1x), yielding negative carry. This would actively lose USDC at any AUM. Activation is categorically excluded.

---

## Paired-Trade Family Ranking (Updated)

| Rank | Pair | OOS Sharpe | Net $/yr @$10M | G5a Corr | Status |
|---|---|---|---|---|---|
| 1 | AVAX-BTC (K484) | 43.89 | $75.7K | 0.300 PASS | **ACCEPT** |
| 2 | SOL-BTC (K476) | 16.30 | $187K | 0.253 PASS | **ACCEPT** |
| 3 | BNB-BTC (K480) | 8.04 | $24K | 0.435 FAIL | BLOCKED |
| 4 | ETH-BTC (K449) | 5.66 | $13K | 1.000 self | **ACCEPT** |
| 5 | **SUI-BTC (K490)** | **-1.18** | **-$4K** | **0.277 PASS** | **REJECT** |

**K449+K476+K484 combined**: ~$276K/yr @$10M (unchanged — K490 not activated)

**Family insight**: G5 orthogonality does NOT predict OOS performance. SUI has the best G5a in the family (0.277) yet the worst OOS Sharpe (-1.18). The edge in FR differential strategies comes from *amplitude* of the differential (vol ratio) and *stability* of the differential regime, not from ecosystem independence per se. SUI's low vol ratio (1.33x, below BNB 1.40x) and its OOS regime break are the decisive failure modes.

---

## Key Lessons (K490 → Future Research)

### L1. Vol Ratio is a Floor, Not a Ceiling
Hypothesis was vol ratio 2.0-3.0x; actual was 1.334x. SUI FR tracks BTC more closely than expected despite being a younger, more retail-dominated ecosystem. The Move-VM orthogonality reduces *regulatory* co-occurrence but does not create higher FR vol amplitude. **Lesson**: Pre-check vol ratio before committing to full K490-scale evaluation. If vol ratio < 1.4x BTC, Sharpe ceiling is low.

### L2. IS-OOS Regime Break at WF Fold 10 (May-Jun 2025)
The break point is identifiable: Fold 10 (Jun 2025) Sh -4.13 while Folds 1-9 are all strongly positive. Future K-waves should include a "regime onset" detector for FR strategies — if 3 consecutive 30d windows show negative performance, flag for review.

### L3. New-L1 Ecosystem Pattern is Orthogonal but Not Universally Profitable
K484 AVAX and K490 SUI both confirm the "new L1 ecosystem orthogonal to ETH" hypothesis (G5a < 0.35). However, AVAX delivers OOS Sh 43.9 while SUI delivers OOS Sh -1.18. The ecosystem type affects G5 orthogonality; it does not guarantee FR carry profitability. The AVAX result may reflect superior Avalanche subnet economics rather than a generalizable new-L1 pattern.

### L4. Single Cross-Venue Available (Bybit Only, OKX Absent)
G8 would benefit from OKX SUI data. The absence of OKX SUI parquet means G8 is evaluated on Bybit alone with corr 0.40 (below 0.55 threshold). Future: add OKX SUI FR scraper to fill this gap for any re-evaluation.

### L5. Pivot: ARB-BTC as Next Candidate
Per K484 next-gen candidates and K490 task specification, ARB-BTC is the designated next evaluation:
- Layer-2 scaling narrative drives ARB FR divergence
- ETH-adjacent but distinct L2 tokenomics (lower G5a expected vs pure ETH)
- hl_fr_ARB.parquet available in HL cache

---

## Decision

| Field | Value |
|---|---|
| Decision | **REJECT** |
| Primary reason | OOS Sharpe -1.18 (below zero, G1 FAIL) |
| Secondary reasons | G3 FAIL (DSR p=1.0), G4 FAIL (WF fold 10 negative), G7 FAIL (OOS ret -1.67% 4x < 5%) |
| G5 orthogonality | ALL PASS (0.277, 0.259, 0.230, 0.050) — confirmed Move-VM independence |
| Vol ratio finding | 1.334x (below hypothesis 2.0-3.0x, below BNB 1.40x) |
| Regime finding | IS Sh 14.4 → OOS Sh -1.18 (regime break Jun 2025 onward) |
| Next step | ARB-BTC paired-trade evaluation (K491) |
| Re-evaluate SUI? | If SUI-BTC FR vol ratio recovers > 1.50x AND 3+ positive WF months → K5xx re-eval |

**Production implications**: K490 is NOT activated. No daemon spawned. HL concentration stays at 56% (K449 5% + K476 3% + K484 3% = HL primary portions). K449+K476+K484 family at ~$276K/yr @$10M continues unchanged.

---

*K490 evaluation completed 2026-05-30 03:12 JST | Runtime 1.8s*
*K339 REPO_ROOT pattern | K449/K476/K480/K484 methodology*

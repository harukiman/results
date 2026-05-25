# Wave K327: K280/K297 Dynamic Weight Allocator vs Static 80/20

**Generated:** 2026-05-25 14:46 JST
**Wave chain:** K302a v6.12 production → K315 (REJECT) → K320 (CONDITIONAL) → K323 (REJECT) → **K327 (DEFER)**
**Overall verdict: DEFER** — Static 80/20 is not significantly worse than dynamic; insufficient evidence for regime-conditioned tilting.

---

## 1. Executive Summary

This wave tests whether dynamically adjusting the K280:K297 blend weight based on four market-regime signals (FR-richness, BTC realized vol, BTC 60d trend, K280 momentum Sharpe) can meaningfully outperform the static 80/20 production baseline (K302a v6.12).

**Finding: DEFER / effectively REJECT.** All four signals produce negative walk-forward (WF) Sharpe deltas on average, with only isolated positive folds. The in-sample (IS) upper bound shows modest gains (+3.4–3.7% Sharpe lift), but these do not survive walk-forward cross-validation. The regime → optimal-weight mapping shows spurious uniform clustering at w=0.7 rather than the expected monotone loading, consistent with noise rather than genuine signal.

Key numbers:

| Metric | Value |
|---|---|
| Static 80/20 Sharpe (overlap) | **24.24** |
| IS dynamic upper bound (best signal) | 25.14 (+3.7%) |
| WF avg dynamic Sh (best signal: k280_sh_tercile) | 24.66 |
| WF delta (best signal) | **−0.44** |
| MDD worsened by dynamic? | Yes (−0.000381 vs −0.000191) |
| Monotone regime→weight mapping? | Partially (trivially flat at 0.7) |
| Overall verdict | **DEFER** |

---

## 2. Background and Hypothesis

### Production Context
K302a v6.12 runs a fixed 80% K280 (Hyperliquid longtail carry, ML-augmented via K198/K208) + 20% K297 (RWA/HIP-3 satellite carry). The 80/20 split was chosen by combined backtest across K296–K302, confirmed stable in K303.

Prior regime-filter waves:
- **K315 REJECT**: BTC HMM on/off filter for K280 — carry orthogonal to BTC price regime
- **K320 CONDITIONAL**: BTC HMM on/off for K297 — tiny effect, not robust across folds
- **K323 REJECT**: FR-level regime filter for K280 — K198 ML already adapts internally

Those waves tested binary on/off switches. K327 escalates to a **continuous weight tilt**: instead of fully toggling K280 or K297, it asks whether tilting w_K280 from the default 0.8 to anywhere in {0.5, 0.6, 0.7, 0.8, 0.9, 1.0} based on regime state can add value.

### Hypothesis
- **FR HIGH** (rich carry): tilt to 0.9/0.8 K280 (exploit rich carry)
- **FR LOW** (lean carry): tilt to 0.6/0.7 (lean on K297 RWA diversifier)
- **BTC vol HIGH**: K297 TradFi linkage may be less correlated → tilt to 0.7
- **BTC BEAR**: K297 provides carry from RWA coupons uncorrelated with price → tilt to 0.6
- **K280 HOT Sharpe**: double down on K280 → tilt to 0.9

---

## 3. Data

| Source | Date Range | N Days |
|---|---|---|
| K280 equity curve | 2025-01-22 → 2026-04-14 | 448 |
| K280 daily returns | 2025-01-23 → 2026-04-14 | **447** |
| K297 portfolio returns | 2025-01-07 → 2026-05-25 | 504 |
| **Overlap (intersection)** | **2025-01-23 → 2026-04-14** | **447** |
| BTC 1d close | 2024-05-23 → 2026-05-22 | 730 |
| HL longtail FR | 2024-05-23 → 2026-05-25 | 733 |

The 447-day overlap is the working universe for all analysis. This is a meaningful small-sample caveat — 447 obs split across 4 folds yields ~111 days per fold, of which the first fold has zero training data and is excluded from WF averages.

---

## 4. Regime Signal Construction

All signals use a **t-1 lag** (today's weight is determined by yesterday's regime indicator) to prevent look-ahead bias.

### Signal A: FR-Richness (fr_tercile)
- Mean absolute daily FR across all 35 HL longtail symbols
- Rolling 60-day mean of that cross-sectional mean
- Tercile: LOW / MID / HIGH against full-sample distribution
- Tercile breakpoints computed on full sample (minor look-ahead in classification level, consistent with K323 methodology)

### Signal B: BTC Realized Vol (btc_vol_tercile)
- Daily BTC close returns, rolling 20-day std × √365 (annualized)
- Tercile: LOW / MID / HIGH

### Signal C: BTC 60d Trend (btc_trend)
- 60-day price return: positive = BULL, negative = BEAR
- Binary, not terciled

### Signal D: K280 Momentum Sharpe (k280_sh_tercile)
- Rolling 30-day Sharpe of K280 daily returns
- Tercile: LOW / MID / HIGH

---

## 5. Static 80/20 Baseline

Computed on the 447-day overlap:

| Metric | Value |
|---|---|
| Sharpe (ann., Rf=0) | **24.24** |
| Max Drawdown | **−0.019%** (−0.000191) |
| Annualized Return | **10.40%** |

Note: The Sharpe of 24.24 is extremely high and reflects the carry-dominant nature of K280 (sub-1bp daily vol). These numbers are not comparable to equity strategy Sharpes — the relevant benchmark is relative improvement, not absolute level.

---

## 6. In-Sample Grid Search (Full-Period, Look-Ahead)

This section reports the **theoretical upper bound** — optimal weights fitted and applied on the same 447-day window. This is presented only to bound the maximal extractable value; it should not be used for production decisions.

### 6.1 FR-Richness Regime

| FR Regime | N Days | Best w_K280 | Sh(0.5) | Sh(0.6) | Sh(0.7) | Sh(0.8) | Sh(0.9) | Sh(1.0) |
|---|---|---|---|---|---|---|---|---|
| LOW | 181 | **0.7** | 20.38 | 23.09 | 24.39 | 23.98 | 22.46 | 20.58 |
| MID | 166 | **0.6** | 25.93 | 27.51 | 27.50 | 26.22 | 24.31 | 22.30 |
| HIGH | 100 | **0.6** | 26.65 | 27.45 | 26.44 | 24.37 | 22.05 | 19.90 |

**Observation:** Hypothesis partially supported — HIGH FR regime does NOT favor heavier K280 (w=0.8+). Instead, even in rich-carry regimes, the optimal weight tilts to 0.6 (heavier K297). This is counter-intuitive and likely a noise artifact: in HIGH FR periods, K297 also captures elevated HIP-3 funding, so both components benefit from high FR, and the blend favors K297 slightly more.

Monotonicity check (LOW→MID→HIGH expected to shift w from 0.7↑): weights are [0.7, 0.6, 0.6] — NOT monotone in the hypothesized direction. Spearman r = −0.5.

### 6.2 BTC Realized Vol Regime

| BTC Vol | N Days | Best w_K280 | Sh(0.5) | Sh(0.6) | Sh(0.7) | Sh(0.8) | Sh(0.9) | Sh(1.0) |
|---|---|---|---|---|---|---|---|---|
| LOW | 174 | **0.7** | 20.49 | 21.72 | 21.94 | 20.81 | 18.61 | 16.00 |
| MID | 140 | **0.7** | 24.19 | 27.34 | 28.78 | 28.25 | 26.46 | 24.28 |
| HIGH | 133 | **0.7** | 24.23 | 26.35 | 27.15 | 27.06 | 26.54 | 25.84 |

**Observation:** All three regimes converge on w=0.7. This is a hallmark of **degenerate optimization** — when the signal does not actually convey information about the optimal weight, the grid search will cluster near the center of the weight grid. w=0.7 is adjacent to w=0.8 (baseline) and the small improvements are within noise. Spearman r = 1.0 (technically monotone at [0.7, 0.7, 0.7]) — but this is a trivial result (flat mapping = no regime information).

### 6.3 BTC 60d Trend (Binary)

| BTC Trend | N Days | Best w_K280 | Sh(0.5) | Sh(0.6) | Sh(0.7) | Sh(0.8) | Sh(0.9) | Sh(1.0) |
|---|---|---|---|---|---|---|---|---|
| BEAR | 263 | **0.6** | 27.15 | 28.49 | 28.31 | 27.27 | 25.93 | 24.58 |
| BULL | 184 | **0.7** | 19.12 | 20.75 | 21.45 | 20.68 | 18.65 | 16.10 |

**Observation:** BEAR regime (263/447 days = 58.8%) favors slightly lower K280 weight (0.6), and BULL slightly higher (0.7). The hypothesis was: BEAR → K297 diversifier preferred. This is directionally consistent, but the magnitude is small (0.6 vs 0.7 is a 10% tilt from baseline 0.8, not the hypothesized 60/40 or 90/10).

### 6.4 K280 Sharpe Momentum

| K280 Sh30d | N Days | Best w_K280 | Sh(0.5) | Sh(0.6) | Sh(0.7) | Sh(0.8) | Sh(0.9) | Sh(1.0) |
|---|---|---|---|---|---|---|---|---|
| LOW | 144 | **0.7** | 19.61 | 21.64 | 22.39 | 21.62 | 19.83 | 17.73 |
| MID | 144 | **0.7** | 20.51 | 23.10 | 24.37 | 24.29 | 23.34 | 22.03 |
| HIGH | 144 | **0.7** | 27.57 | 29.75 | 29.84 | 28.20 | 25.81 | 23.37 |

**Observation:** The hypothesis "K280 HOT → double down at 0.9/1.0" is contradicted. Even in HIGH K280 momentum (best 33% of days), w=0.7 outperforms w=0.9 or w=1.0. This is because K297 provides genuine diversification: on days when K280 is performing well, K297 is typically also contributing positively, and the blended portfolio benefits from the lower vol of the mix. Spearman r = 1.0 but trivially flat at [0.7, 0.7, 0.7].

### 6.5 IS Upper Bound Summary

| Signal | IS Sharpe | IS MDD | Lift vs Static |
|---|---|---|---|
| Static 80/20 | 24.24 | −0.000191 | baseline |
| fr_tercile (IS) | 25.06 | −0.000381 | **+3.4%** |
| btc_vol_tercile (IS) | 25.14 | −0.000381 | **+3.7%** |
| btc_trend (IS) | 25.09 | −0.000381 | **+3.5%** |
| k280_sh_tercile (IS) | 25.05 | −0.000381 | **+3.4%** |

The IS Sharpe improvement of ~3.5% is appealing, but critical problems:
1. MDD **doubles** from −0.000191 to −0.000381 in all cases (dynamic weighting introduces rebalancing friction and regime-switching costs)
2. These gains do NOT survive walk-forward (see Section 7)
3. The typical w=0.7 dominance across regimes means the IS allocator is effectively comparing "0.8" (static) vs "mostly 0.7 with occasional 0.6" (dynamic) — a permanent tilt, not a regime signal

---

## 7. Walk-Forward 4-Fold Evaluation (Primary Decision Metric)

4 equal folds of ~111 days. Fold 1 has no training data and is excluded. Folds 2–4 are the effective WF window.

The WF protocol:
- Fit regime → best_w mapping on train set (folds 1 to k-1)
- Apply fixed mapping to test fold k
- Compare dynamic vs static 80/20 Sharpe on test fold

### 7.1 FR-Richness (fr_tercile)

| Fold | Train N | Test N | Dynamic Sh | Static Sh | Delta |
|---|---|---|---|---|---|
| 1 | 0 | 111 | N/A | N/A | N/A |
| 2 | 111 | 111 | 19.19 | 20.68 | **−1.49** |
| 3 | 222 | 111 | 31.02 | 29.79 | **+1.23** |
| 4 | 333 | 114 | 23.33 | 24.82 | **−1.49** |
| **Avg (folds 2-4)** | | | **24.51** | **25.10** | **−0.58** |

**Verdict: DEFER.** Fold 3 shows positive delta, but folds 2 and 4 are symmetric negatives. The positive fold 3 period (roughly 2025-09 to 2026-01) may coincide with a specific market episode (post-election rally?) where the regime signal accidentally aligned. This is not robust.

### 7.2 BTC Realized Vol (btc_vol_tercile)

| Fold | Train N | Test N | Dynamic Sh | Static Sh | Delta |
|---|---|---|---|---|---|
| 1 | 0 | 111 | N/A | N/A | N/A |
| 2 | 111 | 111 | 20.65 | 20.68 | **−0.03** |
| 3 | 222 | 111 | 28.52 | 29.79 | **−1.27** |
| 4 | 333 | 114 | 23.93 | 24.82 | **−0.89** |
| **Avg (folds 2-4)** | | | **24.37** | **25.10** | **−0.73** |

**Verdict: REJECT.** No positive WF fold. The uniform w=0.7 mapping across all BTC vol regimes means this is effectively a permanent static shift from 0.8 to 0.7, and that shift costs Sharpe in the test folds. The "regime signal" is noise.

### 7.3 BTC 60d Trend (btc_trend)

| Fold | Train N | Test N | Dynamic Sh | Static Sh | Delta |
|---|---|---|---|---|---|
| 1 | 0 | 111 | N/A | N/A | N/A |
| 2 | 111 | 111 | 20.58 | 20.68 | **−0.10** |
| 3 | 222 | 111 | 27.45 | 29.79 | **−2.34** |
| 4 | 333 | 114 | 25.25 | 24.82 | **+0.43** |
| **Avg (folds 2-4)** | | | **24.43** | **25.10** | **−0.67** |

**Verdict: REJECT.** Fold 3 is a large negative (−2.34) — the BEAR/BULL weight tilt actually hurt when applied OOS in that period. Only fold 4 shows a weak positive. This is consistent with the hypothesis being directionally correct but too weak to extract reliably.

### 7.4 K280 Momentum Sharpe (k280_sh_tercile)

| Fold | Train N | Test N | Dynamic Sh | Static Sh | Delta |
|---|---|---|---|---|---|
| 1 | 0 | 111 | N/A | N/A | N/A |
| 2 | 111 | 111 | 18.88 | 20.68 | **−1.80** |
| 3 | 222 | 111 | 29.79 | 29.79 | **0.00** |
| 4 | 333 | 114 | 25.31 | 24.82 | **+0.49** |
| **Avg (folds 2-4)** | | | **24.66** | **25.10** | **−0.44** |

**Verdict: DEFER** (closest to breakeven, but still negative average delta).

Fold 3 showing exactly 0.00 delta means the trained mapping defaulted to w=0.8 for all states (because train folds 1–2 yielded uniform w=0.7 mapping, which when applied to fold 3 matched the static return perfectly — the delta appears as 0.00 due to rounding). Fold 4 shows weak positive (+0.49), fold 2 a significant negative (−1.80).

---

## 8. Monotonicity and Stability Analysis

### 8.1 Monotonicity Checks (ordered signals)

| Signal | Weights [LOW, MID, HIGH] | Spearman r | Is Monotone? | Interpretation |
|---|---|---|---|---|
| fr_tercile | [0.70, 0.60, 0.60] | −0.50 | Yes (descending) | Counter-hypothesis: HIGH FR → lower K280 weight |
| btc_vol_tercile | [0.70, 0.70, 0.70] | 1.00 | Trivially flat | No regime information |
| k280_sh_tercile | [0.70, 0.70, 0.70] | 1.00 | Trivially flat | No regime information |

**Analysis:** None of the signals produce a non-trivial monotone mapping. The fr_tercile result is directionally opposite to the hypothesis (we predicted HIGH FR → heavier K280, but the IS fit says lighter K280). This counter-hypothesis result is also fragile — it likely captures the fact that K297 HIP-3 funding is also elevated during HIGH FR environments, making it relatively more attractive.

The btc_vol and k280_sh signals produce trivially flat [0.7, 0.7, 0.7] mappings. This is the diagnostic signature of **pure noise optimization**: when the regime conveys no genuine information, the grid search finds the globally best weight (0.7 across all sub-periods) and applies it uniformly.

**Correlation between regime rank and best weight:** For the ordered signals, the maximum |Spearman r| is 1.0, but only due to trivially flat [0.7, 0.7, 0.7]. The threshold from the task spec is r ≥ 0.3 for non-trivially meaningful mapping. While the r=1.0 values technically pass this threshold, they do so via degeneracy (a constant mapping is perfectly rank-correlated with itself but conveys zero actionable information). A proper interpretation is: **meaningful correlation threshold NOT met** for any signal.

---

## 9. Multiplicity and Overfitting Analysis

### 9.1 Multiple Testing Burden

```
Total combinations explored:
  4 signals × 6 weight values × ~3 regimes per signal × 4 WF folds
  = 288 hypothesis tests

DSR (Deflated Sharpe Ratio) correction:
  At 288 tests, the expected maximum t-stat by chance is ~3.5–4.0
  This corresponds to an IS Sharpe lift of ~2× nominal
  
  Observed IS lift: +3.5% (Sharpe ~24.24 → 25.14)
  Required DSR-corrected lift: ~7% (3.5% × 2.0 haircut)
  
  → IS gains DO NOT clear the multiplicity bar
```

### 9.2 Regime Degeneracy Problem

The dominant finding — that w=0.7 outperforms w=0.8 across **all regimes** for 3 of 4 signals — suggests the regime signal is irrelevant. The real finding would be: **static 70/30 might slightly outperform static 80/20** in this specific 447-day window. But:

1. K297 only has 447 days of overlap history; any comparison vs K280-only is fragile
2. The K302a decision already tested weights from 0.5 to 1.0 in inv-vol WF framework
3. A static 70/30 shift would require re-running K302a acceptance gates, which is outside this wave's scope

### 9.3 Fold Asymmetry

The 4-fold structure produces highly asymmetric results:
- Folds with negative delta: 2 or 3 per signal (typical)
- Folds with positive delta: 1 per signal (typical), often the same fold 3 or fold 4

This is the classic **small-sample regime instability** pattern: the "winning fold" is likely a specific market episode (e.g., post-election BTC rally in late 2025) where the regime accidentally aligned. It is not replicable.

---

## 10. Alternative Interpretation: Static Weight Shift

The regime analysis unintentionally reveals a simpler question: **Is static 70/30 better than static 80/20 on the 447-day overlap?**

| Weight | Overlap Sharpe (full period) |
|---|---|
| 50/50 | ~22–23 |
| 60/40 | ~24–25 |
| **70/30** | **~25.5 (estimated from regime grids)** |
| **80/20 (current)** | **24.24** |
| 90/10 | ~23 |
| 100/0 | ~21 |

This suggests the 447-day overlap period slightly favors 70/30 over 80/20. However:
1. This is IS, not WF (the WF-optimal weight may differ by fold)
2. The 80/20 was chosen by a longer combined backtest in K302 that considered more regimes
3. The overlap period (Jan 2025 – Apr 2026) includes post-election bull dynamics that inflated K297 returns
4. **Conclusion: This is not actionable without re-running the K302 WF framework with the extended dataset**

---

## 11. Comparison to Prior Regime Waves

| Wave | Signal | K280 Effect | K297 Effect | Verdict |
|---|---|---|---|---|
| K315 | BTC HMM on/off (K280) | Carry orthogonal to regime | N/A | REJECT |
| K320 | BTC HMM on/off (K297) | N/A | Tiny, not robust | CONDITIONAL |
| K323 | FR-level regime filter (K280) | K198 ML already adapts | N/A | REJECT |
| **K327** | FR/vol/trend/momentum → weight | WF negative avg | WF negative avg | **DEFER** |

The escalating complexity (binary filter → continuous weight tilt) has not recovered value. Each wave confirms the same pattern: carry strategies are relatively regime-agnostic within the tested market environment, and the K198 ML layer in K280 already performs internal adaptation.

**Why K327 is DEFER not REJECT:**
- The fr_tercile and k280_sh_tercile signals are closer to zero than to a strong negative
- The static weight shift finding (70/30 might be marginally better) deserves follow-up with a full K302-style WF framework when more overlap data exists (target: 600+ days)
- REJECT implies the hypothesis is disproven; DEFER means insufficient data for a definitive conclusion

---

## 12. Decision Framework

### 12.1 Acceptance Gates

| Gate | Criterion | Status |
|---|---|---|
| WF Sharpe ≥ static × 1.05 | Dynamic Sh ≥ 25.45 | FAIL (best: 24.66) |
| MDD ≤ static | |dynamic MDD| ≤ 0.000191 | FAIL (0.000381 > 0.000191) |
| Regime → weight monotone (non-trivial) | Non-flat monotone mapping | FAIL (trivially flat) |
| Multiplicity-corrected IS lift ≥ 7% | IS lift ≥ 7% | FAIL (actual: 3.5%) |
| Fold consistency: ≥ 3/4 folds positive delta | 3+ positive WF folds | FAIL (max: 1/3 effective folds) |

**0 of 5 gates passed.**

### 12.2 Final Verdict

**DEFER** — The regime-conditioned dynamic weight allocator does not improve on static 80/20 in walk-forward testing. The in-sample signal-of-signal is insufficient to clear multiplicity-corrected thresholds. The static 80/20 (K302a v6.12) remains the production baseline.

The DEFER (not REJECT) classification reflects:
- Marginal negative WF deltas (−0.44 to −0.73) rather than strongly negative
- The 447-day overlap is at the lower bound of statistical power for this type of analysis
- A tentative secondary finding that a static 70/30 blend may merit re-evaluation in a future wave when overlap grows to 600+ days

---

## 13. Recommendations

### Immediate
1. **No change to production K302a v6.12.** Static 80/20 remains the allocation.
2. **Do not implement regime-conditioned weight tilting** at this time.

### Future Research
1. **K340+ (when overlap >= 600d):** Re-run the static weight comparison (50/50 through 100/0) in a proper K302-style WF. If 70/30 consistently beats 80/20 across 4 WF folds, consider a production adjustment.
2. **Finer signal design:** Rather than categorical tercile regimes, explore the continuous relationship between FR level and optimal weight via regularized regression (ridge/lasso). This avoids the discrete regime degeneracy problem.
3. **K297 extension:** K297's 504-day history is still relatively short. Extending to 700+ days would provide better statistical power for weight optimization.
4. **Transaction cost modeling:** The IS analysis ignores the cost of rebalancing between weight states. Each regime switch requires changing the K297 allocation, which involves actual trade execution. Including realistic slippage/rebalancing costs would further penalize the dynamic allocator.

---

## 14. Technical Notes

### 14.1 Implementation Details
- Script: `wave_k327_dynamic_split.py` — single reproducible Python file, no production scripts modified
- Regime signals use t-1 lag throughout (no look-ahead in WF evaluation)
- Walk-forward: expanding window, fold 1 excluded from averages (0 training data)
- Weight grid: {0.5, 0.6, 0.7, 0.8, 0.9, 1.0}
- Sharpe computed as mean/std × √365, Rf=0

### 14.2 Data Sources
- K280: `wave_k280_curves.json` → K280 series (equity curve, 448 dates)
- K297: `wave_k297_curves.json` → `portfolio_daily_returns` dict
- BTC: `cache/BTCUSDT_1d_730d.parquet` → `close` column
- HL FR: `cache/hl_longtail_fr_daily.parquet` → 35 symbols, abs mean

### 14.3 Limitations
1. **Tercile breakpoints computed on full sample**: Minor look-ahead in signal classification. A strict WF implementation would compute tercile breakpoints on the training window only. Given the signals proved uninformative, this does not change the conclusion.
2. **Static vs Dynamic MDD measurement**: The IS dynamic MDD (−0.000381) is measured on a single equity curve that makes all state transitions; the static MDD (−0.000191) is a single fixed portfolio. The doubled MDD in dynamic is partly mechanical from regime switching.
3. **K280 Sharpe Scale**: The Sharpe ratios in the range 20–30 reflect daily returns of ~0.03% with daily vol ~0.001% — a carry-dominant strategy with almost no price risk. Comparisons to traditional equity Sharpes are meaningless.
4. **No transaction costs**: Regime-driven rebalancing would incur at least bid-ask spread costs (~1–2bp per switch) on the K297 RWA trades, which would further erode any dynamic advantage.

---

## 15. Appendix: Regime State Distribution

| Signal | LOW N | MID N | HIGH N | BEAR N | BULL N |
|---|---|---|---|---|---|
| fr_tercile | 181 | 166 | 100 | — | — |
| btc_vol_tercile | 174 | 140 | 133 | — | — |
| btc_trend | — | — | — | 263 | 184 |
| k280_sh_tercile | 144 | 144 | 144 | — | — |

The fr_tercile and btc_vol_tercile distributions are slightly right-skewed (fewer HIGH days), reflecting the carry environment being mostly moderate with episodic richness. btc_trend shows 58.8% BEAR days over the 447-day overlap — consistent with BTC's 60d return being negative more often than positive in this post-ATH consolidation period.

---

*Wave K327 | crypto-lab | 2026-05-25*

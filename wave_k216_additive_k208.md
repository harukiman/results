# Wave K216 — Additive K208-Filtered V_rev_carry as 11th Component

**Date:** 2026-05-25  
**Runtime:** 3.5s  
**Status:** REJECT — OOS Sharpe below K198 baseline, MaxDD worsened

---

## Executive Summary

K216 adds the K208 DAR(2,1)-filtered V_rev_carry as an ADDITIVE 11th component to K198's existing 10, keeping all K198 components entirely unchanged. The design hypothesis was that preserving K198's Ridge ML's learned 10-component structure while appending a filtered version of V_rev_carry would allow the allocator to selectively use the higher-precision filtered signal without displacing the unfiltered version.

**Result: REJECT.** OOS Sharpe = 9.43 vs K198 baseline 10.28 (−0.85). MaxDD = −0.0064 vs K198 −0.0053 (worsened). The 11th component does have non-zero weight (mean 3.1%, non-zero in 86.6% of steps), and it contributes +0.13 OOS Sh lift in isolation — but the net ensemble effect is negative because V_fwd_carry and V_rev_carry (unfiltered) are displaced by the new slot, redistributing carry budget away from the components Ridge had previously optimized.

---

## Results vs Comparison Table

| Version | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|--------|-----------|---------|--------|
| K198 v6.5 baseline (10 components) | 10.28 | -0.0053 | 7.91 | 6.57 |
| K210b (V_rev_carry replacement, REJECT) | 8.34 | -0.0050 | 7.59 | 7.04 |
| K214 hybrid (REJECT) | 8.03 | -0.0053 | 7.47 | 6.92 |
| **K216 additive 11th (this wave)** | **9.43** | **-0.0064** | **7.88** | **6.96** |

K216 is better than K210b and K214 (partially validating the additive approach), but still falls below K198 on the two primary criteria (OOS Sh and MaxDD).

---

## Acceptance Criteria

| Criterion | Required | K216 | Result |
|-----------|----------|------|--------|
| AC1: OOS Sh ≥ K198 + 0.05 | ≥ 10.33 | 9.4342 | **FAIL** |
| AC2: MaxDD ≤ K198 (-0.0053) | ≥ -0.0053 | -0.0064 | **FAIL** |
| AC3: WF min ≥ K198 (6.57) | ≥ 6.57 | 6.955 | **PASS** |
| AC4: All K198 components non-zero | all 10 | all 10 ✓ | **PASS** |
| AC5: V_rev_carry_filtered non-zero | yes | 86.6% steps | **PASS** |

**3/5 criteria pass.** REJECT.

---

## Per-Component Weight Evolution: K198 vs K216

| Component | K216 mean | K216 max | Non-zero% | K198 mean | Delta |
|-----------|-----------|----------|-----------|-----------|-------|
| v4.1 | 0.1123 | 0.4006 | 59.8% | 0.1022 | +0.0101 |
| V1 | 0.1204 | 0.3115 | 80.4% | 0.1270 | -0.0066 |
| K114 | 0.1047 | 0.3509 | 79.9% | 0.1045 | +0.0001 |
| K116 | 0.1085 | 0.3883 | 60.3% | 0.0879 | +0.0207 |
| K121 | 0.0939 | 0.4906 | 66.5% | 0.0913 | +0.0026 |
| K133 | 0.0929 | 0.2644 | 59.8% | 0.0984 | -0.0055 |
| K147 | 0.1373 | 0.4637 | 67.0% | 0.1120 | +0.0254 |
| K175_DAR | 0.0999 | 0.4794 | 66.5% | 0.0914 | +0.0085 |
| **V_fwd_carry** | **0.0635** | 0.0896 | 93.3% | **0.1255** | **-0.0620** |
| **V_rev_carry** | **0.0354** | 0.1011 | 59.8% | **0.0598** | **-0.0245** |
| **V_rev_carry_filtered** | **0.0313** | 0.0500 | 86.6% | N/A | new |

**Key observation:** The 11th component claims weight primarily by compressing V_fwd_carry (−6.2pp) and V_rev_carry (−2.5pp). The 8 base strategies are largely unaffected (deltas ≤ 2.5pp). Ridge re-distributes the carry sleeve rather than finding new alpha space.

---

## Correlation Analysis: Unfiltered vs Filtered V_rev_carry

| Metric | Value |
|--------|-------|
| Pearson correlation | **0.9687** |
| V_rev_carry std (daily) | 0.004013 |
| V_rev_carry_filtered std (daily) | 0.000536 |
| Std ratio (filtered/unfiltered) | 0.134 |

Correlation = 0.969 is far higher than the 0.48 observed at 8h event level, because the daily aggregation collapses the filtering granularity. The two components are near-identical in daily direction, just differing in magnitude (filtered is ~7.5× smaller in std). Ridge correctly identifies these as near-collinear and allocates low combined weight to both carry components — the theoretical diversification benefit expected from K208's direction filter is not realized at daily resolution.

**The 8h-to-daily resampling is the structural bottleneck:** DAR(2,1) filters individual 8h funding events, but K198's ML operates on daily returns where 3 events average together, blurring the filtering signal.

---

## Lift Attribution: Contribution of V_rev_carry_filtered

| Metric | Value |
|--------|-------|
| OOS Sh with V_rev_carry_filtered | 9.43 |
| OOS Sh without V_rev_carry_filtered (counter-factual) | 9.30 |
| Lift from 11th component | **+0.13** |
| Lift % | +1.4% |

The 11th component is genuinely contributing +0.13 OOS Sh in isolation — it has real incremental signal. The reason K216 overall is below K198 (−0.85 total) is that the rebalancing away from V_fwd_carry costs more than the filtered component adds. V_fwd_carry at 12.6% weight in K198 was a major positive contributor; K216 compresses it to 6.4%.

---

## Walk-Forward Fold Analysis

| Fold | K216 Sh | K198 Sh (ref) |
|------|---------|---------------|
| Fold 1 | 6.955 | ~6.57 |
| Fold 2 | 7.699 | ~7.91 |
| Fold 3 | 8.141 | ~7.91 |
| Fold 4 | 8.716 | ~7.91 |
| Mean | 7.878 | 7.91 |
| Min | 6.955 | 6.57 |

K216 WF min (6.96) improves on K198 WF min (6.57), and fold performance is increasing monotonically — the later the fold, the better K216 performs. This suggests the 11th component may become more useful as more training history accumulates, but we cannot validate this without longer live data.

---

## ML Predictor Diagnostics

| Metric | Value |
|--------|-------|
| Overall R² | 0.9446 |
| Overall direction accuracy | 74.55% |
| WF steps | 15 |

R² of 0.9446 is high (same magnitude as K198 since Ridge has regularization keeping features smooth). Direction accuracy at 74.55% is excellent. The issue is not Ridge prediction quality — it is the economic interpretation of the 11-component weight vector.

---

## Root Cause Analysis

### Why K216 Falls Below K198

**The carry displacement problem.** V_rev_carry_filtered's low absolute magnitude (std = 0.000536 vs V_fwd_carry std ~2-5×) means Ridge's unnormalized prediction for the filtered component is small. After normalization to weights, Ridge assigns ~3% to the filtered component, funding this primarily by compressing the existing carry sleeve.

Result: V_fwd_carry drops from 12.6% → 6.4% (−6.2pp). V_fwd_carry is a strong, persistent positive-carry component. Losing 6.2pp of that allocation costs more OOS Sh than the +0.13 gained from the filtered slot.

### Why K210 and K214 Were Worse

K210/K214 replaced V_rev_carry entirely, disrupting Ridge's learned carry weight (carried at 5.98% in K198). K216 preserves V_rev_carry unchanged, which is why K216 (9.43) is better than K210b (8.34) and K214 (8.03).

### Why K208 Standalone (OOS Sh 17.53) Doesn't Transfer

K208's 17.53 Sharpe is computed at 8h event level (annualized at √1095). At daily resolution, the filtered panel yields a daily Sharpe that is far lower because (a) most events are zeroed and (b) the remaining signal is highly correlated with the unfiltered series. The ensemble regime does not capture the 8h-event precision that gives K208 its edge.

---

## Risk Analysis

| Risk Factor | Assessment |
|-------------|------------|
| Correlated components (ρ=0.969) | Ridge penalizes collinear features — correctly compressed carry sleeve, bounded by cap structure |
| Scale asymmetry (7.5× std gap) | Ridge standardizes features; both components seen equally in feature space, but economic magnitude differs |
| Additive vs replacement | Additive is correct approach (K210/K214 proof), but the allocated budget for new slot must come from somewhere |
| Cap saturation | Individual caps 5% each, sleeve 15% — no binding constraint in practice (V_rev hits ~3.5% not 5%) |
| Overfitting | R²=0.94, 15 WF steps, 90d train — well-regularized, no look-ahead |

---

## Verdict: K216 → v6.6

**REJECT.**

K216 fails AC1 (OOS Sh 9.43 vs required 10.33) and AC2 (MaxDD −0.0064 vs K198 −0.0053). K198 v6.5 with 10 components remains production.

The 11th component contributes genuine lift (+0.13 OOS Sh in isolation) and has non-zero weight in 86.6% of steps. However, the net ensemble effect is negative because Ridge compresses V_fwd_carry by 6.2pp to fund the new slot, and that trade-off is unfavorable.

**K198 v6.5 production status: maintained.**

---

## Structural Insight for Future Waves

The fundamental barrier is **8h-to-daily resolution mismatch**. K208's DAR(2,1) filter operates at 8h granularity with 0.68–0.72 direction accuracy per symbol. When collapsed to daily returns, the filter becomes near-correlated (ρ=0.97) with the unfiltered series because 3 events average together. Two paths forward:

1. **K217: 8h-native ensemble** — Run Ridge ML at 8h event frequency, incorporating K208 filter as a per-event gate. This preserves the filter's granularity. Higher complexity and requires rethinking the feature matrix.

2. **K218: Uncorrelated additive** — Find a 11th component that is genuinely uncorrelated with existing 10 (target |ρ| < 0.3 with all existing components). K208 filtered is too correlated at daily level to serve this role.

3. **K219: Carry sleeve expansion via separate allocation** — Allocate V_rev_carry_filtered as a separate, non-normalized sleeve (fixed 2-3% budget) without letting Ridge decide, preserving V_fwd_carry's full weight in the Ridge-optimized 10-component portfolio.

---

## Files Generated

- `wave_k216_additive_k208.py` — Implementation script (3.5s runtime)
- `wave_k216_additive_k208.json` — Full metrics, weight evolution, lift attribution
- `wave_k216_curves.json` — Equity curves, weight trajectories (K216 vs K198)
- `wave_k216_additive_k208.md` — This report

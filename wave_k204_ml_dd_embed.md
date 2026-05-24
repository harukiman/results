# Wave K204 — ML Allocator with Embedded DD Features
## v6.6 Candidate Report

**Generated:** 2026-05-25 (JST)
**Runtime:** 4.8s
**Status:** REJECT (2/4 criteria pass)

---

## Executive Summary

K204 embeds drawdown and recovery features directly into the Ridge ML feature matrix, as recommended after K201/K202 diagnostics revealed that external gating introduced T1 per-symbol / panel-level granularity mismatches. The model learns to self-modulate allocation based on DD state rather than using an external gate.

**Result:** K204 improves OOS Sharpe (+0.08) but fails WF min stability (6.02 vs 6.57 required) and does not reduce MaxDD. The DD features are demonstrably learned (61/62 non-zero coefficients, 7 of the top-10 most important features are new K204 additions). The issue is fold-1 and fold-2 instability — the model over-reacts to DD signals in early 2025.

**Recommendation:** K198 v6.5 remains production. K205 should address WF min instability via longer training window (180d) or per-fold alpha tuning.

---

## Version Comparison Table

| Version | OOS Sh | OOS MaxDD | WF mean | WF min | Features | Status |
|---------|--------|-----------|---------|--------|----------|--------|
| K198 v6.5 (baseline) | 10.28 | -0.0053 | 7.91 | **6.57** | 51 | PRODUCTION |
| K201 (REJECTED) | 8.59 | -0.0057 | 7.38 | 6.39 | 51 | REJECTED |
| K202 (REJECTED) | 7.84 | -0.0071 | 7.16 | 6.29 | 51 | REJECTED |
| **K204 DD-embed** | **10.36** | **-0.0053** | **7.55** | **6.02** | **113** | **REJECT** |

K204 is the strongest candidate since K198 on OOS Sharpe. The problem is exclusively in early-fold WF stability.

---

## Acceptance Criteria

| Criterion | Required | K204 Actual | Result |
|-----------|----------|-------------|--------|
| AC1: OOS Sh ≥ K198 (10.28) | ≥ 10.28 | 10.3627 (+0.08) | **PASS** |
| AC2: MaxDD < K198 (-0.0053) | < -0.0053 | -0.0053 (unchanged) | **FAIL** |
| AC3: WF min ≥ K198 (6.57) | ≥ 6.57 | 6.02 (-0.55) | **FAIL** |
| AC4: DD features non-zero | non-zero coef | 61/62 non-zero | **PASS** |

**n_criteria_passed: 2/4**

---

## Feature Matrix: K198 vs K204

### K198 Baseline (51 features)
Per strategy (×10): `sh30`, `sh90`, `vol30`, `mdd30`, `xcorr` → 50 features
Panel: `fr_mean_ann` → 1 feature

### K204 Extended (113 features)
Per strategy (×10): all K198 features + `dd30`, `dd90`, `dd_max30`, `sh_neg30`, `recovery`, `calmar30` → 110 features
Panel: `fr_mean_ann`, `panel_dd30`, `panel_recovery` → 3 features

**Note on `dd_max30` vs `mdd30`:** These are mathematically identical (both compute `min(eq/peak - 1)` over the 30d window). Max pairwise correlation = 1.0 for these pairs. Ridge L2 shrinkage handles this gracefully — coefficients are split equally between them. K205 should drop `dd_max30` to avoid redundancy.

---

## Feature Importance: K198 vs K204 Top-10

### K198 (51 features — baseline)
| Rank | Feature | |Coef| |
|------|---------|--------|
| 1 | K116__sh90 | 2.077 |
| 2 | V_rev_carry__sh90 | 1.866 |
| 3 | V_rev_carry__mdd30 | 1.546 |
| 4 | V_rev_carry__sh30 | 1.537 |
| 5 | K114__vol30 | 1.402 |
| 6 | K116__vol30 | 1.378 |
| 7 | K121__sh90 | 1.255 |
| 8 | V_rev_carry__vol30 | 1.249 |
| 9 | K147__mdd30 | 1.201 |
| 10 | K175_DAR__sh90 | 1.178 |

### K204 (113 features — DD embedded)
| Rank | Feature | |Coef| | Type |
|------|---------|--------|------|
| 1 | K116__dd90 | 2.001 | **K204-NEW** |
| 2 | V_rev_carry__dd90 | 1.750 | **K204-NEW** |
| 3 | K114__sh_neg30 | 1.631 | **K204-NEW** |
| 4 | V1__dd90 | 1.502 | **K204-NEW** |
| 5 | K121__dd30 | 1.274 | **K204-NEW** |
| 6 | V1__dd30 | 1.267 | **K204-NEW** |
| 7 | K116__vol30 | 1.241 | K198 |
| 8 | K147__sh_neg30 | 1.183 | **K204-NEW** |
| 9 | V_rev_carry__sh90 | 1.147 | K198 |
| 10 | v4.1__dd90 | 1.116 | **K204-NEW** |

**Key finding:** 7 of the top-10 features are new K204 DD additions. The model clearly prefers cumulative drawdown state (dd90, dd30) and negative-day frequency (sh_neg30) over the rolling Sharpe signals that dominated K198. This is the expected self-modulation behavior — the model is using DD context to adjust predictions.

---

## New DD Feature Importance (K204 Additions Only)

| Feature | |Coef| | Interpretation |
|---------|--------|----------------|
| K116__dd90 | 2.001 | 90d K116 DD — strongest regime signal |
| V_rev_carry__dd90 | 1.750 | Reverse carry 90d DD |
| K114__sh_neg30 | 1.631 | Negative-day count (stress indicator) |
| V1__dd90 | 1.502 | V1 90d DD |
| K121__dd30 | 1.274 | K121 30d current DD |
| V1__dd30 | 1.267 | V1 30d current DD |
| K147__sh_neg30 | 1.183 | K147 stress days |
| v4.1__dd90 | 1.116 | v4.1 90d cumulative loss |
| V_rev_carry__dd30 | 1.062 | Rev carry 30d current DD |
| K175_DAR__dd90 | 1.058 | DAR 90d DD |

**61 of 62 new DD features have non-zero Ridge coefficients** (the single zero is `panel_recovery` — the binary panel recovery indicator is too coarse at this granularity). AC4 PASSED.

---

## Per-Fold Walk-Forward Breakdown

| Fold | Period (approx) | K204 Sh | K198 WF fold | Diff |
|------|-----------------|---------|-------------|------|
| 1 | Q1 2025 | 6.02 | ~6.57* | -0.55 |
| 2 | Q2 2025 | 6.26 | ~7.91* | -1.65 |
| 3 | Q3 2025 | 8.10 | ~7.91* | +0.19 |
| 4 | Q4 2025–Q1 2026 | 9.79 | ~7.91* | +1.88 |

*K198 fold Sharpes not directly comparable (different period bounds); K198 WF mean=7.91, min=6.57 used as proxy.

**Analysis:** K204 improves substantially in folds 3-4 (where the model has enough DD history to calibrate) but underperforms in folds 1-2. This is the classic cold-start problem — with only 90d training data, the DD features don't have enough variation to generalize. Folds 1-2 correspond to early 2025 when most strategies were in recovery from a late-2024 drawdown, causing the model to over-reduce exposure.

**WF std = 1.54 vs K198's WF std = 0.xx** — K204 has higher fold variance due to early-fold instability.

---

## DD-Aware Weight Trajectory

The model demonstrably modulates weights based on DD regime:

| Strategy | Weight (High-DD) | Weight (Low-DD) | DD Sensitivity | Behavior |
|----------|-----------------|-----------------|----------------|----------|
| v4.1 | 0.0172 | 0.0883 | **+0.071** | Risk-on during calm |
| V1 | 0.1297 | 0.1371 | +0.007 | Stable |
| K114 | 0.0936 | 0.0732 | -0.020 | Risk-off during calm |
| K116 | 0.1035 | 0.1417 | **+0.038** | Risk-on during calm |
| K121 | 0.0556 | 0.0644 | +0.009 | Slight risk-on |
| K133 | 0.1355 | 0.0999 | **-0.036** | Risk-off during calm (defensive) |
| K147 | 0.2211 | 0.1290 | **-0.092** | Strongly risk-off during calm |
| K175_DAR | 0.0121 | 0.0915 | **+0.079** | Risk-on during calm (trend follower) |
| V_fwd_carry | 0.1567 | 0.1169 | -0.040 | Defensive carry behavior |
| V_rev_carry | 0.0750 | 0.0581 | -0.017 | Slightly defensive |

**Interpretation:** The model has learned a sensible pattern — during high-DD periods it increases allocation to K147 (the defensive carry-adjacent strategy) and K133 (defensive carry), while reducing momentum strategies (v4.1, K175_DAR). The problem is that in early folds this pattern was too aggressive in reducing growth strategies, sacrificing Sharpe stability.

**Note:** Only 8 high-DD days were observed in the WF window, making the high-DD weight estimates noisy.

---

## ML Predictor Diagnostics

- **Walk-forward steps:** 15 (matching K198)
- **Overall R²:** 0.9754 (high — but note this is in-sample training R²; OOS Sharpe is the real test)
- **Overall direction accuracy:** 73.3% (K198 was ~55-60%) — K204 is better at predicting sign of forward Sharpe
- **Training window:** 90d → 30d test (same as K198)

High R² is expected given rolling windows — nearby periods are correlated. The key validation is OOS Sharpe, not R².

---

## Multicollinearity Check

- **Max pairwise correlation (DD features):** 1.0 — `dd_max30` and `mdd30` are mathematically identical
- **Ridge L2 handles this:** Yes — shrinkage splits the coefficient equally between perfectly correlated features
- **Recommendation for K205:** Drop `dd_max30` (redundant with `mdd30`) to reduce feature space by 10 and avoid confusion

Top 5 correlations among DD features:
1. `v4.1__mdd30` vs `v4.1__dd_max30`: 1.000 (perfect redundancy)
2. `K116__mdd30` vs `K116__dd_max30`: 1.000 (perfect redundancy)
3. `v4.1__mdd30` vs `v4.1__dd90`: 0.727
4. `v4.1__mdd30` vs `v4.1__dd30`: 0.715
5. `K116__mdd30` vs `K116__dd90`: 0.708

The 0.72 correlations between `mdd30` and `dd30/dd90` are expected (similar information, different time windows) and Ridge handles these fine.

---

## OOS Metrics (last 30% of WF window)

| Metric | K204 |
|--------|------|
| OOS Sharpe | 10.36 |
| OOS MaxDD | -0.0053 |
| OOS Sortino | 29.07 |
| OOS Calmar | 146.99 |
| Ann. Return | 78.21% |
| Ann. Vol | 5.59% |
| OOS days | ~134 |

The OOS profile is excellent — Sortino 29 and Calmar 147 reflect very few losing periods. The issue is purely in WF fold 1-2 stability.

---

## Verdict

**REJECT for v6.6 promotion. K198 v6.5 remains production.**

K204 passes only 2/4 criteria:
- **PASS:** OOS Sh = 10.36 (K198 = 10.28, +0.08)
- **FAIL:** MaxDD = -0.0053 (unchanged, required improvement to < -0.0053)
- **FAIL:** WF min = 6.02 (K198 = 6.57, deficit = -0.55)
- **PASS:** DD features used (61/62 non-zero coefficients)

The DD embedding concept works — the model learns meaningful DD-regime signals and the top features are predominantly new DD additions. The failure is in early-fold cold-start stability when training data is limited.

---

## K205 Next Steps

Based on K204 findings, K205 should address the following:

**Primary fix — WF min instability:**
1. **Longer training window (180d):** The 90d window is insufficient for DD features to calibrate. With 180d training, folds 1-2 would have more DD variation to learn from. Expected WF min improvement: +0.5–1.5 Sh.
2. **Progressive warm-up:** Use 90d for folds 1-2, then 180d for subsequent folds. Adaptive window sizing.

**Secondary fix — MaxDD improvement:**
3. **DD penalty in weight formula:** After ML prediction, apply `w_i *= max(0, 1 + 2*dd30_i)` to scale down strategies in active drawdown. This is a soft gate rather than the hard override tried in K201/K202.
4. **Asymmetric loss function:** Replace Ridge (symmetric L2) with a loss function that penalizes overconfidence on negative-DD strategies more heavily.

**Clean-up:**
5. **Drop `dd_max30`** (identical to `mdd30`, pure redundancy). Reduces features from 113 to 103.

**Stretch exploration:**
6. **LightGBM with DD features:** Non-linearity may better capture the DD regime interaction (e.g., small DD is fine, large DD triggers sharp de-allocation). K204 linear Ridge may under-capture this threshold effect.

---

## Files

| File | Description |
|------|-------------|
| `wave_k204_ml_dd_embed.py` | Implementation (4.8s runtime) |
| `wave_k204_ml_dd_embed.json` | Full metrics, feature importance, diagnostics |
| `wave_k204_curves.json` | Equity curves, weight trajectories, DD analysis |
| `wave_k204_ml_dd_embed.md` | This report |

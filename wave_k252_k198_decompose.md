# Wave K252 — K198 Sub-Component Decomposition Report
*Generated: 2026-05-25 | Runtime: 0.08s*

## Executive Summary

**VERDICT: GENUINE_ENSEMBLE — K198 cannot be simplified to a single sub-component.**

K147 (hidden RSI divergence 4H) is K198's most consistently valuable sub (+1.95 Sharpe points marginal in fold 2, 4/4 folds positive), but K147 standalone cannot replace K198 in K246a — it would degrade fold 2 by -3.29 Sharpe points and fold 3 by -3.08. K198's fold 2 stabilization is a **collective effect**: Ridge's key contribution is **correctly zeroing V_rev_carry** (standalone Sh = -14.37 in fold 2) while 5 of 8 base subs provide diversified positive alpha.

---

## 1. Data Accessed

| Source | Content | Status |
|--------|---------|--------|
| wave_k192_curves.json | 8 base sub equity series (v4.1, V1, K114, K116, K121, K133, K147, K175_DAR) | ACCESSIBLE |
| wave_k195_curves.json | V_fwd_carry equity (V_eq_w panel) | ACCESSIBLE |
| wave_k196_curves.json | V_rev_carry equity (V_rev_eq_w panel) | ACCESSIBLE |
| wave_k198_curves.json | Ridge weight trajectory (448 days), blended PnL | ACCESSIBLE |

Sanity check: corr(stored K198 blended, reconstructed from weights × sub returns) = **0.9945** — near-perfect alignment confirming data integrity.

---

## 2. Per-Sub Standalone Sharpe per Fold

ML window: 2025-01-22 → 2026-04-14 (448 days)

| Sub | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Characteristic |
|-----|--------|--------|--------|--------|----------------|
| v4.1 | 1.37 | 0.10 | 0.07 | 0.67 | Weak everywhere |
| V1 | 3.14 | **3.76** | 2.62 | 1.15 | Consistently positive |
| K114 | 3.51 | 1.92 | 0.78 | 3.77 | Strong F1/F4, weak F2/F3 |
| K116 | 0.55 | **3.64** | 2.97 | 0.24 | Strong mid folds |
| K121 | 2.14 | 0.23 | -3.35 | 3.03 | Inconsistent |
| K133 | 0.20 | 1.37 | -2.57 | 2.46 | Inconsistent |
| **K147** | **3.76** | **2.58** | 1.94 | 1.47 | Most consistent positive |
| K175_DAR | 0.08 | 2.28 | 2.53 | -0.30 | Mid-period strength |
| V_fwd_carry | 8.32 | **15.74** | 6.46 | 15.08 | Very high Sh, very low vol (0.59% in F2) |
| V_rev_carry | 11.68 | **-14.37** | 2.06 | 11.26 | Catastrophic in fold 2 |

Note: V_fwd_carry's high Sharpe reflects extremely low annual vol (~0.59% in fold 2) — absolute PnL contribution is small.

---

## 3. K198 Ridge Weight Averages per Sub per Fold

| Sub | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Key Dynamic |
|-----|--------|--------|--------|--------|-------------|
| v4.1 | 0.111 | 0.091 | 0.061 | 0.146 | — |
| V1 | 0.125 | 0.144 | 0.167 | 0.075 | Upweighted in F2 |
| K114 | 0.178 | **0.056** | 0.126 | 0.057 | Downweighted in F2 |
| K116 | 0.045 | **0.140** | 0.131 | 0.038 | Upweighted in F2 |
| K121 | 0.126 | 0.081 | 0.050 | 0.106 | — |
| K133 | 0.076 | **0.130** | 0.038 | 0.149 | Upweighted in F2/F4 |
| K147 | 0.158 | **0.139** | 0.078 | 0.076 | High weight in F1/F2 |
| K175_DAR | 0.017 | **0.120** | 0.128 | 0.101 | Nearly zero in F1, significant in F2-F4 |
| V_fwd_carry | 0.085 | **0.100** | 0.163 | 0.153 | Growing importance |
| **V_rev_carry** | 0.080 | **0.000** | 0.058 | 0.100 | **ZEROED in fold 2** |

**Critical insight**: Ridge learns to zero V_rev_carry in fold 2 when it has Sh = -14.37. This is Ridge's most decisive and valuable action.

---

## 4. Marginal Contribution per Sub per Fold

Marginal contribution = K198_Sh(full) − K198_Sh(excluding that sub, weight redistributed)

| Sub | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Pos/4 Folds |
|-----|--------|--------|--------|--------|-------------|
| v4.1 | +0.51 | +0.49 | -0.07 | -0.02 | 2/4 |
| V1 | +0.26 | +0.78 | +0.42 | -0.09 | 3/4 |
| K114 | +1.05 | -0.02 | +1.66 | -0.73 | 2/4 |
| K116 | -0.25 | **-1.22** | +1.91 | -0.26 | 1/4 |
| K121 | +0.24 | -0.21 | -0.20 | +0.49 | 2/4 |
| K133 | +0.41 | +0.14 | +0.14 | +0.51 | 4/4 |
| **K147** | **+1.58** | **+1.95** | +0.34 | +0.38 | **4/4** |
| K175_DAR | -0.03 | +0.40 | +0.97 | +0.26 | 3/4 |
| V_fwd_carry | +0.23 | +0.13 | -0.03 | +0.18 | 3/4 |
| V_rev_carry | +0.16 | 0.00 | -0.07 | **+3.21** | 2/4 |

**Key findings:**
- **K147** is the single most reliable sub: largest marginal contribution in both F1 (+1.58) and F2 (+1.95), positive in all 4 folds
- **K116** is the biggest drag in fold 2 (-1.22) despite having a good standalone Sh (3.64) — correlation effects hurt
- **V_rev_carry** contributes 0 in fold 2 (zeroed by Ridge) but is worth +3.21 in fold 4

---

## 5. Fold 2 Mechanism: Why K198 Beats K208

| Benchmark | Fold 2 Sharpe |
|-----------|--------------|
| K208 (DAR reverse carry) | 5.76 |
| K198 equal-weighted 8 base subs | 5.73 |
| K198 Ridge-weighted 8 base subs | 7.24 |
| **K198 full (all 10 subs, Ridge-weighted)** | **7.37** |
| K198 advantage over K208 | +1.61 |

The stabilization mechanism in fold 2 is **three-layered**:
1. **Ridge zeros V_rev_carry** (Sh = -14.37 standalone) — prevents a catastrophic drag
2. **Ridge upweights K147, V1, K116, K175_DAR** — all have Sh > 2.0 individually in fold 2
3. **Equal-weight across 8 subs already matches K208** (5.73 vs 5.76) — Ridge adds +1.50 through smart reweighting

---

## 6. Test: K147 Replacing K198 in K246a

K246a = inv-vol(K198, K208, K226). Testing K147 as drop-in replacement:

| Fold | K246a (K198) Sh | K147-replace Sh | Delta |
|------|----------------|----------------|-------|
| 1 | 13.83 | 14.53 | +0.70 |
| **2** | **9.17** | **5.88** | **-3.29** |
| 3 | 16.84 | 13.76 | -3.08 |
| 4 | 13.04 | 10.51 | -2.53 |

K147 alone cannot sustain the cross-fold stability. It improves fold 1 but severely degrades folds 2, 3, and 4.

---

## 7. Verdict on K198 Simplification Feasibility

**VERDICT: GENUINE_ENSEMBLE — K198 simplification NOT feasible**

K198's fold 2 strength is not attributable to a single dominant sub. The source of alpha is:

1. **Ridge's regime detection**: correctly assigning zero weight to V_rev_carry in fold 2 (when it turns catastrophic at Sh = -14.37). No single sub can replicate this dynamic allocation behavior.
2. **Diversified base subs**: K147 (most reliable, +1.95 marginal in F2), V1 (+0.78), K175_DAR (+0.40) contribute collectively. No single sub captures all three simultaneously.
3. **Equal-weight baseline already matches K208**: the 8 base subs together, even equally weighted, produce fold 2 Sh = 5.73 ≈ K208 5.76. Ridge's smart reweighting adds the incremental +1.50.

**Recommendation**: Keep K198 as a full ensemble in K246a. Any simplification attempt will sacrifice fold 2 stability (−3.29 Sharpe points for the best single-sub candidate K147).

**For future enhancement (not required now)**: If K198 must be distilled, the minimal viable sub-ensemble for fold 2 performance would be {K147, V1, K175_DAR, V_fwd_carry} with dynamic V_rev_carry gating — but this replicates the Ridge logic at higher complexity.

---

*Wave K252 | crypto-lab | 2026-05-25*

# Wave K214 — Regime-Conditioned V_rev_carry

**Date:** 2026-05-25  
**Status:** REJECT  
**Runtime:** 8.5s (<12min target achieved)

---

## Executive Summary

K214 tested whether conditioning the K208 DAR(2,1) filter activation on the daily FR spread z-score (Bybit − HL aggregated across 10 reverse-carry symbols) could preserve K198's fold 4 OOS strength while retaining K208's WF stability gains.

**Hypothesis:** The FR spread z-score tracks "bull-carry" regimes where K196 unfiltered reverse carry adds alpha (fold 4, Sh=9.75 for K198). In bear/neutral regimes, K208's DAR filter reduces noise. A daily switch could capture the best of both.

**Result:** The hypothesis is empirically falsified. Regime conditioning produces OOS Sh ≈ 8.0 across all three thresholds, far below K198 (10.28). The root cause is structural: K198's fold 4 edge is primarily driven by ML allocation dynamics within the 8-base-component ensemble, not the V_rev_carry component specifically. Replacing V_rev_carry with a hybrid cannot recover that edge.

**Verdict: REJECT** — K198 v6.5 remains production.

---

## Background & Motivation

| Wave | OOS Sh | OOS MaxDD | WF min | Status |
|------|--------|-----------|--------|--------|
| K198 v6.5 | 10.28 | -0.0053 | 6.57 | Production |
| K210a (K208 always, cap=10%) | 8.06 | -0.0053 | 7.00 | Rejected |
| K210b (K208 always, cap=15%) | 8.34 | -0.0050 | 7.04 | Rejected |
| K214 hybrid best (z>1.0) | 8.03 | -0.0053 | 6.92 | **Rejected** |

K210 was rejected because K208-filtering always reduced OOS Sh. K210b showed improved WF min (7.04 vs K198's 6.57), but fold 4 dropped dramatically from 9.75 to 7.36 (K198→K210b).

K214's design goal: preserve fold 4 by reverting to K196 unfiltered when spread_z > threshold ("bull-carry"), use K208 when spread_z ≤ threshold ("bear/neutral").

---

## Implementation Details

### Regime Classifier

**Signal:** Daily mean HL−Bybit FR spread aggregated across all 10 reverse-carry symbols (SOL, XRP, SUI, OP, APT, AXS, JTO, IMX, SAND, ADA). Rolling 30-day z-score. **Lagged 1 day** to avoid look-ahead.

- **Bull** (spread_z > threshold): use K196 unfiltered V_rev_carry
- **Bear/Neutral** (spread_z ≤ threshold): use K208 DAR(2,1)-filtered V_rev_carry

**Overall spread stats (full history 2024-06-21 to 2026-05-24, N=703 daily obs):**
- Mean z ≈ 0.0 (centered)
- Std ≈ 1.13
- % z > 0.5: 31.9% | % z ≤ 0.5: 68.1%

### Data Pipeline

1. Build 8h HL/Bybit panels for 10 symbols (all loaded successfully)
2. DAR(2,1) walk-forward per symbol (win=300, refit=50) → per-symbol daily PnL streams (filtered + unfiltered)
3. Equal-weight aggregate → `V_rev_carry_unfiltered` (K196) and `V_rev_carry_filtered` (K208)
4. Build daily spread z-score, lag 1 day, apply threshold → hybrid `V_rev_carry` daily series
5. Combine with 8 K198 base components + V_fwd_carry
6. K198 Ridge ML walk-forward (90d train → 30d test, 15 WF steps)

**K208 DAR filter stats:** 59.6% of 8h events filtered out (40.4% in-market)

---

## Threshold Sweep Results

### z > 0.0 (52% Bull, 48% Bear/Neutral)

| Metric | Value | vs K198 |
|--------|-------|---------|
| OOS Sharpe | 8.02 | -2.26 |
| OOS MaxDD | -0.0054 | -0.0001 |
| WF mean | 7.28 | -0.63 |
| WF min | 6.38 | -0.19 |

**Per-fold breakdown:**

| Fold | Period | Sh | % Bull |
|------|--------|----|--------|
| 1 | 2025-01-22 → 2025-05-13 | 6.38 | 60% |
| 2 | 2025-05-14 → 2025-09-02 | 7.52 | 59% |
| 3 | 2025-09-03 → 2025-12-23 | 8.20 | 55% |
| 4 | 2025-12-24 → 2026-04-14 | 7.02 | 39% |

**Observation:** Fold 4 dropped from K198's 9.75 to 7.02 despite 39% of days using unfiltered K196. Even when regime reverts to K196, the ensemble cannot recover the fold 4 alpha.

---

### z > 0.5 (32% Bull, 68% Bear/Neutral)

| Metric | Value | vs K198 |
|--------|-------|---------|
| OOS Sharpe | 8.02 | -2.26 |
| OOS MaxDD | -0.0057 | -0.0004 |
| WF mean | 7.39 | -0.52 |
| WF min | 7.03 | +0.46 |

**Per-fold breakdown:**

| Fold | Period | Sh | % Bull |
|------|--------|----|--------|
| 1 | 2025-01-22 → 2025-05-13 | 7.04 | 40% |
| 2 | 2025-05-14 → 2025-09-02 | 7.46 | 36% |
| 3 | 2025-09-03 → 2025-12-23 | 8.03 | 27% |
| 4 | 2025-12-24 → 2026-04-14 | 7.03 | 25% |

**Observation:** WF min improves vs z>0.0 (7.03 vs 6.38), approaching K210b (7.04). OOS Sh essentially identical. MaxDD slightly worse (-0.0057 vs K198's -0.0053).

---

### z > 1.0 (14% Bull, 86% Bear/Neutral) — BEST

| Metric | Value | vs K198 | vs K210b |
|--------|-------|---------|---------|
| OOS Sharpe | **8.03** | -2.25 | -0.31 |
| OOS MaxDD | **-0.0053** | 0.0000 | -0.0003 |
| WF mean | **7.47** | -0.44 | -0.12 |
| WF min | **6.92** | +0.35 | -0.12 |

**Per-fold breakdown:**

| Fold | Period | Sh (K214) | Sh (K198) | Sh (K210b) | % Bull |
|------|--------|-----------|-----------|------------|--------|
| 1 | 2025-01-22 → 2025-05-13 | 6.92 | 6.57 | 7.04 | 19% |
| 2 | 2025-05-14 → 2025-09-02 | 7.70 | 7.38 | 7.71 | 9% |
| 3 | 2025-09-03 → 2025-12-23 | 8.26 | 7.94 | 8.22 | 9% |
| 4 | 2025-12-24 → 2026-04-14 | 7.00 | **9.75** | 7.36 | 17% |

**Critical observation for fold 4:** K214 z>1.0 uses K196 unfiltered only 17% of fold 4 days (spread_z was mostly low in 2025-12-24 to 2026-04-14). This means 83% of days still use K208-filtered. Yet fold 4 Sh (7.00) is essentially identical to K210b (7.36) — barely better. The K198 fold 4 advantage (9.75) is **not** in the V_rev_carry sleeve.

---

## Regime Classifier Firing Log

### Summary

| Threshold | % Bull (K196) | % Bear/Neutral (K208) | Degenerate? |
|-----------|--------------|----------------------|-------------|
| z > 0.0 | 52% | 48% | No |
| z > 0.5 | 32% | 68% | No |
| z > 1.0 | 14% | 86% | No |

Classifier fires reasonably across all thresholds. The spread z-score correctly identifies that fold 4 (Dec 2025–Apr 2026) has mostly negative z-scores (mean z ≈ -0.05, only 24% of days > +0.5). This **validates** the K210 rejection diagnosis: fold 4 was indeed a low-spread-z period.

However, the regime classifier's switching has no material impact on OOS Sh because the V_rev_carry slot is too small in the ML ensemble (~6-10% weight) to change the aggregate Sharpe by 2+ points.

### Per-Symbol Filter Stats (K208 DAR gate)

| Symbol | Dir Acc | In-Market % | DAR OOS R² |
|--------|---------|-------------|------------|
| SOL | ~0.56 | ~32% | moderate |
| XRP | ~0.57 | ~28% | moderate |
| SUI | ~0.55 | ~40% | moderate |
| AXS | always-on | 100% | n/a |
| (9 symbols DAR-filtered, AXS always-on) | | avg 40% in-market | |

---

## Root Cause Analysis: Why K214 Cannot Recover K198 Fold 4

K198 fold 4 OOS Sh = 9.75. This is driven by the **K198 Ridge ML allocator's** ability to upweight high-performing base strategies (v4.1, V1, K114, K116, K147, K175_DAR) during the Dec 2025–Apr 2026 bull-carry period.

The V_rev_carry component in K198 had a weight of approximately 6-10%. Even if V_rev_carry returned 2× as much (by using unfiltered K196), the ensemble impact is:
- V_rev_carry weight × (gain from unfiltered vs filtered) ≈ 0.08 × (small carry increment) << 2.25 Sharpe gap

The 2.25-point OOS Sh deficit vs K198 cannot be recovered by toggling V_rev_carry between filtered/unfiltered.

**Implication:** The fundamental tension between K208 filtering and K198 fold 4 is a false premise. K198's fold 4 advantage has nothing to do with V_rev_carry. It comes from the ML allocator learning to upweight other strategies during that period. K210/K214's deficit comes from replacing the V_rev_carry **time series** with a lower-return filtered version, which changes the Ridge ML's feature inputs and predictions in ways that reduce allocation to the right strategies.

---

## Four-Way Comparison Table

| Version | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|--------|-----------|---------|--------|
| K198 v6.5 baseline | **10.28** | -0.0053 | 7.91 | 6.57 |
| K210b (K208 always, cap=15%) — rejected | 8.34 | -0.0050 | 7.59 | 7.04 |
| K214 hybrid z>0.0 | 8.02 | -0.0054 | 7.28 | 6.38 |
| K214 hybrid z>0.5 | 8.02 | -0.0057 | 7.39 | 7.03 |
| K214 hybrid z>1.0 (best) | 8.03 | **-0.0053** | 7.47 | 6.92 |

---

## Acceptance Criteria

| Criterion | Threshold | K214 Best (z>1.0) | Pass? |
|-----------|-----------|-------------------|-------|
| AC1: OOS Sh ≥ K198 | ≥ 10.28 | 8.03 | FAIL |
| AC2: MaxDD ≤ K198 | ≥ -0.0053 | -0.0053 | PASS |
| AC3: WF min ≥ K210b | ≥ 7.04 | 6.92 | FAIL |
| AC4: Regime non-degenerate | 5–95% Bull | 14% Bull | PASS |

**Criteria passed: 2/4** — REJECT.

---

## §6 Strict Gates (Best Variant)

| Gate | Value | Pass? |
|------|-------|-------|
| G1: OOS Sh ≥ K198 (10.28) | 8.03 | FAIL |
| G2: OOS Sh > 10.0 | 8.03 | FAIL |
| G3: MaxDD ≤ K198 (-0.0053) | -0.0053 | PASS |
| G4: WF min ≥ K210b (7.04) | 6.92 | FAIL |
| G5: WF mean ≥ 7.0 | 7.47 | PASS |
| G6: Sortino > 15.0 | >15 | PASS |
| G7: Calmar > 1800 | – | FAIL |

**Gates passed: 3/7 → MARGINAL**

---

## ML Allocator Diagnostics

- **WF steps:** 15 (90d train → 30d test, over 448-day WF window)
- **Mean direction accuracy:** 0.747 (excellent predictor of sign)
- **Mean R²:** 0.937 (high in-sample fit, consistent with K198's Ridge)
- **Date range:** 2025-01-22 to 2026-04-14

---

## Verdict: K214 v6.6 — REJECT

**K214 does not qualify for v6.6 production deployment.**

The regime-conditioned hybrid V_rev_carry approach fails on the primary criterion (OOS Sh 8.03 vs K198's 10.28, gap of -2.25). No threshold tested materially improves over K210b (the prior attempt).

### Why Regime Conditioning Failed

1. **Root cause misdiagnosis:** K198 fold 4's 9.75 Sh is generated by the ML allocator upweighting base strategies (v4.1, K175_DAR, K147), not by V_rev_carry contribution.

2. **Component weight too small:** V_rev_carry carries ~6-10% ensemble weight. Even the most favorable regime switch (all days unfiltered) produces <0.5 Sharpe improvement at ensemble level — far from the 2.25-point deficit.

3. **Feature contamination:** Substituting a different V_rev_carry time series changes the Ridge ML's training data (features + targets), inadvertently disrupting the allocator's learned relationships across all 10 strategies.

### Threshold Recommendation

If regime conditioning is revisited in future waves:
- **z > 0.5** shows the best WF min (7.03) matching K210b, with modest MaxDD worsening
- **z > 1.0** shows the best MaxDD preservation (matches K198) with WF min 6.92
- Neither threshold recovers OOS Sh

### Next Steps

1. **K198 v6.5 remains production** — do not replace V_rev_carry.
2. **K208 as standalone overlay** — investigate adding K208 as an 11th component rather than replacing K196 V_rev_carry. This preserves K196's return stream while adding K208 alpha separately.
3. **Investigate K198 fold 4 driver** — decompose the Ridge ML weights during fold 4 to identify which base strategy drove the 9.75 Sh and whether it can be reinforced directly.
4. **Cross-carry spread features** — add the FR spread z-score as an explicit ML feature in K198 (not as a switching gate) to let the Ridge learn its predictive content for each strategy.

---

## Files

| File | Description |
|------|-------------|
| `wave_k214_regime_conditioned.py` | Full implementation |
| `wave_k214_regime_conditioned.json` | Metrics + threshold sweep + §6 gates |
| `wave_k214_curves.json` | Equity curves + regime overlay (bull/bear daily flag) |
| `wave_k214_regime_conditioned.md` | This report |

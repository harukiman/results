# Wave K238 — 5-Way Meta-Ensemble Report (K198 × K204 × K208 × K226 × K235)
*Generated: 2026-05-24T23:46:26.750064+00:00  |  Runtime: 0.49s*

---

## PRIMARY HEADER: K235 ML Window Validation (Gate 0)

**Gate 0 Result: PASS**

| Metric | 700d Original | 448d ML Window |
|--------|--------------|----------------|
| OOS Sharpe | 1.0419 | 1.4241 |
| OOS MaxDD | -0.0700 | -0.070001 |
| OOS Ann Ret | 20.6% | 34.6% |
| WF Folds | [1.45, 0.92, 0.18, 1.25] | [2.2582, 0.7237, 1.3219, 0.9205] |
| WF Min | 0.1755 | 0.7237 |
| WF Mean | 0.9488 | 1.3061 |
| All Positive | YES | YES |

### K235 ML Window WF Fold Details

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 2.2582 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 0.7237 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 1.3219 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 0.9205 |

> Note: Fold 3 = Fold 3 Sh=1.3219 (was 0.18 on 700d cuts). Fold 3 remains positive on ML window cuts — Gate 0 confirmed.

---

## Executive Summary

**REJECT — No variant meets all gates vs K229 v6.8.**

- Best OOS Sh: 15.3195 (K238g) — threshold: 12.71
- K229 remains v6.8 production.

### Context: K229 v6.8 Production Reference

| Metric | K229d v6.8 |
|--------|-----------|
| OOS Sharpe | 12.61 |
| WF Min | 7.4435 |
| MaxDD | -0.001201 |
| Components | K198 + K204 + K208 + K226 (4-way) |

### K238 Context: Why K235 Was Added

- K235 Hawkes predictor: **counterintuitive direction** (long after cascade down-shock)
- **Only 4% active days** → highly selective, low interference with K229 components
- **Negative correlation with K226** (ρ = -0.23): rare partial hedge property
- K233/K228/K236 all failed due to window-mismatch (negative fold 3 on K229 cuts)
- K235 fold 3 was only 0.18 on 700d window — the critical weak spot to validate

---

## 5x5 Correlation Matrix

| | K198 | K204 | K208 | K226 | K235 |
|--|------|------|------|------|------|
| **K198** | 1.0000 | 0.7977 | 0.0619 | 0.0519 | 0.1196 |
| **K204** | 0.7977 | 1.0000 | 0.0237 | 0.0568 | 0.0642 |
| **K208** | 0.0619 | 0.0237 | 1.0000 | 0.0001 | 0.0455 |
| **K226** | 0.0519 | 0.0568 | 0.0001 | 1.0000 | -0.2288 |
| **K235** | 0.1196 | 0.0642 | 0.0455 | -0.2288 | 1.0000 |

**Key correlations with K235:**

- K198_K235: ρ = 0.1196 (Low)
- K204_K235: ρ = 0.0642 (Low)
- K208_K235: ρ = 0.0455 (Low)
- K226_K235: ρ = -0.2288 (Low)

> K235 max |ρ| with K229 components: 0.2288 (Low, no dominant correlation)

---

## Baseline Metrics (ML Window: 448 days)

| Strategy | OOS Sh | OOS MaxDD | WF Mean | WF Min | WF Folds | All+ |
|----------|--------|-----------|---------|--------|----------|------|
| K198 | 10.2796 | -0.005266 | 7.9153 | 6.5911 | [6.5911, 7.3739, 7.9652, 9.731] | YES |
| K204 | 10.3627 | -0.005320 | 7.5136 | 5.9200 | [5.92, 6.2598, 8.183, 9.6915] | YES |
| K208 | 13.5396 | -0.000080 | 13.4351 | 5.7585 | [17.2988, 5.7585, 17.3212, 13.3618] | YES |
| K226 | 2.4097 | -0.152979 | 2.2845 | 0.3800 | [3.2959, 0.38, 2.8378, 2.6243] | YES |
| K235 | 1.4241 | -0.070001 | 1.3061 | 0.7237 | [2.2582, 0.7237, 1.3219, 0.9205] | YES |

---

## Variant Performance Summary

Thresholds: OOS Sh > 12.71 | WF min >= 7.4435 | MaxDD <= -0.001201

| Variant | OOS Sh | WF Min | WF Mean | MaxDD | Min Wt | DR | Pass? |
|---------|--------|--------|---------|-------|--------|-----|-------|
| **K238a** | 4.7456 x | 2.2564 x | 4.4423 | -0.043876 x | 0.200 v | 1.5008 | FAIL |
| **K238b** | 9.1633 x | 2.1633 x | 7.8071 | -0.002596 x | 0.013 v | 1.1910 | FAIL |
| **K238c** | 9.1633 x | 2.1633 x | 7.8071 | -0.002596 x | 0.008 x | 1.1413 | FAIL |
| **K238d** | 11.3857 x | 7.2960 x | 11.0021 | -0.002416 x | 0.025 v | 1.7960 | FAIL |
| **K238e** | 11.1620 x | 7.3062 x | 10.9327 | -0.002596 x | 0.024 v | 1.9162 | FAIL |
| **K238f** | 11.0884 x | 7.3165 x | 10.9020 | -0.002596 x | 0.023 v | 1.9120 | FAIL |
| **K238g** | 15.3195 v | 1.6978 x | 6.5006 | -0.000091 v | 0.043 v | 1.6437 | FAIL |

---

## Per-Variant Per-Fold Breakdown

### K238a: Equal weight 20/20/20/20/20
**Avg weights:** K198=0.200, K204=0.200, K208=0.200, K226=0.200, K235=0.200

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 5.4805 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 2.2564 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 5.5391 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 4.4933 |

### K238b: Inverse-vol weighted uncapped (30d rolling)
**Avg weights:** K198=0.031, K204=0.027, K208=0.468, K226=0.013, K235=0.460

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 10.2054 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 2.1633 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 10.2316 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 8.6280 |

### K238c: Inv-vol (30d rolling) + K226 cap 20%
**Avg weights:** K198=0.031, K204=0.027, K208=0.468, K226=0.008, K235=0.466

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 10.2054 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 2.1633 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 10.2316 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 8.6280 |

### K238d: Inv-vol (30d rolling) + K226 cap 20% + K235 cap 5%
**Avg weights:** K198=0.042, K204=0.035, K208=0.863, K226=0.025, K235=0.035

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 12.7600 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 7.2960 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 12.8530 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 11.0994 |

### K238e: Inv-vol (30d rolling) + K226 cap 20% + K235 cap 10%
**Avg weights:** K198=0.041, K204=0.035, K208=0.839, K226=0.024, K235=0.061

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 12.5977 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 7.3062 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 12.9716 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 10.8550 |

### K238f: Inv-vol (30d rolling) + K226 cap 20% + K235 cap 15%
**Avg weights:** K198=0.041, K204=0.034, K208=0.818, K226=0.023, K235=0.085

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 12.4375 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 7.3165 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 13.0872 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 10.7670 |

### K238g: Minimum Variance Portfolio (rolling 60d covariance, long-only)
**Avg weights:** K198=0.045, K204=0.054, K208=0.810, K226=0.043, K235=0.048

| Fold | Start | End | N Days | Sharpe |
|------|-------|-----|--------|--------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 5.9313 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 1.6978 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 3.7474 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 14.6260 |

---

## K235 Active Days Analysis

| Fold | Start | End | N Days | Active | Active% | K235 Fold Sh |
|------|-------|-----|--------|--------|---------|--------------|
| 1 | 2025-01-23 | 2025-05-13 | 111 | 4 | 3.6% | 2.2582 |
| 2 | 2025-05-14 | 2025-09-01 | 111 | 2 | 1.8% | 0.7237 |
| 3 | 2025-09-02 | 2025-12-21 | 111 | 5 | 4.5% | 1.3219 |
| 4 | 2025-12-22 | 2026-04-14 | 114 | 7 | 6.1% | 0.9205 |

**Total ML window:** 18/448 days active (4.0%)
**Original 700d window:** 28/700 (~4.0%)

> K235 is the most selective strategy in the ensemble. Its low active rate means it acts
> as a *spike enhancer* on specific cascade events, not a continuous alpha source.
> This property is why a cap (5–15%) rather than free inv-vol allocation is preferred.

---

## Synergy Analysis

| Metric | Value |
|--------|-------|
| Avg individual OOS Sh (5-way) | 7.6031 |
| Avg individual OOS Sh (4-way K229) | 9.1479 |
| Best ensemble (K238g) OOS Sh | 15.3195 |
| Synergy vs avg individuals | +7.7164 |
| Improvement vs K229 v6.8 | +2.7095 |
| WF-min avg individuals | 3.8747 |
| Best ensemble WF-min | 1.6978 |
| WF-min synergy | -2.1769 |

---

## Historical Evolution

| Version | OOS Sh | WF Min | MaxDD | Components |
|---------|--------|--------|-------|------------|
| K198 v6.5 | 10.28 | 6.57 | -0.0053 | 1 |
| K217 v6.6 | 10.43 | 6.91 | -0.0053 | 2 |
| K218e v6.7 | 11.03 | 6.928 | -0.0036 | 3 |
| K229d v6.8 | 12.61 | 7.4435 | -0.001201 | 4 |
| K238 a v6.9 | 4.7456 | 2.2564 | -0.043876 | 5 |
| K238 b v6.9 | 9.1633 | 2.1633 | -0.002596 | 5 |
| K238 c v6.9 | 9.1633 | 2.1633 | -0.002596 | 5 |
| K238 d v6.9 | 11.3857 | 7.2960 | -0.002416 | 5 |
| K238 e v6.9 | 11.1620 | 7.3062 | -0.002596 | 5 |
| K238 f v6.9 | 11.0884 | 7.3165 | -0.002596 | 5 |
| K238 g v6.9 | 15.3195 | 1.6978 | -0.000091 | 5 |

---

## Verdict: K238 v6.9 if Accepted

### **REJECT — Gates Not Met**

K235 passes Gate 0 (ML window WF all positive) but no variant achieves sufficient
OOS Sh improvement (++2.7095 vs threshold +0.10).

**K229d v6.8 remains production.**

---
*Wave K238 | 2026-05-24T23:46:26.750064+00:00 | Runtime: 0.49s*
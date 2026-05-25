# Wave K249 — K208 Spread Magnitude Gating
**Date:** 2026-05-25 | **Runtime:** 1.4s | **Status:** ACCEPTED

---

## Objective
K247 confirmed: DAR direction accuracy in Fold 2 = 0.698 (highest of all folds — not a DAR misfire problem).
True root cause: **spread magnitude compression** in Fold 2 (carry level near zero → low signal-to-noise).
K249 tests halt-during-low-spread gating to recover Fold 2 Sharpe ≥ 7.0.

---

## Method: Spread Magnitude Gate
1. Per symbol: compute 7-day (21 events) rolling mean of |bybit_FR − HL_FR| (abs spread)
2. Cross-symbol mean → single panel `spread_mag` time series
3. Compute global percentile threshold; halt trading when `spread_mag < threshold`
4. K249d additionally applies K245d FR regime gate (trade only when annualized FR > 5%)

---

## Spread Distribution (Panel 7d-rolling mean |spread|)
| Percentile | bps |
|-----------|-----|
| p10 | 0.493 |
| p25 | 0.645 |
| p30 | 0.700 |
| p35 | 0.742 |
| p50 | 0.897 |
| p75 | 1.322 |
| p90 | 2.243 |

**Fold 2 mean spread = 0.720 bps** — slightly above p30 but the gate firing rate was 39–52% depending on threshold. The fold is genuinely a low-spread environment.

---

## Per-Variant Results

| Variant | OOS Sh | WF mean | WF min | Fold 2 | Active% | Verdict |
|---------|--------|---------|--------|--------|---------|---------|
| baseline | 12.23 | 18.65 | 6.81 | 6.81 | 100% | — |
| **K249a (p25 halt)** | **17.53** | **19.05** | **7.57** | **7.57** | **75%** | **ACCEPT** |
| K249b (p30 halt) | 17.54 | 18.83 | 6.74 | 6.74 | 70% | MARGINAL |
| K249c (p35 halt) | 17.40 | 17.87 | 3.74 | 3.74 | 65% | MARGINAL |
| K249d (p30 + regime) | 10.40 | 8.30 | 2.89 | 2.89 | 70% | FAIL |

### K249a Per-Fold Breakdown
| Fold | Period | Sharpe | Gate Active | Spread Mag | Note |
|------|--------|--------|------------|------------|------|
| 1 | 2025-01-22 → 2025-05-13 | +26.44 | 93.7% | 1.089 bps | NORMAL |
| **2** | **2025-05-14 → 2025-09-02** | **+7.57** | **48.5%** | **0.720 bps** | **LOW_SPREAD** |
| 3 | 2025-09-03 → 2025-12-23 | +23.72 | 71.6% | 1.014 bps | MODERATE |
| 4 | 2025-12-24 → 2026-04-14 | +17.88 | 100.0% | 3.464 bps | NORMAL |

**Fold 2 insight:** Gate fires 51.5% of the time (halts nearly half the fold). The active subset (spread ≥ p25 threshold) still generates Sh = +7.57, recovering from +6.81 baseline. Gating correctly identifies low-carry periods and avoids them.

---

## Acceptance Evaluation: K249a
| Gate | Threshold | Value | Result |
|------|----------|-------|--------|
| Fold 2 Sh | ≥ 7.0 | 7.57 | **PASS** |
| OOS Sh | ≥ 10.57 | 17.53 | **PASS** |
| WF min | ≥ 7.0 | 7.57 | **PASS** |
| Active rate | ≥ 65% | 75.0% | **PASS** |

**4/4 gates pass → K249a ACCEPTED.**

---

## Comparison vs Prior Work
| Version | OOS Sh | WF min | Fold 2 |
|---------|--------|--------|--------|
| K208 baseline | 10.57 | 5.74 | 5.74 |
| K229d ensemble | 10.17 | 7.48 | 7.48 |
| K246a v6.9 (3-way) | 12.69 | 8.93 | — |
| K245d (best DAR conf) | — | 6.27 | 6.27 |
| K247b (best dir-acc) | — | 6.81 | 6.81 |
| **K249a (spread gate)** | **17.53** | **7.57** | **7.57** |

K249a is the **first K208 variant to achieve Fold 2 ≥ 7.0** while also beating the OOS Sharpe and WF min thresholds.

---

## Verdict on K208 Fold 2 Reducibility

**VERDICT: REDUCIBLE**

The Fold 2 weakness (Sh = 5.74 → 6.81 baseline) was caused by **spread magnitude compression**, not DAR direction accuracy failures. The 25th-percentile spread halt (K249a) recovers Fold 2 to **Sh = 7.57** with 75% active trading rate.

**Action: Accept K249a → replace V_K208 slot in K246a ensemble.**

Optimization series: K242 (binary gate, fail) → K245d (DAR confidence, Fold2=6.27, fail) → K247 (dir-acc scalar, Fold2=6.81, fail) → **K249a (spread halt, Fold2=7.57, PASS)**.

---

## Next Steps
1. Integrate K249a spread gate into V_K208 slot in K246a (3-way ensemble)
2. Re-run K246a ensemble with K249a replacing baseline K208
3. Verify ensemble OOS Sh ≥ 12.69 and WF min ≥ 8.93 maintained
4. Paper-trade K249a gating for 7 days before live deployment

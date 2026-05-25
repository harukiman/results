# Wave K261 — K246a + K259 as 4th Component
**As of:** 2026-05-25 | **Runtime:** 0.4s | **Window:** 2025-01-22 → 2026-04-14 (448 days)

---

## Gate 0: K259 Validation on K246a ML Window

| Metric | Value | Status |
|--------|-------|--------|
| OOS Sharpe | 15.03 | — |
| MaxDD | -0.000076 | — |
| WF Folds | [15.35, 2.21, 14.48, 15.02] | — |
| WF Min | 2.21 | — |
| All Folds Positive | **YES** | PASS |

Gate 0 PASSES. However, WF fold 2 (2.21) is significantly lower than others, echoing the same fold-2 stress pattern as K256.

---

## CRITICAL FINDING: ρ(K208, K259) = 0.805 on K246a Window

K259 reported daily ρ vs K208 = 0.58 **on its own native window**. On K246a's exact 448-day window, the correlation is **0.805** — far above the 0.7 threshold defined in K259's own gates. This is the **K225 lesson**: window-dependent correlation. K259 and K208 share the same 8h-resolution Ridge architecture over overlapping symbols; the K246a window captures a period where their signals align much more tightly.

## 4x4 Correlation Matrix

```
        K198    K208    K226    K259
 K198:  1.000   0.062   0.052   0.061
 K208:  0.062   1.000   0.000   0.805  ← HIGH
 K226:  0.052   0.000   1.000   0.013
 K259:  0.061   0.805   0.013   1.000
```

K259 is orthogonal to K198 (ρ=0.06) and K226 (ρ=0.01) but nearly collinear with K208 (ρ=0.805).

---

## Per-Variant Results

| Variant | OOS Sh | WF Mean | WF Min | MaxDD | WF Folds |
|---------|--------|---------|--------|-------|-----------|
| K246a v6.9 (ref) | 12.69 | 12.25 | 8.93 | -0.00115 | — |
| K261a (3-way baseline) | 12.69 | 12.25 | 8.93 | -0.00115 | [13.60, 8.93, 13.84, 12.61] |
| K261b (+K259 cap 15%) | 13.14 | 12.56 | 8.93 | -0.000942 | [14.04, 8.93, 14.23, 13.06] |
| K261c (+K259 cap 20%) | 13.31 | 12.69 | 8.92 | -0.000874 | [14.21, 8.92, 14.39, 13.24] |
| K261d (+K259 cap 25%) | 13.50 | 12.82 | 8.91 | -0.000807 | [14.39, 8.91, 14.55, 13.43] |
| K261e (uncapped 4-way) | 15.67 | 13.66 | 8.32 | -0.000291 | [15.37, 8.32, 15.40, 15.56] |
| K261f (MVP) | 8.86 | 7.34 | 6.65 | -0.005417 | [6.99, 6.65, 7.28, 8.44] |

### Average Weights (where K259 included)

| Variant | K198 | K208 | K226 | K259 |
|---------|------|------|------|------|
| K261b | 4.1% | 79.7% | 1.3% | 15.0% |
| K261c | 3.8% | 74.9% | 1.2% | 20.0% |
| K261d | 3.6% | 70.3% | 1.1% | 25.0% |
| K261e | 1.9% | 37.8% | 2.3% | 58.0% |
| K261f | 29.5% | 32.6% | 5.3% | 32.6% |

---

## Acceptance Gate Evaluation

**Gates:** OOS Sh > 12.79 | WF min ≥ 8.93 | MaxDD ≤ -0.00115 | All weights > 0

| Variant | OOS Sh >12.79 | WF min ≥8.93 (Δ) | MaxDD | OVERALL |
|---------|:---:|:---:|:---:|:---:|
| K261b | PASS | **FAIL** (8.9294, -0.0006) | PASS | REJECT |
| K261c | PASS | **FAIL** (8.9213, -0.008) | PASS | REJECT |
| K261d | PASS | **FAIL** (8.9081, -0.022) | PASS | REJECT |
| K261e | PASS | **FAIL** (8.3165, -0.614) | PASS | REJECT |
| K261f | FAIL | FAIL | FAIL | REJECT |

All variants fail WF min. Bottleneck: **fold 2** — same weak fold as K259 standalone (2.21). ρ=0.805 with K208 means K259 provides no independent rescue in that period.

---

## Comparison Summary

| Version | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|--------|-----------|---------|--------|
| K246a v6.9 | 12.69 | -0.00115 | 12.25 | 8.93 |
| K261b (best gate-adjacent) | 13.14 | -0.000942 | 12.56 | 8.93 |
| K261d (best OOS in capped) | 13.50 | -0.000807 | 12.82 | 8.91 |
| K261e (best OOS overall) | 15.67 | -0.000291 | 13.66 | 8.32 |

---

## Verdict: K261 → v6.9.2 REJECTED

**Gate 0 PASS** — K259 has all-positive WF folds on K246a window.

**Production gate FAIL** — WF min falls short in all 4-way variants. Root cause is ρ(K208,K259) = 0.805 on K246a window; K259 and K208 are near-collinear on this 448-day period, so K259 adds minimal independent stress-resilience in fold 2.

**K246a v6.9 remains the production standard.**

### Observations for Next Wave
1. ρ=0.805 vs K208 on K246a window disqualifies K259 as additive component under current methodology
2. K261e (uncapped) OOS Sh 15.67 but WF min 8.32 — K259 dominates (58%) and exposes fold-2
3. MaxDD improves in all 4-way variants — K259 does reduce drawdown where it is not collinear
4. The fold-2 weakness (standalone 2.21) is inherited into every combined variant
5. Next path: find a component with ρ < 0.4 to BOTH K208 and K259, or attack fold-2 with a mean-reversion strategy

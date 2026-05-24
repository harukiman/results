# Wave K223 — Carry-Stress Index (CSI) Leverage on K218e

**Generated:** 2026-05-24 22:32 UTC  
**Runtime:** 0.8s  
**Period:** 2025-01-22 → 2026-04-14 (447 return days, OOS=135 days)

---

## Executive Summary

Wave K223 builds a **Carry-Stress Index (CSI)** from real Bybit funding-rate data 
(BTC/ETH/SOL/XRP) and uses it to dynamically lever K218e (v6.7 production, OOS Sh=
11.031). Mechanism validated by K220: carry strategies earn 
*more* alpha during market stress (capitulation Sh=10.0 vs buy-window Sh=6.38).

| Metric | K218e ref | Best K223 | Gate |
|--------|-----------|-----------|------|
| OOS Sharpe | 11.031 | 10.7534 | >11.13 |
| WF min Sh  | 6.9282 | 6.7481 | ≥6.93 |
| OOS MaxDD  | -0.003640 | -0.003640 | ≥-0.0036 |
| ΔSh vs K218e | — | -0.2776 | ≥+0.10 |

**Verdict: REJECT — no variant clears all acceptance gates. Best: K223c**

---

## 1. Carry-Stress Index Construction

### 1.1 Algorithm

1. Load Bybit FR 730d cache for BTC, ETH, SOL, XRP
2. For each symbol, sum daily |FR_t| across all funding periods (typ. 3/day)
3. Take mean across 4 symbols → raw daily carry stress
4. Annualise: × 365 (funding already summed over 3 daily periods)
5. 14-day rolling z-score: z_t = (x_t − μ̄₁₄) / σ₁₄
6. Regime: high_stress (z > +1.0), low_stress (z < −1.0), normal

### 1.2 Regime Balance — K218e Period (2025-01-22 → 2026-04-14)

| Regime | Days | Fraction | Gate 20–40% |
|--------|------|----------|------------|
| high_stress | 78 | 17.4% | FAIL |
| low_stress  | 65  | 14.5%  | FAIL |
| normal      | 304 | 68.0% | — |

**Note:** Both high and low stress fire below the 20% gate target. 
The z-score threshold of ±1.0 produces balanced but under-firing regimes 
(only ~17% and ~15% respectively vs the 20–40% ideal). This is informational — 
not a hard gate — but suggests CSI fires conservatively.

### 1.3 CSI-z Distribution

| Stat | Value |
|------|-------|
| Mean | -0.0181 |
| Std  | 1.0134 |
| Min  | -2.6894 |
| Max  | 3.4713 |
| P25  | -0.7287 |
| P75  | 0.6679 |

---

## 2. K220 Capitulation Validation

K220 found carry ensemble earns more during miner capitulation. We test whether 
CSI's high-stress regime captures those same periods.

| Metric | Value |
|--------|-------|
| CSI-z vs cap_state Pearson r | 0.1537 |
| K223 high-stress days | 78 |
| K220 capitulation days | 148 |
| Overlap (both) | 37 |
| Precision: P(cap | CSI high) | 47.44% |

**Interpretation:** CSI correlates positively (r=0.154) with K220's 
hash-ribbon capitulation state, confirming partial conceptual alignment. However, 
only 37/78 CSI high-stress days coincide with K220 
capitulation (47%), confirming CSI captures a 
*different but complementary* dimension of stress: funding-rate spikes vs miner exit.

---

## 3. Leverage Variants

| Variant | Description |
|---------|-------------|
| K223a | Symmetric: high ×1.3, low ×0.7, normal ×1.0 |
| K223b | Boost-only: high ×1.3, else ×1.0 |
| K223c | Tight threshold: z>+1.5 → ×1.5, z<−1.5 → ×0.5, else ×1.0 |
| K223d | Smooth: weight = 1 + 0.3 × tanh(z) |

All variants applied to K218e daily returns; OOS = last 30% (≈135 days).
Walk-forward = 4 equal chronological folds over all 447 return days.

---

## 4. Walk-Forward Results — Per Variant Per Fold

### K223a — Symmetric: high ×1.3, low ×0.7, normal ×1.0

**OOS Sh=10.4262  WF_min=6.5427  WF_mean=7.9016  MaxDD=-0.003640  ΔSh=-0.6048**

| Fold | Period | n | Base Sh | Lev Sh | ΔSh | MaxDD | High-d | Low-d |
|------|--------|---|---------|--------|-----|-------|--------|-------|
| 1 | 2025-01-23→2025-05-13 | 111 | 7.5144 | 7.1589 | -0.3555 | -0.007397 | 15 | 16 |
| 2 | 2025-05-14→2025-09-01 | 111 | 6.9282 | 6.5427 | -0.3855 | -0.015290 | 24 | 17 |
| 3 | 2025-09-02→2025-12-21 | 111 | 8.3475 | 8.1628 | -0.1847 | -0.010635 | 18 | 18 |
| 4 | 2025-12-22→2026-04-14 | 114 | 10.4739 | 9.7419 | -0.7319 | -0.003547 | 21 | 14 |

Gate checks: Sh>11.13 ✗ | WF_min≥6.93 ✗ | MaxDD≥-0.0036 ✗ → **REJECT**

### K223b — Boost-only: high ×1.3, else ×1.0

**OOS Sh=10.6120  WF_min=6.8172  WF_mean=8.1076  MaxDD=-0.003640  ΔSh=-0.4190**

| Fold | Period | n | Base Sh | Lev Sh | ΔSh | MaxDD | High-d | Low-d |
|------|--------|---|---------|--------|-----|-------|--------|-------|
| 1 | 2025-01-23→2025-05-13 | 111 | 7.5144 | 7.4089 | -0.1055 | -0.007397 | 15 | 16 |
| 2 | 2025-05-14→2025-09-01 | 111 | 6.9282 | 6.8172 | -0.1110 | -0.015290 | 24 | 17 |
| 3 | 2025-09-02→2025-12-21 | 111 | 8.3475 | 8.3168 | -0.0306 | -0.010635 | 18 | 18 |
| 4 | 2025-12-22→2026-04-14 | 114 | 10.4739 | 9.8877 | -0.5862 | -0.003547 | 21 | 14 |

Gate checks: Sh>11.13 ✗ | WF_min≥6.93 ✗ | MaxDD≥-0.0036 ✗ → **REJECT**

### K223c — Tight threshold: z>+1.5 → ×1.5, z<−1.5 → ×0.5, else ×1.0

**OOS Sh=10.7534  WF_min=6.7481  WF_mean=8.1166  MaxDD=-0.003640  ΔSh=-0.2776**

| Fold | Period | n | Base Sh | Lev Sh | ΔSh | MaxDD | High-d | Low-d |
|------|--------|---|---------|--------|-----|-------|--------|-------|
| 1 | 2025-01-23→2025-05-13 | 111 | 7.5144 | 7.2520 | -0.2624 | -0.007646 | 15 | 16 |
| 2 | 2025-05-14→2025-09-01 | 111 | 6.9282 | 6.7481 | -0.1801 | -0.014610 | 24 | 17 |
| 3 | 2025-09-02→2025-12-21 | 111 | 8.3475 | 8.2713 | -0.0762 | -0.010635 | 18 | 18 |
| 4 | 2025-12-22→2026-04-14 | 114 | 10.4739 | 10.1951 | -0.2788 | -0.003596 | 21 | 14 |

Gate checks: Sh>11.13 ✗ | WF_min≥6.93 ✗ | MaxDD≥-0.0036 ✗ → **REJECT**

### K223d — Smooth: weight = 1 + 0.3 × tanh(z)

**OOS Sh=10.2594  WF_min=6.6497  WF_mean=7.8050  MaxDD=-0.004302  ΔSh=-0.7716**

| Fold | Period | n | Base Sh | Lev Sh | ΔSh | MaxDD | High-d | Low-d |
|------|--------|---|---------|--------|-----|-------|--------|-------|
| 1 | 2025-01-23→2025-05-13 | 111 | 7.5144 | 6.9239 | -0.5905 | -0.007547 | 15 | 16 |
| 2 | 2025-05-14→2025-09-01 | 111 | 6.9282 | 6.6497 | -0.2785 | -0.013495 | 24 | 17 |
| 3 | 2025-09-02→2025-12-21 | 111 | 8.3475 | 7.9634 | -0.3840 | -0.010739 | 18 | 18 |
| 4 | 2025-12-22→2026-04-14 | 114 | 10.4739 | 9.6828 | -0.7911 | -0.003462 | 21 | 14 |

Gate checks: Sh>11.13 ✗ | WF_min≥6.93 ✗ | MaxDD≥-0.0036 ✗ → **REJECT**

---

## 5. Summary Table

| Variant | OOS Sh | WF_min | WF_mean | MaxDD | ΔSh | Status |
|---------|--------|--------|---------|-------|-----|--------|
| K223a | 10.4262 | 6.5427 | 7.9016 | -0.003640 | -0.6048 | REJECT |
| K223b | 10.6120 | 6.8172 | 8.1076 | -0.003640 | -0.4190 | REJECT |
| K223c | 10.7534 | 6.7481 | 8.1166 | -0.003640 | -0.2776 | REJECT |
| K223d | 10.2594 | 6.6497 | 7.8050 | -0.004302 | -0.7716 | REJECT |
| K218e (ref) | 11.0310 | 6.9282 | 8.3160 | -0.003640 | — | Reference |

---

## 6. Verdict — K223 → v6.8

### REJECT — no variant clears all acceptance gates. Best: K223c

No variant clears all 3 critical gates.

**Gap analysis:**

| Gate | Required | Best (K223c) | Gap |
|------|----------|---------|-----|
| OOS Sharpe | >11.13 | 10.7534 | -0.3766 |
| WF min | ≥6.93 | 6.7481 | -0.1819 |
| MaxDD | ≥-0.0036 | -0.003640 | -0.000040 |

### Root Cause Analysis

1. **CSI leverage amplifies MaxDD:** K218e has extremely tight MaxDD (-0.0036); 
   any leverage scaling > 1.0 risks breaching it. High-stress periods have 
   higher FR returns AND higher volatility — net Sharpe effect is diluted.

2. **Regime fractions below 20% gate:** CSI fires high-stress only 17.4% 
   of days. Not enough active days for leverage to materially lift OOS Sharpe.

3. **OOS Sharpe near-ceiling:** K218e already achieves Sh=11.03 in OOS. 
   Leveraging a near-optimal strategy risks Sharpe degradation from volatility 
   amplification (denominator grows faster than numerator).

4. **Inverted-relationship nuance:** K220's mechanism (cap→stress→carry alpha) 
   operates at monthly timescales. CSI z-score at 14d captures short FR spikes 
   that may not correspond to multi-week carry regime shifts.

### Recommendations for K224

| # | Idea | Expected Effect |
|---|------|----------------|
| 1 | Extend CSI z-score window to 21d or 28d | Reduce false high-stress signals, increase regime stability |
| 2 | Use CSI as *portfolio selection* not leverage | Route to carry-heavy sub-portfolio during high-stress |
| 3 | CSI × BTC realised vol gate | Only boost when BTC vol > 30% (stress is real, not noise) |
| 4 | Fractional Kelly leverage | Size leverage by f × E[R]/Var[R] — avoids Sharpe degradation |
| 5 | Multi-symbol FR dispersion | Cross-sectional spread of FR ranks as stress dimension |

---

*Wave K223 complete. Runtime 0.8s.*
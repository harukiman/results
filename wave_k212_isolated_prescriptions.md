# Wave K212 — Isolated Prescription Analysis

**Generated:** 2026-05-25 06:48 JST  
**Runtime:** 3.9s

## Executive Summary

DD penalty has NEUTRAL effect on OOS Sh (+0.03). Window size is the primary lever. | Window shrink 180->135 HURTS OOS Sh by -0.37 (K212A vs K205). 180d window is better for OOS stability. | K212A WF min lift vs K209: +0.03. Check fold breakdown to determine if 135d window is stable with penalty. | NO K212 variant clears all acceptance criteria. Best OOS Sh=9.25 from K212B. K198 v6.5 remains production. K213 next: try 120d window or threshold-based penalty (only dd30 < -0.15).

## Objective

Decompose the K205 prescriptions into independent tests to identify which lever 
(window length vs DD penalty) drives performance and stability.

| Variant | Training window | DD Penalty | Hypothesis |
|---------|----------------|------------|------------|
| K212A | 135d | 2.0 | Window alone rescues K209 collapse |
| K212B | 180d | 0.0 | Removing penalty alone rescues K205 OOS Sh |
| K212C | 150d | 2.0 | Conservative middle ground |

## Six-Way Comparison Table

| Version | OOS Sh | OOS MaxDD | WF mean | WF min | Folds | Status |
|---------|--------|-----------|---------|--------|-------|--------|
| K198 (prod) | 10.2800 | -0.0053 | 7.9100 | 6.5700 | 6.57/7.91/8.90/8.26 | PRODUCTION |
| K204 | 10.3600 | -0.0053 | 7.5451 | 6.0200 | 6.02/6.26/8.10/9.79 | REJECTED |
| K205 | 9.2200 | -0.0039 | 8.5200 | 6.4600 | 7.88/6.46/9.78/9.95 | REJECTED |
| K209 | 8.8600 | -0.0270 | 6.5900 | 3.4600 | 8.24/5.51/3.46/9.16 | REJECTED |
| K212A (135d+pen=2) | 8.8512 | -0.0271 | 6.5966 | 3.4934 | 8.27/5.47/3.49/9.16 | REJECT |
| K212B (180d+pen=0) | 9.2457 | -0.0039 | 8.3575 | 6.4664 | 7.17/6.47/9.80/9.99 | REJECT |
| K212C (150d+pen=2) | 8.0613 | -0.0190 | 8.3298 | 7.2550 | 8.38/7.94/7.25/9.74 | REJECT |

## Per-Fold Breakdown

### K212A (135d+pen=2)

| Fold | Sharpe | vs K198 ref | vs K205 ref | vs K209 ref | vs K198 WF min |
|------|--------|-------------|-------------|-------------|----------------|
| 1 | 8.2657 | +1.6935 | +0.3860 | +0.0251 | +1.6957 |
| 2 | 5.4659 | -2.4441 | -0.9906 | -0.0451 | -1.1041 <-- WEAK |
| 3 | 3.4934 | -5.4066 | -6.2894 | +0.0320 | -3.0766 <-- WEAK |
| 4 | 9.1612 | +0.9012 | -0.7907 | +0.0006 | +2.5912 |

### K212B (180d+pen=0)

| Fold | Sharpe | vs K198 ref | vs K205 ref | vs K209 ref | vs K198 WF min |
|------|--------|-------------|-------------|-------------|----------------|
| 1 | 7.1720 | +0.5998 | -0.7077 | -1.0686 | +0.6020 |
| 2 | 6.4664 | -1.4436 | +0.0099 | +0.9554 | -0.1036 <-- WEAK |
| 3 | 9.8047 | +0.9047 | +0.0219 | +6.3433 | +3.2347 |
| 4 | 9.9869 | +1.7269 | +0.0350 | +0.8263 | +3.4169 |

### K212C (150d+pen=2)

| Fold | Sharpe | vs K198 ref | vs K205 ref | vs K209 ref | vs K198 WF min |
|------|--------|-------------|-------------|-------------|----------------|
| 1 | 8.3817 | +1.8095 | +0.5020 | +0.1411 | +1.8117 |
| 2 | 7.9439 | +0.0339 | +1.4874 | +2.4329 | +1.3739 |
| 3 | 7.2550 | -1.6450 | -2.5278 | +3.7936 | +0.6850 |
| 4 | 9.7384 | +1.4784 | -0.2135 | +0.5778 | +3.1684 |

## Win-Loss Attribution

### 1. Penalty Isolation: K212B vs K205 (same 180d window, differ on penalty)

- OOS Sh delta: **+0.0257**
- MaxDD delta: +0.0000
- WF min delta: +0.0064
- Interpretation: POSITIVE delta => penalty was DRAGGING OOS Sh in K205. NEGATIVE delta => removing penalty hurts.

### 2. Window 135d Isolation: K212A vs K205 (same penalty=2, differ on window)

- OOS Sh delta: **-0.3688**
- MaxDD delta: -0.0232
- WF min delta: -2.9666
- Interpretation: POSITIVE delta => 135d window recovers OOS vs 180d (K205 over-smoothed). NEGATIVE delta => shorter window hurts (more noise).

### 3. Window 150d Isolation: K212C vs K205 (same penalty=2, differ on window)

- OOS Sh delta: **-1.1587**
- MaxDD delta: -0.0151
- WF min delta: +0.7950
- Interpretation: Conservative window step-down. Positive => 150d better than 180d (K205). Check if WF min improves vs K205.

### 4. Penalty at 135d: K212A vs K209 (same 135d window, differ on penalty)

- OOS Sh delta: **-0.0088**
- MaxDD delta: -0.0001
- WF min delta (Fold3 rescue?): **+0.0334**
- Interpretation: CRITICAL: K209 had Fold3 collapse (Sh 3.46). If K212A WF min >> K209's 3.46 => DD penalty was the key stabilizer. If K212A Fold3 still collapses => 135d window is the root cause, not penalty.

## Acceptance Criteria Summary

Thresholds: OOS Sh >= 10.28 | MaxDD >= -0.0053 | WF min >= 6.57

| Variant | OOS Sh | MaxDD | WF min | ALL PASS |
|---------|--------|-------|--------|----------|
| K212A | 8.8512 (FAIL) | -0.0271 (FAIL) | 3.4934 (FAIL) | FAIL |
| K212B | 9.2457 (FAIL) | -0.0039 (PASS) | 6.4664 (FAIL) | FAIL |
| K212C | 8.0613 (FAIL) | -0.0190 (FAIL) | 7.2550 (PASS) | FAIL |

## Verdict — Which K20x Branch is the Winner? / K213 Next

**DD penalty has NEUTRAL effect on OOS Sh (+0.03). Window size is the primary lever. | Window shrink 180->135 HURTS OOS Sh by -0.37 (K212A vs K205). 180d window is better for OOS stability. | K212A WF min lift vs K209: +0.03. Check fold breakdown to determine if 135d window is stable with penalty. | NO K212 variant clears all acceptance criteria. Best OOS Sh=9.25 from K212B. K198 v6.5 remains production. K213 next: try 120d window or threshold-based penalty (only dd30 < -0.15).**

### K213 Next Steps

- No K212 variant passes all criteria — K198 v6.5 remains production.
- K213A: try 120d+pen=2 (closer to K198's 90d baseline, milder from K198)
- K213B: threshold-based penalty — only penalize when dd30 < -0.15 (avoid over-firing)
- K213C: 180d window + partial penalty coef=1.0 (softer DD multiplier than K205's 2.0)
- Use K212 prescription analysis to guide: if penalty_isolation > 0, go K213A (120d no-pen).

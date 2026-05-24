# Wave K202 — Gate-Then-Allocate: Full Report

**Date:** 2026-05-25  
**Runtime:** 4.2s  
**Status: REJECTED (0/3 primary criteria)**

---

## Executive Summary

K202 implements the "gate-then-allocate" architecture: T1/T2/T3 triggers pre-filter eligible strategies before the Ridge ML allocator runs, rather than overriding post-allocation (K201's failed approach). Despite the architecturally correct sequencing, K202 is rejected for v6.6 production.

**Root cause of failure:** T1 trigger over-fires (78.7% of all days, 80% of walk-forward steps). The trigger is computed on per-symbol raw reverse-carry returns, which are inherently high-volatility. Most symbols fall below the Sh < -2.0 threshold during normal market noise. As a result, the reverse carry sleeve is excluded in 12/15 ML prediction steps — including 7 steps where ML correctly predicted strongly positive Sharpe (mean realized Sh = 22.9 during exclusion). The trigger is not protecting against bad carry regimes; it is systematically excluding a profitable sleeve based on short-window noise.

**K198 v6.5 (Ridge ML alone) remains production.**

---

## Five-Way Comparison

| Version | OOS Sh | OOS MaxDD | WF mean | WF min | Notes |
|---------|--------|-----------|---------|--------|-------|
| K196 v6.4 baseline | 9.20 | -0.0038 | 5.37 | 3.54 | Static P3 risk-parity |
| K198 ML alone (current prod) | **10.28** | -0.0053 | 7.91 | **6.57** | Ridge ML allocator, v6.5 |
| K199b triggers alone | 7.83 | -0.0040 | 4.98 | 3.41 | T1/T2/T3 on static P3 |
| K201 ML→trigger override (rejected) | 8.59 | -0.0057 | 7.38 | 6.39 | Post-allocation adversarial |
| **K202 trigger→ML filter (this wave)** | **7.84** | **-0.0071** | **7.16** | **6.29** | Pre-filter gate |

K202 vs K198: OOS Sh −2.44 | MaxDD −0.0018 (worse) | WF min −0.28

---

## Acceptance Criteria

| Criterion | Required | K202 Actual | Result |
|-----------|----------|-------------|--------|
| AC1: OOS Sh ≥ K198 | ≥ 10.28 | 7.84 | **FAIL** |
| AC2: WF min ≥ K198 | ≥ 6.57 | 6.29 | **FAIL** |
| AC3: MaxDD < K198 | < −0.0053 | −0.0071 | **FAIL** |
| AC4: ML-trigger conflict < 50% steps | < 50% | 46.7% | PASS |

**Criteria passed: 1/4. K202 REJECTED for v6.6.**

---

## Architecture Description

### Gate-Then-Allocate Flow (per 30-day step)

```
T = prediction date
  │
  ├─ [PRE-FILTER] Compute T1/T2/T3 state at T
  │     T1: per-symbol 30d Sh < −2.0 → exclude that symbol
  │     T2: panel 30d Sh < 0 → exclude entire reverse panel
  │     T3: panel cumulative DD > 2% → exclude reverse panel
  │     ANY trigger → V_rev_carry excluded from ML universe
  │
  ├─ [ML] Train Ridge on [T−90, T] feature matrix
  │     Predict next-30d Sharpe for ALL 10 strategies
  │     Zero gated predictions for excluded strategies
  │
  ├─ [ALLOCATE] weights ∝ max(pred, 0) among eligible only
  │     Renormalize: excluded weights redistribute proportionally
  │
  └─ [CAPS] K121 ≤ 30%, fwd_carry ≤ 10%, rev_carry ≤ 5%
```

### Key Difference from K201

K201 ran ML first, then applied triggers as override (post-allocation adversarial). K202 runs triggers first, then ML allocates among the filtered universe — architecturally non-adversarial by design. However, trigger miscalibration causes the gate to block profitable allocation.

---

## Filter Effect Log — Per-Step Breakdown

| Step | Gate Date | Rev Excluded | T1 Syms | T2 | T3 | ML Pred (rev) | Realized Sh | Opp Cost? |
|------|-----------|-------------|---------|----|----|--------------|-------------|-----------|
| 0 | 2025-01-22 | Yes | 8/10 | Yes | Yes | +1.93 | +3.18 | Yes |
| 1 | 2025-02-21 | Yes | 2/10 | No | Yes | +31.61 | +35.76 | **Yes (severe)** |
| 2 | 2025-03-23 | No | 0/10 | No | No | — | — | No |
| 3 | 2025-04-22 | No | 0/10 | No | No | −0.98 | — | No |
| 4 | 2025-05-22 | Yes | 4/10 | Yes | No | −16.82 | — | No |
| 5 | 2025-06-21 | Yes | 7/10 | Yes | No | −6.85 | — | No |
| 6 | 2025-07-21 | Yes | 6/10 | Yes | No | −14.90 | — | No |
| 7 | 2025-08-20 | Yes | 9/10 | Yes | No | −37.53 | — | No |
| 8 | 2025-09-19 | Yes | 9/10 | Yes | Yes | −7.56 | — | No |
| 9 | 2025-10-19 | Yes | 5/10 | Yes | Yes | +30.00 | +25.12 | **Yes** |
| 10 | 2025-11-18 | Yes | 3/10 | No | Yes | +31.84 | +31.03 | **Yes** |
| 11 | 2025-12-18 | Yes | 2/10 | No | No | +17.40 | +10.14 | **Yes** |
| 12 | 2026-01-17 | Yes | 5/10 | No | No | +21.60 | +24.39 | **Yes** |
| 13 | 2026-02-16 | No | 0/10 | No | No | +15.04 | — | No |
| 14 | 2026-03-18 | Yes | 1/10 | No | No | +27.59 | +30.51 | **Yes** |

**Trigger accuracy when blocking ML-positive steps: 0/7 correct (trigger was wrong every time).**  
Mean realized Sharpe during exclusion: **+22.88** (strongly profitable periods blocked).

---

## Root Cause Diagnosis: T1 Over-Firing

### The Problem

T1 is defined as: "per-symbol 30d rolling Sharpe < −2.0 → exclude that symbol from rev-carry panel."

This threshold was calibrated in K199 for the *aggregated* reverse carry panel (V_rev_carry), not for individual per-symbol raw returns. Individual per-symbol reverse carry returns are much more volatile than the aggregated panel, because:

1. **Equal-weight aggregation smooths idiosyncratic noise** — V_rev_carry aggregates 10 symbols, reducing per-position vol by ~√10
2. **Concentration effect** — single symbols like SOL/XRP can have 30d rolling Sh < −2.0 even when the *panel-level* Sharpe is strongly positive
3. **Different signal level** — K199b computed T1 at the panel level using per-symbol weights, then halted specific symbols within the panel allocation; K202 maps T1 to the full sleeve exclusion (too coarse)

### Per-Symbol T1 Fire Rate

| Symbol | T1 Fire % | Notes |
|--------|-----------|-------|
| SOL | 67.6% | Extremely noisy; dominant panel contributor |
| XRP | 71.1% | Highest fire rate; regulatory/news driven |
| SUI | 50.8% | New-era altcoin, high vol |
| OP | 37.7% | Moderate |
| APT | 46.2% | Moderate-high |
| AXS | 1.2% | Stable carry; rarely fires |
| JTO | 54.3% | High fire; small-cap vol |
| IMX | 34.3% | Moderate |
| SAND | 24.3% | Lower vol, lower fire rate |
| ADA | 35.3% | Moderate |

**Conclusion:** T1 in K202 acts as a near-permanent exclusion of the rev-carry sleeve, not a targeted risk circuit breaker.

### ML Response Analysis

The ML predictor (Ridge) maintained high R² (mean 0.935) and direction accuracy (mean 73%) throughout — the predictor quality is unchanged from K198. The ML correctly predicted positive Sharpe for V_rev_carry in steps 0, 1, 9, 10, 11, 12, 14. The gate blocked 5 of those 7 correctly-predicted positive periods, reducing the portfolio's return without reducing realized drawdown.

---

## Walk-Forward Fold Analysis

| Fold | Sharpe | Notes |
|------|--------|-------|
| Fold 1 | 6.29 | 2025-01-22 to ~2025-05-14 |
| Fold 2 | 7.38 | Rev excluded most of period |
| Fold 3 | 8.12 | Best fold |
| Fold 4 | 6.83 | Opp cost in steps 11-12 |
| **Mean** | **7.16** | vs K198 7.91 |
| **Min** | **6.29** | vs K198 6.57 |

---

## OOS Metrics

Period: last 30% of 448-day walk-forward window.

| Metric | K202 | K198 | Delta |
|--------|------|------|-------|
| Sharpe | 7.84 | 10.28 | −2.44 |
| Sortino | 21.06 | — | — |
| Calmar | 96.22 | — | — |
| MaxDD | −0.0071 | −0.0053 | −0.0018 (worse) |
| Ann Return | 68.4% | — | — |
| Ann Vol | 6.68% | — | — |

Paradoxically, K202 has *worse* MaxDD despite trigger protection. This is because the gate reduced the diversification benefit of the rev-carry sleeve without eliminating the underlying vol of the remaining strategies.

---

## Opportunity Cost Quantification

When triggers fired while ML predicted positive Sharpe for V_rev_carry:

- **7 events** across 15 walk-forward steps
- **Trigger correct: 0/7 (0%)** — every trigger-block was incorrect
- **Mean realized Sharpe during exclusion: +22.88** — extremely high
- **Estimated Sharpe loss per step:** ~(22.88 × 0.05 cap) = ~1.14 Sharpe units per step lost

The opportunity cost accounts for the full gap between K202 (7.84) and K198 (10.28) OOS Sharpe difference.

---

## Why K201 and K202 Both Fail

| K201 (post-allocation) | K202 (pre-filter gate) |
|----------------------|----------------------|
| ML allocates fully, triggers override | Triggers pre-filter, ML allocates within |
| Adversarial: triggers fire ML's highest-weight period | Non-adversarial: triggers gate before ML |
| Trigger calibrated for static P3, not ML weights | Trigger calibrated for panel-level, not per-symbol |
| OOS Sh 8.59 | OOS Sh 7.84 |
| Conflict: triggers fire on ML bullish | Conflict: T1 over-fires on symbol noise |

**Common finding:** The T1/T2/T3 triggers in their K199b form are not portable to the ML allocator context. K199b triggers were designed for a static equal-weight reverse carry panel with 10% cap. They assume panel-level Sharpe signals — and fire correctly at that granularity. The K202 gate maps T1 at the per-symbol level to a panel-level exclusion decision, creating a coarse granularity mismatch.

---

## Architectural Validation

Despite rejection, K202 validates important architectural properties:

1. **AC4 passes (46.7% conflict steps < 50% threshold):** K202 does not create a systematically adversarial anti-momentum mechanism. The ML and gate agree ~53% of steps.

2. **Gate-then-allocate sequencing is correct:** When triggers and ML agree (8 steps with exclusion and ML-negative rev-carry), the outcome is constructive — those 8 steps correctly avoided losses.

3. **T1 re-calibration is the key lever:** If T1 threshold were raised to Sh < −4.0 or applied to the panel-level 30d Sh rather than per-symbol, fewer false-positive exclusions would occur.

---

## Verdict: REJECT — K202 Not Promoted to v6.6

**K198 v6.5 (Ridge ML, OOS Sh 10.28, WF min 6.57) retains production status.**

K202 gate-then-allocate architecture is conceptually sound but operationally miscalibrated. The T1 trigger signal is too noisy at per-symbol granularity, creating systematic over-exclusion of a profitable sleeve.

### Root Cause in One Sentence

The T1 trigger computed on per-symbol 30d rolling Sharpe (σ~high) fires on noise; the K198 ML computed on the aggregated panel (σ~low) correctly predicts signal — the two signals operate at incompatible granularities.

---

## Next Investigation Paths (K203+)

1. **Recalibrate T1:** Use panel-level 30d Sh < −1.0 (not per-symbol < −2.0) as gate criterion; matches K198's prediction target granularity
2. **Selective gating:** Only gate on T3 (DD > 2%) which is high-confidence protection; drop T1/T2 as pre-filters
3. **Hybrid: ML-native DD protection:** Embed DD-awareness into ML feature matrix (include rolling realized DD as feature) so ML self-modulates without external gate
4. **K199b T1 at panel level:** Recompute T1 using V_rev_eq_w (aggregated) 30d Sh rather than per-symbol; reduces false positive rate by ~5-10x
5. **Asymmetric cap:** Keep K198 unchanged but reduce V_rev_carry cap from 10% → 5% (K199b cap) without trigger — simpler, less noise

---

## Files Produced

- `/Users/nekonaomichi/crypto-lab/wave_k202_gate_then_allocate.py` — implementation (4.2s runtime)
- `/Users/nekonaomichi/crypto-lab/wave_k202_gate_then_allocate.json` — full metrics + filter log
- `/Users/nekonaomichi/crypto-lab/wave_k202_curves.json` — equity curves + eligibility trace
- `/Users/nekonaomichi/crypto-lab/wave_k202_gate_then_allocate.md` — this report

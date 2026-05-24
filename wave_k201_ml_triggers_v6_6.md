# Wave K201 — ML Allocator + Safety Triggers (v6.6 Candidate)
**Date:** 2026-05-25  
**Runtime:** 3.4s  
**Files:** `wave_k201_ml_triggers_v6_6.py`, `wave_k201_ml_triggers_v6_6.json`, `wave_k201_curves.json`

---

## Executive Summary

K201 combines K198's Ridge ML allocator with K199b's T1/T2/T3 safety triggers. The hypothesis — that ML provides regime-adaptive weighting and triggers provide tail-event protection, composing into a superior v6.6 — does **not** hold. The two layers are in active conflict 41.3% of the time, producing negative synergy (-0.32). K201 is **REJECTED** for v6.6 promotion. K198 Ridge ML alone remains the best candidate. K202 should explore a trigger-aware ML architecture to fix the conflict mechanism.

---

## Four-Way Comparison

| Version | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|--------|-----------|---------|--------|
| K196 v6.4 baseline | 9.2005 | -0.0038 | 5.32 | 3.25 |
| K198 ML alone | 10.2796 | -0.0053 | 7.91 | 6.57 |
| K199b triggers alone | 7.8274 | -0.0040 | 4.98 | 3.41 |
| **K201 ML + triggers** | **8.5864** | **-0.0057** | **7.38** | **6.39** |

K201 lands between K198 and K199b on all metrics, but on the wrong side of K198 — it captures neither the full ML alpha nor the DD protection benefit of triggers applied cleanly to a static allocator.

---

## ML Weight vs Trigger Override Log

Over 448 total trading days in the K201 walk-forward window:

| Trigger Action | Days | % of total |
|----------------|------|-----------|
| None (no trigger) | 101 | 22.5% |
| T1 reduce (per-symbol Sh < -2.0) | 104 | 23.2% |
| T2 halt (panel 30d Sh < 0) | 96 | 21.4% |
| T3 halt (cumulative DD > 2%) | 147 | 32.8% |

**ML vs trigger disagreement events** (ML wanted rev carry, trigger halted or reduced):

| Type | Days | % |
|------|------|---|
| Total disagreement days | 185 | 41.3% |
| Full override (T2/T3 while ML wanted rev) | 93 | 20.8% |
| Partial reduce (T1 while ML wanted rev) | 92 | 20.5% |

**Interpretation:** The ML allocator consistently assigns positive reverse carry predictions (mean predicted weight = 2.99%, max = 5.0% — at the cap). The trigger layer fires on 77.5% of all days (T1/T2/T3 combined). This creates a structural conflict: ML says "hold reverse carry," triggers say "halt." On 41.3% of days the ML wanted to hold but the trigger overrode or reduced. This is not a healthy composition — it is a zero-sum redistribution that undermines ML alpha.

**Key diagnostic: T3 dominant.** T3 (cumulative panel DD > 2%) was the primary trigger, firing 28.0% of all days and 20.7% of OOS days. The cumulative nature of T3 means it fires for extended stretches even after the underlying condition clears. This creates long periods where the ML is effectively operating without the reverse carry sleeve — reducing its ability to express its signal.

---

## Per-Fold Breakdown

| Fold | Period | K196 Sh | K198 Sh | K199b Sh | K201 Sh | K201 vs K198 |
|------|--------|---------|---------|----------|---------|-------------|
| 0 | 2025-01-22 to 2025-05-13 | 4.39 | 6.57 | 4.27 | 6.39 | -0.18 |
| 1 | 2025-05-14 to 2025-09-02 | 5.66 | 7.38 | 5.88 | 7.38 | 0.00 |
| 2 | 2025-09-03 to 2025-12-23 | 2.90 | 7.94 | 2.88 | 8.01 | +0.07 |
| 3 | 2025-12-24 to 2026-04-14 | 10.88 | 9.75 | 8.70 | 7.72 | -2.03 |

**Fold analysis:**

- **Folds 1 & 2 (mid-period):** K201 is essentially identical to K198 (Fold 1, delta=0.00) or marginally better (Fold 2, +0.07). These are regimes where the trigger layer had limited OOS activity — the ML ran relatively unconstrained.
- **Fold 3 (2025-Q4 to 2026-Q1, the most profitable regime):** K201 significantly underperforms K198 by 2.03 Sharpe points. This is the high-FR tail-carry environment where reverse carry is most lucrative. T3 (cumulative DD trigger) fired most aggressively here (20.7% OOS rate), repeatedly cutting the reverse carry allocation at precisely the moments ML wanted maximum exposure. This is the core conflict: the triggers were designed for tail protection in bad regimes, but they also fire in good regimes if the cumulative drawdown counter has not reset.
- **Fold 0 (early period):** Mild underperformance (-0.18). Triggers active, ML somewhat constrained.

**Which fold benefits most from combination?** Fold 2 shows the only clean benefit (+0.07). This is a moderate-volatility, ambiguous regime where ML guidance adds marginal value over K199b's static allocation without the trigger layer undermining it.

---

## Synergy Analysis

| Metric | Value |
|--------|-------|
| K196 baseline OOS Sh | 9.2005 |
| K198 marginal lift vs K196 | +1.079 |
| K199b marginal lift vs K196 | -1.373 |
| Sum of individual marginal lifts | -0.294 |
| K201 marginal lift vs K196 | -0.614 |
| **Synergy (K201 - sum)** | **-0.320** |
| DD improvement K201 vs K198 | -0.0004 (worse) |

Synergy is **-0.32**: K201 is meaningfully worse than the sum of its parts. This confirms the layers conflict rather than compose. The negative synergy has a concrete mechanism:

1. K199b's triggers were designed assuming a **static P3 risk-parity allocator** — they are calibrated to a fixed weight structure where reverse carry always receives a stable baseline allocation.
2. K198's ML allocator **dynamically varies** reverse carry weight period-to-period based on predictions. When triggers fire, they create an asymmetric disruption: they cut during the ML's high-weight periods (when ML is most bullish on reverse carry) and have no effect during low-weight periods.
3. This effectively turns the trigger into an **anti-momentum mechanism** on the ML signal — it systematically underweights reverse carry in the exact regimes where ML predicts it should be overweight.

---

## ML Predictor Diagnostics

| Metric | Value |
|--------|-------|
| Overall Ridge R² (train) | 0.937 |
| Overall direction accuracy | 73.3% |
| Walk-forward steps | 13 |

The ML predictor itself performs well — 73.3% direction accuracy on next-30d Sharpe. The problem is not the ML prediction quality; it is the post-allocation trigger interference pattern.

---

## Verdict

**REJECT for v6.6 production. 0/4 acceptance criteria passed.**

| Criterion | Required | K201 Actual | Pass? |
|-----------|----------|-------------|-------|
| AC1: OOS Sh > K198 (10.28) or within -0.1 with DD/WF gain | ≥ 10.18 or compensating | 8.5864 | FAIL |
| AC2: WF min > K198 (6.57) | > 6.57 | 6.39 | FAIL |
| AC3: MaxDD better than K198 (-0.0053) | > -0.0053 | -0.0057 | FAIL |
| AC4: Synergy > -0.20 | > -0.20 | -0.32 | FAIL |

---

## Deployment Risks (if K201 were to be deployed)

1. **High conflict rate (41.3%):** In nearly half of trading days, the ML wanted to express reverse carry but was overridden. This inconsistency creates unpredictable realized returns versus expected returns from the ML model — eroding trader confidence and creating execution friction.

2. **T3 trigger anti-momentum dynamic:** The cumulative DD trigger (T3) is path-dependent. A bad stretch in the carry panel sets T3, which then fires for weeks even as the panel recovers — during which ML is predicting high forward Sharpe. The combination locks out reverse carry alpha during recovery windows.

3. **Cap reduction compound effect:** K199b's 5% reverse carry cap (vs K198's 10%) combines with trigger halts to reduce average realized reverse carry exposure from ~3% (K198 capped at 10%) to effectively ~1.5% in K201. The cap was designed to reduce tail risk; when combined with trigger halts, it creates near-zero reverse carry in many regimes where the signal is genuinely positive.

4. **Fold 3 tail risk:** The worst degradation (-2.03 Sharpe in Fold 3) coincides with a high-carry regime where trigger over-intervention cost significant alpha. In live trading, this would manifest as systematic underperformance vs K198 in trending carry environments — which are the most historically profitable periods.

---

## K202 Next Steps

The core insight from K201 is that **post-allocation trigger application is architecturally wrong** for ML allocators. The trigger was designed to interact with static P3 weights; applying it after ML allocation creates conflicting signals. K202 should explore:

1. **Trigger-aware ML features:** Encode T1/T2/T3 state (is T2 currently active? how many days since T3 last fired? current cumulative DD) as explicit ML input features. Let the ML learn to downweight reverse carry predictions when triggers are likely to fire — rather than having two competing layers fight post-hoc.

2. **Two-layer hierarchy (gate then allocate):** Apply triggers first to determine the universe of active strategies, then run ML allocation only within that universe. This makes the trigger a pre-filter rather than a post-override. The ML learns weights knowing which strategies are available.

3. **Regime-conditional ML models:** Train separate Ridge models for: (a) T2/T3 active regimes (reverse carry in stress) vs (b) normal regimes. Let the ML switch models based on trigger state. This handles the signal-distribution shift that occurs during trigger events.

4. **T3 cooldown logic:** The current T3 trigger never resets unless the cumulative DD recovers. A time-decay cooldown (e.g., reactivate after 14d if no new DD threshold breach) would reduce the "stuck halt" problem seen in Fold 3.

5. **Asymmetric ML-trigger interaction:** Only allow triggers to *reduce* ML weights, not to redistribute. When T2 fires, zero the rev carry allocation but do not redistribute to other strategies — this preserves the ML's cross-strategy relative weighting and avoids over-concentrating into non-carry strategies during stress periods.

---

## Production Decision

| Version | Status |
|---------|--------|
| K196 v6.4 | Baseline reference, deprecated if K198 promoted |
| K198 Ridge ML | Best current candidate (OOS Sh 10.28, WF min 6.57) — recommend continued evaluation |
| K199b triggers | Safety-only variant (OOS Sh 7.83) — retain if MaxDD constraint is binding |
| K201 ML+triggers | **REJECTED** — negative synergy, 0/4 criteria |
| K202 | Trigger-aware ML architecture — next wave |

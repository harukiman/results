# Wave K211 — Ethena TVL Interaction Features for K198 ML Allocator

**Date**: 2026-05-25  
**Status**: REJECT  
**Runtime**: 2.8s  
**Objective**: Apply K207 prescription — carry-specific interaction features instead of global Ethena features

---

## Executive Summary

K211 tested the hypothesis that carry-specific interaction features (`eth_tvl_change_30d × V_rev_carry__sh30` and `eth_tvl_drawdown × V_fwd_carry__sh30`) would fix K207's failure by making the Ethena TVL signal per-strategy rather than global noise. The approach partially worked mechanically — interaction features achieved non-zero, economically meaningful Ridge coefficients (rank #6 and #28 out of 53). However, the OOS Sharpe improvement was not achieved: K211 produced 8.8068 vs K198's 10.28 baseline, slightly worse than K207's 8.8748.

**VERDICT: REJECT.** K211 does not promote to v6.6. The Ethena signal, even when carry-specific, cannot overcome the fundamental issue that adding features to a 51-feature Ridge on only ~90d of training data increases estimation error faster than the signal value it adds.

---

## Three-Way Comparison

| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min |
|---------|--------|-----------|---------|--------|
| K198 v6.5 baseline | **10.2800** | **-0.0053** | **7.9100** | **6.5700** |
| K207 global Ethena (REJECTED) | 8.8748 | -0.0063 | 7.5252 | 6.5760 |
| K211 interaction Ethena (THIS) | 8.8068 | -0.0062 | 7.3937 | 6.4892 |

**Lift vs K198**: OOS Sh −1.4732, WF min −0.0808  
**Lift vs K207**: OOS Sh −0.0680 (K211 slightly *worse* than K207)

---

## Interaction Feature Design

The interaction features were constructed as:

```python
eth_x_V_rev_carry = eth_tvl_change_30d * V_rev_carry__sh30
eth_x_V_fwd_carry = eth_tvl_drawdown   * V_fwd_carry__sh30
```

Both computed with 7-day lag (no look-ahead bias). The TVL signal × carry momentum product was designed to give Ridge a per-strategy modulation of the Ethena regime, rather than the global-identical value that diluted discrimination in K207.

### Feature Coverage
- `eth_x_V_rev_carry`: 568/568 non-zero (100.0%), mean=−4.01, std=5.87
- `eth_x_V_fwd_carry`: 407/568 non-zero (71.7%), mean=−1.17, std=2.48

The non-zero coverage confirms the features are well-populated and active throughout the sample.

---

## Interaction Feature Importance and Coefficients

### Global Feature Ranking (full-sample Ridge, mean |coef| across all strategies)

| Rank | Feature | |Coef| |
|------|---------|-------|
| 1 | K116__sh90 | 2.2178 |
| 2 | V_rev_carry__mdd30 | 2.0593 |
| 3 | V_rev_carry__sh90 | 1.9883 |
| 4 | K114__vol30 | 1.5409 |
| 5 | K116__vol30 | 1.4642 |
| **6** | **eth_x_V_fwd_carry** | **1.2995** ← INTERACTION |
| 7 | V_rev_carry__vol30 | 1.1859 |
| 8 | V_rev_carry__sh30 | 1.1854 |
| ... | ... | ... |
| **28** | **eth_x_V_rev_carry** | **0.6874** ← INTERACTION |

`eth_x_V_fwd_carry` achieves rank #6/53 — a top-tier feature by absolute importance. `eth_x_V_rev_carry` is rank #28, still meaningful.

### Signed Coefficients by Strategy (full-sample)

**eth_x_V_rev_carry** (eth_tvl_change_30d × V_rev_carry momentum):
- V_rev_carry: **+2.954** — high positive; TVL growth × rev_carry momentum strongly predicts rev_carry Sharpe
- K116: +1.056 — spillover effect
- v4.1: −0.658 — reverse effect on trend strategy

**eth_x_V_fwd_carry** (eth_tvl_drawdown × V_fwd_carry momentum):
- V_fwd_carry: **+4.201** — very strong; TVL drawdown × fwd_carry momentum → fwd_carry Sharpe
- V_rev_carry: −2.760 — negative; TVL drawdown suppresses reverse carry

### Walk-Forward Coefficient Aggregation (V_rev_carry and V_fwd_carry)

| Strategy | Feature | Mean Coef | Abs Mean | Non-Zero | Sign Consistency |
|----------|---------|-----------|----------|----------|-----------------|
| V_rev_carry | eth_x_V_rev_carry | +0.145 | 0.907 | 100% | 47% |
| V_rev_carry | eth_x_V_fwd_carry | +0.683 | 0.838 | 100% | 80% |
| V_fwd_carry | eth_x_V_rev_carry | −0.619 | 1.263 | 100% | 67% |
| V_fwd_carry | eth_x_V_fwd_carry | −0.232 | 0.770 | 100% | 73% |

Key insight: `eth_x_V_rev_carry` for V_rev_carry has low sign consistency (47%), suggesting the TVL growth × rev_carry signal is regime-dependent and changes direction mid-sample. `eth_x_V_fwd_carry` for V_rev_carry has better sign consistency (80%) and positive mean, indicating the fwd-carry TVL drawdown signal cross-predicts rev_carry more stably.

---

## V_rev_carry Weight Trajectory: K207 vs K211 vs K198

| Step | Test Period | K211 V_rev_carry W | K211 V_fwd_carry W |
|------|------------|---------------------|---------------------|
| 0 | 2025-01-22 | 0.0500 | 0.0557 |
| 1 | 2025-02-21 | 0.0500 | 0.1273 |
| 2 | 2025-03-23 | 0.0500 | 0.0000 |
| 3 | 2025-04-22 | 0.0000 | 0.0500 |
| 4 | 2025-05-22 | 0.0000 | 0.0500 |
| 5 | 2025-06-21 | 0.0000 | 0.0500 |
| 6 | 2025-07-21 | 0.0000 | 0.0500 |
| 7 | 2025-08-20 | 0.0000 | 0.0500 |
| 8 | 2025-09-19 | 0.0000 | 0.0500 |
| 9 | 2025-10-19 | 0.0500 | 0.1430 |
| 10 | 2025-11-18 | 0.0500 | 0.1008 |
| 11 | 2025-12-18 | 0.0500 | 0.0910 |
| 12 | 2026-01-17 | 0.0500 | 0.0108 |
| 13 | 2026-02-16 | 0.0500 | 0.0747 |
| 14 | 2026-03-18 | 0.0500 | 0.1503 |

V_rev_carry mean weight: 0.030, min: 0.000, max: 0.050  
The pattern shows V_rev_carry is dropped to 0 during steps 3–8 (Apr–Sep 2025), which coincides with Ethena TVL contraction period. This is directionally correct regime behavior — but the carry reduction is too aggressive and the model cannot recover performance.

K198 reference: V_rev_carry maintained around 5–10% consistently by pure Sharpe prediction without TVL interaction.  
K207 (global): V_rev_carry reduced to 3% average across entire sample — the interference problem identified in K207 diagnosis.  
K211 (interaction): V_rev_carry mean 3.0% — interaction features did not restore the weight; they further confirmed the suppression in carry-decay regimes.

---

## Walk-Forward OOS Analysis

### WF Fold Sharpes (4 folds)

| Fold | Sharpe |
|------|--------|
| Fold 1 (early) | 6.489 |
| Fold 2 | 7.077 |
| Fold 3 | 7.968 |
| Fold 4 (late) | 8.040 |

WF mean: 7.394, WF min: 6.489, WF max: 8.040  
The monotonically increasing fold Sharpes suggest the model improves over time as more data becomes available for Ridge training — but the early folds are dragged down by poor carry allocation during the 2025 TVL contraction period.

### OOS Period Performance

K211 OOS (last 30% = ~135 days):
- Sharpe: 8.807 (annualized)
- MaxDD: −0.0062
- Sortino: (see JSON)
- Ann. Return: see JSON
- Ann. Vol: see JSON

---

## Root Cause Analysis: Why K211 Still Fails

1. **Training window too short for interaction signal**: With only 90d of training data, the Ridge model cannot distinguish the interaction feature signal from spurious correlations. The 30-day ETH TVL signal requires at least 2–3 TVL cycles (each ~90d) to learn reliably — meaning 180–270d of training would be needed.

2. **Interaction feature is doubly noisy**: `eth_x_V_rev_carry = eth_tvl_change_30d × V_rev_carry__sh30`. Both components are noisy 30d rolling estimates. Their product amplifies noise, especially in short training windows.

3. **Sign inconsistency (47% for key term)**: The V_rev_carry coefficient for `eth_x_V_rev_carry` has only 47% sign consistency across WF steps, meaning the model learns opposite signs in different regimes. Ridge then averages toward zero, providing no net benefit.

4. **CARRY_REV_CAP = 5% binding**: With a hard cap at 5% for V_rev_carry, even correctly predicting the strategy won't change portfolio weights beyond the cap. The TVL interaction can push the weight to 0 (when predicting negative Sharpe) but cannot push above 5%.

5. **The fundamental K207 diagnosis was partially correct but incomplete**: Global features dilute Ridge — interaction features fix this conceptually. But the signal mechanism is `TVL decline → lower funding rates → lower carry returns`. This mechanism operates at 90–180d scale, not 30d. A 30d × 30d interaction feature doesn't capture the right timescale.

---

## Acceptance Check

| Criterion | Threshold | K211 | Result |
|-----------|-----------|------|--------|
| OOS Sharpe ≥ K198 | ≥ 10.28 | 8.807 | **FAIL** |
| WF min ≥ K198 | ≥ 6.57 | 6.489 | **FAIL** |
| MaxDD ≤ K198 | ≥ −0.0053 | −0.0062 | **FAIL** |
| Interaction features non-zero | > 0 | ✓ (rank #6, #28) | **PASS** |

**OVERALL: REJECT.** K211 does not promote to v6.6.

---

## Verdict and K212 Recommendations

### K211 Signal Analysis: What Was Learned

Despite rejection, K211 produces valuable findings:

1. **`eth_x_V_fwd_carry` (rank #6) is a strong feature** — TVL drawdown × fwd_carry momentum cross-predicts both carry strategies and has 73–80% sign consistency in walk-forward. This is the most promising Ethena signal found so far.

2. **The interaction design is correct in direction** — V_rev_carry sees +2.954 coefficient for its own interaction feature (TVL growth × rev_carry momentum), confirming the mechanism. The problem is estimation variance, not signal direction.

3. **Longer training window needed**: Switching from 90d → 180d training might allow the Ridge to learn the interaction signal more reliably, at the cost of 3 fewer WF steps.

### K212 Recommendations

If K210 was accepted: **K212 = combine K210 + K211 ensemble approach** (use K211 weights when TVL signal strong, K198 otherwise).

If K210 was rejected: **K212 should investigate**:

**Option A (Most promising)**: Increase training window to 180d for Ethena interaction features. Accept 12 vs 15 WF steps in exchange for better coefficient stability.

**Option B**: Replace interaction with a **regime gate**: use K198 weights normally, but if `eth_tvl_change_30d < −0.15` (TVL dropped >15% in 30d), zero out carry strategies (similar to FR trigger logic). No ML learning needed — rule-based regime conditioning.

**Option C**: Replace `V_rev_carry__sh30` with a longer-window signal (`sh90`) in the interaction. `eth_tvl_change_30d × V_rev_carry__sh90` would be less noisy and might achieve sign consistency >60%.

**Option D (Structural)**: Instead of modifying the feature matrix, implement a 2-layer model: K198 base allocation, then a TVL overlay layer that scales carry allocations. The overlay is trained on 180d windows independently.

### On Combining K211 + K210

If K210 was accepted, K212 should test a conditional combination: use K211 weights when `eth_tvl_change_30d > 0` (TVL growing, carry favorable), use K198 weights when TVL declining. This regime-conditional combination preserves K198's OOS Sh 10.28 in carry-unfavorable regimes while potentially boosting carry-favorable periods.

---

## Output Files

- `/Users/nekonaomichi/crypto-lab/wave_k211_ethena_interaction.py` — Implementation (2.8s runtime)
- `/Users/nekonaomichi/crypto-lab/wave_k211_ethena_interaction.json` — Full metrics and diagnostics
- `/Users/nekonaomichi/crypto-lab/wave_k211_curves.json` — Equity curves and weight series
- `/Users/nekonaomichi/crypto-lab/wave_k211_ethena_interaction.md` — This report

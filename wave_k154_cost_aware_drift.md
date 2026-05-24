# Wave K154 — K153 Cost-Aware Variant (z>3, long hold)

**Hypothesis**: K153's gross signal (SR +0.51) was destroyed by turnover (4,146 trades × 14 bp roundtrip ≈ cost 0.68 vs gross PnL 0.30). Restricting entries to rarer events (|z| > 3) and extending hold to 15–30 events (≈5–10 days) should preserve signal while cutting turnover ~3×.

**Data**: 29 symbols, 2,187 8h-events, 2024-05-24 .. 2026-05-23 (~730d).
**z stats**: mean=0.258, std=1.044, |z|>2 frac=7.51%, **|z|>3 frac=2.38%** (rare-event slice as expected).

---

## Per-variant Sharpe (vs K153 baseline)

| Variant | Direction | gross SR | net SR | OOS SR | MaxDD | trades | cost | gates |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **K153 V_z2_h3d** (baseline) | fade z>2, hold 9 | +0.51 | -0.63 | +0.17 | — | 4,146 | 0.680 | 1/6 |
| **K154 V_z3_h15** | fade z>3, hold 15 | +0.24 | -0.34 | **+0.58** | -29.4% | 1,376 | 0.211 | 3/6 |
| **K154 V_z3_h30** | fade z>3, hold 30 | +0.26 | -0.31 | **+0.58** | -29.8% | 1,376 | 0.211 | 3/6 |
| **K154 V_z25_h30_xs** | xs z>2.5, hold 30 | -0.69 | -0.72 | -1.23 | -19.0% | 57 | 0.006 | 2/6 |
| **K154 V_z3_continuation** | z>3 → LONG | -0.24 | -0.81 | -1.97 | -41.8% | 1,376 | 0.211 | 1/6 |

WF (4-fold OOS-SR):
- V_z3_h15:  -2.84  +1.56  -0.16  -0.25   (one good fold; not robust)
- V_z3_h30:  -2.95  +1.65  -0.16  -0.25   (mirror of h15)
- V_z25_h30_xs: +1.25 -0.05 +1.46 +0.17   (mostly positive, but small samples; final OOS still -1.23)
- V_z3_continuation: +1.69 -2.13 -0.86 -1.37   (signal flips early then collapses)

Bootstrap OOS 95% CI (Sharpe):
- V_z3_h15: [-2.53, +2.85] mean +0.37   (wide — small OOS sample, low confidence)
- V_z3_h30: [-2.53, +2.85] mean +0.37
- V_z25_h30_xs: [-3.39, +1.76] mean -0.71
- V_z3_continuation: [-4.15, +1.00] mean -1.78

---

## Cost analysis — did rare+long hold solve K153's cost problem?

**Yes for cost, NO for the gross signal.** The cost reduction worked exactly as engineered, but the underlying alpha shrank in parallel.

| Quantity | K153 V_z2_h3d | K154 V_z3_h15 | change |
|---|---:|---:|---:|
| trades (|z| trigger × n_periods) | 4,146 | 1,376 | **-67%** |
| Σ cost | 0.680 | 0.211 | **-69%** |
| Σ price PnL (gross excl. funding) | +0.300 | +0.088 | **-71%** |
| Σ fund PnL | +0.002 | -0.001 | ≈0 |
| Σ net PnL | -0.378 | -0.124 | better (less negative) |
| gross Sharpe | +0.51 | +0.24 | **-53%** |
| net Sharpe | -0.63 | -0.34 | better (less negative) |

**Critical interpretation**: Removing the |z|∈(2,3] slice removed *more than its proportional share of gross alpha*. That means the K153 signal was not concentrated in the rare tail — it was a broad |z|>2 effect with cost-per-trade fatally close to per-trade expected PnL. The "design FR drift" signal is real but *weak per event*; you cannot afford to be selective and still pay 14 bp roundtrip.

**XS variant (V_z25_h30_xs)**: cost obliterated (0.006), but gross is now **-0.69** — selecting 6 names on |z| in 30-event blocks gives no signal at all (in fact anti-signal). Insufficient breadth (only 57 rebalances over 720d ≈ 1 per 12d).

**Continuation (V_z3_continuation)**: mirror of fade by construction (same trades, reversed sign) → confirms the fade variant's gross sign is correct, but symmetric magnitude (gross ±0.24) shows the signal is too small in either direction to overcome cost.

**Conclusion on cost**: turnover engineering succeeded (−69%) but signal-per-trade did not improve. The K153 alpha lives near |z|≈2, not in the |z|>3 tail.

---

## §6 mini-gates

Six gates: OOS_SR≥0.5, p_perm<0.05, MaxDD>−40%, cost-stress robust, DSR_oos>0.5, price_dominant.

| Variant | OOS≥0.5 | p<0.05 | DD>−40 | cost robust | DSR_oos>0.5 | price_dom | Pass |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| V_z3_h15 | ✓ +0.58 | ✗ p=0.41 | ✓ -29% | ✗ | ✗ DSR≈0 | ✓ | **3/6** |
| V_z3_h30 | ✓ +0.58 | ✗ p=0.36 | ✓ -30% | ✗ | ✗ | ✓ | **3/6** |
| V_z25_h30_xs | ✗ -1.23 | ✗ p=0.87 | ✓ -19% | ✗ | ✗ | ✓ | **2/6** |
| V_z3_continuation | ✗ -1.97 | ✗ p=0.41 | ✗ -42% | ✗ | ✗ | ✓ | **1/6** |

**No variant clears §6.** Failures concentrated in: permutation p-value (signal not distinguishable from cross-sectional row shuffle), cost stress (net SR collapses further at 1.5× cost), and DSR (Sharpe not deflation-robust against the 4-trial selection set).

The OOS=+0.58 on V_z3_h15/h30 is *driven entirely by fold 2* (+1.56–1.65) — the other 3 folds are negative. This is a 30%-OOS-window artifact, not a stable property. Bootstrap CI [-2.53, +2.85] confirms zero distinguishability from null.

---

## Correlation with K133 (REVERSAL — ensemble check)

K154 vs K133 reversal variants, |ρ| over n=71–143 overlapping rebal windows:

| K154 variant | K133::V_rev_5d_z15 | K133::V_rev_7d_z15 | K133::V_rev_3d_z15 | K133::V_rev_5d_z20 |
|---|---:|---:|---:|---:|
| V_z3_h15 | -0.05 | -0.06 | -0.05 | -0.02 |
| V_z3_h30 | -0.05 | -0.06 | -0.05 | -0.01 |
| V_z25_h30_xs | -0.14 | +0.01 | -0.10 | -0.01 |
| V_z3_continuation | +0.06 | +0.06 | +0.05 | +0.02 |

**All |ρ| ≤ 0.14 — fully orthogonal to K133.** Confirms K153/K154 capture a distinct premium-vs-realized FR mechanism, not the broad FR reversal that K133 trades. If K154 had produced any verdict-eligible variant, it would be a clean ensemble candidate. It did not.

---

## Verdict

**REJECT all K154 variants.**

- The cost fix worked (−69% cost) but proportionally killed gross PnL (−71%), implying K153's signal is **concentrated near the lower z-tail (|z|∈[2,3])** and cannot be filtered by stricter entry without losing the alpha that pays for it.
- Best variant (V_z3_h15/h30): OOS Sharpe driven by 1-of-4 walk-forward fold; bootstrap CI straddles zero (mean +0.37, 95% [-2.53, +2.85]); permutation p≈0.4. Not real.
- Cross-sectional variant (V_z25_h30_xs): gross now negative — XS picks on rare tail of design-FR residual have no edge. Insufficient breadth (57 rebals).
- Continuation variant: confirms the fade gross sign is correct (mirror, |gross|=0.24 both directions) but the magnitude is too small to overcome any reasonable cost.
- Correlation with K133: clean orthogonality (|ρ| ≤ 0.14) — would have been useful for ensemble had any variant passed.

**Conclusion on the K153 family**: the "designed FR drift" mechanism has a small, broad gross edge (~0.5 Sharpe at |z|>2 with hold ≈3d) that **cannot survive 14 bp roundtrip cost at any tested turnover-reduction setting**. Further variants in this family (e.g. cost-aware K155+) should pivot away from threshold-based turnover throttling and instead test:
1. Lower cost regime (e.g. maker-only quoting at ~2 bp per side) to see if the gross +0.5 SR survives;
2. Combining the signal with a turnover-suppressing wrapper (e.g. only trade when a co-signal agrees) rather than raising z-threshold;
3. Different signal construction (e.g. premium *level* not residual z) to find a thicker-tail edge.

---

## Files

- `/Users/nekonaomichi/crypto-lab/wave_k154_cost_aware_drift.py`
- `/Users/nekonaomichi/crypto-lab/wave_k154_cost_aware_drift.json`
- `/Users/nekonaomichi/crypto-lab/wave_k154_curves.json`

Wall time: 621 s (10.4 min). n_perm=300, n_boot=300, WF folds=4, DSR n_trials=4.

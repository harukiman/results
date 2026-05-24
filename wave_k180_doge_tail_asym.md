# Wave K180: DOGE Asymmetric Tail Mechanism Investigation

**Date:** 2026-05-25
**Runtime:** 4.5s
**Parent waves:** K175, K177, K178

---

## Executive Summary

K178 revealed DOGE z>2 → next-event return = -43.94 bps (very strong K175-favorable edge, comparable to XRP's -49 bps). Yet K177 DOGE aggregate net Sharpe was -0.19. This wave investigated the **tail asymmetry hypothesis**: the z>2 SHORT tail has genuine edge, but the z<-2 LONG tail destroys aggregate performance.

**Verdict: REJECT — V_doge_z2_short_only gross Sharpe = -0.30, below the §6 G6 threshold of 0.3.**

**Root cause identified:** The K178 "+43.94 bps edge" is a **contemporaneous (same-period) signal artifact**, not a predictive (lag=1) edge. The K175 convention executes one period AFTER the signal fires, at which point the DOGE edge reverses to **-20.41 bps** (lag=1). XRP captures +38.50 bps at lag=1 (edge persists). DOGE does not. The strategy is fundamentally chasing a move that has already occurred.

**K181 Recommendation: REJECT. Do not integrate into K176 ensemble.**

---

## 1. Data Summary

| Item | Value |
|------|-------|
| Symbol | DOGE |
| Events | 2,187 |
| Date range | 2024-05-24 → 2026-05-23 |
| FR premium mean | -0.54 bps (HL > Bybit on average) |
| FR premium std | 1.66 bps |
| FR premium skew | -8.88 (strong left tail) |
| FR premium ACF lag-1 | +0.47 (persistent series) |
| Cost model | 2 bps/side slippage, 0 maker fee, 4 bps round-trip |

---

## 2. Per-Event Tail Decomposition (z=2.0, win=30)

| Tail | Direction | Count | Mean fwd return | Mean PnL (K175) | Sharpe | p-value | Win rate |
|------|-----------|-------|-----------------|-----------------|--------|---------|----------|
| SHORT (z>+2) | SELL Bybit | 46 | -43.94 bps | **+43.94 bps** | +4.79 | 0.337 | 0.522 |
| LONG (z<-2) | BUY Bybit | 97 | -58.74 bps | **-58.74 bps** | -7.27 | 0.034 | 0.392 |

**Critical distinction:** These per-event Sharpe numbers are computed over only the triggered events, using the *same-period* forward return (not lag=1). They show that:
- In the SAME period z>2 fires, DOGE price falls 43.94 bps on average → SHORT profits
- In the SAME period z<-2 fires, DOGE price ALSO falls 58.74 bps → LONG loses severely

### Tail asymmetry mechanism confirmed
The asymmetry hypothesis is **confirmed but not actionable**: BOTH tails have edge issues. The LONG tail is chronically wrong (price continues falling when z<-2), and the SHORT tail edge vanishes at lag=1 (see Section 3). The strategy executes at lag=1, missing the same-period edge entirely.

---

## 3. Critical Finding: Lag Structure Reveals Contemporaneous-Only Signal

The +43.94 bps edge in the SHORT tail exists only at **lag=0** (same period as signal). The K175 convention executes at **lag=1** (next period after signal fires). At lag=1, the edge **reverses**.

| Lag from signal | DOGE SHORT PnL | XRP SHORT PnL | SUI SHORT PnL |
|-----------------|---------------|---------------|---------------|
| lag=0 (same period) | **+43.94 bps** | +49.17 bps | -20.68 bps |
| lag=1 (K175 convention) | **-20.41 bps** | +38.50 bps | **+66.08 bps** |
| lag=2 | -24.38 bps | -3.59 bps | -16.55 bps |
| lag=3 | +26.24 bps | +54.84 bps | +8.95 bps |

**Interpretation:**
- XRP: edge persists at lag=1 (+38.50 bps) → K175 captures it correctly
- SUI: edge strengthens at lag=1 (+66.08 bps) → K175 captures it correctly
- DOGE: edge reverses at lag=1 (-20.41 bps) → K175 **chases the move after it has already happened**

This explains why K178's per-event analysis showed a promising signal that could not be operationalized: DOGE's FR premium extreme events predict same-period reversion but do not predict next-period continuation of that reversion. The mean-reversion in DOGE happens *within* the 8-hour funding window, not across the next window.

---

## 4. Variant Comparison (GROSS and NET, K173 META-LESSON)

All variants: z=2.0, win=30 events, 2 bp/side maker cost.

| Variant | Sh Gross | Sh Net | IS Sh Net | OOS Sh Net | Trades | TPY |
|---------|----------|--------|-----------|------------|--------|-----|
| V_doge_aggregate (K177 replicate) | -0.096 | -0.191 | -0.415 | +0.594 | 143 | 71.6 |
| **V_doge_z2_short_only (PRIMARY)** | **-0.297** | **-0.344** | -0.569 | +0.575 | 46 | 23.0 |
| V_doge_z2_long_only (SANITY) | +0.131 | +0.047 | -0.043 | +0.331 | 97 | 48.6 |

**Finding:** Isolating the SHORT tail *worsens* the aggregate (−0.297 vs −0.096 gross). The LONG tail, despite its per-event negative PnL, adds diversification that slightly helps the aggregate Sharpe. The LONG tail's very low win rate (39.2%) means it has high variance, providing some positive skew to the aggregate via occasional large LONG wins.

The LONG-only variant (+0.131 gross) outperforms SHORT-only in aggregate Sharpe — a counter-intuitive result confirming that the strategy dynamics are dominated by variance characteristics, not per-event mean PnL direction.

---

## 5. Asymmetric Z-Threshold Variants

| Variant | Sh Gross | Sh Net | OOS Sh Net | Trades |
|---------|----------|--------|------------|--------|
| short_z2.0 + long_z1.5 | +0.145 | +0.034 | +0.621 | 221 |
| short_z1.5 + long_z2.0 | +0.157 | +0.059 | +0.407 | 203 |
| short_z2.5 + long_z1.5 | +0.031 | -0.076 | +0.298 | 186 |
| short_z2.5 + long_z2.0 | -0.300 | -0.391 | +0.154 | 108 |
| short_z2.0 + long_z2.5 | -0.802 | -0.874 | +0.508 | 96 |

**Best asymmetric variant:** short_z1.5 + long_z2.0 = +0.157 gross. Even the best asymmetric configuration fails to reach gross ≥ 0.3. The OOS Sharpe being positive across most variants suggests residual but weak signal; it is insufficient for ACCEPT classification.

---

## 6. Z-Threshold Sweep (V_doge_short_only)

| Z-threshold | Sh Gross | Sh Net | OOS Sh Net | Trades |
|-------------|----------|--------|------------|--------|
| z=1.5 | +0.098 | +0.038 | +0.265 | 106 |
| z=2.0 | -0.297 | -0.344 | +0.576 | 46 |
| z=2.5 | -1.369 | -1.397 | -1.669 | 11 |
| z=3.0 | -1.211 | -1.225 | 0.000 | 5 |

**Observation:** z=1.5 gives the best gross Sharpe (+0.098) but still well below 0.3. Lower thresholds include noisier events. The z=2.5 / 3.0 cases suffer from sample count (≤11 trades) leading to unreliable estimates.

---

## 7. Lookback Window Sweep (V_doge_short_only, z=2.0)

| Window | Sh Gross | Sh Net | OOS Sh Net | Trades |
|--------|----------|--------|------------|--------|
| win=30 | -0.297 | -0.344 | +0.576 | 46 |
| win=60 | -1.045 | -1.091 | -0.535 | 40 |
| win=90 | -1.553 | -1.590 | -1.447 | 37 |

Longer windows further degrade performance, consistent with the signal's non-predictive (contemporaneous-only) nature.

---

## 8. V_doge_z2_short_only Full Metrics

| Metric | Value |
|--------|-------|
| Sharpe (GROSS) | -0.2972 |
| Sharpe (NET) | -0.3439 |
| CAGR (NET) | -5.3% |
| Max DD (NET) | -24.4% |
| IS Sharpe (NET) | -0.5688 |
| OOS Sharpe (NET) | +0.5754 |
| WF Fold Sharpes (NET) | [-0.038, -1.245, +0.349] |
| Perm p-value (NET) | 0.000 |
| DSR (NET) | 0.000 |
| Bootstrap CI 5-95 (NET) | [-1.84, +0.80] |
| N Trades | 46 |
| Trades/Year | 23.0 |

**Note on IS/OOS split:** IS net Sharpe = -0.569, OOS net Sharpe = +0.575. This reversal (IS worse than OOS) does not indicate genuine OOS edge — it reflects high variance with small sample count per tail. With only 34 IS short events, the IS estimate is noise-dominated. The wide bootstrap CI (-1.84, +0.80) confirms this.

**Note on perm p-value = 0.000:** This is the probability that a random permutation achieves a Sharpe as NEGATIVE as the observed. Since the strategy underperforms random shuffling, p=0 means the strategy is significantly *bad*, not good.

---

## 9. §6 Gate Evaluation

Evaluated on: **V_doge_z2_short_only** (primary hypothesis variant)

| Gate | Threshold | Result |
|------|-----------|--------|
| G1: OOS Sharpe Net | ≥ 1.0 | FAIL (0.575) |
| G2: Perm p-value | ≤ 0.05 | PASS (0.000 — negative direction) |
| G3: DSR | ≥ 0.95 | FAIL (0.000) |
| G4: WF all folds positive | All > 0 | FAIL (fold 1 = -1.245) |
| G5: IS/OOS ratio | ≥ 0.5 | FAIL (IS negative) |
| G6: Gross Sharpe | ≥ 0.3 | FAIL (-0.297) |
| G7: Trades/year | ≥ 20 | PASS (23.0) |

**Gates passed: 2/7** (G2 pass is due to significantly negative performance, not positive alpha)

**Best variant by gross Sharpe:** short_z1.5 + long_z2.0 = +0.157 — still below G6 threshold.

---

## 10. Rolling Sharpe Stability

| Metric | V_doge_short_only | V_doge_aggregate |
|--------|-------------------|-----------------|
| Mean rolling Sharpe (365-event window) | -0.720 | -0.464 |
| Std | 1.390 | 1.417 |
| Min | -3.428 | — |
| Max | +1.412 | — |
| Fraction windows positive | 37.7% | 46.8% |

DOGE does not sustain positive rolling Sharpe in either configuration. The aggregate variant (both tails) has slightly better stability.

---

## 11. Tail Sweep Across Windows and Thresholds

| win/z | SHORT n | SHORT PnL | SHORT Sh | LONG n | LONG PnL | LONG Sh |
|-------|---------|-----------|----------|--------|----------|---------|
| win=30, z=1.5 | 106 | +22.77 bps | +2.38 | 175 | -16.83 bps | -2.00 |
| win=30, z=2.0 | 46 | +43.94 bps | +4.79 | 97 | -58.74 bps | -7.27 |
| win=30, z=2.5 | 11 | -25.53 bps | -3.92 | 50 | -64.32 bps | -7.43 |
| win=60, z=2.0 | 40 | +2.52 bps | +0.38 | 95 | -14.70 bps | -1.50 |
| win=90, z=2.0 | 37 | -22.31 bps | -2.77 | 90 | -21.88 bps | -2.32 |

**Key pattern:** The "strong" SHORT edge (+43.94 bps Sh=+4.79) at win=30, z=2.0 is an artefact of small-sample high-variance contemporaneous returns. At win=60 the same threshold delivers only +0.38 Sh. This confirms the win=30 result is window-specific and not robust.

---

## 12. Verdict and Implications for K176 Ensemble

### Verdict: REJECT

**V_doge_z2_short_only: gross Sharpe = -0.297 < G6 threshold (0.3). §6 gates: 2/7 passed.**
No asymmetric variant clears gross ≥ 0.3. The mechanism investigation is complete.

### Mechanism Summary

1. **Tail asymmetry confirmed:** DOGE FR premium has structurally negative LONG tail (z<-2 → price continues falling, -58.74 bps/event at lag=0) and a superficially positive SHORT tail (z>+2 → price falls -43.94 bps *same period*).

2. **Critical failure mode — contemporaneous-only signal:** The SHORT tail edge exists at lag=0 (same funding period) but reverses at lag=1 (-20.41 bps). K175 executes at lag=1. DOGE price mean-reverts *within* the 8-hour window, not *across* the next window. The signal is inherently contemporaneous.

3. **XRP/SUI are different:** XRP edge is +49 bps at lag=0 AND +38 bps at lag=1 (persistent). SUI strengthens to +66 bps at lag=1. DOGE is the outlier where the reversion has already happened by the time the next funding period begins.

4. **FR premium skew (-8.88):** Extreme left tail in DOGE FR premium suggests occasional sharp HL-dominated episodes that drive the z<-2 events. These episodes cluster (DOGE price crash events) and are directionally adverse for the K175 LONG signal.

### Implications for K176 Ensemble

- **Do not add DOGE as a K175 variant to the K176 8-strategy ensemble.**
- DOGE would reduce diversification while adding contemporaneous-only noise.
- The K176 production configuration (XRP+SUI K175, 7 other strategies, OOS Sh +5.41) remains unchanged.
- K175 DOGE integration should be formally closed as a research direction under the current lag=1 execution model.

### Next Steps for K181

1. **Investigate intra-period execution:** If DOGE FR premium z>2 can be detected mid-8h-period (using hourly data) and a position entered with remaining time in the same funding window, the contemporaneous edge may be capturable. Requires HL hourly FR data streaming.

2. **DOGE pure funding-rate carry:** DOGE has consistent HL > Bybit FR (mean premium = -0.54 bps = HL pays more). A direct HL-long / Bybit-short delta-neutral carry could extract 0.54 bps/event × 1095 = ~590 bps/year gross before mean-reversion risk. This is a different alpha class (carry, not z-score reversion).

3. **Symbol expansion for K175:** Consider BNB, ETH, SOL as additional candidates for K175 basket. These have HL data available (see `cache/k163_hl/`). The K178 per-symbol lag sweep should be repeated systematically.

4. **Ensemble correlation check:** Before any new addition to K176, run pairwise OOS correlation of PnL series to ensure diversification benefit.

---

*Report generated by wave_k180_doge_tail_asym.py — Wave K180 / 2026-05-25*

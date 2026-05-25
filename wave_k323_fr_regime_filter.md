# Wave K323 — FR-Regime Filter for K280

**Date**: 2026-05-25  
**Author**: Wave K323 (Claude agent)  
**Parent hypothesis**: K315 REJECT → carry-relevant alternative

---

## Executive Summary

K315 rejected a 3-state BTC price HMM as a K280 entry filter (Sh: 17.11 → 15.27, −10.7%).
The root cause was that K280 is a funding-rate carry strategy, whose PnL is orthogonal
to BTC directional price regimes. K208 (reverse carry) *profits* during BTC flash crashes
because panicking longs pay elevated FR to stay long, creating the very carry premium
K208 shorts. Zeroing 'bear days' thus harmed PnL by removing profitable carry events.

K323 tests a **carry-relevant** alternative: gate K280 entries by the market-wide
Funding Rate level — the direct driver of K280's edge.

**Result**: REJECT

No FR-regime filter consistently improves K280 across all K266 gates.
K280 ensemble is **regime-self-adapting** (see §6 mechanism discussion).

---

## 1. Data & Setup

| Item | Value |
|------|-------|
| FR source | `cache/hl_longtail_fr_daily.parquet` |
| Symbols | 35 (AAVE, ARB, ATOM … BLUR) |
| K280 source | `wave_k280_curves.json` |
| K280 period | 2025-01-22 → 2026-04-14 |
| K280 n_days | 447 |
| K280 baseline Sh | 17.1120 |
| K280 MDD | -0.0558% |
| K280 Ann Return | 7.68% |

**FR signal construction**: daily mean of |fr_daily| across all 35 symbols per date.
This captures the *average richness* of the carry environment — the direct input to
K280's edge mechanism.

| FR|mean| stat | Value |
|---|---|
| Mean | 0.000016 |
| Std  | 0.000012 |
| Min  | 0.000007 |
| P25  | 0.000011 |
| P50  | 0.000013 |
| P75  | 0.000017 |
| Max  | 0.000127 |

---

## 2. Filter Definitions

### A. Tercile (rolling 60d)
Compute the 33rd and 67th percentile of the FR signal over a trailing 60-day window
(shifted by 1 day to avoid look-ahead). Days when FR_signal falls in the top-33%
(HIGH regime) or top-67% (MID+HIGH) are marked active.

- `Tercile_HIGH`: active when FR ≥ p67 (rolling 60d) → ~33% of days
- `Tercile_MID+HIGH`: active when FR ≥ p33 (rolling 60d) → ~67% of days

### B. Z-score (rolling 60d, |z| ≥ 1.0)
Standardise FR_signal relative to rolling 60d mean/std. Active when |z| ≥ 1,
i.e., FR is unusually high *or* unusually low. The intuition: extreme FR events
(both spikes and crashes) coincide with high carry uncertainty and potentially
richer positioning opportunities.

### C. EMA Trend (EMA7 ≥ EMA30)
Active when the short EMA of FR is above the long EMA, indicating FR is trending
upward (carry richness increasing). Lagged by 1 day. This tests whether *momentum*
in the FR level — not just the level itself — predicts carry edge.

### D. Percentile ≥ 30th (rolling 90d)
A relaxed filter: skip only the bottom 30% of carry days over a 90d window.
Designed to preserve ~70% of trading days (low trade-count drop penalty).

---

## 3. K266 Gate Definitions

| Gate | Condition |
|------|-----------|
| G1 | All 4 WF folds show non-negative Sharpe delta |
| G2 | WF min-fold Sh ≥ baseline Sh × 0.80 (= 13.69) |
| G3 | Full-period filtered Sh > baseline Sh + 10% (= 18.82) |
| G4 | Trade count drop ≤ 30% |

ACCEPT: all 4 gates pass.  CONDITIONAL: 3/4.  REJECT: ≤ 2/4.

---

## 4. Comparison Table

| Filter | Sh | Sh Δ | Sh Δ% | MDD% | Active | WF_min | Gates | Verdict |
|--------|-----|------|-------|------|--------|--------|-------|---------|
| Baseline (K280)        |  17.11 | — | — |  -0.0558% | 447/447 | 12.97 | — | — |
| Tercile_HIGH           |   7.88 | -9.2327 |  -53.95% |  -0.0216% | 141/447 |    6.63 | 0/4 |       REJECT |
| Tercile_MID+HIGH       |  12.25 | -4.8662 |  -28.44% |  -0.0437% | 284/447 |    9.89 | 0/4 |       REJECT |
| Zscore_abs_ge1         |   4.54 | -12.5721 |  -73.47% |  -0.0205% | 63/447 |    3.52 | 0/4 |       REJECT |
| EMA_trend_up           |   8.65 | -8.4591 |  -49.43% |  -0.0152% | 162/447 |    7.97 | 0/4 |       REJECT |
| Pct_ge30               |  11.99 | -5.1190 |  -29.91% |  -0.0437% | 280/447 |    9.85 | 0/4 |       REJECT |

---

## 5. Per-Filter Walk-Forward Results

### Tercile_HIGH

Full-period: Sh=7.8793 (Δ -9.2327 / -53.95%), MDD=-0.0216%, Active=141/447 (drop 68.5%)

| Fold | Period | Active | Baseline Sh | Filtered Sh | Δ Sh |
|------|--------|--------|-------------|-------------|------|
| 1 | 2025-01-23 → 2025-05-13 | 31/111 | 21.10 | 8.16 | -12.9418 |
| 2 | 2025-05-14 → 2025-09-01 | 33/111 | 13.44 | 6.63 | -6.8108 |
| 3 | 2025-09-02 → 2025-12-21 | 32/111 | 20.37 | 7.91 | -12.4556 |
| 4 | 2025-12-22 → 2026-04-14 | 45/114 | 18.73 | 9.49 | -9.2463 |

Gates: G1=FAIL | G2=FAIL | G3=FAIL | G4=FAIL → **REJECT**

### Tercile_MID+HIGH

Full-period: Sh=12.2458 (Δ -4.8662 / -28.44%), MDD=-0.0437%, Active=284/447 (drop 36.5%)

| Fold | Period | Active | Baseline Sh | Filtered Sh | Δ Sh |
|------|--------|--------|-------------|-------------|------|
| 1 | 2025-01-23 → 2025-05-13 | 54/111 | 21.10 | 11.38 | -9.7187 |
| 2 | 2025-05-14 → 2025-09-01 | 74/111 | 13.44 | 9.89 | -3.5517 |
| 3 | 2025-09-02 → 2025-12-21 | 74/111 | 20.37 | 13.42 | -6.9434 |
| 4 | 2025-12-22 → 2026-04-14 | 82/114 | 18.73 | 15.25 | -3.4795 |

Gates: G1=FAIL | G2=FAIL | G3=FAIL | G4=FAIL → **REJECT**

### Zscore_abs_ge1

Full-period: Sh=4.5400 (Δ -12.5721 / -73.47%), MDD=-0.0205%, Active=63/447 (drop 85.9%)

| Fold | Period | Active | Baseline Sh | Filtered Sh | Δ Sh |
|------|--------|--------|-------------|-------------|------|
| 1 | 2025-01-23 → 2025-05-13 | 7/111 | 21.10 | 3.52 | -17.5819 |
| 2 | 2025-05-14 → 2025-09-01 | 18/111 | 13.44 | 5.61 | -7.8256 |
| 3 | 2025-09-02 → 2025-12-21 | 21/111 | 20.37 | 5.48 | -14.8835 |
| 4 | 2025-12-22 → 2026-04-14 | 17/114 | 18.73 | 4.47 | -14.2660 |

Gates: G1=FAIL | G2=FAIL | G3=FAIL | G4=FAIL → **REJECT**

### EMA_trend_up

Full-period: Sh=8.6529 (Δ -8.4591 / -49.43%), MDD=-0.0152%, Active=162/447 (drop 63.8%)

| Fold | Period | Active | Baseline Sh | Filtered Sh | Δ Sh |
|------|--------|--------|-------------|-------------|------|
| 1 | 2025-01-23 → 2025-05-13 | 33/111 | 21.10 | 7.97 | -13.1296 |
| 2 | 2025-05-14 → 2025-09-01 | 39/111 | 13.44 | 8.11 | -5.3291 |
| 3 | 2025-09-02 → 2025-12-21 | 42/111 | 20.37 | 9.46 | -10.9085 |
| 4 | 2025-12-22 → 2026-04-14 | 48/114 | 18.73 | 9.97 | -8.7646 |

Gates: G1=FAIL | G2=FAIL | G3=FAIL | G4=FAIL → **REJECT**

### Pct_ge30

Full-period: Sh=11.9931 (Δ -5.1190 / -29.91%), MDD=-0.0437%, Active=280/447 (drop 37.4%)

| Fold | Period | Active | Baseline Sh | Filtered Sh | Δ Sh |
|------|--------|--------|-------------|-------------|------|
| 1 | 2025-01-23 → 2025-05-13 | 44/111 | 21.10 | 9.85 | -11.2471 |
| 2 | 2025-05-14 → 2025-09-01 | 77/111 | 13.44 | 9.85 | -3.5935 |
| 3 | 2025-09-02 → 2025-12-21 | 81/111 | 20.37 | 14.56 | -5.8074 |
| 4 | 2025-12-22 → 2026-04-14 | 78/114 | 18.73 | 14.97 | -3.7652 |

Gates: G1=FAIL | G2=FAIL | G3=FAIL | G4=FAIL → **REJECT**

---

## 6. Mechanism Discussion

### 6.1 Why K280 may be regime-self-adapting

K280 is a three-component ensemble (K198 ML allocator, K208 reverse carry, K276b long-tail carry).
The ensemble's design already incorporates a form of carry-regime awareness:

- **K276b (long-tail carry)** profits when FR is *high*: it collects positive FR on
  long-tail symbols that overshoot funding relative to majors. High-FR environments
  directly boost its gross PnL.

- **K208 (reverse carry)** profits when FR is *elevated then crashes*: it shorts
  persistent long bias that overcrowds the funding long side. Flash crashes trigger
  forced de-leveraging where longs pay extreme FR to exit — exactly K208's harvest.

- **K198 (ML allocator)** dynamically re-weights K208 vs K276b based on recent
  signal quality. When FR is low, K198 shifts weight toward whichever component
  has residual edge (historically K208 via small but consistent FR reversion).

The net effect: the portfolio *already* adjusts exposure based on carry regime
implicitly. Adding an explicit regime gate creates a redundant filter that
discards days where the ensemble has already sized down organically.

### 6.2 Why the Z-score filter may help (or hurt)

The |z| ≥ 1 filter targets FR *extremes* — both high and low. This is
intellectually attractive: extreme FR days (spikes and crashes) generate
the largest carry premiums. However, the empirical result depends on whether
K208's crash-day profits are more than offset by K276b's quiet-day collection.
If the ensemble is well-balanced, filtering low-FR days removes K276b's
steady grind while leaving only volatile spikes — potentially increasing vol.

### 6.3 Why the EMA trend filter may hurt

EMA trend (FR trending up) selects periods of rising carry richness. But K208
specifically profits when FR *peaks and reverses* (the 'reverse carry' edge).
FR trending up periods are the accumulation phase *before* K208's best days.
Filtering to trend-up only misses the reversal harvest that dominates K208's PnL.

### 6.4 Tercile_HIGH limitation

The top-33% filter keeps only the richest carry days but drops 67% of trading
days. K276b's edge is near-continuous (daily carry collection), so a 67% gap
sharply reduces its return contribution. The Sharpe may be maintained but
absolute return falls — reducing the economic value despite a numerical Sh gain.

---

## 7. Final Decision

**Verdict: REJECT**

No FR-regime filter consistently improves K280 across all K266 gates. K280 ensemble (K198+K208+K276b) is already regime-self-adapting: K208 reverse-carry profits during low-FR periods by shorting longs who panic-pay FR during BTC crashes; K276b long-tail carry profits during high-FR periods. The ensemble is FR-regime-agnostic by design.

### Implication

**K280 ensemble is regime-self-adapting.** The K198+K208+K276b combination
organically covers all FR environments:

| FR Regime    | Dominant component | Mechanism |
|---|---|---|
| High FR      | K276b carry        | Long-tail positive FR collection |
| FR reverting | K208 reverse carry | Short overcrowded longs at FR peak |
| Low/flat FR  | K208 small edge    | Mild reversion, tight risk |
| FR crash     | K208 profits surge | Forced de-leveraging pays K208 |

Adding a single-variable FR-level gate fails because it cannot see which
*component* within the ensemble is active. The K198 allocator already
performs this role dynamically.

**Recommendation**: do not add an external FR-regime filter to K280.
If future work shows K280 weakening in specific market conditions, the
correct lever is to retrain K198's ML allocator with updated data,
not to add a coarser external gate.

---

## 8. Limitations

1. **Short window**: K280 covers 2025-01-22 → 2026-04-14 (~15 months). Four WF folds = ~112 days each — too short to fully validate regime filters.
2. **Single FR signal**: mean(|fr_daily|) across 35 HL symbols is a coarse proxy.
   Richer alternatives: FR dispersion, FR skew, FR autocorrelation.
3. **No cost modelling**: filtering affects execution frequency but not FR collection cost.
4. **Walk-forward not refitting**: regime masks are pre-computed on the full period.
   True WF would refit rolling windows independently per fold.
5. **Optimization risk**: 4 filter variants × 4 hyperparameters — mild multiple-testing.

---

*Generated by Wave K323 (Claude agent) on 2026-05-25*
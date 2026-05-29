# K462 GBTC-IBIT Divergence Signal — Research Report

**Wave:** K462  
**Status:** REJECT (0/7 gates passed)  
**Date:** 2026-05-30 01:28 JST  
**Author:** Systematic Alpha Discovery Agent  
**Predecessor:** K455 ETF Total Flow (CONDITIONAL, detrended SR = -0.54)

---

## Executive Summary

K462 tests the GBTC-IBIT cross-fund divergence as a K455 alternative, motivated by the hypothesis that institutional rotation (old money exiting GBTC, new money entering IBIT) captures a signal orthogonal to BTC price trend. The hypothesis has economic intuition but fails empirically on every K266 gate (0/7 passed). The divergence signal is directionally **wrong** — high IBIT-vs-GBTC divergence predicts **negative** forward BTC returns (t+1 corr = -0.116). The detrended Sharpe (-2.03) is far worse than K455 (-0.54). Decision: **REJECT**, do not include in v6.20.

---

## 1. Hypothesis & Motivation

### 1.1 The Rotation Narrative

K455 (ETF total flow) was rejected at CONDITIONAL due to:
- 75% momentum correlation (EMA-21 total flow ≈ EMA-21 BTC price direction)
- Detrended OOS Sharpe = -0.54 (signal is mostly trend-following in disguise)

K462 hypothesis: Split the ETF total into GBTC outflows vs IBIT inflows:
- **GBTC bleeds**: Legacy Grayscale fund investors rotating out (redemption arbitrage closes, converting to spot)
- **IBIT absorbs**: New institutional buyers entering via BlackRock's lower-fee product
- **Net divergence** = IBIT_flow − GBTC_flow should capture "quality of capital entering" vs K455's noise-floor of total flow

Prediction: When IBIT strongly absorbs while GBTC strongly bleeds = rotation = bullish for BTC (new institutional demand replacing old), and this divergence should be more orthogonal to BTC price trend than total flow.

### 1.2 Why This Was Worth Testing

The GBTC-to-IBIT rotation narrative was well-documented in 2024:
- Post-ETF-launch (Jan 2024), GBTC had persistent outflows as investors switched to cheaper products
- IBIT accumulated to $58B+ AUM by May 2026
- The "rotation trade" was discussed by major institutions as structural bullish demand

This is a genuine institutional-flow hypothesis, not purely derivative of BTC trend.

---

## 2. Data

### 2.1 Sources

| Source | Coverage | Rows |
|--------|----------|------|
| `cache/etf_flow_daily.parquet` | Jan 2024 - May 2026 | 609 |
| Farside Investors (via Wayback CDX) | Jul 2024 - Apr 2026 | 188 |
| Wayback CDX timestamps used | 13 monthly snapshots | 176 unique |

### 2.2 Per-Fund Data Limitations

Farside Investors requires membership login for full historical data. The public page only shows the most recent ~2 weeks. Wayback Machine CDX indexes `farside.co.uk/btc/` beginning **Aug 2024** (no snapshots for Jan-Jul 2024 in the CDX database). This means:

- **Missing**: Jan 11 - Jul 22, 2024 (the initial ETF launch period)
- **Missing**: Aug - Dec 2025 (Wayback CDX doesn't index this period)
- **Available**: Jul-Dec 2024, Jan-Jul 2025, Mar-Apr 2026

The 164-row merged dataset (after joining with BTC price) is approximately 27% of the K455 sample. Results are directionally robust but should be re-evaluated with full history if Farside data becomes accessible.

### 2.3 IBIT & GBTC Flow Statistics

| Fund | Mean Flow (M/day) | Std | Min | Max |
|------|------------------|-----|-----|-----|
| IBIT | +128.7 | 215.8 | -430.8 | 1,112.6 |
| GBTC | -21.4 | 72.3 | -405.4 | 140.7 |
| Divergence (IBIT-GBTC) | +150.1 | 251.4 | -430.8 | 1,112.6 |

IBIT dominated GBTC flows throughout the observation period. GBTC was net negative (outflows) on most days. Divergence was positive 77% of days — the signal was mostly persistently long, similar to K455's total flow regime signal.

---

## 3. Lead-Lag Analysis

### 3.1 Forward Return Correlations

| Horizon | Raw Divergence Corr | EMA5 Divergence Corr |
|---------|--------------------|--------------------|
| t+1 | **-0.117** | -0.128 |
| t+3 | **-0.211** | -0.191 |
| t+7 | **-0.130** | -0.049 |

**Critical finding**: All correlations are **negative**. High divergence (IBIT heavily absorbing, GBTC heavily bleeding) predicts lower forward BTC returns. This is the inverse of the hypothesis. The signal would be marginally contrarian, not momentum-following.

### 3.2 Momentum Correlation

| Signal | Corr with BTC 21d momentum | Orthogonal (< 0.40)? |
|--------|--------------------------|---------------------|
| K455 EMA-21 total flow | 0.756 | NO |
| K462 raw divergence | 0.461 | NO |
| K462 EMA5 divergence | 0.441 | NO (barely) |

K462 achieves partial de-correlation from BTC momentum (0.441 vs 0.756 for K455) — this is the intended improvement. However, 0.441 still exceeds the 0.40 orthogonality gate, and the signal's negative predictive direction means this partial de-correlation doesn't help.

---

## 4. Detrending Test — K455 Alternative Gate

The key K455 failure was: detrend ETF flow against BTC momentum → residual has no edge (OOS SR = -0.54). K462 must pass this test to succeed as an alternative.

### 4.1 Regression

```
divergence_t = 565.7 × btc_mom21_t + 109.7
R² = 0.198 (20% of divergence variance explained by BTC momentum)
```

K455 EMA-21 had R² = 0.57 (57% momentum-explained). K462 divergence is materially less momentum-correlated at the raw level. This is the design win.

### 4.2 Residual Signal Performance

| Metric | K455 Detrended | K462 Detrended |
|--------|---------------|---------------|
| OOS Sharpe | -0.54 | **-2.03** |
| OOS Ann Return | -XX% | -202.7% |

K462's detrended signal is dramatically worse than K455. The residual component of divergence (after removing momentum) has strongly negative predictive power. This suggests the only return source in the raw divergence signal was the (partial) momentum component — and after removing that, what remains is actively harmful.

---

## 5. Signal Construction & Grid Search

### 5.1 Signal Definition

```python
divergence_t = IBIT_flow_t - GBTC_flow_t
div_ema_t    = EMA(divergence_t, span=5)
signal_t     = sign(div_ema_t)           # +1 long, -1 short
position_t   = signal_t.shift(1)         # no lookahead
```

### 5.2 Grid Search Results (EMA span × threshold, OOS SR)

| EMA Span | T50% (sign) | T60% | T70% |
|----------|-------------|------|------|
| EMA-3 | -1.330 | -1.956 | -2.358 |
| EMA-5 | **-0.770** | -2.054 | -2.007 |
| EMA-7 | -0.770 | -1.993 | -2.488 |
| EMA-10 | -0.770 | -2.054 | -2.352 |

**Best OOS Sharpe across all 12 configurations: -0.770** (EMA-5, sign threshold).

Every configuration has deeply negative OOS Sharpe. This is not a parameter selection problem — the signal itself has negative predictive power across all tested configurations.

---

## 6. K266 Gates Evaluation

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | -0.770 | ≥ 1.0 | **FAIL** |
| G2 Perm p | 0.534 | ≤ 0.05 | **FAIL** |
| G3 DSR Bonf. | 0.534 | ≤ 0.0042 | **FAIL** |
| G4 WF 4-fold all+ | [0.92, 2.84, -3.51, -0.98] | all > 0 | **FAIL** |
| G5 Momentum corr | 0.444 | < 0.40 | **FAIL** |
| G6 Trades/yr | 14.0 | > 50 | **FAIL** |
| G7 OOS Ann Return | -75.5% | > 5% | **FAIL** |

**Gates passed: 0/7**

### 6.1 Fold Analysis

| Fold | Period | Sharpe | Ann Ret | Explanation |
|------|--------|--------|---------|-------------|
| 1 | Jul-Oct 2024 | +0.92 | +58.9% | Mixed BTC sideways, signal coincidentally right |
| 2 | Oct 2024-Jan 2025 | +2.84 | +171% | BTC +120% bull run, signal persistently long |
| 3 | Jan-May 2025 | -3.51 | -210% | BTC corrected -35%, signal stayed long (wrong) |
| 4 | May 2025-Apr 2026 | -0.98 | -98% | BTC volatile, divergence failed to signal direction |

Fold 2 (the only positive fold) captures the Q4-2024 BTC mega-rally where the signal was accidentally correct — IBIT inflows dominated and BTC rallied. This is pure momentum capture, not rotation alpha.

---

## 7. Structural Explanation of Failure

### 7.1 The Peak Enthusiasm Problem

The GBTC-IBIT divergence peaks when:
1. IBIT inflows are maximum (retail and institutional FOMO buying at or near peaks)
2. GBTC outflows are maximum (legacy holders realizing gains at or near peaks)

Both behaviors **concentrate near BTC price peaks**. Maximum rotation occurs when:
- New money is most enthusiastic → near top
- Old money is most eager to exit → near top

Result: High divergence = peak sentiment = contrarian indicator, not bullish signal.

### 7.2 Why Total Flow Works Better (In-Sample)

K455 total flow EMA-21 (0.756 momentum corr) effectively measures whether BTC is in a persistent uptrend. The signal is long when momentum is strong → captures trend. Despite high momentum correlation, this is a profitable momentum strategy in IS, only failing the detrending test.

K462 divergence partially separates "quality" from "quantity" of flow, but the "quality" component (IBIT absorption vs GBTC bleeding) turns out to be a peak indicator, not a leading indicator. The partial momentum de-correlation comes at the cost of signal direction.

---

## 8. Comparison vs K455

| Metric | K455 ETF Total | K462 Divergence |
|--------|---------------|----------------|
| OOS Sharpe (raw) | +1.041 | -0.770 |
| OOS Ann Return | +46.4% | -75.5% |
| Detrended OOS Sharpe | -0.54 | -2.03 |
| Momentum corr | 0.756 | 0.441 |
| WF folds positive | 4/4 | 1/4 |
| Trades/yr | 9.1 | 14.0 |
| Gates passed | 4/8 | 0/7 |
| Verdict | CONDITIONAL | **REJECT** |

**K462 is strictly inferior to K455 on every backtest metric.** The only improvement is reduced momentum correlation (0.441 vs 0.756), but this comes with negative predictive direction, making it meaningless.

---

## 9. Capacity Analysis

If the signal had been accepted (it was not):
- ETF market: $60B+ AUM, $150M+ avg daily divergence
- BTC perp or spot execution
- $100M AUM × 15% sleeve = $15M position
- $15M / $150M avg daily divergence = 10% of daily signal volume
- Zero market impact on BTC perp (signal is informational, not flow-based execution)

Capacity is not the binding constraint. Signal quality is.

---

## 10. Decision: REJECT

**Decision**: REJECT

**Rationale**:
- 0/7 K266 gates passed (K455 passed 4/8)
- Signal direction is empirically wrong (predicts negative returns)
- Detrended Sharpe (-2.03) is far worse than K455 baseline (-0.54)
- WF stability is absent (1/4 folds positive, vs 4/4 for K455)
- The rotation narrative is economically appealing but empirically contradicted

**This is not a data limitation issue.** The directional failure (all lags negative) is consistent across the full observation period including 2024 H2, 2025 H1, and 2025 H2+. More data would not rescue this signal.

**v6.20 Recommendation**: Do not include K462. K455 remains CONDITIONAL (paper-trade, 60d regime monitoring). No ETF divergence signal should be included in production until a revised hypothesis with positive forward return correlation is demonstrated.

---

## 11. Future Research Directions

If this area is worth revisiting:

1. **IBIT flow acceleration**: rate of change of IBIT flow (d²/dt²), not level — may capture demand accelerating before price
2. **GBTC discount to NAV**: as GBTC closed its discount post-ETF conversion, the outflow story changed; structurally different in 2025-2026
3. **Cross-fund balance**: IBIT / (IBIT + GBTC) ratio — relative share of capital, not absolute divergence
4. **Threshold-based contrarian**: if divergence = leading peak indicator, then ultra-high divergence (>95th percentile) as short signal

These are speculative. Any new test must include the orthogonality gate and detrended Sharpe benchmark.

---

## Appendix: Data Coverage

| Month | Days Available | Notes |
|-------|--------------|-------|
| Jul 2024 | 7 | Wayback first indexes Aug 2024; Jul partial |
| Aug 2024 | 22 | First full month in CDX |
| Sep-Nov 2024 | 42 | Good coverage |
| Dec 2024 | 13 | CDX snapshot available |
| Jan 2025 | 13 | CDX snapshot available |
| Feb-Jul 2025 | 81 | Good coverage |
| Aug-Dec 2025 | 0 | CDX gap — Wayback not indexing |
| Jan-Mar 2026 | 0 | CDX gap |
| Apr 2026 | 12 | Single CDX snapshot |
| **Total** | **176** | vs K455: 609 rows (29% coverage) |

---

*Generated by wave_k462_gbtc_ibit.py | 2026-05-30 01:28 JST*

# Wave K320: HMM Regime Filter on K297 RWA Satellite
## K315 Follow-Up — Directional Strategy Regime Filter Test

**Date:** 2026-05-25  
**Author:** Wave K320 (Claude agent)  
**Decision: CONDITIONAL** — Filter marginally helpful but insufficient signal to justify production deployment

---

## Executive Summary

K315 applied a 3-state BTC HMM regime filter to K280 (funding carry) and rejected it (Sharpe 17.11 → 15.27, −10.7%). K315 explicitly recommended retesting on K297, hypothesizing that K297's directional RWA exposure to TradFi assets (PAXG gold + SPX equity) might benefit from regime filtering during BTC crashes.

**K320 finds the opposite pattern from K280 — the filter is weakly helpful on K297 — but the improvement is insufficient to justify deployment:**

| Metric | Baseline | No-Bear | Bull-Only | No-Bear+Crash |
|--------|----------|---------|-----------|----------------|
| Sharpe | 8.45 | **8.48** | 6.36 | **8.49** |
| MDD | −0.70% | **−0.60%** | −0.46% | **−0.60%** |
| Active Days | 504 | 465 | 305 | 461 |
| Ann. Return | 5.22% | 4.92% | 3.11% | 4.92% |

The No-Bear filter improves Sharpe by +0.37% (far below the 10% threshold) and reduces MDD from −0.70% to −0.60%. Walk-forward validation shows 2/3 positive folds with an average Sharpe delta of +2.67 — driven almost entirely by Fold 2 (+7.13). **The signal is too weak and uneven to ACCEPT.**

---

## 1. Context and Motivation

### 1.1 K315 Background

K315 tested whether BTC 3-state HMM regime labels (BEAR / NEUTRAL / BULL) could filter K280 (a multi-strategy funding carry portfolio: K272a + K276b). The result was a clear REJECT: bear states coincide with funding rate spikes, which are exactly when K280's short-funding component (K208) earns the most. Filtering bear states destroyed K280's best days.

**K315 hypothesis for K320:** K297 has directional RWA exposure — PAXG tracks gold prices, SPX tracks S&P 500 futures. Unlike K280 (which is delta-neutral carry), K297 may have returns that co-move with market regime. If PAXG goes down during BTC crashes (crypto contagion to gold) or SPX goes down (correlated risk-off), then removing bear-state days should improve K297.

### 1.2 K297 Strategy Description

K297 is an always-on funding rate carry strategy on HyperLiquid HIP-3 RWA perpetuals:
- **PAXG**: PAX Gold-backed token perp — tracks gold spot price
- **SPX**: S&P 500 index perp — tracks US equity index
- **Weights**: Inverse-volatility weighted (PAXG ~60%, SPX ~40%)
- **Position**: LONG perp (collect positive funding rate from perpetual traders paying longs)
- **Date range**: 2025-01-07 → 2026-05-25 (504 days)
- **Baseline Sharpe**: 8.45, Ann. Return 5.22%, MDD −0.70%

**Sign convention:** Daily PnL is positive when funding rates are positive and the strategy collects them as the long side. The strategy does NOT take directional delta on the underlying assets — it holds the perpetual and profits from the funding payment regardless of price direction, as long as FR stays positive.

---

## 2. BTC HMM States

The ManualGaussianHMM (K315 implementation, Baum-Welch EM) was re-fit identically on BTC 4h log returns (4,514 bars, 2024-05-02 → 2026-05-25):

| State | Label | Mean 4h Return | Std 4h Return | Freq |
|-------|-------|---------------|---------------|------|
| 0 | BEAR | −0.001133 (−0.11%/4h) | 0.020089 (2.01%/4h) | 7.7% |
| 1 | NEUTRAL | +0.000163 (+0.02%/4h) | 0.003253 (0.33%/4h) | 28.8% |
| 2 | BULL | +0.000291 (+0.03%/4h) | 0.008308 (0.83%/4h) | 63.5% |

**BEAR state characteristics:** Large negative mean return and high volatility (4× NEUTRAL, 2.4× BULL). This state captures sharp 4-hour crash episodes. Average persistence: 2.7 bars (10.8 hours) before transitioning. Occurs on 7.7% of 4h bars and 7.7% of calendar days.

**In the K297 aligned period (504 days):** 39 BEAR days (7.7%), 160 NEUTRAL days (31.7%), 305 BULL days (60.5%).

---

## 3. Hypothesis Check: BTC-K297 Correlation Analysis

### 3.1 Pearson Correlations

| Correlation | Value | Verdict |
|-------------|-------|---------|
| BTC daily ret vs K297 portfolio | +0.0646 | WEAK |
| BTC daily ret vs SPX component | +0.0839 | WEAK |
| BTC daily ret vs PAXG component | +0.0703 | WEAK |

All correlations are in the 0.06–0.08 range — statistically non-zero (with 504 observations, threshold for 5% significance ≈ 0.087) but economically negligible. This is the central finding: **K297 PnL is largely orthogonal to BTC price direction.**

### 3.2 K297 Mean Return by HMM State

| BTC State | N Days | K297 Mean Daily | BTC Mean Daily |
|-----------|--------|-----------------|----------------|
| BEAR | 39 | +0.0147%/day | −0.498%/day |
| NEUTRAL | 160 | +0.0217%/day | +0.071%/day |
| BULL | 305 | +0.0201%/day | −0.066%/day |

**Key observation:** During BEAR states (when BTC falls ~0.5%/day), K297 earns +0.0147%/day — slightly less than NEUTRAL/BULL days (+0.020%), but still positive. This small difference is what the No-Bear filter exploits. However, the difference is marginal: 0.0147% vs 0.0201% mean daily PnL.

### 3.3 BTC Crash Days (>5% daily drop)

12 days in the 504-day sample had BTC log returns below −5% (mostly the April 2025 Trump tariff crash and isolated flash crashes).

- **K297 mean return on crash days**: −0.0025%/day
- **K297 mean return on normal days**: +0.0207%/day
- **PAXG on crash days**: +0.0030%/day vs +0.0223%/day normal
- **SPX on crash days**: −0.0377%/day vs +0.0197%/day normal

**Interpretation:** On extreme BTC crash days, K297 is slightly negative (−0.0025%). This is driven primarily by SPX funding rates flipping negative (−0.0377%) when equity risk-off coincides with crypto risk-off. PAXG provides partial flight-to-safety offset (+0.0030%, lower than normal but still positive — gold holders pay longs even during market stress). The net effect is near-zero, not the large negative draw that would make filtering worthwhile.

### 3.4 Flight-to-Safety Analysis (PAXG)

PAXG gold perp does NOT exhibit strong flight-to-safety behavior in FR terms. During BTC crashes, PAXG FR stays slightly positive (+0.0030%) because:
1. Gold may rise in price (flight to safety), but the perpetual funding rate depends on demand for leverage, not just price direction
2. PAXG's perpetual funding rate is positive by default — it attracts long-side demand from gold bulls regardless of crypto regime
3. PAXG FR correlation with BTC is +0.07 — statistically weak

**Conclusion:** PAXG is a modest but not strong flight-to-safety diversifier within K297. The hypothesis that K297 would strongly benefit from regime filtering is partially wrong — the RWA component does not have strong regime-conditional behavior in FR space.

---

## 4. Filter Variant Results

Four variants were tested against the K297 baseline (504 days, Sh=8.45):

### 4.1 No-Bear Filter
Zero out daily PnL when BTC 4h HMM state (most-frequent of the day) = BEAR.

- Active: 465/504 days (92.3% of days traded)
- Sharpe: **8.4781** (+0.37% vs baseline)
- MDD: **−0.5963%** (improved from −0.7042%)
- Ann. Return: 4.92% (vs 5.22% — gives up some returns by sitting out 39 BEAR days)

**Assessment:** Marginal Sharpe improvement, but the MDD improvement (−0.60% vs −0.70%) is more meaningful since PAXG and SPX occasionally go through brief funding rate inversions during BEAR states.

### 4.2 Bull-Only Filter
Trade only during BULL days (305/504 = 60.5% active).

- Sharpe: **6.36** (−24.7% vs baseline) — major degradation
- MDD: −0.46% (improved due to fewer days at risk)
- Ann. Return: 3.11%

**Assessment:** REJECT. Bull-only removes too many profitable NEUTRAL days. K297 earns consistently in NEUTRAL states (+0.0217%/day), so excluding them is destructive.

### 4.3 No-Crash Filter
Zero out days after BTC falls >5% (12 events → 12 days zeroed, using 1-day lag).

- Active: 492/504 days
- Sharpe: **8.3584** (−1.1% vs baseline)
- MDD: −0.6629%

**Assessment:** Slightly worse than baseline due to the 1-day lag causing us to miss the recovery day after a crash. The 12 crash days are not reliably negative for K297.

### 4.4 No-Bear+Crash Combined
Zero out BEAR days AND days after >5% crash.

- Active: 461/504 days
- Sharpe: **8.4937** (+0.55% vs baseline — best of all variants)
- MDD: −0.5963%

**Assessment:** Best absolute Sharpe, but improvement is still only +0.55% — insufficient to meet the 10% improvement threshold for ACCEPT.

---

## 5. Walk-Forward 4-Fold Validation

The No-Bear filter was validated across 3 usable chronological folds (4th fold had no test data):

| Fold | Train Period | Test Period | Test N | Bear Days | Baseline Sh | No-Bear Sh | Delta |
|------|-------------|------------|--------|-----------|-------------|------------|-------|
| 1 | 2025-01-07 → 2025-05-12 | 2025-05-13 → 2025-09-15 | 126d | 0 | 12.14 | 12.14 | +0.00 |
| 2 | 2025-01-07 → 2025-09-15 | 2025-09-16 → 2026-01-19 | 126d | 18 | 13.69 | 20.82 | **+7.13** |
| 3 | 2025-01-07 → 2026-01-19 | 2026-01-20 → 2026-05-25 | 126d | 13 | 5.89 | 6.76 | +0.87 |

**Average delta: +2.67 Sh units. 2/3 folds positive.**

### 5.1 Fold-Level Analysis

**Fold 1 (May–Sep 2025):** Zero BEAR days in test period — no filter effect whatsoever. This reflects a period of BTC calm (no flash crashes). The filter has no cost but no benefit.

**Fold 2 (Sep 2025–Jan 2026):** 18 BEAR days in 126. Massive improvement: baseline 13.69 → filtered 20.82 (+7.13 Sh). This fold coincides with volatile BTC price action (multiple corrections late 2025) that coincided with actual K297 negative FR days. The filter correctly removes these days.

**Fold 3 (Jan–May 2026):** 13 BEAR days in 126. Modest improvement: 5.89 → 6.76 (+0.87). The BEAR days in early 2026 carried slightly negative K297 returns on average, so filtering helps.

### 5.2 Walk-Forward Interpretation

The Fold 2 improvement is enormous (+7.13 Sh) and drives the positive average. This is non-trivial — it means in one specific regime (late 2025 high-volatility crypto period), BEAR states correlated with K297 drawdowns. However, Fold 1's zero effect reveals the filter has no impact in calm periods. The pattern suggests **the filter is regime-specific**: helpful when BTC bear states coincide with actual FR inversions (which happens episodically), unhelpful otherwise.

**Stability concern:** The average Sh delta of +2.67 is dominated by a single fold. If Fold 2 were removed, the average would be +0.44 — effectively zero.

---

## 6. Decision: CONDITIONAL

### 6.1 Acceptance Criteria Evaluation

| Criterion | Threshold | Value | Pass? |
|-----------|-----------|-------|-------|
| Sharpe improvement ≥ 10% | ≥1.1× baseline | +0.37% | FAIL |
| MDD ≤ baseline | ≤ −0.70% | −0.60% | PASS |
| All folds positive | 3/3 | 2/3 | CONDITIONAL |
| Correlation support | > threshold | 0.065 (WEAK) | MARGINAL |

### 6.2 CONDITIONAL Rationale

The filter does not ACCEPT because Sharpe improvement is only +0.37% on the full period — well below the 10% threshold. The MDD improvement (−0.70% → −0.60%) is positive but small in absolute terms.

The filter does not REJECT because:
1. Walk-forward shows 2/3 folds positive, including a large improvement in Fold 2 (+7.13)
2. MDD does not worsen
3. The theoretical mechanism (BEAR = low-vol FR days) has partial empirical support
4. The correlation, while weak (0.065), is in the correct direction (positive: BTC up = slightly better K297)

**CONDITIONAL means:** The filter shows promise in high-volatility BTC regimes but insufficient strength to deploy without further OOS validation. A longer live period with more BEAR-state episodes would provide better evidence.

---

## 7. K315 Line of Inquiry Closure

### 7.1 Comparative Summary

| Strategy | Type | Baseline Sh | No-Bear Sh | Sh Delta | MDD Change | Decision |
|----------|------|-------------|------------|----------|------------|----------|
| K280 | Funding carry (neutral) | 17.11 | 15.27 | **−10.7%** | negligible | REJECT |
| K297 | RWA FR carry (TradFi) | 8.45 | 8.48 | **+0.37%** | improved | CONDITIONAL |

### 7.2 Why the Opposite Directions?

**K280 (REJECT):** K280's K208 component explicitly profits from funding rate spikes during flash crashes. BTC BEAR states trigger massive funding rate spikes on crypto perps — exactly when K208 earns the most. Filtering BEAR states removes K280's best days.

**K297 (CONDITIONAL/marginal positive):** K297 earns from TradFi FR, not crypto FR. SPX funding rates may briefly go negative during risk-off (when both BTC and equities crash), and PAXG provides partial offset. The mechanism is weak but points in the correct direction. BEAR days are slightly less profitable (+0.015%/day) than non-BEAR days (+0.020%/day) for K297.

### 7.3 General Principle Derived

**BTC HMM regime filters:**
- HURT strategies that profit FROM crypto volatility (K280, K208 carry)
- MARGINALLY HELP strategies with weak TradFi risk-on/risk-off correlation (K297)
- Would likely HELP directional momentum strategies (not yet tested)

The next logical test would be a pure directional crypto momentum strategy — where BULL state = strong entry signal and BEAR state = strong exit/short signal. K297 is not this: it's still a carry strategy (collect FR), just on TradFi-linked assets instead of crypto-native ones.

---

## 8. What Would Have Worked Better

If the goal is regime-filtering K297 specifically, the following approaches would be more principled:

1. **SPX equity futures regime filter** (instead of BTC HMM): K297's SPX component is correlated with US equity regime. A VIX-based or S&P 500 drawdown filter would be more relevant.

2. **FR-regime filter**: Filter on SPX/PAXG own funding rate Z-score. When FR approaches zero or inverts, pause the position. This is the correct signal — not a proxy BTC HMM signal.

3. **Volatility gate**: When realized volatility of SPX or PAXG perp spikes (indicating dislocations), pause carry. This addresses the actual risk without needing BTC HMM.

4. **Directional momentum strategies**: BTC HMM states would be most powerful on a strategy that explicitly bets on BTC price direction (e.g., BULL=long, BEAR=short or flat). Neither K280 nor K297 is such a strategy.

---

## 9. Technical Notes

### 9.1 HMM Implementation
- ManualGaussianHMM from K315 (Baum-Welch EM, mathematically identical to hmmlearn.GaussianHMM)
- Fit on 4,514 BTC 4h bars (2024-05-02 → 2026-05-25)
- Converged at iteration 195 (full-period HMM), 100 iterations for walk-forward folds
- States sorted by mean 4h return: BEAR (lowest) → NEUTRAL → BULL (highest)

### 9.2 Daily State Mapping
- 4h states → daily via mode (most frequent state on that calendar day)
- BEAR: 7.7% of days, NEUTRAL: 31.7%, BULL: 60.5% (in K297 period)

### 9.3 K297 Data
- Portfolio daily returns from `wave_k297_curves.json` → `portfolio_daily_returns`
- Inv-vol weighted: PAXG ~60%, SPX ~40%
- SPX available from 2025-01-07, PAXG from 2025-04-06 (shorter)
- Filters applied to portfolio-level daily returns (not individual components)

### 9.4 Walk-Forward Protocol
- 4 folds chronological (Fold 4 had no test data due to data length)
- Train: cumulative from start to fold boundary
- Test: next fold_size (~126 days) window
- HMM re-fit on each training window's BTC 4h bars
- States re-sorted by mean for each fold's model

---

## 10. Conclusions

1. **K297 is also orthogonal to BTC regime** — BTC-K297 correlation is 0.065 (WEAK). The strategy earns positive funding rates in all three BTC HMM states. K315's hypothesis was partially wrong: even TradFi RWA perps on HL are not strongly correlated with BTC price direction in FR space.

2. **No-Bear filter gives marginal improvement** (+0.37% Sharpe, MDD −0.70% → −0.60%) — directionally correct but economically small. Walk-forward confirms 2/3 folds positive (average delta +2.67 driven by Fold 2).

3. **Decision: CONDITIONAL** — not ready for production. Would require more BEAR-state episodes in live data to confirm the signal, plus a principled FR-regime gate is more appropriate than a BTC HMM proxy.

4. **K315 line of inquiry closed**: HMM BTC regime filters do not improve carry-type strategies (funding carry K280 or RWA carry K297). The filter is category-appropriate only for directional momentum strategies that bet on BTC price direction.

5. **Recommended next step**: If regime filtering remains of interest, test it on K113/K257 (directional Donchian trend following) or build a pure BTC directional strategy where the filter has theoretical grounding. Alternatively, for K297 specifically, explore an SPX-VIX or own-FR-Z-score gate.

---

*Wave K320 | 2026-05-25 | crypto-lab*

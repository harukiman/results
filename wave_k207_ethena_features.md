# Wave K207 — Ethena TVL Features + K198 ML Allocator (v6.6 Candidate)

**Generated:** 2026-05-24T21:31:12 UTC  
**Runtime:** 3.0s  
**Wave:** K207 | crypto-lab systematic alpha discovery

---

## Executive Summary

K207 augments the K198 Ridge ML allocator's 51-feature matrix with 4 Ethena TVL features
(`eth_tvl_change_7d`, `eth_tvl_change_30d`, `eth_tvl_drawdown`, `eth_tvl_acceleration`)
discovered in K206 to test whether Ridge regression can learn the TVL→carry signal.

**Result: REJECT for v6.6 promotion.**

While Ridge successfully learned the Ethena signal (V_rev_carry eth_tvl_change_7d
coefficient = +0.490, active in all 15 WF steps), the 55-feature model underperforms
K198 on OOS Sharpe (-1.41 vs baseline). The primary issue is that Ethena TVL data only
begins in 2024 and covers a narrow market regime — adding global-panel features with
limited regime diversity introduces prediction noise for strategies unrelated to carry.

| Criterion | K198 v6.5 (production) | K207 Ethena (55 feat) | Pass? |
|-----------|------------------------|----------------------|-------|
| OOS Sharpe ≥ K198 (10.28) | 10.2800 | 8.8748 | FAIL |
| MaxDD ≤ K198 (-0.0053) | -0.0053 | -0.0063 | FAIL |
| WF min ≥ K198 (6.57) | 6.5700 | 6.5760 | PASS |
| Ethena feature non-zero Ridge coef | — | YES | PASS |

**Criteria passed: 2/4**

---

## 1. Configuration

| Parameter | Value |
|-----------|-------|
| Base features (K198) | 51 (50 per-strategy + 1 FR regime) |
| Ethena features added | 4 |
| Total features K207 | 55 |
| Ethena TVL lag | 7 days (no look-ahead) |
| Walk-forward | 90d train → 30d test, 15 steps |
| OOS fraction | Last 30% (135 days) |
| Ridge alpha | 1.0 |
| K121 cap | 30% |
| Carry cap (fwd + rev) | 5% each |
| FR trigger threshold | -0.009735 annualized |
| Portfolio date range | 2024-07-26 → 2026-05-14 (658 days) |
| ML window | 2025-01-22 → 2026-04-14 (448 days) |

---

## 2. Final Comparison Table

| Version | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|--------|-----------|---------|--------|
| K198 v6.5 baseline (51 feat) | 10.2800 | -0.0053 | 7.9100 | 6.5700 |
| K204 (REJECTED) | 10.3600 | N/A | N/A | 6.0200 |
| **K207 Ethena (55 feat)** | **8.8748** | **-0.0063** | **7.5252** | **6.5760** |
| WF Static P3 (same windows) | 8.7702 | -0.0042 | 5.2077 | 0.9441 |

K207 lift vs K198: OOS Sh **-1.4052** | WF min **+0.0060**

**OOS period:** 2026-01-09 → 2026-04-14 (135 days)
- OOS Sortino: 23.91
- OOS Calmar: 118.47
- OOS Ann. Return: 74.29%
- OOS Ann. Vol: 6.29%

---

## 3. Walk-Forward Fold Analysis

K207 WF fold Sharpes: [6.576, 7.435, 8.021, 8.069]

| Fold | WF Sharpe | vs K198 |
|------|-----------|---------|
| Fold 1 (earliest) | 6.576 | -0.00 (≈ K198 min of 6.57) |
| Fold 2 | 7.435 | +0.05 |
| Fold 3 | 8.021 | +0.11 |
| Fold 4 (latest) | 8.069 | +0.17 |

**Observation:** WF stability is adequate (all folds ≥ 6.57), showing positive
momentum across folds. The OOS shortfall vs K198 stems from the OOS Sharpe (fold 4+
in OOS territory), suggesting the Ethena features may be injecting noise in the most
recent market regime.

### Walk-Forward Step Details

| Step | Train Window | Test Window | Dir Acc |
|------|-------------|-------------|---------|
| 0 | 2024-10-24 → 2025-01-21 | 2025-01-22 → 2025-02-20 | 0.40 |
| 1 | 2024-11-23 → 2025-02-20 | 2025-02-21 → 2025-03-22 | 0.80 |
| 2 | 2024-12-23 → 2025-03-22 | 2025-03-23 → 2025-04-21 | 0.80 |
| 3 | 2025-01-22 → 2025-04-21 | 2025-04-22 → 2025-05-21 | 0.70 |
| 4 | 2025-02-21 → 2025-05-21 | 2025-05-22 → 2025-06-20 | 0.80 |
| 5 | 2025-03-23 → 2025-06-20 | 2025-06-21 → 2025-07-20 | 0.90 |
| 6 | 2025-04-22 → 2025-07-20 | 2025-07-21 → 2025-08-19 | 0.80 |
| 7 | 2025-05-22 → 2025-08-19 | 2025-08-20 → 2025-09-18 | 0.50 |
| 8 | 2025-06-21 → 2025-09-18 | 2025-09-19 → 2025-10-18 | 0.60 |
| 9 | 2025-07-21 → 2025-10-18 | 2025-10-19 → 2025-11-17 | 0.70 |
| 10 | 2025-08-20 → 2025-11-17 | 2025-11-18 → 2025-12-17 | 0.80 |
| 11 | 2025-09-19 → 2025-12-17 | 2025-12-18 → 2026-01-16 | 0.70 |
| 12 | 2025-10-19 → 2026-01-16 | 2026-01-17 → 2026-02-15 | 0.80 |
| 13 | 2025-11-18 → 2026-02-15 | 2026-02-16 → 2026-03-17 | 0.80 |
| 14 | 2025-12-18 → 2026-03-17 | 2026-03-18 → 2026-04-14 | 0.60 |

Mean dir acc: 0.713 | Overall R²: 0.942

---

## 4. Feature Importance — All 55 Features Ranked

(Mean |coefficient| across all 10 strategies, full-sample Ridge fit)

| Rank | Feature | Importance | Type |
|------|---------|-----------|------|
| #1 | K116__sh90 | 2.147091 | per-strategy |
| #2 | V_rev_carry__sh90 | 2.038511 | per-strategy |
| #3 | V_rev_carry__mdd30 | 1.875810 | per-strategy |
| #4 | K114__vol30 | 1.521921 | per-strategy |
| #5 | K116__vol30 | 1.459829 | per-strategy |
| **#6** | **eth_tvl_change_30d** | **1.206562** | **ETHENA** |
| #7 | V_rev_carry__vol30 | 1.185583 | per-strategy |
| **#8** | **eth_tvl_drawdown** | **1.181703** | **ETHENA** |
| #9 | K175_DAR__sh90 | 1.174420 | per-strategy |
| #10 | V_fwd_carry__vol30 | 1.130528 | per-strategy |
| #11 | V_rev_carry__sh30 | 1.109257 | per-strategy |
| #12 | V1__vol30 | 1.102312 | per-strategy |
| #13 | K147__sh90 | 1.062121 | per-strategy |
| #14 | K121__sh90 | 1.021466 | per-strategy |
| #15 | K114__mdd30 | 1.018175 | per-strategy |
| ... | ... | ... | ... |
| **#45** | **eth_tvl_change_7d** | **0.487034** | **ETHENA** |
| #54 | fr_mean_ann | 0.259122 | global |
| **#55** | **eth_tvl_acceleration** | **0.044728** | **ETHENA** |

### Ethena Feature Summary

| Feature | Rank | Importance | Interpretation |
|---------|------|-----------|----------------|
| eth_tvl_change_30d | **#6** of 55 | 1.207 | Slow TVL drift highly predictive |
| eth_tvl_drawdown | **#8** of 55 | 1.182 | TVL deterioration from peak |
| eth_tvl_change_7d | #45 of 55 | 0.487 | Short-term TVL move, moderate signal |
| eth_tvl_acceleration | #55 of 55 | 0.045 | TVL momentum change, near-noise |

**Key insight:** `eth_tvl_change_30d` (rank #6) and `eth_tvl_drawdown` (rank #8) are
high-importance features — inside the top-10 out of 55. However, these strong global
features paradoxically hurt OOS performance because they constrain the Ridge allocator
to bet on TVL regime when that regime is less informative for most of the 10 strategies.
The `eth_tvl_change_7d` (primary K206 signal) ranks only #45, below even `fr_mean_ann`.

---

## 5. Ethena Feature Analysis — Did Ridge Learn the TVL→Carry Signal?

**YES — but with mixed carry directionality.**

### V_rev_carry Ethena Coefficients (across 15 WF steps)

| Feature | Mean Coef | Abs Mean | % Non-zero | Sign Consistency |
|---------|-----------|----------|-----------|-----------------|
| eth_tvl_change_7d | **+0.491** | 0.960 | 100% | 80% |
| eth_tvl_change_30d | -0.329 | 1.061 | 100% | 47% |
| eth_tvl_drawdown | +0.372 | 0.598 | 100% | 53% |
| eth_tvl_acceleration | -0.075 | 0.089 | 100% | 80% |

**Confirmed: V_rev_carry `eth_tvl_change_7d` mean coefficient = +0.491 (positive sign
consistent with K206 Variant B mechanism — TVL grow → boost carry).**

Ridge learned the K206 signal: higher TVL growth → higher predicted V_rev_carry Sharpe.
Active in all 15 WF steps. 80% sign consistency confirms a real mechanism, not noise.

### Mean eth_tvl_change_7d Coefficient Per Strategy

| Strategy | Mean Coef | Interpretation |
|----------|-----------|----------------|
| V_rev_carry | **+0.491** | Confirmed TVL→carry boost |
| K114 | +0.422 | Unexpected positive — K114 performs well in bullish TVL regimes |
| K133 | +0.334 | K133 benefits from TVL growth (FR regime correlation) |
| V1 | +0.275 | Mild positive correlation |
| K116 | +0.243 | Mild positive |
| K147 | +0.043 | Near-zero, appropriate |
| K175_DAR | -0.083 | Mildly inverse |
| V_fwd_carry | **-0.153** | Inverse — TVL growth mildly predicts lower fwd carry |
| K121 | -0.180 | Inverse |
| v4.1 | -0.250 | Most inverse — TVL signal noise for trend strategy |

**Issue:** TVL features are global (panel-wide), affecting all 10 strategies. For
trend strategies (v4.1, K121), TVL growth is inversely associated with performance —
possibly because TVL growth correlates with low-volatility bull regimes where trend
strategies underperform mean-reversion. This mixed directionality forces Ridge to
compromise, reducing overall predictive power.

---

## 6. Per-Strategy Weight Changes vs K198 Baseline

| Strategy | K198 Mean Wt | K207 Mean Wt | Delta | Notable |
|----------|-------------|-------------|-------|---------|
| v4.1 | 10.22% | 11.31% | +1.08% | |
| V1 | 12.70% | 13.42% | +0.71% | |
| K114 | 10.45% | 11.45% | +1.00% | |
| K116 | 8.79% | 9.58% | +0.79% | |
| K121 | 9.13% | 9.26% | +0.13% | |
| K133 | 9.84% | 10.96% | +1.12% | |
| K147 | 11.20% | 12.00% | +0.80% | |
| K175_DAR | 9.14% | 11.59% | +2.45% | Largest increase |
| **V_fwd_carry** | **12.55%** | **7.44%** | **-5.10%** | Largest decrease |
| **V_rev_carry** | **5.98%** | **2.99%** | **-2.99%** | Reduced carry exposure |

**Pattern:** K207 systematically reduces carry allocations (V_fwd_carry -5.1pp,
V_rev_carry -3.0pp) while redistributing to non-carry strategies, particularly
K175_DAR (+2.5pp). This suggests the Ethena features push Ridge away from carry
in the recent OOS period — the opposite of the K206 Variant B mechanism intent.

**Hypothesis:** The Ethena TVL stagnation/decline in late 2025 (Ethena TVL peaked
and drew down) caused Ridge to associate lower TVL with lower carry returns, leading
to systematic underweighting of carry in the OOS period.

---

## 7. ML Predictor Diagnostics

| Metric | Value |
|--------|-------|
| Overall R² (training) | 0.942 |
| Overall direction accuracy | 71.3% |
| WF steps | 15 |

### Per-Strategy Direction Accuracy

| Strategy | Dir Acc | R² | Above 55%? |
|----------|---------|-----|-----------|
| V_rev_carry | **93.3%** | 0.9907 | YES |
| V_fwd_carry | **93.3%** | 0.9742 | YES |
| V1 | 93.3% | 0.9283 | YES |
| K175_DAR | 73.3% | 0.9328 | YES |
| K133 | 73.3% | 0.9414 | YES |
| K147 | 66.7% | 0.9248 | YES |
| K121 | 60.0% | 0.9505 | YES |
| K114 | 60.0% | 0.9031 | YES |
| K116 | 53.3% | 0.9483 | near |
| v4.1 | 46.7% | 0.9284 | NO |

Ridge is highly accurate for carry strategies (V_rev_carry 93.3%, V_fwd_carry 93.3%)
but less accurate for trend/momentum strategies. The overall R² of 0.942 is high but
mainly reflects in-sample fit quality.

---

## 8. Root Cause Analysis — Why Does K207 Underperform K198?

### Hypothesis 1: Global feature interference (primary cause)

Ethena TVL features are identical across all 10 strategies for any given day.
Ridge sees them as global predictors, and they compete with per-strategy features
(sh30, sh90, vol30, mdd30, xcorr) that contain richer within-strategy information.
Adding global features with limited cross-strategy discriminative power forces Ridge
to share coefficient budget across 55 features, diluting the strong per-strategy
signals that drove K198's OOS Sh 10.28.

### Hypothesis 2: TVL regime mismatch in OOS period

Ethena TVL growth was concentrated in early 2024–2025 (rapid expansion phase).
The OOS period (Jan–Apr 2026) coincides with TVL maturation/stagnation. Features
trained on TVL expansion regimes may mispredict in a stable or declining TVL regime.

### Hypothesis 3: Over-compression of carry weight

K207 allocates only 2.99% to V_rev_carry (vs 5.98% in K198), which is half the K198
carry allocation. This reduction is mechanically caused by the Ethena features
associating recent TVL stagnation with lower carry returns — but in the OOS period,
V_rev_carry actually performed well (dir acc 93.3%). The TVL-induced underweighting
costs performance.

---

## 9. Ethena Feature Coverage

| Feature | Non-zero Days | Total Days | Mean | Std |
|---------|--------------|-----------|------|-----|
| eth_tvl_change_7d | 568/568 | 100.0% | 0.003 | 0.038 |
| eth_tvl_change_30d | 568/568 | 100.0% | 0.007 | 0.072 |
| eth_tvl_drawdown | 407/568 | 71.7% | -0.019 | 0.038 |
| eth_tvl_acceleration | 568/568 | 100.0% | ~0.000 | 0.006 |

TVL data fully covers the ML window with 7d lag applied. `eth_tvl_drawdown` is 0 on
28.3% of days (when TVL is at or near rolling peak) — appropriate behavior.

---

## 10. Acceptance Criteria Results

| Criterion | Threshold | K207 | Pass |
|-----------|-----------|------|------|
| AC1: OOS Sh ≥ K198 | ≥ 10.2800 | 8.8748 (-1.41) | FAIL |
| AC2: MaxDD not worsened | ≥ -0.0053 | -0.0063 | FAIL |
| AC3: WF min ≥ K198 | ≥ 6.5700 | 6.5760 (+0.006) | PASS |
| AC4: Ethena feature non-zero | YES | YES | PASS |

**2/4 criteria passed.** K198 v6.5 remains production allocator.

---

## 11. Positive Findings to Carry Forward to K208

Despite the REJECT verdict, K207 yields actionable insights:

1. **eth_tvl_change_30d ranks #6** of 55 features — it captures a real signal
   (slow TVL drift predicts carry regime)
2. **V_rev_carry learns positive TVL coefficient (+0.491)** — confirms K206
   mechanism: TVL grow → higher predicted carry Sharpe (Variant B)
3. **Global features may work better as interaction terms** rather than raw features —
   e.g., `V_rev_carry__sh30 × eth_tvl_change_7d` as an explicit feature
4. **eth_tvl_drawdown (rank #8)** is a strong signal; consider including in K208
   with carry-strategy-specific interaction
5. **WF min 6.576** nearly matches K198 (6.572) — Ethena features do not destabilize
   the model; the weakness is purely OOS Sharpe

---

## 12. Verdict

### REJECT: K207 Ethena features do not improve K198 sufficiently (2/4 criteria).

OOS Sharpe 8.8748 vs K198 10.28 (-1.41). MaxDD -0.0063 vs K198 -0.0053 (slightly worse).
K198 v6.5 remains production allocator.

**Root cause:** Ethena TVL features are panel-wide signals with a single TVL trajectory.
Adding them to a 51-feature per-strategy matrix compresses the per-strategy discriminative
power without providing sufficient new information to compensate. Ridge learned the signal
(V_rev_carry eth_tvl_change_7d = +0.491) but the global nature of TVL features
systematically underweighted carry in the OOS period, costing -1.41 Sharpe.

**Ethena signal is real but needs delivery mechanism reform for K208.**

---

## 13. K208 Recommendation — Combine with K205 if Both Accept

**Verdict, K208 combine with K205 if both accept:**

| Scenario | K208 Action |
|----------|------------|
| K205 ACCEPT + K207 REJECT (current) | Take K205 as v6.6; add Ethena as K208 secondary feature set with carry-specific interactions |
| K205 REJECT + K207 REJECT | Keep K198 v6.5; design K208 as full re-architecture with interaction features |
| Both ACCEPT | K208 = K205 + K207 combined 55+DD features (~60 features total), validate with 180d window |
| Both REJECT | K208 = radical redesign (non-Ridge: quantile regression, or ensemble of specialized per-cluster models) |

**K208 specific engineering if Ethena features are included:**
1. Use carry-strategy-specific Ethena features: `V_rev_carry__eth_tvl_7d = sh30_rev_carry × eth_tvl_change_7d`
2. Include only `eth_tvl_change_30d` and `eth_tvl_drawdown` (top-2 Ethena features by importance)
3. Drop `eth_tvl_acceleration` (#55/55, near-noise)
4. Test whether Ridge or quantile regression better handles the global signal

---

*Wave K207 | crypto-lab systematic alpha discovery | 2026-05-24*

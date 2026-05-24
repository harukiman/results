# Wave K210 — K198 v6.5 + K208-Filtered V_rev_carry Integration
## Full Report: v6.6 Candidate Assessment

**Date:** 2026-05-25  
**Objective:** Replace K198's unfiltered V_rev_carry slot with the K208 DAR(2,1)-filtered version. Evaluate ensemble-level lift at two carry cap levels (10% vs 15%).

---

## Executive Summary

K210 **REJECTED for v6.6 promotion.** Replacing K198's V_rev_carry with the K208-filtered version degrades OOS Sharpe from 10.28 to 8.06–8.34, despite improving walk-forward stability (WF min: 6.57 → 6.99–7.04). The root cause is period-specific: in the K198 OOS window (last 135 days of the 448-day WF period), the unfiltered K196 V_rev_carry delivered a Sharpe of ~10.2, making it an excellent contributor. The K208 DAR filter, which reduces in-market participation by ~60%, removes these profitable events in a high-carry regime — net harm to the ensemble. K198 v6.5 remains production.

**Key finding:** WF minimum is meaningfully better in K210 (6.99–7.04 vs 6.57), confirming K208 filter improves worst-case stability. But the OOS period happened to coincide with a bull carry environment where filtering hurts.

---

## Comparison Table

| Version | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|--------|-----------|---------|--------|
| **K198 v6.5 baseline** | **10.28** | **-0.0053** | **7.91** | **6.57** |
| K210a (cap=10%, K208-filtered) | 8.06 | -0.0053 | 7.48 | **7.00** |
| K210b (cap=15%, K208-filtered) | 8.34 | **-0.0050** | 7.59 | **7.04** |

*Acceptance gate: OOS Sh > 10.38 (+0.10 vs K198), MaxDD ≥ -0.0053, WF min ≥ 6.57.*

---

## 1. K208 Filter Applied in K210 Context

### DAR(2,1) Per-Symbol Direction Accuracy

All 9 DAR-filtered symbols show strong direction accuracy (65–72%), confirming the predictor is valid:

| Symbol | Dir Acc | In-Market | Events Filtered |
|--------|---------|-----------|----------------|
| SOL | 68.5% | 27% | 73% |
| XRP | 65.9% | 26% | 74% |
| SUI | 66.7% | 34% | 66% |
| OP | 68.9% | 41% | 59% |
| APT | 65.8% | 33% | 67% |
| JTO | 70.1% | 32% | 68% |
| IMX | 70.2% | 37% | 63% |
| SAND | 71.8% | 37% | 63% |
| ADA | 68.8% | 38% | 62% |
| AXS | always-on | 100% | 0% |

**Average in-market participation: 40.4%** (filtering out ~60% of 8h events).

### K208-Filtered V_rev_carry Daily Sharpe in K210 Context

The filtered reverse carry component, when aggregated to daily returns, achieves a Sharpe of **7.70** over the WF period. This is worse than the K196 unfiltered reverse carry in the OOS window (Sharpe ~10.2), which explains the ensemble degradation.

---

## 2. Acceptance Criteria Evaluation

### K210a (carry_rev_cap = 10%)

| Criterion | Threshold | Actual | Result |
|-----------|-----------|--------|--------|
| AC1: OOS Sh > 10.38 | > 10.38 | 8.06 | **FAIL** |
| AC2: MaxDD ≥ -0.0053 | ≥ -0.0053 | -0.0053 | PASS |
| AC3: WF min ≥ 6.57 | ≥ 6.57 | 7.00 | PASS |

**Result: 2/3 criteria pass → REJECT**

### K210b (carry_rev_cap = 15%)

| Criterion | Threshold | Actual | Result |
|-----------|-----------|--------|--------|
| AC1: OOS Sh > 10.38 | > 10.38 | 8.34 | **FAIL** |
| AC2: MaxDD ≥ -0.0053 | ≥ -0.0053 | -0.0050 | PASS |
| AC3: WF min ≥ 6.57 | ≥ 6.57 | 7.04 | PASS |

**Result: 2/3 criteria pass → REJECT**

---

## 3. Per-Fold Breakdown

| Fold | K198 v6.5 | K210a (10%) | K210b (15%) |
|------|-----------|-------------|-------------|
| 1 | 6.57 | 7.00 | 7.04 |
| 2 | 7.38 | 7.72 | 7.71 |
| 3 | 7.94 | 8.17 | 8.22 |
| 4 | **9.75** | **7.04** | **7.36** |
| **mean** | 7.91 | 7.48 | 7.59 |
| **min** | 6.57 | 7.00 | 7.04 |

**Key observation:**
- K210 is more uniformly distributed across folds (min 7.00–7.04, max 8.22)
- K198 is "J-shaped" — weak fold 1, excellent fold 4 (9.75)
- K210's fold 4 drops significantly vs K198 (7.04–7.36 vs 9.75) — the K208 filter cost in the high-carry OOS period
- K210 improves fold 1 (weakest in K198), conferring better WF stability
- Net WF mean: K210 slightly lower (7.48–7.59 vs 7.91)

---

## 4. Root Cause Analysis: Why K210 OOS Sharpe is Lower

### The Bull Carry Problem

The K198 OOS window (last 135 days) coincided with a **high-carry regime** where the unfiltered K196 V_rev_carry delivered exceptional returns (daily Sharpe ~10.2). The K208 DAR filter, designed to avoid adverse carry events, reduced in-market participation to ~40%. In this regime, the filter was removing profitable events — net harm.

### Expected vs Actual Ensemble Lift

| Metric | Value |
|--------|-------|
| K208 standalone lift vs K196 (8h basis) | +8.33 Sharpe points |
| Avg V_rev_carry weight in K210a | 8.66% |
| Expected ensemble lift K210a | ~+0.72 Sharpe points |
| Avg V_rev_carry weight in K210b | 13.0% |
| Expected ensemble lift K210b | ~+1.08 Sharpe points |
| **Actual ensemble change K210a** | **-2.22 Sharpe points** |
| **Actual ensemble change K210b** | **-1.94 Sharpe points** |

### Why the gap?

1. **Annualisation basis mismatch:** K208 standalone Sharpe of 17.53 uses 8h-event annualisation (×1095). K210 ensemble uses daily annualisation (×365). The K208 filtered component's daily Sharpe is 7.70 — plausible but substantially lower than the 8h headline figure.

2. **Period mismatch:** K208's standalone OOS period starts earlier and includes a period when the DAR filter adds genuine value (spread sign prediction catches reversals). K210's OOS window (Jan–Apr 2026) was a sustained positive-spread period where always-on outperforms filtered.

3. **V_rev_carry weight is small but the harm is concentrated:** The ML allocator allocated ~8.7–13% to V_rev_carry. In absolute return terms, the K208-filtered component earns ~2.2% less in OOS than the K196 unfiltered would have. Multiplied by ~10% weight, the raw drag is ~0.22%, which translates to ~-2.2 Sharpe points in the OOS window.

---

## 5. K208 Standalone vs K210 Ensemble Lift Attribution

| Metric | K208 Standalone | K210a Ensemble | K210b Ensemble |
|--------|-----------------|----------------|----------------|
| OOS Sharpe | 17.53 (8h basis) | 8.06 (daily) | 8.34 (daily) |
| MaxDD OOS | -0.0003 | -0.0053 | -0.0050 |
| WF min | 7.39 (8h) | 7.00 (daily) | 7.04 (daily) |
| V_rev_carry avg weight | 100% (standalone) | 8.66% | 13.0% |
| V_rev_carry daily Sharpe | 7.70 | 7.70 | 7.70 |
| Ensemble delta OOS Sh | — | -2.22 vs K198 | -1.94 vs K198 |

**Interpretation:** K208 is a strong standalone filter at the 8h event level. Its lift is real — direction accuracy 65–72% across all symbols, and the standalone OOS Sh 17.53 vs K196 baseline 9.20 (+8.33) is genuine. However, at the ensemble level with ~10% weight, the filtered component delivers a daily Sharpe of 7.70 vs the K196 unfiltered component's OOS daily Sharpe of ~10.2. The ensemble-level damage is ~(-2.5 Sharpe × 9%) ≈ -0.22 return units, which in the short OOS window (135 days) compounds to a large Sharpe degradation.

---

## 6. Positive Findings from K210

Despite the REJECT verdict, K210 surfaces meaningful structural insights:

1. **WF stability improvement is real:** WF min improves from 6.57 → 7.00–7.04 (+0.43–0.47). This means K208 filter makes the ensemble MORE consistent across folds, reducing tail-risk of weak quarters.

2. **DAR direction accuracy holds:** All 9 filtered symbols maintain 65–72% direction accuracy in K210's alignment window. The filter model is robust.

3. **MaxDD is preserved or improved:** K210b MaxDD (-0.0050) is marginally better than K198 (-0.0053). The filter does reduce drawdown risk.

4. **The WF fold structure reveals a K198 concentration risk:** K198's fold 4 Sharpe (9.75) is an outlier driven by a high-carry OOS period. K210 smooths this, suggesting K198's OOS Sh headline may be partially explained by a single lucky-carry regime. K210 is a more honest forward estimate.

5. **AXS always-on is justified:** AXS has only 379 8h events — insufficient for DAR. Keeping it always-on (which K208 recommends) is correct.

---

## 7. Verdict: K210 v6.6 — REJECT

**Decision: REJECT. K198 v6.5 remains production.**

Neither K210a (OOS Sh 8.06) nor K210b (OOS Sh 8.34) meets the OOS Sharpe hurdle (>10.38). The 15% cap variant has marginally better MaxDD (-0.0050 vs -0.0053) and better WF stability, but the OOS Sh gap (-1.94 vs baseline) is decisive.

### Root cause is period-specific, not structural failure

The K208 filter is directionally sound. The issue is that in the K198 OOS window, reverse carry was in a sustained high-spread regime where filtering is suboptimal. This is a form of **selective attrition bias**: K208 was tested on its own panel which included historical periods where filtering helped; K210's OOS window happens to be one where it doesn't.

### Path to v6.6 — Recommended Next Steps

1. **K211 — Regime-conditioned K208 activation:** Turn on the K208 DAR filter only when FR spread z-score is below some threshold (e.g., spread is low/negative). In positive-spread regimes, revert to always-on. This preserves K208's benefit during adverse carry periods without sacrificing bull-carry returns.

2. **K212 — Weight floor for V_rev_carry:** In the current K198 ML allocator, V_rev_carry weight is ~8.7–13%. Consider adding a weight floor of 5% minimum to ensure the component contributes meaningfully. Currently the ML model may underweight it at exactly the wrong times.

3. **K213 — Extended window test:** Re-run K210 with the common data window extended to include the full K208 IS period (pre-2024). If K208 filter is genuinely additive, it should show lift over a longer history.

4. **Forward paper-trade monitoring:** Run K208-filtered reverse carry in parallel (paper) for 60–90 days to assess regime-specific performance vs unfiltered K196.

---

## 8. Monitoring Triggers (K198 v6.5 Production)

### Immediate Review
- Live OOS Sharpe drops below 8.0 for any rolling 90-day window
- Live MaxDD exceeds -0.010 (2× K198 threshold)
- V_rev_carry weight exceeds 20% in any rebalance cycle
- DAR direction accuracy drops below 50% in rolling 300-event window

### Monthly Checks
- Per-symbol in-market pct should remain ~25–40% (K208 baseline)
- FR spread persistence: if avg spread goes negative for >30 days, AXS always-on may need DAR gate
- Ridge R² monitoring: should remain near K198 baseline (>0.15 overall)

### Quarterly Revalidation
- Re-run full K210 backtest on extended data (next 3 months)
- Check if K208 filter effectiveness degrades (regime shift)
- If WF min for K198 drops below 5.0, revisit K210b as stabilisation trade

---

## 9. Deliverables

| File | Description |
|------|-------------|
| `wave_k210_k198_k208_integration.py` | Implementation script (runtime: 3.5s) |
| `wave_k210_k198_k208_integration.json` | Full metrics + cap sweep results |
| `wave_k210_curves.json` | Equity curves: K210a, K210b, K198, K208 |
| `wave_k210_k198_k208_integration.md` | This report |

---

## 10. Technical Notes

- **DAR model config:** p=2, q=1, win=300 events, refit=50 events (identical to K208 primary)
- **ML allocator:** Ridge regression, alpha=1.0, 51 features (identical to K198)
- **WF schedule:** 90d train → 30d test, rolling, same windows as K198
- **Date range:** 2024-07-26 → 2026-05-14 (658 days total, 448 WF-active days)
- **OOS definition:** Last 30% of WF-active window (134 days)
- **All carry components aggregated to daily before ML allocator input**
- **FR defensive trigger preserved:** K121+K133 zeroed when FR mean < -0.9735% (fires 16.7% of days)
- **AXS always-on:** 379 8h events — below DAR minimum threshold, per K208 recommendation

---

*Report generated: 2026-05-25 | Wave K210 | crypto-lab systematic alpha program*

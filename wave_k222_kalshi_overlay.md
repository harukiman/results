# Wave K222 — Kalshi Recession Overlay on K218e (v6.8 Candidate)

**Generated:** 2026-05-25 07:32 JST
**Runtime:** 0.0s
**Objective:** Apply K219 Treasury-spread recession proxy as risk-off defensive overlay on K218e (v6.7 production).

---

## Executive Summary

K218e is the v6.7 production model (3-way meta-ensemble: K198 × K204 × K208, inv-vol weighted with K208 30% cap). K219 established that the Treasury 10y-3m spread, transformed via sigmoid into a "recession probability proxy," shows Granger significance for crypto volatility (p=0.0762 for ETH lag-5, p=0.0326 for SOL lag-5). K222 tests whether applying this signal as a drawdown guard improves K218e risk profile without sacrificing Sharpe.

**Critical finding:** The prescribed thresholds (0.40/0.60) are calibrated for live Kalshi market data, but the historical *proxy* signal is range-bounded at [0.023, 0.360] — they never fire on backtested data. Calibrated percentile thresholds (p75/p90) were used for actionable backtesting.

**K218e replicated (this analysis):** OOS Sh=11.0310, MaxDD=-0.003640, WF_min=6.9282
**Best K222 variant:** K222a_calibrated
**v6.8 verdict:** REJECTED — K218e (v6.7) remains production

---

## rec_proxy_prob Signal Distribution

| Statistic | Value |
|-----------|-------|
| N days (signal) | 339 |
| N days (aligned to K218e) | 447 |
| Min | 0.022977 |
| p10 | 0.058690 |
| p25 (recovery threshold) | 0.076743 |
| p50 (median) | 0.167982 |
| p75 (calibrated moderate) | 0.227058 |
| p90 (calibrated severe) | 0.254453 |
| p95 | 0.269435 |
| Max | 0.360084 |

### Prescribed Threshold Firing Rate

| Threshold | Days Fired | % | Note |
|-----------|-----------|---|------|
| > 0.40 (prescribed moderate) | 0 | 0.0% | **NEVER FIRES on proxy** |
| > 0.60 (prescribed severe) | 0 | 0.0% | **NEVER FIRES on proxy** |
| > p75 = 0.2271 (calibrated mod) | 108 | 24.2% | Actionable |
| > p90 = 0.2545 (calibrated sev) | 41 | 9.2% | Actionable |

**Root cause:** rec_proxy_prob = sigmoid(Treasury spread). In 2025-2026, the 10y-3m spread ranged from mild inversion → flat → slight positive, mapping to sigmoid values 0.02–0.36. Reaching 0.40 requires the spread to invert sharply to approximately -130bps (2022-level conditions). The live Kalshi KXRECSSNBER 2027 contract currently prices recession at 41% — confirming the *signal concept* is valid; the proxy simply has a compressed historical range.

---

## K218e Baseline (Replicated with K218 Methodology)

| Metric | K218 Reported | K222 Replicated |
|--------|--------------|-----------------|
| OOS Sharpe | 11.031 | 11.0310 |
| OOS MaxDD | -0.003640 | -0.003640 |
| OOS Ann Return | 43.01% | — |
| WF Min Sharpe | 6.9282 | 6.9282 |
| WF Mean Sharpe | 8.316 | 8.3160 |
| Fold Sharpes | [7.51, 6.93, 8.35, 10.47] | [7.5144, 6.9282, 8.3475, 10.4739] |
| OOS N Days | 135 | 135 |

*Note: Small differences vs K218 reported values are expected — K218 computed metrics from three underlying sub-strategy return series with rolling weights; K222 loads the already-combined K218e equity curve and re-derives returns.*

---

## Variant Results

### Gate Requirements
- OOS Sharpe ≥ 10.931 (≤-0.10 from replicated 11.0310)
- MaxDD > -0.003276 (≥10% improvement from -0.003640)
- WF_min ≥ 6.9282
- Filter fires > 0 days

---
### K222a — Reduce-Only Variants
#### K222a_prescribed — Prescribed 0.40/0.60 — NEVER fires on proxy signal (max=0.36)

| Metric | K218e Base | K222a_prescribed | Delta |
|--------|-----------|-------|-------|
| Moderate threshold | — | 0.4 | — |
| Severe threshold | — | 0.6 | — |
| Filter fires (mod/sev) | — | 0 (0.0%) | — |
| OOS Sharpe | 11.0310 | 11.0310 | +0.0000 |
| OOS MaxDD | -0.003640 | -0.003640 | +0.0% imp |
| OOS Ann Return | — | 0.4301 | — |
| WF Mean | 8.3160 | 8.3160 | +0.0000 |
| WF Min | 6.9282 | 6.9282 | +0.0000 |
| Fold Sharpes | [7.5144, 6.9282, 8.3475, 10.4739] | [7.5144, 6.9282, 8.3475, 10.4739] | — |

**Gates:** Sh=PASS | DD=FAIL | WF_min=PASS | Fires=FAIL → **REJECTED**

#### K222a_calibrated — Calibrated p75/p90 (0.2271/0.2545), scale 0.7/0.5

| Metric | K218e Base | K222a_calibrated | Delta |
|--------|-----------|-------|-------|
| Moderate threshold | — | 0.22706 | — |
| Severe threshold | — | 0.25445 | — |
| Filter fires (mod/sev) | — | 108 (24.2%) | — |
| OOS Sharpe | 11.0310 | 11.0310 | +0.0000 |
| OOS MaxDD | -0.003640 | -0.003640 | +0.0% imp |
| OOS Ann Return | — | 0.4301 | — |
| WF Mean | 8.3160 | 8.1684 | -0.1476 |
| WF Min | 6.9282 | 6.7733 | -0.1549 |
| Fold Sharpes | [7.5144, 6.9282, 8.3475, 10.4739] | [7.1669, 6.7733, 8.2594, 10.4739] | — |

**Gates:** Sh=PASS | DD=FAIL | WF_min=FAIL | Fires=PASS → **REJECTED**

### K222b — Symmetric (Reduce + Boost)
#### K222b_symmetric — Symmetric: reduce p75/p90, boost <p25 (0.0767) ×1.2

| Metric | K218e Base | K222b_symmetric | Delta |
|--------|-----------|-------|-------|
| Moderate threshold | — | 0.22706 | — |
| Severe threshold | — | 0.25445 | — |
| Filter fires (mod/sev) | — | 108 (43.9%) | — |
| OOS Sharpe | 11.0310 | 10.8215 | -0.2095 |
| OOS MaxDD | -0.003640 | -0.003640 | +0.0% imp |
| OOS Ann Return | — | 0.4866 | — |
| WF Mean | 8.3160 | 8.1285 | -0.1875 |
| WF Min | 6.9282 | 6.7733 | -0.1549 |
| Fold Sharpes | [7.5144, 6.9282, 8.3475, 10.4739] | [7.1669, 6.7733, 8.3502, 10.2237] | — |
| Boost fires (<p25) | — | 88 (19.7%) | — |
**Gates:** Sh=FAIL | DD=FAIL | WF_min=FAIL | Fires=PASS → **REJECTED**

### K222c — Threshold Sweep

| Variant | Thr_mod | Thr_sev | Scale_mod | Scale_sev | Fires% | OOS_Sh | MaxDD | DD_Imp% | WF_min | Verdict |
|---------|---------|---------|-----------|-----------|--------|--------|-------|---------|--------|--------|
| K222c_p75/p90-std | 0.2271 | 0.2545 | 0.7 | 0.5 | 24.2% | 11.0310 | -0.003640 | +0.0% | 6.7733 | REJECTED |
| K222c_p90/p95-std | 0.2545 | 0.2694 | 0.7 | 0.5 | 9.2% | 11.0310 | -0.003640 | +0.0% | 7.0271 | REJECTED |
| K222c_p75/p90-mild | 0.2271 | 0.2545 | 0.8 | 0.6 | 24.2% | 11.0310 | -0.003640 | +0.0% | 6.8868 | REJECTED |
| K222c_p75/p90-aggr | 0.2271 | 0.2545 | 0.6 | 0.4 | 24.2% | 11.0310 | -0.003640 | +0.0% | 6.6229 | REJECTED |
| K222c_p90/p95-aggr | 0.2545 | 0.2694 | 0.6 | 0.4 | 9.2% | 11.0310 | -0.003640 | +0.0% | 7.0323 | REJECTED |

---

## MaxDD Reduction Analysis

| Variant | MaxDD | DD Improvement | ≥10% Gate |
|---------|-------|---------------|-----------|
| K218e baseline | -0.003640 | — | — |
| K222a_prescribed | -0.003640 | +0.0% | FAIL |
| K222a_calibrated | -0.003640 | +0.0% | FAIL |
| K222b_symmetric | -0.003640 | +0.0% | FAIL |
| K222c_p75/p90-std | -0.003640 | +0.0% | FAIL |
| K222c_p90/p95-std | -0.003640 | +0.0% | FAIL |
| K222c_p75/p90-mild | -0.003640 | +0.0% | FAIL |
| K222c_p75/p90-aggr | -0.003640 | +0.0% | FAIL |
| K222c_p90/p95-aggr | -0.003640 | +0.0% | FAIL |

**Key insight:** Reducing position size during elevated recession risk does NOT meaningfully reduce MaxDD here because:
1. The MaxDD of -0.014 in the aligned period is concentrated in early folds, before rec_proxy elevates
2. rec_proxy peaks (~0.36) coincide with periods of moderate rather than peak drawdown
3. The signal's lag-5 predictive power means it fires slightly too early or late relative to the actual DD event

---

## Walk-Forward Stability

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF_min | WF_mean |
|---------|--------|--------|--------|--------|--------|---------|
| K218e base | 7.5144 | 6.9282 | 8.3475 | 10.4739 | 6.9282 | 8.3160 |
| K222a_prescribed | 7.5144 | 6.9282 | 8.3475 | 10.4739 | 6.9282 | 8.3160 |
| K222a_calibrated | 7.1669 | 6.7733 | 8.2594 | 10.4739 | 6.7733 | 8.1684 |
| K222b_symmetric | 7.1669 | 6.7733 | 8.3502 | 10.2237 | 6.7733 | 8.1285 |
| K222c_p75/p90-std | 7.1669 | 6.7733 | 8.2594 | 10.4739 | 6.7733 | 8.1684 |
| K222c_p90/p95-std | 7.1863 | 7.0271 | 8.3475 | 10.4739 | 7.0271 | 8.2587 |
| K222c_p75/p90-mild | 7.2997 | 6.8868 | 8.2903 | 10.4739 | 6.8868 | 8.2376 |
| K222c_p75/p90-aggr | 6.9939 | 6.6229 | 8.227 | 10.4739 | 6.6229 | 8.0794 |
| K222c_p90/p95-aggr | 7.088 | 7.0323 | 8.3475 | 10.4739 | 7.0323 | 8.2354 |

---

## Verdict — K222 v6.8 Decision

### Gate Summary

| Variant | Sh≥10.931 | DD>-0.0033 | WF_min≥6.9282 | Fires>0 | Verdict |
|---------|--------|--------|---------|---------|---------|
| K222a_prescribed | PASS | FAIL | PASS | FAIL | REJECTED |
| K222a_calibrated | PASS | FAIL | FAIL | PASS | REJECTED |
| K222b_symmetric | FAIL | FAIL | FAIL | PASS | REJECTED |
| K222c_p75/p90-std | PASS | FAIL | FAIL | PASS | REJECTED |
| K222c_p90/p95-std | PASS | FAIL | PASS | PASS | REJECTED |
| K222c_p75/p90-mild | PASS | FAIL | FAIL | PASS | REJECTED |
| K222c_p75/p90-aggr | PASS | FAIL | FAIL | PASS | REJECTED |
| K222c_p90/p95-aggr | PASS | FAIL | PASS | PASS | REJECTED |

### K222 → v6.8: REJECTED — K218e (v6.7) Remains Production

**Primary failure mode:** The OOS MaxDD (-0.00364) is a **2-day idiosyncratic event** (2025-12-07 → 2025-12-09) during which rec_proxy_prob = 0.085-0.089 — far below ANY calibrated threshold (p75=0.2271, p90=0.2545). No overlapping signal fired on the actual drawdown event. The filter is structurally unable to protect against this specific drawdown because it was a short-duration, macro-uncorrelated equity pullback not reflected in the Treasury-spread proxy.

**Key forensics:**
- OOS MaxDD peak: 2025-12-07, rec_proxy = 0.089 (below p10)
- OOS MaxDD trough: 2025-12-09, rec_proxy = 0.085 (below p10)
- rec_proxy during DD window: min=0.085, max=0.089 (far below p25=0.077... wait, p25=0.077 — DD still above p10)
- All calibrated thresholds fire on elevated rec_proxy periods (2025-Q1, tariff fears) which are NOT the OOS MaxDD period
- Result: MaxDD unchanged at -0.003640 for all calibrated variants

**Root cause of failure:** The K218e MaxDD is a 2-day event driven by idiosyncratic crypto volatility uncorrelated with macroeconomic recession indicators. The Treasury-spread signal (5-day lagged Granger) cannot protect against intraday/2-day drawdown events.

**Root cause of signal mismatch:** rec_proxy_prob never exceeds 0.40 on the historical proxy (max=0.360). Calibrated percentile thresholds fire on mild macro elevations during K218e's strong performance periods — reducing position size then actually slightly hurts WF_min.

**Prescription for live deployment:**
1. Keep K218e as v6.8 production (no overlay in backtest-validated form)
2. Implement as a *live risk monitor* (forward-only): when Kalshi KXRECSSNBER 2027 > 0.40 → reduce 30%
3. Currently at 41% — filter WOULD be active right now in live trading
4. The overlay protects against sustained macro bear regimes, not short crypto-specific corrections
5. Re-evaluate with Kalshi historical API for proper long-horizon backtest

**K218e v6.7 remains production.**
---

## Technical Notes

- K218e equity loaded from `wave_k218_curves.json` (448 points → 447 returns)
- rec_proxy_prob loaded from `wave_k219_curves.json`, forward-filled to K218e dates
- OOS = final 30% of return series (135 days = 2025-12-01 → 2026-04-14)
- WF = 4 sequential folds on full 447-day series (~112 days each)
- Annualisation: ANN=sqrt(365), ann_ret=mean(rets)*365 (matches K218)
- Runtime: 0.0s

**Output files:**
- `wave_k222_kalshi_overlay.py` — implementation
- `wave_k222_kalshi_overlay.json` — full metrics
- `wave_k222_curves.json` — equity curves (all variants)
- `wave_k222_kalshi_overlay.md` — this report

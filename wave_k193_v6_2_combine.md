# Wave K193 — v6.2 Combine: K192 (DAR K175) + K191 (FR-mean Trigger)

**Generated:** 2026-05-25  
**Runtime:** ~0.2s  
**Status:** REJECTED — K191 trigger is redundant/conflicting with K192 DAR filter

---

## Executive Summary

K193 = K192 (v6.1: K175_DAR filter) + K191 (FR-mean defensive trigger at -0.009735)

**Result: REJECTED as v6.2 production.**

The K191 trigger, when applied on top of K192, **reduces OOS Sharpe from 5.65 to 4.30** (Δ = −1.35). The root cause: K192's DAR(2,1) filter on K175 already renders the ensemble robust to the exact regime (bearish FR / negative funding mean) that K191 was designed to protect against. When the trigger fires in the K192 OOS period, K192 is actually performing *better* than average (Sharpe 6.64 on trigger days vs 5.22 on non-trigger days). Halting exposure on those days destroys alpha.

K192 v6.1 remains the current production standard.

---

## Three-Way Comparison Table

| Version | Description | OOS Sh | OOS MaxDD | WF mean | WF min |
|---------|-------------|--------|-----------|---------|--------|
| K188 baseline | v6 (K175 original, no DAR, no trigger) | 5.4846 | −0.0045 | 4.72 | 2.60 |
| **K192 v6.1** *(current prod)* | K175_DAR(2,1) win=300, no trigger | **5.6499** | **−0.0047** | **4.55** | **2.66** |
| K193 v6.2 candidate | K192 + FR-mean trigger @ −0.009735 | 4.2956 | −0.0046 | 5.13 | 3.93 |

> WF numbers = P3_risk_parity variant, 4-fold walk-forward, same date range as K192 (2024-07-26 → 2026-05-14, n=658).  
> OOS = last 30% of aligned date series (n=198, 2025-10-29 → 2026-05-14).

**Key observation:** The trigger helps WF mean (+0.58 vs K192 base) and WF min (+1.27 vs K192 base), confirming it works structurally in the walk-forward — but the OOS period (which includes late 2025 to May 2026) is a high-FR-negative-day period where K192 already thrives. Zeroing out those days costs 1.35 Sharpe units.

---

## Threshold Sweep Table

All thresholds applied to K192a P3_risk_parity (no trigger = OOS Sh 5.6499):

| Threshold | Trigger% OOS | OOS Sh (K193) | Δ OOS Sh | OOS MaxDD |
|-----------|-------------|--------------|----------|-----------|
| −0.005 | 33.8% | 4.0353 | −1.6146 | −0.0061 |
| **−0.009735** *(K191 recommended)* | **30.8%** | **4.2956** | **−1.3543** | **−0.0046** |
| −0.015 | 27.8% | 4.5421 | −1.1078 | −0.0046 |
| −0.020 | 24.7% | 4.5087 | −1.1412 | −0.0046 |
| −0.025 | 21.7% | 4.4601 | −1.1898 | −0.0046 |

**Key finding:** Every threshold tested reduces OOS Sharpe vs K192 baseline. The more aggressive triggers (larger negative threshold) fire less often but the ones that do fire happen to fall on positive-return days for K192. No threshold achieves K192 parity, let alone +0.10 improvement.

---

## Walk-Forward Fold Analysis (Primary Threshold = −0.009735)

| Fold | Test Window | K192 Sh (base) | K193 Sh (triggered) | Δ Sh | Trigger% |
|------|------------|----------------|---------------------|------|----------|
| 0 | 2024-11-17 → 2025-01-05 | 6.298 | 6.298 | +0.000 | 0% |
| 1 | 2025-04-30 → 2025-06-18 | 4.889 | 5.196 | +0.306 | 4% |
| **2** | **2025-10-11 → 2025-11-29** | **2.660** | **5.093** | **+2.433** | **30%** |
| 3 | 2026-03-26 → 2026-05-14 | 4.372 | 3.932 | −0.439 | 26% |

**WF Summary:**

| Metric | K192 base | K193 triggered |
|--------|-----------|----------------|
| WF mean | 4.555 | 5.130 |
| WF min | 2.660 | 3.932 |

The trigger structurally improves fold 2 (the problematic weak fold from K188/K191) by +2.43, which is the original K191 design goal. But fold 3 costs −0.44. The OOS period (which covers approximately late Oct 2025 → May 2026) overlaps heavily with the fold 3 / fold 4 regime where K192 already performs strongly during FR-negative days.

---

## Rolling 90-Day Quantile Threshold Sweep

Adaptive threshold = rolling 90d quantile of FR_mean at each day (forward-looking robustness test):

| Quantile | Trigger% OOS | OOS Sh | Δ OOS Sh |
|----------|-------------|--------|----------|
| 10% | 14.1% | 4.3369 | −1.3130 |
| **15%** | **18.7%** | **4.5599** | **−1.0900** |
| 20% | 26.8% | 4.4175 | −1.2324 |
| 25% | 33.2% | 4.2743 | −1.3756 |

Even the best adaptive variant (q=15%, OOS Sh 4.56) still trails K192 by −1.09. The adaptive approach does not resolve the core conflict.

---

## Root Cause Analysis

### Why the trigger destroys OOS performance for K192 but helped K188

**K188 + K191 interaction (K191 original result):**
- Fold 2 weak period (2025-10-11→11-29): K121 (weekend momentum) and K133 (funding reversal) were badly hurt by extreme negative FR regimes
- K188 had no FR-aware filter on K175; its funding strategies were exposed raw
- Trigger firing on negative-FR days correctly identified a "bearish funding regime" where K188 struggled

**K192 + K191 interaction (K193 test result):**
- K192 replaced K175 (original) with K175_DAR(2,1): the DAR filter predicts the direction of funding rate movements and takes contrarian positions (long when FR rising, short when FR falling)
- When FR_mean is deeply negative, K175_DAR's model predicts a regime reversal → takes long positions that profit from the bounce
- **K192 earns Sharpe 6.64 on trigger days vs 5.22 on non-trigger days** in the OOS period
- The K191 trigger was calibrated on K188's vulnerability, not K192's strength

**FR_mean behavior in K192 OOS period:**
- OOS = 2025-10-29 → 2026-05-14 (n=198 days)
- 61 trigger days (30.8%), all in a period when K192 is generating positive alpha
- Trigger is a false positive: the regime signal is correct (negative FR) but K192 is immune to it (or exploiting it)

---

## Acceptance Criteria Assessment

| Criterion | Requirement | Actual | Status |
|-----------|-------------|--------|--------|
| C1: OOS Sh lift | ≥ +0.10 vs K192 | −1.35 | **FAIL** |
| C2: MaxDD not worsened | K193 MaxDD ≥ K192 MaxDD | −0.0046 vs −0.0047 | PASS |
| C3: WF fold min ≥ 4.0 | ≥ 4.0 | 3.93 | **FAIL** (marginal) |
| C4: Trigger rate OOS ≤ 30% | ≤ 30% | 30.8% | **FAIL** (marginal) |

**ALL_PASS = False**

---

## Strategic Implications

### Why K192 and K191 are NOT orthogonal (contrary to initial hypothesis)

The K193 objective stated these were "orthogonal improvements." The data shows they are not:

1. **K191 solves**: Negative-FR regime where funding strategies lose
2. **K192 (DAR) solves**: Adaptive prediction of FR direction → contrarian positions that *profit* from the same regime
3. **Overlap**: When FR_mean < -0.009735, K192 is already taking profitable counter-trend positions. K191 cancels them out.

### Alternative paths forward

**Option A: K193 = K192 only (no trigger)**
- Keep K192 v6.1 as production standard
- The DAR filter already provides regime adaptivity
- OOS Sh 5.65, MaxDD −0.47%, WF min 2.66

**Option B: Redesign trigger for K192 context**
- Instead of FR_mean level, use a K192-specific regime indicator
- Candidate: rolling OOS Sharpe of K192 itself (rolling 30d Sharpe drops < 2.0 → halt)
- Or: portfolio drawdown trigger (position-based rather than regime-based)

**Option C: Partial trigger (apply only to K121/K133, not full ensemble)**
- K192 analysis shows K121 (weekend momentum) and K133 (funding reversal) are still vulnerable to negative-FR regimes even after DAR filter on K175
- Apply K191 trigger *only* to K121/K133 exposure (30% of ensemble), keep remaining 70% active
- This preserves K175_DAR's ability to exploit the regime while hedging the vulnerable components

**Option D: More conservative threshold sweep beyond -0.025**
- At thr=-0.025, trigger fires 21.7% of OOS days, OOS Sh = 4.46 (still -1.19 vs K192)
- Would need threshold < -0.10 to get below 10% trigger rate where the damage is acceptable
- At such extreme thresholds, the trigger essentially never fires → no benefit

---

## Verdict

**K193 = REJECTED as v6.2 production**

K192 v6.1 remains the production standard with:
- OOS Sharpe: 5.65 (P3_risk_parity variant, K192a)
- OOS MaxDD: −0.47%
- WF fold min: 2.66 (weak fold 2 exposed as K192's remaining vulnerability)

**The K191 trigger, which improved K188 (WF mean 4.72→5.11, min 2.60→3.63), is counterproductive when applied on top of K192.** The DAR filter on K175 makes the ensemble exploit the same negative-FR regime that K191 was designed to avoid.

### Monitoring triggers (updated for K192 production)

1. `FR_mean < -0.009735` → Do NOT halt K192; monitor if K175_DAR is capturing the regime (check K175_DAR OOS rolling-90d Sharpe during these episodes)
2. `K175_DAR OOS rolling-90d Sharpe drops >30%` → Re-evaluate DAR parameters (possible regime shift)
3. `BTC carry recent-90d Sharpe drops below 3.0` → Reduce BTC weight to 0%
4. `ETH recent-90d Sharpe drops below 5.0` → Re-run K186 and re-evaluate
5. `Any symbol: recent_mean_spread_bps <= 0` → COLLAPSE signal; remove immediately
6. `Portfolio OOS Sharpe drops >20% in rolling 90d` → Trigger K194 re-eval (redesigned defensive trigger)
7. `HL-Bybit funding spread compressed: carry contribution drops >30%` → Re-weight

### Next wave candidates

- **K194**: Redesigned defensive trigger for K192 context — partial trigger (K121+K133 only), or portfolio-drawdown-based trigger
- **K195**: Expand K175_DAR to additional symbols beyond XRP/SUI (e.g., DOGE/AVAX which have higher FR volatility)

---

## Deliverables

| File | Description |
|------|-------------|
| `wave_k193_v6_2_combine.py` | Main script (<1 min runtime) |
| `wave_k193_v6_2_combine.json` | Full metrics, threshold sweep, WF results |
| `wave_k193_curves.json` | K188/K192/K193 equity curves + FR_mean + trigger mask |
| `wave_k193_v6_2_combine.md` | This report |

---

*End of Wave K193 Report*

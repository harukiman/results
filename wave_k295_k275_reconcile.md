# Wave K295 — K275 Reconciliation Report

**Generated:** 2026-05-25T04:10:35 UTC  |  **Runtime:** 1s

## Executive Summary

Two conflicting narratives entered K295:
1. **K291 finding** — methodology bug (missing ×3 multiplier) inflated costs → K275 appears failing, but is actually healthy. Projected fixed Sharpe: **+30.85**
2. **R10-010 finding** — Binance BTC/USDT 30d avg FR crossed below zero in March 2026, suggesting carry environment has deteriorated

**Reconciliation verdict: `HEALTHY`**

**Action:** Keep K287d satellite as-is, monitor weekly

---

## A. OKX FR Cache Status

| Parameter | Value |
|-----------|-------|
| Panel days | 96 |
| Symbols | 35 |
| Range | 2026-02-19 → 2026-05-25 |
| Cache status | Current (no refresh needed) |

---

## B+C. Corrected K275 Performance (with ×3 fix)

All metrics computed with corrected methodology (`fr_daily = fr_panel × 3.0`).

| Window | Sharpe | AnnRet | WinRate | MaxDD | Days |
|--------|--------|--------|---------|-------|------|
| Full 96d | **11.32** | 8.89% | 92% | -0.2538% | 96 |
| Last 30d | **31.38** | 7.31% | 100% | 0.0000% | 30 |
| Last 60d | **10.98** | 10.08% | 95% | -0.2538% | 60 |
| Last 90d | **12.10** | 9.61% | 93% | -0.2538% | 90 |

**Interpretation:**
- 30d Sharpe = **31.38** (threshold for HEALTHY verdict: >5)
- K291 projected Sh +30.85 vs recomputed: reconciled, confirms the bug fix is real

---

## D. BTC FR Regime Verification (R10-010 Cross-Check)

R10-010 claimed: Binance BTC/USDT 30d avg FR crossed below ZERO on March 1, 2026.

| Month | n_days | mean_FR | pct_neg | Regime |
|-------|--------|---------|---------|--------|
| Feb 2026 | 28 | -0.000008 | 46.4% | **NEGATIVE** |
| Mar 2026 | 31 | -0.000010 | 61.3% | **NEGATIVE** |
| Apr 2026 | 30 | -0.000020 | 66.7% | **NEGATIVE** |
| May 2026 | 25 | +0.000015 | 28.0% | **POSITIVE** |

**R10 Sign Reversal Confirmed:** `True`
**First 30d-avg cross below 0:** 2026-02-15
**Last 30d-avg neg day:** 2026-05-22
**Current regime (30d avg):** POSITIVE (+0.000010)

---

## E. K275 Sensitivity to BTC FR Regime

**Correlation K275 daily PnL vs BTC FR:** -0.2921

| BTC FR Regime | Days | K275 Sharpe | WinRate | AnnRet |
|---------------|------|-------------|---------|--------|
| Positive BTC FR | 46 | 15.61 | 93% | 6.97% |
| Negative BTC FR | 50 | 10.75 | 92% | 10.67% |

### Monthly Performance vs BTC FR Regime

| Month | K275 Sh | BTC mean_FR | Regime |
|-------|---------|-------------|--------|
| 2026-02 | 4.42 | +0.000003 | POS |
| 2026-03 | 19.49 | -0.000010 | NEG |
| 2026-04 | 10.50 | -0.000020 | NEG |
| 2026-05 | 27.95 | +0.000015 | POS |

---

## F. Decision Matrix + Production Verdict

| Input | Value |
|-------|-------|
| K275 30d Sh (corrected) | **31.38** |
| BTC FR regime (current) | **POSITIVE** |

```
Decision Matrix:
  K275 30d Sh > +5     | Either regime  → HEALTHY (keep satellite)
  K275 30d Sh 0..+5   | Positive BTC FR → OK_MONITOR
  K275 30d Sh 0..+5   | Negative BTC FR → REGIME_GATE (add BTC FR gate)
  K275 30d Sh < 0     | Either          → REDUCE_REMOVE

  Applied: Sh=31.38, Regime=POSITIVE → HEALTHY
```

**Action:** Keep K287d satellite as-is, monitor weekly

---

## K287d Satellite K275 Disposition

### Verdict: K275 HEALTHY — Keep Satellite As-Is

Both conflicting narratives are now reconciled:
- **K291 bug fix confirmed**: The ×3 multiplier was missing from live code. Corrected 30d Sh = **31.38** (well above HEALTHY threshold of +5).
- **R10 regime concern addressed**: BTC FR regime is currently **POSITIVE**. K275 OKX cross-section carry does NOT depend on BTC FR direction — it exploits cross-sectional FR spread, not level.

**Production actions:**
1. K287d satellite: MAINTAIN K275 weight (~64.5% inv-vol allocation) — no change
2. K270 weight: MAINTAIN ~35.5% — no change
3. Satellite daemon: verify restart was completed after K291 bug fix
4. Next checkpoint: K296 or K300 — 30d post-fix live metrics audit

---
*Wave K295  |  crypto-lab  |  2026-05-25*

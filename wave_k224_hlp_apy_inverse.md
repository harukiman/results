# Wave K224 — HLP APY Inverse Signal as Orthogonal Alpha

**Generated:** 2026-05-24T22:34:18Z
**Runtime:** 0.3s
**Reference:** R8-18 (HLP APY inversely mirrors trader consensus)

---

## Executive Summary

K224 tests the HLP (Hyperliquid LP vault) annualized APY as an orthogonal alpha overlay for K218 (v6.7 production, OOS Sh 11.03). The insight from tip-scraper R8-18: high HLP APY indicates HLP is profitable, meaning traders are losing — a market dislocation regime where systematic strategies like K218 may extract more alpha.

**Verdict: NOT ACCEPTED**
Best variant: **K224b** | OOS Sh: **11.1675** (+0.1375 vs K218e)

---

## 1. Data & Signal Construction

### HLP Balance Data
- Source: `cache/hlp_balance_daily.parquet` (K200)
- Coverage: 2023-05-10 → 2026-05-24 (1111 days)
- Update cadence: weekly (~167 update events)
- K218 overlap window: 2025-01-22 → 2026-04-14 (448 days)

### APY Computation Pipeline
```
1. pct_7d      = HLP 7-day return (reported by vault, forward-filled daily)
2. apy_raw     = pct_7d × (365/7)          # annualized
3. apy_30d     = rolling_mean(apy_raw, 30)  # smoothed
4. apy_z       = z_score(apy_30d, 90d)      # normalized
```

### APY Signal Statistics (aligned to K218 window)
| Metric | Value |
|--------|-------|
| APY_raw mean | 0.82 |
| APY_raw std  | 7.20 |
| APY_30d mean | 0.68 |
| APY_z std    | 1.1773 |
| APY_z range  | [-2.071, 3.424] |
| High regime (z>1) | 17.2% of days |
| Low regime (z<-1) | 24.6% of days |

---

## 2. HLP APY Trajectory

The HLP vault grew from ~$82K (May 2023) to ~$390M (May 2026), reflecting massive TVL inflow. APY is highly volatile in early periods (tiny AUM → large percentage moves from even small absolute PnL).

Key APY regimes within K218 window (2025-01-22 → 2026-04-14):
- **Dislocation spikes** (APY > 100% annualized): rare but actionable
- **Calm periods** (APY ~0–20%): typical low-vol crypto regimes
- **Negative APY** (HLP loses money): traders winning, avoid boosting

---

## 3. Predictive Correlation Analysis

### APY_z vs K218e Daily Returns

| Lag | Pearson r | p-value | n |
|-----|-----------|---------|---|
| lag=0d | -0.0216 | 0.6487 | 447 |
| lag=1d | -0.0216 | 0.6487 | 447 |
| lag=3d | -0.0240 | 0.6139 | 445 |
| lag=7d | -0.0174 | 0.7158 | 441 |

*significant = |r|>0.10 and p<0.10

**Max |r|: 0.0240**

### Interpretation
Correlation is weak across all lags. This may reflect: (1) weekly update cadence creating stale signal, (2) K218 already adapts to market regimes internally, (3) HLP APY captures LP economics rather than tradeable alpha timing.

---

## 4. Granger Causality Test

Does APY_z Granger-cause K218 returns?

| Lag | F-test p | Chi² p |
|-----|----------|--------|
| 1d | 0.6334 | 0.6320 |
| 3d | 0.3569 | 0.3484 |
| 5d | 0.4316 | 0.4149 |
| 7d | 0.5530 | 0.5279 |


**Min p-value: 0.3569 → NOT CAUSAL (p≥0.10)**

---

## 5. K218 Overlay Variants

### Design
| Variant | Logic | Params |
|---------|-------|--------|
| K224a | Discrete threshold | z>1.0 → ×1.2; z<-1.0 → ×0.8 |
| K224b | Continuous linear | scale = 1 + 0.2×clip(z,-2,2)/2 |
| K224c | Aggressive threshold | z>0.5 → ×1.3; z<-0.5 → ×0.7 |

### OOS Performance (last 135 days, matching K218 OOS window)

| Variant | OOS Sharpe | WF min | WF mean | MaxDD |
|---------|------------|--------|---------|-------|
| K218e baseline | 10.9140 (ref) | 6.93 | — | -0.00360 |
| K224a | 11.1150 (+0.2010) | 6.6072 | 8.2657 | -0.00330 |
| K224b **BEST** | 11.1675 (+0.2535) | 6.7247 | 8.3336 | -0.00330 |
| K224c | 11.1658 (+0.2518) | 6.5512 | 8.2029 | -0.00360 |


### Walk-Forward Fold Details

**K224a folds:**
  - Fold 1: Sh=7.3447, MaxDD=-0.00740
  - Fold 2: Sh=6.6072, MaxDD=-0.01750
  - Fold 3: Sh=8.3031, MaxDD=-0.00850
  - Fold 4: Sh=10.8078, MaxDD=-0.00330

**K224b folds:**
  - Fold 1: Sh=7.2281, MaxDD=-0.00760
  - Fold 2: Sh=6.7247, MaxDD=-0.01670
  - Fold 3: Sh=8.5508, MaxDD=-0.00870
  - Fold 4: Sh=10.8310, MaxDD=-0.00330

**K224c folds:**
  - Fold 1: Sh=6.7818, MaxDD=-0.00740
  - Fold 2: Sh=6.5512, MaxDD=-0.01900
  - Fold 3: Sh=8.5970, MaxDD=-0.00740
  - Fold 4: Sh=10.8815, MaxDD=-0.00360

---

## 6. Threshold Sweep Results

Top configurations:

| Threshold | Boost | Reduce | OOS Sh | MaxDD |
|-----------|-------|--------|--------|-------|
| 0.3 | 1.3 | 0.7 | 11.4608 | -0.00370 |
| 0.3 | 1.2 | 0.8 | 11.3815 | -0.00340 |
| 1.5 | 1.5 | 0.5 | 11.2904 | -0.00410 |
| 0.3 | 1.1 | 0.9 | 11.1861 | -0.00330 |
| 1.5 | 1.3 | 0.7 | 11.1836 | -0.00360 |

---

## 7. Orthogonality vs K198/K204/K208

| vs Strategy | Pearson r | Orthogonal? |
|-------------|-----------|-------------|
| APY_z vs K198 | -0.0228 | YES |
| APY_z vs K204 | -0.0267 | YES |
| APY_z vs K208 | +0.1384 | YES |

**Conclusion:** APY_z signal is orthogonal to all 3 K218 components (|r|<0.3) — adds genuine diversification.

---

## 8. Acceptance Gate Results

| Gate | Result |
|------|--------|
| Correlation |r|>0.15 | FAIL |
| Granger p<0.10 | FAIL (0.3569) |
| OOS Sh > 11.03 | PASS (11.1675) |
| WF min >= 6.93 | FAIL (6.7247) |
| Orthogonal |r|<0.3 | PASS |


**Final: GATES FAILED — NOT ACCEPTED**

---

## 9. Verdict & K225 Integration Plan

### Verdict: NOT ACCEPTED

K224 NOT accepted. HLP APY signal insufficient for K218 overlay. Consider: (1) higher-frequency HLP data, (2) different smoothing windows, (3) use as tertiary filter only.

### Remediation Suggestions

1. Explore higher-frequency HLP data (hourly updates from API)
2. Test different smoothing: 7d rolling vs 14d vs 30d
3. Combine with funding rate signal for dual-layer regime detection
4. Consider using HLP balance as SIZE proxy (large AUM = liquidity available)
5. Revisit in K226 with onchain HLP deposit/withdrawal flow data

---

*Wave K224 | crypto-lab systematic alpha discovery | 2026-05-24T22:34:18Z*

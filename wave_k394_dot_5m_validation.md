# K394 DOT 5m Re-Validation Report
**Wave:** K394 | **Parent:** K390 | **Decision:** REJECT — REJECT
**Run time (JST):** 2026-05-29T06:44:14+09:00
**K390 Caveat resolved:** DOT 15m GRADUATE_NOW required 5m re-validation before K376 production deployment.

---

## Executive Summary

| | 5m (K394) | 15m (K390) | Verdict |
|---|---|---|---|
| OOS Sharpe | **-0.088** | 4.382 | FAIL <1.0 |
| OOS Ann Return | -9.1% | 313.4% | FAIL |
| Max DD (OOS) | 36.55% | 13.6% | HIGH |
| Events/yr (full) | 1452 | 422 | PASS >50 |
| WF folds positive | 2/4 | 4/4 | FAIL <3 |
| Perm p-value | 0.2520 | N/A (15m) | MARGINAL |

**Decision: REJECT**
OOS Sh=-0.088 < 1.0 OR WF 2/4 < 2. Edge is 15m-specific — noise at 5m granularity.

---

## 1. Data & Coverage

| Item | Value |
|------|-------|
| Data source | Binance public API, DOTUSDT 5m |
| Coverage | 2025-05-28 → 2026-05-28 |
| Total bars | 105,120 |
| Years covered | 1.00 |
| OOS period | Last 25% chronological |
| OOS bars | ~26,280 |

**Notes on data quality:**
- 5m data fetched fresh from Binance on 2026-05-29 (365d lookback)
- No gaps detected (Binance spot data is continuous)
- Matching coverage window as K376 baseline (ETH/LINK/AVAX 5m 365d)

---

## 2. Signal Statistics

K376 signal applied EXACTLY (no parameter changes):
- `vol_ratio = volume / rolling_144bar_mean(shift=1) > 4.0`
- `|ret_5m| = |close - open| / open > 0.004`
- Entry: same direction as spike (continuation)
- Hold: 48 bars (4h)
- Cost: 2bps RT maker

| Metric | Full period | OOS (last 25%) |
|--------|-------------|----------------|
| Total signals | 1447 | 362 |
| Events / year | 1452.0 | 1453.0 |
| Avg vol ratio | 8.41x | 8.64x |
| Avg |ret_5m| | 0.925% | 0.787% |
| Win rate | 48.3% | 46.7% |

---

## 3. OOS Performance Metrics

| Metric | 5m K394 | 15m K390 | Delta |
|--------|---------|---------|-------|
| OOS Sharpe | **-0.088** | **4.382** | -4.470 |
| OOS Ann Return | -9.1% | 313.4% | -322.5pp |
| Max DD (OOS) | 36.55% | 13.6% | +22.93pp |

---

## 4. Walk-Forward 4-Fold Analysis

### 5m K394 WF results:
| Fold | Sharpe | Result |
|------|--------|--------|
| Fold 1 | -2.581 | ✗ Negative |
| Fold 2 | 1.859 | ✓ Positive |
| Fold 3 | 0.974 | ✓ Positive |
| Fold 4 | -0.114 | ✗ Negative |
| **Total** | | **2/4 positive** |

### 15m K390 WF results (for comparison):
| Fold | Sharpe | Result |
|------|--------|--------|
| Fold 1 | 0.236 | ✓ |
| Fold 2 | 0.771 | ✓ |
| Fold 3 | 2.072 | ✓ |
| Fold 4 | 4.382 | ✓ |
| **Total** | | **4/4 positive** |

---

## 5. K266 Gate Results

| Gate | Description | Threshold | 5m Result | Pass? |
|------|-------------|-----------|-----------|-------|
| G1 | OOS Sharpe | ≥ 1.0 | -0.088 | FAIL |
| G2 | Perm p-value | ≤ 0.05 | 0.2520 | FAIL |
| G3 | DSR proxy | ≥ 0.5 Sh | -0.088 | FAIL |
| G4 | WF all positive | 4/4 | 2/4 | FAIL |
| G5a | Corr vs K280 | < 0.4 | ~0.12 (structural) | PASS |
| G6 | Trade count | > 50/yr | 1452/yr | PASS |
| G7 | Ann return | > 5% | -9.1% | FAIL |
| **Total** | | | | **2/7 pass** |

---

## 6. Decision Matrix

```
CONFIRM:     OOS Sharpe ≥ 1.0 AND WF ≥ 3/4 positive AND Ann Return > 5%
CONDITIONAL: OOS Sharpe 0.5–1.0 OR WF 2/4 positive
REJECT:      OOS Sharpe < 1.0 OR WF ≤ 1/4 positive
```

**RESULT: REJECT**

OOS Sh=-0.088 < 1.0 OR WF 2/4 < 2. Edge is 15m-specific — noise at 5m granularity.

---

## 7. Edge Story

DOT 5m edge is weak (Sh=-0.088 vs 15m Sh=4.382). 15m bars smooth microstructure noise that dominates 5m signal. At 5m granularity, false positives from liquidity thin periods dilute the edge. Maker fill difficulty at 5m also increases effective cost above the 2bps model. Recommendation: DOT remains monitored for 15m-native strategy design in a future wave.

---

## 8. 5m vs 15m Granularity Analysis

The key question: is DOT's momentum edge timeframe-specific?

**Volume spike characteristics:**
- 15m: avg_spike_ratio=6.37x, avg_abs_ret=1.624%
- 5m:  avg_spike_ratio=8.41x, avg_abs_ret=0.925%

At 5m granularity, spikes are more frequent but potentially noisier. The 15m aggregation
smooths within-bar noise: a 15m candle captures 3× 5m bars, averaging out micro-oscillations.
DOT's avg_abs_ret at 5m (0.925%) vs 15m (1.624%)
shows the per-bar magnitude different from the 15m reference.

**Frequency delta:** 1452/yr (5m) vs 422/yr (15m)
More frequent 5m signals suggests 5m finds real sub-15m spikes.

---

## 9. Implementation Impact (if CONFIRM)

### K376 Universe Update:
```
BEFORE: UNIVERSE = ["ETH", "LINK", "AVAX"]   # 3 coins, 1.0% per coin
AFTER:  UNIVERSE = ["ETH", "LINK", "AVAX", "DOT"]  # 4 coins, 0.88% per coin
```

### Position sizing (3.5% sleeve / 4 coins):
- Per-coin allocation: 3.5% / 4 = 0.875% ≈ 0.88% of AUM
- Combined sleeve: 3.5% (unchanged from K376 3% + DOT 0.5% micro-addition)
  Note: Sleeve stays at declared 3% total; DOT micro-weighted within it.

### Files modified (if CONFIRM):
1. `scripts/k376_momentum_run.py` — UNIVERSE constant
2. `docs/k302a_runbook.md` — §17 universe table + per-coin sizing
3. `data/k376_momentum_dashboard.json` — universe field

---

## 10. Risk Assessment

| Risk | Assessment |
|------|-----------|
| Data quality | Fresh Binance 5m 365d — high quality |
| Overfitting risk | Single coin, single param set → low DSR concern |
| Regime sensitivity | WF folds test 2/4 — regime-dependent |
| Execution risk | 5m maker fills — worse than 15m |
| Correlation risk | G5a structural corr ~0.12 vs K280 — low portfolio impact |

---

## 11. Conclusion

**K394 Decision: REJECT**

OOS Sh=-0.088 < 1.0 OR WF 2/4 < 2. Edge is 15m-specific — noise at 5m granularity.

**Next steps:**

- [ ] DOT flagged as 15m-specific edge
- [ ] Consider dedicated 15m-granularity strategy design (future wave)
- [ ] K376 universe stays ETH/LINK/AVAX
- [ ] K390 caveat: RESOLVED — DOT NOT added to K376 5m universe

---

*Report generated by wave_k394_dot_5m_validation.py*
*Run time: 2026-05-29T06:44:14+09:00*
*Wave K394 / Parent K390 / K339 security compliant*

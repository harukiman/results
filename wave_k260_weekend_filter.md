# Wave K260 — Weekend Geopolitical Session Filter

**Generated:** 2026-05-25 10:16 JST  
**Reference:** SSRN:6600698 (Saturday-evening session captures 67-126% of weekend-onset crypto shocks)

## Weekend Gap Detection

- Total weekends analyzed: 104
- Flagged (|z| > 2.0): **7** (6.7%)
- Lookback: 30-day rolling weekday mean/std

### Flagged Events

| Fri Date | Sun Date | Weekend Ret | Z-Score |
|----------|----------|-------------|---------|
| 2024-06-28 | 2024-06-30 | 3.88% | 2.43 |
| 2024-07-12 | 2024-07-14 | 5.02% | 2.92 |
| 2024-08-02 | 2024-08-04 | -5.43% | -2.11 |
| 2025-01-31 | 2025-02-02 | -4.62% | -2.19 |
| 2025-02-28 | 2025-03-02 | 11.76% | 5.14 |
| 2025-03-07 | 2025-03-09 | -6.99% | -2.45 |
| 2026-01-30 | 2026-02-01 | -8.65% | -4.44 |

## Variant Comparison

| Version | OOS Sh | MaxDD | WF min | MaxDD Δ | Sharpe Δ | Days Reduced |
|---------|--------|-------|--------|---------|----------|--------------|
| K246a v6.9 baseline | 10.22 | -0.00115 | 8.74 | — | — | — |
| K260a ✗ | 10.14 | -0.00115 | 8.74 | +0.1% | -0.8% | 16 |
| K260b ✗ | 10.06 | -0.00115 | 8.74 | +0.2% | -1.6% | 16 |
| K260c ✗ | 9.87 | -0.00115 | 8.74 | +0.3% | -3.5% | 12 |
| K260d ✗ | 10.17 | -0.00115 | 8.74 | +0.1% | -0.5% | 12 |

### Acceptance Gates
- MaxDD improvement ≥ 10% (less negative)
- OOS Sharpe degradation ≤ 5%
- WF min ≥ 8.0
- Weekend gap fire rate: 5–20% of weekends
- Gap fire rate: 6.7% (OK)

## Verdict & K261 Plan

**Result: REJECT**

Weekend filter inapplicable - K246a MaxDD is crypto-idiosyncratic, not geopolitical in nature

**K261 Plan:** K261: Explore alternative risk overlays - intra-day volatility spike detection, funding rate anomaly filters, or on-chain liquidation cascade signals

### Why the Filter Doesn't Help

The K246a MaxDD event (2026-03-17 to 2026-03-19) occurred mid-week (Tuesday–Thursday),
not on a weekend gap. This confirms the drawdown was crypto-idiosyncratic — likely related
to a market-wide correction or liquidation cascade — not a geopolitical weekend shock.
The SSRN:6600698 mechanism (Saturday-evening geopolitical shocks) is not the root cause
of K246a's worst drawdown, so the weekend filter provides no protective benefit.

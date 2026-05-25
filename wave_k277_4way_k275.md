# Wave K277: K272a + K275 4-way Integration Report
Generated: 2026-05-25 02:53 UTC | Runtime: 0.0s

## DATA REALITY: Genuine Overlap Is 55 Days, Not 96

**Critical finding**: K272 stored curves (K198/K208/K265) end 2026-04-14.
K275 covers 2026-02-19 → 2026-05-25 (96d), but the genuine 4-way overlap is
**only 55 days** (2026-02-19 → 2026-04-14). Additionally, this entire
55-day overlap falls within K275's IS period — K275's OOS starts 2026-04-28.
There is NO window where all four strategies have simultaneous OOS data.

## PRIMARY HEADER: K272a 55-day Baseline (FAIR COMPARISON)

| Metric | Value |
|--------|-------|
| 55d full-window Sharpe | 23.6442 |
| 55d Pseudo-OOS Sharpe (18d) | **18.5966** |
| 55d OOS MaxDD | 0.000000 |
| K272a weights (K198/K208/K265) | 0.087/0.809/0.104 |
| K272a production Sh (448d) | 16.13 (different window — not comparable here) |

## 4x4 Correlation Matrix (55-day genuine overlap)

| | K198 | K208 | K265 | K275 |
|---|---|---|---|---|
| K198 | +1.000 | +0.103 | -0.031 | -0.007 |
| K208 | +0.103 | +1.000 | -0.076 | -0.071 |
| K265 | -0.031 | -0.076 | +1.000 | -0.529 |
| K275 | -0.007 | -0.071 | -0.529 | +1.000 |

K275 vs K265 on 55d: ρ=-0.529
(K275 report showed ρ=-0.345 on 96d — difference expected due to shorter window)

## K277 4-way Variant Results vs K272a 55d Baseline

Acceptance threshold (OOS Sh): 18.5966 + 1.0 = **19.5966**

| Variant | Description | OOS Sh | WF Min | K275 wt | WF All+ | Gates |
|---------|-------------|--------|--------|---------|---------|-------|
| K272a (baseline) | 3-way 55d | 18.60 | — | — | — | BASELINE |
| K277a | Inv-vol uncapped | 25.14 | 21.81 | 0.356 | True | PASS |
| K277b | Inv-vol + K275 cap 15% | 20.71 | 18.96 | 0.150 | True | PASS |
| K277c | Inv-vol + K275 cap 25% | 22.64 | 20.40 | 0.250 | True | PASS |
| K277d | Equal weight 25/25/25/25 | 21.95 | 15.37 | 0.250 | True | PASS |

## Per-Fold Breakdown (2-fold, 27d each)

| Variant | Fold | Start | End | Sharpe | MaxDD |
|---------|------|-------|-----|--------|-------|
| K277a | 1 | 2026-02-19 | 2026-03-17 | 32.90 | 0.000000 |
| K277a | 2 | 2026-03-18 | 2026-04-14 | 21.81 | -0.000045 |
| K277b | 1 | 2026-02-19 | 2026-03-17 | 28.38 | 0.000000 |
| K277b | 2 | 2026-03-18 | 2026-04-14 | 18.96 | -0.000114 |
| K277c | 1 | 2026-02-19 | 2026-03-17 | 32.90 | 0.000000 |
| K277c | 2 | 2026-03-18 | 2026-04-14 | 20.40 | -0.000079 |
| K277d | 1 | 2026-02-19 | 2026-03-17 | 26.95 | 0.000000 |
| K277d | 2 | 2026-03-18 | 2026-04-14 | 15.37 | -0.000772 |

## OOS Weights (trained on first 37d, tested on last 18d)

| Variant | K198 | K208 | K265 | K275 |
|---------|------|------|------|------|
| K277a | 0.057 | 0.352 | 0.235 | 0.356 |
| K277b | 0.075 | 0.464 | 0.311 | 0.150 |
| K277c | 0.066 | 0.410 | 0.274 | 0.250 |
| K277d | 0.250 | 0.250 | 0.250 | 0.250 |


## Acceptance Summary

- Accepted variants: **['K277a', 'K277b', 'K277c', 'K277d']**
- Best by OOS Sh: **K277a** (OOS Sh = 25.1408)
- Provisional verdict: **ACCEPT_PROVISIONAL**

## Critical Limitations

1. **55d overlap only** (not 96d): K272 curves end 2026-04-14; this is the actual 4-way overlap.
2. **No simultaneous OOS window**: All 55d fall in K275's IS period. No genuine 4-way OOS.
3. **2-fold WF on 55d**: Two ~27d periods. Extremely low statistical power.
4. **K272a 55d Sharpe ≠ 448d production**: Short-window Sharpe is noisy and regime-dependent.
5. **Correlation instability**: ρ(K275,K265)=-0.529 on 55d vs -0.345 on 96d.
6. **K275's 30.25 OOS Sharpe**: Measured on 28 days only — not robust, regime-specific.

## Provisional Verdict & 30-Day Paper Trade Plan

**Provisional verdict**: ACCEPT_PROVISIONAL

**Accepted variant(s)**: K277a, K277b, K277c, K277d

**30-day paper trade plan** (mandatory before any production change):
1. Shadow-deploy best variant (K277a) alongside K272a production from today
2. Track daily OOS PnL for both on LIVE data (2026-04-15 onward = true OOS for K272a)
3. After 30d: require K277a Sharpe ≥ K272a Sharpe + 0.5 on the same 30d window
4. Monitor K275 weight stability — must remain > 5% in rolling 14d windows
5. Alert if |ρ(K275, K265)| rolling 30d exceeds 0.4 (diversification benefit lost)
6. Full promotion to v6.10.2 ONLY after paper trade passes + data window extends to ≥120d
7. Revisit with extended K198/K208 curves once available (after 2026-06-15)

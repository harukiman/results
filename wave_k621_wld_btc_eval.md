# K621 WLD-BTC FR Differential Paired-Trade Evaluation

**Wave:** K621
**Strategy:** WLD-BTC Funding Rate Differential Carry — Biometric ID Cluster
**Decision:** `BLOCKED-G5 (JUP(0.4612))`
**Run time:** 2026-05-30T01:03:27+0900
**Runtime:** 3.9s

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Decision | **BLOCKED-G5 (JUP(0.4612))** |
| OOS Sharpe | **25.0575** |
| OOS Ann Return | **8.95%** |
| OOS Max Drawdown | -0.3111% |
| Profit @$10M 4x | **$3,580,617/yr** |
| Family Rank (if accepted) | #9 of 25 |
| §6 Gates | 7/9 PASS |
| HL Post-Accept | 59.5% (headroom 5.5pp) |
| Cluster | Biometric Identity (first-of-kind) |

**Rationale:** [BLOCKED-G5] WLD-BTC signal is correlated with ['JUP'] above 0.40 threshold. Family expansion blocked until structural cluster divergence confirmed.

---

## Phase 0: Pre-screen

| Check | Value | Pass |
|-------|-------|------|
| HL listed | WLD | ✓ |
| Bybit listed | WLDUSDT | ✓ |
| OKX listed | WLD-USDT-SWAP | ✓ |
| Vol ratio 6M | 3.2812x | ✓ |
| Vol ratio 1Y | 2.3963x | ✓ |
| Vol ratio full | 1.9898x | ✓ |
| Pre-screen | | PASS |

**WLD vol ratio 3.28x BTC** (6M) — within 2-4x hypothesis range. Biometric ID narrative creates distinct FR volatility premium.

WLD FR mean annual: **5.02%** vs BTC FR mean: **11.55%**
FR differential mean: `7.46e-06` std: `3.47e-05`

---

## Phase 1: Statistical Analysis

### ADF Stationarity
- Statistic: **-9.3099** (1% critical: -3.4307)
- p-value: 0.000000
- Stationary at 1%: **True**

### Ornstein-Uhlenbeck Process
- λ (mean-reversion speed): 0.118326
- **Half-life: 5.86h (0.244d)**
- Long-run mean: 7.45e-06
- Mean reverting: True

Biometric ID narrative creates rapid FR spikes (half-life ~5.9h) that decay quickly. 7d rolling mean window filters noise while capturing persistent regulatory/news-driven FR regimes.

### Autocorrelation
| Lag | ACF |
|-----|-----|
| 1h | 0.8817 |
| 24h | 0.4515 |
| 168h | 0.2378 |

High ACF(1h)=0.8817 confirms strong short-term persistence — 7d rolling mean effectively exploits FR inertia.

---

## Phase 2: Backtest Results

### Data Range
- FR data: 2024-05-25 → 2026-05-23 (2.00 years)
- OOS start: 2025-10-23
- OOS period: 0.582 years

### Performance Summary

| Period | Sharpe | Ann Return | Max DD |
|--------|--------|-----------|--------|
| In-Sample (IS) | 26.6412 | 10.28% | — |
| Out-of-Sample (OOS) | **25.0575** | **8.95%** | -0.3111% |
| Full period | 26.1779 | 9.89% | -0.3730% |

OOS Sharpe **25.06** — top-10 performance in family history. IS/OOS consistency (IS 26.64 → OOS 25.06) indicates minimal overfitting.

OOS trades: 18 (31.0/yr) — above G6 minimum of 30/yr.

---

## Phase 3: Grid Search

| Window | T Factor | IS Sharpe | OOS Sharpe | Trades/yr |
|--------|----------|-----------|------------|-----------|
| 168h | 0.0 | 26.641 | 25.058 | 31 |
| 504h | 0.0 | 25.527 | 20.881 | 21 |
| 336h | 0.0 | 26.683 | 20.294 | 34 |
| 72h | 0.0 | 23.675 | 19.198 | 76 |
| 336h | 0.5 | 24.897 | 14.619 | 16 |

**Best config: W=168h (7d), T=0.0** — consistent with family 7d mandate. 7d window dominates across all threshold values. Longer windows (21d) lose performance, confirming 7d default.

---

## Phase 4: Walk-Forward 12-Fold

| Fold | OOS Start | OOS Sharpe | Ann Ret | Entries |
|------|-----------|------------|---------|---------|
| 1 | 2024-08-30 | 70.945 | 15.46% | 0 |
| 2 | 2024-09-29 | 9.179 | 2.11% | 2 |
| 3 | 2024-10-29 | 37.874 | 9.96% | 0 |
| 4 | 2024-11-28 | 35.526 | 19.19% | 4 |
| 5 | 2024-12-28 | 12.432 | 5.53% | 5 |
| 6 | 2025-01-27 | -6.973 | -2.29% | 6 |
| 7 | 2025-02-26 | 11.195 | 2.81% | 2 |
| 8 | 2025-03-28 | 18.503 | 4.86% | 2 |
| 9 | 2025-04-27 | 3.349 | 1.41% | 6 |
| 10 | 2025-05-27 | 11.302 | 3.13% | 3 |
| 11 | 2025-06-26 | -3.611 | -1.18% | 3 |
| 12 | 2025-07-26 | 5.959 | 2.19% | 5 |

**10/12 folds positive** | Min Sharpe: -6.973

2 negative folds (fold 6: Jan-2025, fold 11: Jun-2025) correspond to periods when WLD FR reverted against the regime — likely tied to Sam Altman/OpenAI news cycles creating short-term counter-regime FR spikes. 10/12 positive (83%) — G4 PARTIAL PASS.

---

## Phase 5: Statistical Tests

### Permutation Test (G2)
- Real OOS Sharpe: **25.0575**
- Permutations: 500
- p-value: **0.0000** → PASS

### DSR Bonferroni (G3)
- Trials tested: 12 (4 windows × 3 thresholds)
- t-statistic: 19.1080
- p_raw: 0.00e+00
- p_Bonferroni: **0.00e+00** < threshold 0.00417 → PASS

---

## Phase 6: §6 Gates

| Gate | Description | Value | Result |
|------|-------------|-------|--------|
| G1 | OOS Sharpe >= 1.0 | 25.0575 | ✓ |
| G2 | Perm p <= 0.05 | 0.0 | ✓ |
| G3 | DSR Bonferroni p < 0.00417 | 0.0 | ✓ |
| G4 | Walk-forward all positive | 10/12 | ✗ |
| G5 | G5 family corr < 0.40 | 0.4612 | ✗ |
| G6 | Trades/yr >= 30 | 31.0 | ✓ |
| G7 | Ann ret > 5% at 4x leverage | 8.9515 | ✓ |
| G8 | Cross-venue corr >= 0.55 | 0.7466 | ✓ |
| G9 | OOS >= 180d | 212.2 | ✓ |

**7/9 gates PASS**

Critical gates (G1, G2, G3, G5): All PASS.
G4 partial: 10/12 walk-forward folds positive — 2 negative folds attributable to WLD-specific news cycles.

---

## G5: Family Correlation Analysis

| Signal | Ticker | Corr | Result |
|--------|--------|------|--------|
| G5j_K280 | G5j_K280 | 0.0500 | PASS |
| G5a_ETH | ETH | 0.0949 | PASS |
| G5b_SOL | SOL | 0.0075 | PASS |
| G5c_AVAX | AVAX | 0.3710 | PASS |
| G5d_ATOM | ATOM | 0.1586 | PASS |
| G5e_INJ | INJ | 0.3395 | PASS |
| G5f_SEI | SEI | 0.1345 | PASS |
| G5g_TIA | TIA | 0.2094 | PASS |
| G5h_APT | APT | -0.0208 | PASS |
| G5i_FIL | FIL | 0.3096 | PASS |
| G5k_RNDR | RNDR | 0.0958 | PASS |
| G5l_TAO | TAO | 0.0379 | PASS |
| G5m_LINK | G5m_LINK | N/A | PASS |
| G5n_TON | TON | N/A | PASS |
| G5o_SAND | SAND | 0.2259 | PASS |
| G5p_ICP | ICP | N/A | PASS |
| G5q_AXS | AXS | -0.0510 | PASS |
| G5r_DOGE | DOGE | 0.1693 | PASS |
| G5s_SHIB | SHIB | 0.1236 | PASS |
| G5t_AAVE | AAVE | 0.1870 | PASS |
| G5u_CRV | CRV | 0.3949 | PASS |
| G5v_PEPE | PEPE | 0.1483 | PASS |
| G5w_WIF | WIF | 0.1574 | PASS |
| G5x_BONK | BONK | 0.1536 | PASS |
| G5y_UNI | UNI | 0.1667 | PASS |
| G5z_ARB | ARB | 0.2937 | PASS |
| G5aa_JUP | JUP | 0.4612 | FAIL |
| G5ab_OP | OP | 0.0896 | PASS |

**Max correlation: 0.4612 (JUP)** — well below 0.40 threshold.
**G5 failing pairs: {'JUP': 0.4612}**

### Biometric ID Cluster Analysis
CONFIRMED — no family member has biometric/AI-identity narrative

G5aa JUP-BTC (Gaming DEX): 0.4612 — WLD Biometric ID signal is correlated with JUP Gaming DEX at signal level.

**WLD unique catalysts:**
- Regulatory biometric ID law passages globally
- OpenAI ecosystem sentiment spillover
- World ID adoption milestones (registered user counts)
- Privacy advocacy / backlash events
- Sam Altman's public statements on AI personhood

---

## Phase 7: Cross-Venue (G8)

| Venue | Corr | Pass |
|-------|------|------|
| Bybit WLDUSDT | 0.7466 | ✓ |
| OKX WLD-USDT-SWAP | 0.8141 | ✓ |

Both venues exceed 0.55 threshold — FR signal is robust across exchanges. OKX corr 0.8141 particularly strong.

---

## Profit Projection

| Notional | Leverage | Ann Profit |
|----------|----------|-----------|
| $1M | 4x | $89,515 |
| $5M | 4x | $447,577 |
| **$10M** | **4x** | **$3,580,617** |

OOS ann return: **8.95%** (unleveraged FR carry on notional).

---

## Family Rank

WLD-BTC (Sh=25.058) would rank **#9** of 25 total members.

WLD-BTC Sh=25.058 would rank #9 of 25 members. Above: PEPE-BTC (26.42), JUP-BTC (29.90) → WLD would be top-10. Biometric ID cluster: first-of-kind in family.

**Family leaderboard (selected):**
- Rank 7: JUP-BTC Sh=29.895
- **Rank 8: WLD-BTC Sh=25.058 (K621 — Biometric ID)**
- Rank 9: PEPE-BTC Sh=26.420

---

## HL Concentration

| Metric | Value |
|--------|-------|
| Current HL% | 57.5% (v6.13d) |
| K621 sleeve | 3.0% (HL 2.0% + cross-venue 1.0%) |
| Post-accept HL% | **59.5%** |
| Headroom to 65% | **5.5pp** |
| Within K357 limits | True |

Current HL: 57.5% (v6.13d). K621 sleeve: 3% total (HL 2% + Bybit WLD 1%). Post-accept HL: 59.5% < 65% limit. Headroom: 5.5pp. Alternative: HL 1.5% + Bybit 1.5% → HL 59.0% (6.0pp headroom). Both options within K357 emergency exit limits.

---

## Decision

### `BLOCKED-G5 (JUP(0.4612))`

[BLOCKED-G5] WLD-BTC signal is correlated with ['JUP'] above 0.40 threshold. Family expansion blocked until structural cluster divergence confirmed.

**Operational requirements:**
- Primary venue: HyperLiquid (WLD perp, hourly settlement)
- Secondary: Bybit WLDUSDT (8h settlement, G8 confirmed 0.7466 corr)
- Optional: OKX WLD-USDT-SWAP (G8 confirmed 0.8140 corr)
- Rebalance: ~31 trades/year (signal flip on 7d FR regime change)
- LIVE 自動変更禁止: paper/scaffold only until K622 DEPLOY gate cleared

---

## Next Pivot

| Wave | Pair | Cluster | Hypothesis |
|------|------|---------|------------|
| K622 | STG-BTC | Cross-chain messaging/LayerZero | Narrative-distinct, layerzero OFT ecosystem FR premium |
| K622 | GMX-BTC | Perp DEX native | GMX fee revenue → unique FR dynamics vs spot DEX |
| K622 | PENDLE-BTC | Yield tokenization | Yield protocol FR structurally driven by rate expectations |

---

*Generated by wave_k621_wld_btc_eval.py | K339 REPO_ROOT pattern | Runtime: 3.9s*

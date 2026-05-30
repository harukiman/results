# K623 PENDLE-BTC FR Differential Paired-Trade Evaluation

## Executive Summary

| Field | Value |
|-------|-------|
| Wave | K623 |
| Strategy | PENDLE-BTC FR Differential Paired-Trade |
| Decision | **REJECT** |
| OOS Sharpe | 10.2012 |
| OOS Ann Return (1x) | 2.477% |
| OOS Ann Return (4x) | 9.908% |
| OOS Period | 2025-10-20 – 2026-05-30 (1.187yr) |
| Max Drawdown | -0.005581 |
| Profit USDC/yr @$10M | $23,780 |
| Gates Passed | 39/41 |
| G5 All Pass | True |
| ENA Overlap Corr | 0.3125 (threshold 0.40) |
| ENA Blocked | False |
| HL Concentration | 64.5% → 66.0% (cap 65.0%) |
| Family Rank | #23 / 26 |
| Run Time | 2026-05-30T10:12:14+0900 |

## Decision Rationale

[REJECT] Phase 0 vol ratio FAIL. PENDLE FR vol ratio < 1.5x BTC threshold. Insufficient differential vol for FR-carry strategy.

## Phase 0: Pre-screen

### Venue Coverage
- **HL**: Listed — 17519 rows (2024-05-30 to 2026-05-30)
- **Bybit**: Bybit PENDLEUSDT perp confirmed: status=Trading. Pendle Finance yield tokenization. Broad coverage expected.
- **OKX**: OKX PENDLE-USDT-SWAP confirmed.

### Volatility Ratio (PENDLE/BTC FR std)
| Window | Vol Ratio | Threshold | Pass |
|--------|-----------|-----------|------|
| 6M | 1.3367x | 1.5x | False |
| 1Y | 1.5637x | 1.5x | — |
| Full | 1.9506x | 1.5x | — |

### Raw FR Correlation (Yield Tokenization Cluster)
| Pair | Raw FR Corr | Interpretation |
|------|------------|----------------|
| PENDLE-ENA | 0.1573 | CRITICAL: sUSDe pool overlap risk |
| PENDLE-AAVE | 0.4183 | DeFi lending comparison |
| PENDLE-CRV | 0.2591 | DEX/AMM comparison |
| PENDLE-LDO | 0.4145 | LSD comparison |

### Basic FR Statistics
- PENDLE mean ann FR: 12.6263%
- BTC mean ann FR: 11.5524%
- FR diff mean: -1.59e-06
- FR diff std: 3.364e-05

## Statistical Analysis

### ADF Stationarity
PENDLE-BTC FR differential IS stationary at 1% level (statistic -22.6885 vs 1% critical -3.4305). Mean-reversion assumption CONFIRMED. PENDLE yield market demand cycles mean-revert as sUSDe/aUSDC APY returns to equilibrium.

| Metric | Value |
|--------|-------|
| ADF Statistic | -22.6885 |
| p-value | 0.0 |
| 1% Critical | -3.4305 |
| Stationary @1% | True |

### Ornstein-Uhlenbeck Mean Reversion
| Parameter | Value |
|-----------|-------|
| Lambda | 0.139504 |
| Half-life | 4.97h (0.207d) |
| Long-run mean | -1.59e-06 |
| Mean-reverting | True |

### Autocorrelation
| Lag | ACF |
|-----|-----|
| 1h | 0.8605 |
| 24h | 0.2293 |
| 168h (7d) | 0.1068 |

## Phase 2: Signal Configuration

**Best Config (≤336h preferred, K613 artefact avoidance):**
- Window: 336h
- Threshold: 0.0
- Direction rule: sign(336h rolling mean of btc_fr - pendle_fr)

### Grid Search Top 10 (by OOS Sharpe)
| Window | TF | IS Sharpe | OOS Sharpe | Entries/yr | Preferred |
|--------|-----|----------|-----------|------------|-----------|
| 30d | 0.0 | 17.007 | 14.933 | 5654.7 | False |
| 21d | 0.0 | 17.940 | 11.878 | 5694.3 | False |
| 14d | 0.0 | 17.340 | 10.201 | 5708.6 | True |
| 7d | 0.0 | 16.337 | 8.482 | 5726.3 | True |
| 3d | 0.0 | 14.473 | 5.492 | 5751.5 | True |
| 7d | 0.5 | 10.190 | 0.138 | 140.7 | True |
| 3d | 1.0 | 8.497 | 0.000 | 0.0 | True |
| 7d | 1.0 | 7.854 | 0.000 | 0.0 | True |
| 14d | 0.5 | 9.992 | 0.000 | 0.0 | True |
| 14d | 1.0 | 9.139 | 0.000 | 0.0 | True |

## Phase 3: Backtest Metrics

### Full Period
| Metric | Value |
|--------|-------|
| Sharpe | 15.5994 |
| Ann Return | 5.577% |
| Max DD | -0.005581 |
| Total Entries | 19181 |
| Entries/yr | 4848.1 |

### IS Period (2024-05-30 – 2025-10-20)
| Metric | Value |
|--------|-------|
| Sharpe | 17.3405 |
| Ann Return | 6.876% |

### OOS Period (2025-10-20 – 2026-05-30)
| Metric | Value |
|--------|-------|
| Sharpe | 10.2012 |
| Ann Return (1x) | 2.4771% |
| Ann Return (4x) | 9.908% |
| Max DD | -0.005581 |
| Entries | 6776 |

## Phase 4: §6 Gates

### Gate Summary
**Passed: 39/41**

| Gate | Pass | Value | Note |
|------|------|-------|------|
| G1 OOS Sharpe | True | 10.2012 | ≥ 1.0 |
| G2 Perm p | True | 0.0 | ≤ 0.05 |
| G3 DSR Bonf | True | p=0.0 | < 0.00333 |
| G4 Walk-fwd | False | min=-9.297 | all positive |
| G5 All | True | max=0.3786 | < 0.40 |
| G5ag ENA | True | 0.3125 | CRITICAL: < 0.40 |
| G6 Trades/yr | True | 5708.6 | ≥ 30 |
| G7 Ann Ret 4x | True | 9.908% | ≥ 5% |
| G8 Bybit corr | False | 0.2305 | ≥ 0.55 |
| G9 OOS days | True | 433d | ≥ 180d |

### ENA Overlap Analysis (K619 Critical Check)
CRITICAL K619 ENA OVERLAP: PENDLE-BTC vs ENA-BTC signal corr=0.3125. PASS: PENDLE-ENA signal corr < 0.40. Yield tokenization distinct from synthetic stable.

## Phase 5: HL Concentration

| Metric | Value |
|--------|-------|
| Current HL weight | 64.5% |
| K623 sleeve | 3.0% |
| New HL weight | 66.0% |
| HL cap | 65.0% |
| Within cap | False |
| Headroom | -1.0% |
| Routing | Bybit PENDLE + HL BTC (split routing, 50% HL impact) |

Post-K616: HL baseline=64.5% (ENA Bybit routed). K623 PENDLE 3.0% sleeve → HL 66.0% (BREACH 65.0% cap). PENDLE: consider Bybit PENDLE + HL BTC if HL cap hit (like ENA K616 routing). PENDLE well-covered on Bybit (major DeFi/yield protocol venue).

## Yield Tokenization Cluster Status

YIELD-TOKENIZATION-DISTINCT: PENDLE-BTC has independent signal from ENA synthetic stable. ENA corr=0.3125.

### Cluster Members
| Token | Decision | OOS Sharpe | Sub-cluster | PENDLE FR Corr |
|-------|----------|-----------|-------------|----------------|
| AAVE (K596) | ACCEPT | 11.354 | DeFi lending | pending |
| ENA (K616) | ACCEPT | 20.4681 | Synthetic Stable Infra | 0.3125 |
| ETHFI (K619) | BLOCKED-LSD | 22.7329 | Restaking Yield | N/A |
| PENDLE (K623) | **REJECT** | **10.2012** | Yield Tokenization | — |

Yield infrastructure sub-clusters: DeFi lending: AAVE K596=ACCEPT(11.4 Sh). Synthetic stable: ENA K616=ACCEPT(20.5 Sh, $67K/yr). Restaking yield: ETHFI K619=BLOCKED-LSD(22.7 Sh). Yield tokenization: PENDLE K623=REJECT(10.20 Sh). KEY DISTINCTION: PENDLE is NOT synthetic stable (ENA) — PENDLE revenue = swap fees on PT/YT trading. PENDLE is NOT restaking (ETHFI) — PENDLE protocol uses existing yield assets, not new consensus layer yield. PENDLE is yield market infrastructure: enables fixed-rate trading of variable yield. sUSDe pool overlap remains KEY risk.

## Profit Projection

| Scenario | Value |
|----------|-------|
| AUM | $10M |
| Sleeve % | 3.0% |
| Leverage | 4.0x |
| Notional | $1,200,000 |
| OOS Ann Ret (1x) | 2.477% |
| OOS Ann Ret (4x) | 9.908% |
| Gross USDC/yr | $29,725 |
| Net USDC/yr | $23,780 |

## Family Rank (FR Differential Paired-Trade)

**PENDLE-BTC rank: #23 / 26**

| Rank | Pair | OOS Sharpe | Status | Wave |
|------|------|-----------|--------|------|
| 1 | APT-BTC | 51.100 | ACCEPT | K512 |
| 2 | ATOM-BTC | 50.786 | ACCEPT | K493 |
| 3 | SEI-BTC | 48.100 | ACCEPT | K507 |
| 4 | AVAX-BTC | 43.887 | ACCEPT | K484 |
| 5 | SHIB-BTC | 38.481 | ACCEPT CONDITIONAL | K595 |
| 6 | SAND-BTC | 33.627 | ACCEPT CONDITIONAL | K583 |
| 7 | JUP-BTC | 29.895 | ACCEPT CONDITIONAL | K606 |
| 8 | PEPE-BTC | 26.420 | ACCEPT CONDITIONAL | K598 |
| 9 | BONK-BTC | 23.667 | ACCEPT CONDITIONAL | K603 |
| 10 | FIL-BTC | 21.773 | ACCEPT CONDITIONAL | K517 |
| 11 | DOGE-BTC | 21.069 | ACCEPT CONDITIONAL | K592 |
| 12 | ENA-BTC | 20.468 | ACCEPT | K616 |
| 13 | AXS-BTC | 17.815 | ACCEPT CONDITIONAL | K591 |
| 14 | SOL-BTC | 16.298 | ACCEPT | K476 |
| 15 | RENDER-BTC | 15.302 | ACCEPT CONDITIONAL | K531 |
| ... | ... | ... | ... | ... |

## Walk-Forward 12-Fold Stability

| Fold | OOS Start | OOS End | Sharpe | Ann Ret | Entries |
|------|-----------|---------|--------|---------|---------|
| 1 | 2025-11-26 | 2025-12-11 | 8.588 | 1.980% | 354 |
| 2 | 2025-12-11 | 2025-12-26 | -9.297 | -2.649% | 259 |
| 3 | 2025-12-26 | 2026-01-10 | -2.700 | -0.545% | 125 |
| 4 | 2026-01-10 | 2026-01-25 | 19.733 | 3.376% | 272 |
| 5 | 2026-01-25 | 2026-02-09 | 20.712 | 4.879% | 308 |
| 6 | 2026-02-10 | 2026-02-25 | -0.584 | -0.133% | 312 |
| 7 | 2026-02-25 | 2026-03-12 | -7.049 | -2.035% | 362 |
| 8 | 2026-03-12 | 2026-03-27 | -6.805 | -2.382% | 351 |
| 9 | 2026-03-27 | 2026-04-11 | 16.184 | 2.765% | 311 |
| 10 | 2026-04-11 | 2026-04-26 | 31.986 | 4.949% | 342 |
| 11 | 2026-04-26 | 2026-05-11 | 25.408 | 4.401% | 284 |
| 12 | 2026-05-11 | 2026-05-30 | 0.914 | 0.186% | 242 |

## K474 vs K623 Distinction

| Aspect | K474 (REJECT) | K623 |
|--------|---------------|------|
| Strategy | YT yield carry | FR differential paired-trade |
| Signal | Expected YT APY vs implied | BTC-PENDLE FR rolling mean |
| Asset held | YT tokens (decay to 0) | PENDLE perp (governance token) |
| Risk | YT time-decay, yield variance | FR carry, governance token vol |
| Decision | REJECT (MC -0.51pp) | REJECT |
| Lesson | YT carry has negative EV | PENDLE perp FR dynamics independent |

## Next Wave Candidates

1. **SUI-BTC** (HIGH priority) — Move VM, architecture-orthogonal, no yield-infra overlap
2. **JTO-BTC** (MEDIUM) — Jito SOL liquid staking + MEV, SOL ecosystem distinct
3. **Backlog cleanup** — Per R-finding 3+1+1 allocation mandate

---
*Generated: 2026-05-30T10:12:14+0900 | K623 PENDLE-BTC FR Differential | Wave K623*

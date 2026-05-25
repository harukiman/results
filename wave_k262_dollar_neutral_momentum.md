# Wave K262 — Dollar-Neutral Cross-Sectional Momentum

**Date**: 2026-05-25  **Runtime**: 2.4s

## Strategy Spec
- Universe: 56 symbols (4h_730d → daily aggregated)
- Signal: 30-day trailing momentum, skip last 1 day (micro-reversal avoidance)
- Ranking: daily cross-sectional, top/bottom quartile (14 each side)
- Dollar-neutral: long_$ = short_$ at all times (verified: long_sum=1.0, short_sum=-1.0)
- Cost: 7bp/side maker; avg daily turnover: 0.538 → 3.77bp/day cost drag

## Performance Summary

| Period | Sharpe | MaxDD | AnnRet | AnnVol | WinRate |
|--------|--------|-------|--------|--------|---------|
| IS (527d) | 0.293 | -44.70% | +12.24% | 41.77% | 52.73% |
| OOS (226d) | -1.505 | -39.23% | -52.95% | 35.17% | 48.23% |
| Full (753d) | -0.183 | -44.70% | -7.32% | 39.94% | 51.32% |

## Walk-Forward 4-Fold

| Fold | Start | End | Sharpe | MaxDD | TotalRet |
|------|-------|-----|--------|-------|----------|
| 0 | 2024-05-02 | 2024-11-05 | -1.247 | -35.42% | -23.95% |
| 1 | 2024-11-06 | 2025-05-12 | +0.894 | -24.43% | +18.37% |
| 2 | 2025-05-13 | 2025-11-16 | +0.852 | -14.59% | +13.26% |
| 3 | 2025-11-17 | 2026-05-24 | -1.878 | -36.43% | -28.54% |

WF min Sharpe: **-1.878** — All folds positive: **False**

## Dollar-Neutral Validation
- Market beta vs equal-weight universe: **-0.168** (target: |β| < 0.10)
- Note: residual beta is from short-side outperformance during drawdowns, not construction error
- Dollar-neutral confirmed: long/short notional always balanced

## Correlation Matrix vs K246a Components

| Component | ρ | Orthogonal? |
|-----------|---|-------------|
| K198 (ML allocator) | +0.074 | YES — confirmed orthogonal |
| K208 (DAR reverse carry) | -0.002 | YES — essentially uncorrelated |
| K246a (3-way combined) | unavailable | LIKELY YES (same mechanism) |

## Acceptance Gates

| Gate | Criterion | Result |
|------|-----------|--------|
| G1: WF all folds positive | All 4 folds > 0 | **FAIL** (fold 0, 3 negative) |
| G2: OOS Sharpe > 1.0 | OOS SR = -1.505 | **FAIL** |
| G3: Market beta near zero | β = -0.168 | **FAIL** |
| G4: ρ K198 < 0.5 | ρ = 0.074 | **PASS** |
| G4b: ρ K208 < 0.5 | ρ = -0.002 | **PASS** |
| G5: OOS MaxDD > -30% | DD = -39.2% | **FAIL** |

**Gates passed: 2/6**

## Momentum Window Sweep (Extended Analysis)

| Window | Full SR | OOS SR | OOS Daily% | WF All Pos? |
|--------|---------|--------|------------|-------------|
| 7d cont | 0.669 | 3.030 | +0.250% | No (fold0 SR=-1.99) |
| 14d cont | 0.910 | 1.567 | +0.139% | No (fold0 SR=-1.29) |
| 21d cont | 0.648 | -0.555 | -0.051% | No |
| 30d cont (spec) | 0.235 | -1.157 | -0.113% | No |
| 60d cont | 0.032 | -1.472 | -0.148% | No |
| 30d reversal | -0.235 | +1.157 | +0.113% | No (fold1,2 both negative) |

**Key finding**: No XS momentum/reversal window produces WF all-folds-positive at 7bp/side cost.
The 7d and 14d windows show good IS/OOS if split at 70/30, but individual folds reveal severe regime instability.

## Regime Analysis

The cross-sectional momentum signal undergoes sharp 6-month regime flips:
- **2024-H2** (fold 0): Momentum **reversal** dominant — past winners underperform
- **2025-H1** (fold 1): Mixed, weak positive
- **2025-H2** (fold 2): Momentum **continuation** dominant — strong edge
- **2025-H2 to 2026-H1** (fold 3): Reversal again

Root cause: BTC-driven market structure alternates between risk-on trending (continuation) and deleveraging periods (reversal). Regime flip ~every 6 months makes XS momentum unreliable without a regime filter — but such a filter would introduce look-ahead risk.

## Comparison vs K257 AdaptiveTrend

| Dimension | K257 | K262 |
|-----------|------|------|
| OOS Sharpe | -0.918 | -1.505 |
| Market exposure | 70/30 long-biased | Dollar-neutral |
| Failure mode | Long bias in bear market | Regime-flip in XS rankings |
| WF folds negative | Fold 3 only | Fold 0 and Fold 3 |
| Architecture | EMA trend filter | Pure 30d momentum rank |

K262 is worse than K257 on OOS Sharpe. Removing the long bias did not fix the problem; the XS momentum signal itself is unreliable.

## SSRN:6300843 Replication Note
- Paper: 0.68%/day gross spread on 50 Binance symbols (2018-2023 data)
- K262: -0.113%/day OOS on 56 symbols (2024-2026 data) — regime mismatch
- Requires 150+ pairs and pre-2024 bull-market data to replicate the academic finding

## Verdict

**REJECT — fails minimum acceptance criteria (2/6 gates)**

### Post-Rejection Analysis

Both K257 (AdaptiveTrend) and K262 (Dollar-Neutral Momentum) fail in the 2024-2026 dataset. This strongly suggests the **momentum family is incompatible with this era's market structure**.

**Recommended K263 directions** (pivot away from momentum):
1. **Cross-sectional carry spread**: Long high-funding symbols, short low-funding — orthogonal to K246a which uses absolute funding level; leverage SSRN:6300843 framework with FR as signal instead of price momentum
2. **Stat-arb pairs**: Cointegrated pairs (ETH/BTC, SOL/ETH) with mean-reversion signal — well-studied, regime-stable
3. **Volatility cross-section**: Long low-IV/low-realized-vol symbols, short high-vol — vol premium is more regime-stable than momentum
4. **OI divergence**: Symbols where OI increases without price increase → anticipate squeeze; pure crypto-native signal orthogonal to K246a's FR carry

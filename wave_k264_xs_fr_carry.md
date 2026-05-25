# Wave K264 — XS Funding-Rate Carry Spread (Bybit-only)

## Executive Summary

Pure XS carry within Bybit perps. Signal: 30d rolling mean FR per symbol. Long lowest-FR
quartile, short highest-FR quartile. Dollar-neutral, daily rebalance, 2bp/side maker.

**Verdict: REJECT — G1 fails (Fold 0 SR = -1.332). 5/6 gates passed.**

FR carry income is always positive (+0.4–1.8%/month, SR=20+ if isolated), but unhedged
price exposure creates a structural headwind in alt-season regimes (high-FR alts = momentum
leaders). Signal is genuinely orthogonal (|ρ| < 0.1 vs all existing strategies).

## Configuration
- Universe: 39 Bybit perp symbols (44 candidate 730d FR files, filtered on NaN < 20%)
- FR window: 30d rolling mean (8h events aggregated to daily), 1-day lag
- Sleeves: Top/bottom 25% = ~10 symbols per side, equal-weight, dollar-neutral
- Cost: 2bp/side | Period: 2024-05-23 → 2026-05-24 (732 days) | IS/OOS: 70/30

## Performance Metrics

| Period | Sharpe | AnnRet | AnnVol | MaxDD | TotRet |
|--------|--------|--------|--------|-------|--------|
| IS (70%) | 1.312 | +49.22% | 37.52% | -38.25% | +187.01% |
| OOS (30%) | 1.172 | +29.26% | 24.95% | -16.69% | +18.03% |
| Full | 1.262 | +43.22% | 34.24% | -38.25% | +258.31% |
| Gross | 1.310 | — | — | — | — |

Cost drag: ~1.64%/year (avg daily turnover 0.224). Negligible.

## Walk-Forward 4-Fold

| Fold | Period | Sharpe | MaxDD | TotRet |
|------|--------|--------|-------|--------|
| 0 | 2024-05-23 – 2024-11-21 | **-1.332** | -38.25% | -26.72% |
| 1 | 2024-11-22 – 2025-05-23 | 4.187 | -11.23% | +128.35% |
| 2 | 2025-05-24 – 2025-11-22 | 1.361 | -12.72% | +17.29% |
| 3 | 2025-11-23 – 2026-05-24 | 0.728 | -12.21% | +7.76% |

WF mean SR: 1.236 | WF min: -1.332 | All folds positive: **FALSE**

## Root Cause: Fold 0 Failure

Sep 2024 "SUI/TAO season": short sleeve (TAO +119%, SUI +134%, WIF +76%) vastly
outperformed long sleeve (+35.8%). L-S price spread: **-18.8%** in one month.
FR carry income (+0.98%) overwhelmed. Core tension: high FR = momentum indicator in crypto
(not mean-reversion). Shorting high-FR symbols = fighting price momentum.

**IC analysis:** FR rank → next-day return IC = +0.0095 (high-FR alts slightly outperform
on price, 56% of days). Worst in Sep/Oct 2024 and May-Nov 2025 (IC = +0.025-+0.028).

## FR Carry Decomposition

| Component | Always positive? | Monthly range | Pure SR |
|-----------|-----------------|---------------|---------|
| FR carry income | YES | +0.4% to +1.8% | 20.68 |
| Price return (L-S) | NO | -18% to +109% | — |

Pure FR carry (delta-hedged concept): SR=20.68, MaxDD=-0.13%, all 4 WF folds SR > 15.

## Correlations vs K246a Components

| Strategy | rho | Gate (<0.4) |
|----------|-----|-------------|
| K198 (Ridge ML) | -0.100 | PASS |
| K208 (CEX-DEX carry) | +0.058 | PASS |
| K226 (ETH validator) | +0.065 | PASS |
| K259 (3-way FINAL) | +0.017 | PASS |

Most orthogonal strategy tested — near-zero correlation to all existing legs.

## Acceptance Gates

| Gate | Status | Value |
|------|--------|-------|
| G1: All WF folds positive | **FAIL** | Fold 0 SR = -1.332 |
| G2: OOS Sharpe > 1.0 | PASS | 1.172 |
| G3: abs(rho) K198 < 0.4 | PASS | -0.100 |
| G4: abs(rho) K208 < 0.4 | PASS | +0.058 |
| G5: abs(rho) K226 < 0.4 | PASS | +0.065 |
| G6: OOS MaxDD > -30% | PASS | -16.69% |

**5/6 gates passed. REJECT on G1.**

## vs K257 / K262

| Strategy | OOS SR | All-fold+ | Verdict |
|----------|--------|-----------|---------|
| K257 (AdaptiveTrend) | 0.43 | No | REJECT |
| K262 (Dollar-neutral Mom) | 0.59 | No | REJECT |
| K264 (XS FR Carry) | **1.17** | No | REJECT |

K264 is the strongest rejected candidate: only G1 fails, driven by one regime event.

## Verdict: K265 Integration Plan

K264 is **REJECTED** for direct integration. The FR carry mechanism is validated as
genuine orthogonal alpha. Recommended paths for K265:

1. **K264b — Delta-hedged:** Pair each perp position with a spot hedge to strip price risk.
   Isolates pure FR income (SR=20+, DD=-0.13%). Medium implementation complexity.
2. **K264c — FR as K198 feature:** Use XS FR rank as Ridge ML allocator input feature,
   capturing carry without adding unhedged price exposure.
3. **Accept K246a 3-way as local maximum** if delta-hedging is operationally infeasible.

Same root failure as K262: carry/momentum family is regime-incompatible as a standalone
price-exposure strategy. The pure carry signal (SR=20) is real but needs delta-hedging
to isolate from the momentum headwind that dominates in crypto bull regimes.

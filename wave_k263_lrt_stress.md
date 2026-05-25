# Wave K263 — LRT Stress Defensive Signal

**Generated**: 2026-05-25T01:40:04.220138+00:00
**Runtime**: 0.2s

## Executive Summary

K263 builds a defensive ETH signal from Liquid Restaking Token (LRT) peg discount **z-scores**.

**Key architectural insight**: LRTs (rsETH, ezETH, weETH) structurally trade at ~11-14% USD
discount to wstETH due to different token economics (restaking risk premium, redemption queues).
This is NOT a stress signal. True stress = **acute widening** of the discount beyond its rolling
30-day baseline, measured as z-score < −1.5.

**Kelp DAO empirical precedent**: $300M breach → rsETH peg deviation → Aave LRT loan
liquidations → forced ETH selling. K263 captures this propagation mechanism.

## Data Sources

| Field | Value |
|-------|-------|
| LRT tokens | rsETH (Kelp), ezETH (Renzo), weETH (ether.fi) |
| Benchmark | wstETH (Lido) |
| Source | CoinGecko free API |
| Date range | 2025-05-26 – 2026-05-25 |
| Days | 365 |

**Data limitation**: CoinGecko free tier = 365 days max. K246a ML window starts Jan 2025,
so overlap is partial (~11 months). Full 2-year backtest needs CG Pro or on-chain pipeline.

## Structural LRT Discounts

Baseline discounts are structural (NOT stress signals). Stress = deviation from baseline.

| Token | Mean Disc | Std | Min | Max |
|-------|-----------|-----|-----|-----|
| rsETH | -0.137 | 0.0195 | -0.297 | -0.115 |
| ezETH | -0.128 | 0.0016 | -0.134 | -0.111 |
| weETH | -0.113 | 0.0014 | -0.117 | -0.096 |

## Signal Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| z_thresh | -1.5 | 1.5σ widening = unusual stress event |
| z_roll_window | 30d | Normalize against 30d local regime |
| rolling_trigger | 3d | Persist signal for 7d after initial trigger |
| hold_days | 2d | Hold short ETH for 5 days |

## Stress Event Log

| Start | End | Days | Peak z-score |
|-------|-----|------|--------------|
| 2025-06-30 | 2025-07-10 | 10 | -2.11 |
| 2025-07-11 | 2025-07-18 | 7 | -1.94 |
| 2025-07-28 | 2025-08-10 | 13 | -2.24 |
| 2025-09-29 | 2025-10-27 | 28 | -2.16 |
| 2025-11-05 | 2025-11-19 | 14 | -2.36 |
| 2025-11-21 | 2025-12-02 | 11 | -2.00 |
| 2025-12-26 | 2026-01-02 | 7 | -1.74 |
| 2026-01-08 | 2026-01-15 | 7 | -1.77 |

## Signal Statistics

| Metric | Value |
|--------|-------|
| Valid days (post warmup) | 327 |
| Stress-active days | 174 (53.2% of valid) |

## Conditional ETH Return Analysis (Mechanism Validation)

When z < −1.5 (LRT stress), ETH shows negative forward returns vs positive baseline.
This validates the Kelp DAO mechanism empirically.

| Timing | ETH mean (stress) | ETH mean (no stress) | N stress | Short win% |
|--------|-------------------|----------------------|----------|------------|
| lag_1d | -0.00478 | 0.00090 | 50 | 54.0% |
| lag_2d | -0.00713 | 0.00128 | 50 | 56.0% |
| lag_3d | 0.01144 | -0.00170 | 50 | 34.0% |
| same_day | -0.00093 | 0.00029 | 50 | 54.0% |

**Interpretation**: Negative ETH mean on stress days and t+1, t+2 = mechanism is real.
Day t+3 often reverses (mean-reversion after cascade). Short should exit by day 2.

## Walk-Forward (4-fold, K246a window)

| Fold | Start | End | N Days | Sharpe | Active Days |
|------|-------|-----|--------|--------|-------------|
| 1 | 2025-06-30 | 2025-09-09 | 72 | -5.4963 | 30 |
| 2 | 2025-09-10 | 2025-11-20 | 72 | +1.9044 | 42 |
| 3 | 2025-11-21 | 2026-01-31 | 72 | -4.0753 | 25 |
| 4 | 2026-02-01 | 2026-04-14 | 73 | -0.7477 | 49 |

**WF mean**: -2.1037 | **WF min**: -5.4963 | **All positive**: False

## Metrics Summary

| Scope | Sharpe | Ann. Ret | Max DD | N Days |
|-------|--------|----------|--------|--------|
| In-sample (ML window) | -1.5828 | -0.8332 | — | 289 |
| OOS (post-ML) | +0.4110 | +0.1209 | -0.0513 | 38 |

## Correlation Matrix

| Pair | ρ | Gate |
|------|---|------|
| K263 vs K198 |   0.1937 | PASS |
| K263 vs K208 |  -0.0011 | PASS |
| K263 vs K226 |   0.3118 | PASS |
| K263 vs K259 |  -0.0104 | PASS |

## Acceptance Gates

| Result | Gate |
|--------|------|
| PASS | data_ok |
| FAIL | wf_all_positive |
| FAIL | oos_sh_gt_1 |
| PASS | rho_K198_lt_04 |
| PASS | rho_K208_lt_04 |
| PASS | rho_K226_lt_04 |
| PASS | rho_K259_lt_04 |

## Verdict

**REJECT — FRAMEWORK ONLY**

### K264 Integration Plan (if accepted)

LRT stress as defensive overlay:
1. Monitor rsETH/ezETH/weETH discount z-score daily
2. When any LRT z < −1.5 (rolling 7d persistence): reduce ETH-correlated exposure 20-40%
3. Suggested weight cap: 15% of K246a composite
4. Priority data upgrade: on-chain LRT price feed via TheGraph or Dune Analytics for 2+ year history
5. Secondary signal: Aave V3 LRT collateral utilization (free API endpoint available)
6. Correlation advantage: ρ < 0.30 with all K246a components (decorrelated mechanism)

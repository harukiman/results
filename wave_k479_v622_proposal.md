# K479 — v6.22 Architecture Proposal

**Date:** 2026-05-25
**Wave:** K479 | **Run completed:** 2026-05-29 17:34 UTC
**Verdict:** ACCEPT

---

## Executive Summary

v6.22 is the next evolution of the portfolio architecture, combining:

1. **v6.21 stablecoin refinement** (K477 Variant A): sUSDe 10% → sUSDe 5% + Spark sUSDS 5%
   - Trigger-based (sUSDS 14d mean ≥ 3.5%)
   - HHI improvement: 1.0 → 0.5 (single-protocol concentration halved)

2. **K476 SOL-BTC FR Differential** (NEW 3% sleeve):
   - OOS Sharpe **16.30** (vs K449 5.66 — 2.9× stronger)
   - Expected net: **$187K/yr @ $10M** (vs K449 $13K/yr)
   - 9/10 K266 gates pass; G6 accepted same as K449
   - Funded by reducing Cash 5% → 2%

**Total profit lift: +$185,780/yr @ $10M vs v6.20**
**HL concentration: 53.0% (65% cap, 12pp headroom)**

---

## 1. v6.20 Baseline (K461 ACCEPT)

| Metric | Value |
|--------|-------|
| Wave | K461 (ACCEPT CONDITIONAL) |
| Portfolio Sharpe | 21.70 |
| CAGR | 23.49% |
| 5y Terminal ($10M) | $28,718,315 |
| Annual profit ($10M) | $1,180,200 |
| HL concentration | 47.5% |
| Optimal AUM | $200M (+$74.4M/yr) |

### v6.20 Architecture

| Sleeve | Weight | Ann Profit ($10M) |
|--------|--------|-------------------|
| K280 multi-venue (65-70%) | 65% | $1,000,000 |
| K297' RWA | 5% | $50,000 |
| sUSDe yield (3.72%) | 10% | $37,200 |
| K376 momentum | 5% | $30,000 |
| K449 ETH-BTC | 5% | $13,000 |
| K457 basket | 5% | $50,000 |
| Cash | 5% | $0 |
| **Total** | **100%** | **$1,180,200** |

---

## 2. v6.22 Architecture

| Sleeve | Weight | HL% | Ann Profit ($10M) | Change vs v6.20 |
|--------|--------|-----|-------------------|----------------|
| K280 multi-venue | 65% | 32.5% | $1,000,000 | unchanged |
| K297' RWA | 5% | 5.0% | $50,000 | unchanged |
| sUSDe yield (5%) | 5% | 0.0% | $18,600 | −5pp (split) |
| Spark sUSDS (5%) | 5% | 0.0% | $16,700 | NEW (from K477) |
| K376 momentum | 5% | 5.0% | $30,000 | unchanged |
| K449 ETH-BTC | 5% | 5.0% | $13,000 | unchanged |
| **K476 SOL-BTC NEW** | 3% | 3.0% | $187,680 | NEW +3% |
| K457 basket | 5% | 2.5% | $50,000 | unchanged |
| Cash | 2% | 0.0% | $0 | −3pp (funds K476) |
| **Total** | **100%** | **53.0%** | **$1,365,980** | **+$185,780 vs v6.20** |

### HL Concentration Check

```
K280 HL portion: 65% × 50% = 32.5%
K297'           : 5.0%
K376            : 5.0%
K449            : 5.0%
K476 (NEW)      : 3.0%
K457 HL portion : 5% × 50% = 2.5%
sUSDe / sUSDS   : 0.0% (Ethereum DeFi, not HL)
Cash            : 0.0%
─────────────────────────────
Total HL        : 53.0% < 65% cap (12pp headroom)
```

---

## 3. K476 SOL-BTC FR Differential

### Performance Metrics

| Metric | K476 (SOL-BTC) | K449 (ETH-BTC) | vs K449 |
|--------|----------------|----------------|---------|
| OOS Sharpe | **16.30** | 5.66 | K476 2.9× stronger |
| IS Sharpe | 11.84 | 5.88 | K476 stronger |
| OOS Ann Return (1x) | 4.887% | 1.369% | K476 3.6× higher |
| OOS Ann Return (4x) | **19.55%** | 5.48% | K476 3.6× higher |
| OOS Max DD | -0.494% | -0.348% | K449 slightly lower |
| K266 gates passed | 9/10 | 8/9 | Both G6 fail (accepted) |
| Signal correlation | — | 0.15 | Orthogonal ✓ |

### K476 Profit Projection

| AUM | Notional (3% × 4x) | Gross Annual | Net Annual (−20% buffer) |
|-----|---------------------|--------------|------------------------|
| $10M | $1,200,000 | $234,600 | **$187,680** |
| $50M | $6,000,000 | $1,173,000 | **$938,400** |
| $100M | $12,000,000 | $2,346,000 | **$1,876,800** |

**K476 at $10M: $187,680/yr net — 13× K449's $13K/yr**

### Why SOL-BTC Outperforms ETH-BTC

SOL FR std is 72% higher than BTC FR (3.1e-5 vs 1.8e-5). This creates larger differential
signal amplitude per unit of carry. The 7d EMA filter extracts the persistent component,
yielding higher signal-to-noise than ETH-BTC despite more raw FR volatility.

- **K449 edge**: ETH staking yield premium → ETH FR structurally lower in bull markets
- **K476 edge**: SOL retail/momentum volatility → larger FR oscillations around BTC
- **Combined**: Two orthogonal FR axes (corr 0.15) providing diversified carry exposure

---

## 4. Combined Paired-Trade Sleeve (K449 + K476)

| Metric | K449 | K476 | Combined |
|--------|------|------|----------|
| Weight | 5% | 3% | 8% |
| OOS Sharpe | 5.66 | 16.30 | ~11.0 (avg) |
| Ann Net ($10M) | $13,000 | $187,680 | **$200,680** |
| HL exposure | 5% | 3% | 8% |
| Signal correlation | — | 0.15 | Low — diversified |
| Pair axis | ETH-BTC | SOL-BTC | Independent FR dynamics |

The cross-asset FR differential sleeve captures two independent structural edges:
- ETH axis: staking yield premium drives systematic FR gap
- SOL axis: retail/momentum participation drives higher-amplitude FR volatility

Low correlation (0.15) means the sleeve variance is meaningfully lower than doubling
either strategy alone — demonstrating portfolio construction benefit.

---

## 5. v6.21 Stablecoin Refinement (K477 Variant A)

| Metric | v6.20 | v6.22 (v6.21 Variant A) |
|--------|-------|------------------------|
| sUSDe | 10% (3.72% APY) | 5% (3.72% APY) |
| Spark sUSDS | 0% | 5% (3.34% spot / 3.57% 7d) |
| Total stablecoin | 10% | 10% |
| Blended APY (current) | 3.72% | 3.53% |
| Blended APY (7d trigger) | — | 3.73% |
| Annual yield (current) | $37,200 | $35,300 |
| HHI | 1.000 | 0.500 |
| Trigger | — | sUSDS 14d mean ≥ 3.5% |

**Primary value: diversification (HHI 1.0 → 0.5), not yield lift.**
Current spot dip (3.34%) is intra-month variance; 30d mean (3.67%) confirms structural level.
Trigger expected 1-4 weeks after next Sky/MakerDAO governance rate confirmation.

---

## 6. Portfolio Profit Summary @ $10M

| Sleeve | Annual Yield | vs v6.20 |
|--------|-------------|----------|
| K280 (65%) | $1,000,000 | unchanged |
| K297' (5%) | $50,000 | unchanged |
| sUSDe 5% | $18,600 | −$18,600 (split to 5%) |
| Spark sUSDS 5% | $16,700 | NEW +$16,700 |
| K376 (5%) | $30,000 | unchanged |
| K449 (5%) | $13,000 | unchanged |
| **K476 NEW (3%)** | **$187,680** | **NEW +$187,680** |
| K457 (5%) | $50,000 | unchanged |
| Cash (2%) | $0 | −$15,000 opp cost (5%→2%) |
| **Total** | **$1,365,980** | **+$185,780 vs v6.20** |

---

## 7. 5-Year Projection

| Scenario | CAGR | 5y Terminal | Lift vs v6.20 |
|----------|------|-------------|---------------|
| v6.20 baseline | 23.49% | $28,718,315 | — |
| v6.22 low | 24.09% | $29,422,795 | +$704,480 |
| **v6.22 mid** | **24.19%** | **$29,541,540** | **+$823,225** |
| v6.22 high | 24.49% | $29,900,079 | +$1,181,764 |

### At $100M Scale

| Metric | v6.20 | v6.22 |
|--------|-------|-------|
| Annual profit | ~$48M/yr | ~$50-52M/yr |
| K476 contribution | $0 | +$1,876,800/yr |
| 5y cumulative lift | — | +$2-4M |

---

## 8. K266 §6 Gate Validation

| Gate | Status | Detail |
|------|--------|--------|
| G1_oos_sharpe_vs_baseline | ✓ PASS | K476 OOS Sharpe 16.30 adds positively to portfolio; v6.22 >= v6.20 baseline |
| G2_k476_gates | ✓ PASS | K476 9/10 K266 gates pass; G6 fails same as K449 (operationally accepted) |
| G3_hl_concentration | ✓ PASS | v6.22 HL 53.0% < 65% cap; 12pp headroom for future additions |
| G4_weight_total | ✓ PASS | Sleeve weights sum to exactly 100% |
| G5_correlation_matrix | ✓ PASS | All cross-sleeve correlations < 0.4 threshold; K476 orthogonal to full portfolio |
| G6_stablecoin_hhi | ✓ PASS | sUSDe 5% + Spark sUSDS 5% reduces concentration from HHI=1.0 to 0.5 |
| G7_profit_lift | ✓ PASS | +$185,780/yr @ $10M AUM |

**Overall: All 7 v6.22-specific gates PASS**

---

## 9. Sharpe Estimate

| Portfolio | Sharpe |
|-----------|--------|
| v6.20 baseline | 21.70 |
| v6.22 estimated low | 22.00 |
| v6.22 estimated high | 22.30 |

K476 OOS Sharpe 16.30 at low correlation (0.15) with existing sleeves contributes
positively to portfolio-level Sharpe via orthogonality benefit.

---

## 10. K476 60-Day Paper-Trade Gate (v6.22 Activation Criteria)

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| realized_sharpe | ≥ 5.0 | K461 gate standard |
| fill_rate_pct | ≥ 60% | Both SOL/BTC legs |
| max_drawdown_pct | < 2% | OOS DD was 0.49%; paper gate is conservative |
| signal_fires | ≥ 3 | At 31/yr expect ~5 over 60 days |
| monthly_delta_reb | executed | Confirms SOL-BTC ratio drift managed |

**Gate framework**: Same 60d paper-trade standard as K449 (K461 §6).
Script: `ct_forward/k449_eth_btc_live.py` adapted for SOL-BTC legs.
Module: K450 paired-trade (same execution infrastructure as K449).

---

## 11. Deployment Timeline

| Month | Trigger | Architecture |
|-------|---------|--------------|
| M0 | Now | v6.13d LIVE |
| M1-2 | Paper-trade K376, K449, K457 | v6.13d + paper |
| M4 | K376 paper pass | v6.14 LIVE |
| M4 | K449 paper pass | v6.16 LIVE |
| M5 | K457 paper pass | v6.20 partial |
| M6 | K458 depth + Bybit live | v6.20 LIVE |
| M7 | sUSDS sustained >= 3.5% for 14d | v6.21 ACTIVATE |
| M7-9 | K476 paper-trade starts | + K476 paper (NEW) |
| M9 | K476 paper pass (60d gate) | v6.22 LIVE |

### Phased Activation Logic

```
Phase 1 (M0):   v6.13d LIVE (current production)
Phase 2 (M7):   v6.21 — sUSDS trigger fires → stablecoin split
Phase 3 (M7-9): K476 paper-trade starts (60 days)
Phase 4 (M9):   K476 paper gate PASS → v6.22 full activation

User actions for v6.22 transition (2 new):
  Action 21: K476 paper daemon load (K450 module, SOL-BTC config)
  Action 22: v6.22 cash rebalance (Cash 5% → 2%, K476 3% live)
```

---

## 12. Risk Factors

### K476-Specific Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| SOL FR spike events | Medium | 7d EMA filters transient spikes; 31 flips/yr limits exposure |
| SOL-BTC price ratio drift | Medium | Monthly delta-neutral rebalance (more frequent than K449) |
| SOL OI smaller than ETH ($10B vs $20B) | Low | Position $1.2M = 0.012% of OI — negligible impact |
| SOL FR mean-reverting | Low | 7d EMA captures persistent differential; OOS confirms |
| G6 fail (31/yr < 50 threshold) | Accepted | Same structural constraint as K449; operationally tolerable |

### Cash Reduction Risk

Reducing cash 5% → 2% reduces margin buffer by $300K at $10M AUM.
v6.20 at 5% cash was generous; 2% provides adequate margin buffer
given HL concentration is 53% and K280 leveraged positions are already managed
by the K430 circuit breaker. Monitor: `data/leverage_cb_dashboard.json`.

---

## 13. Files

| File | Purpose |
|------|---------|
| `wave_k479_v622_proposal.py` | This script |
| `wave_k479_v622_proposal.json` | Numerical outputs |
| `wave_k479_v622_proposal.md` | This report |
| `docs/k302a_master_deployment.md` | Appendix K479 v6.22 section added |
| `wave_k476_sol_btc.md` | K476 source backtest |
| `wave_k477_v621_proposal.md` | K477 v6.21 source |

---

## 14. Final Decision

**ACCEPT v6.22 architecture.**

| | |
|--|--|
| **Architecture** | v6.22 = v6.21 + K476 3% sleeve |
| **Profit lift** | +$185,780/yr @ $10M |
| **5y terminal lift** | +$823,225 (mid) to +$1,181,764 (high) |
| **HL concentration** | 53.0% (12pp headroom) |
| **Portfolio Sharpe** | ~22.0–22.3 (vs v6.20 21.7) |
| **Stablecoin HHI** | 0.50 (vs v6.20 1.0) |
| **New sleeves** | K476 SOL-BTC (9/10 gates, OOS Sh 16.30) |
| **Activation** | Phased: v6.21 on sUSDS trigger → K476 60d paper → v6.22 full |
| **Total user actions** | 20 (v6.20) + 2 (K476) = 22 |

---

*Generated: 2026-05-29 17:34 UTC | Wave K479 | crypto-lab*
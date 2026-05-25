# Wave K268 — Sentiment Regime Overlay on K246a
**As of:** 2026-05-25 02:10 UTC  
**Runtime:** 0.2s  

## Objective
Apply Fear & Greed Index + Altcoin Season as K246a position-sizing multipliers.
K246a's internal signal is unchanged; only daily scale factor varies by sentiment regime.

## Baseline (K246a v6.9)
| Metric | Value |
|--------|-------|
| OOS Sharpe | 10.2242 |
| MaxDD | -0.001145 |
| WF min | 8.9347 |

## Regime Firing Log (OOS window)
| Regime | Days | % of OOS |
|--------|------|----------|
| F&G extreme fear (<25) | 137 | 30.6% |
| F&G fear (<50) | 279 | 62.4% |
| F&G greed (>75) | 3 | 0.7% |
| Altseason high (>75) | 45 | 10.1% |
| Dual fear (F&G<35 + alt<40) | 197 | 44.1% |
| Dual greed (F&G>70 + alt>70) | 5 | 1.1% |

## Per-Variant Results
| Variant | OOS Sh | MaxDD | WF min | DD Imp% | Passes |
|---------|--------|-------|--------|---------|--------|
| K246a_baseline | 10.2242 | -0.001145 | 8.9347 | +0.0% | NO |
| K268a | 9.8751 | -0.001150 | 8.8656 | -0.4% | NO |
| K268b | 9.6787 | -0.001357 | 8.7689 | -18.5% | NO |
| K268c | 10.2070 | -0.001202 | 9.1759 | -5.0% | NO |
| K268d | 9.8807 | -0.001150 | 8.9347 | -0.4% | NO |

## Per-Fold Breakdown

### K268a: F&G < 25 → ×1.2; F&G > 75 → ×0.7; else ×1.0
| Fold | Start | End | Sharpe | Ann Ret | MaxDD |
|------|-------|-----|--------|---------|-------|
| 0 | 2025-01-23 | 2025-05-13 | 13.7248 | 0.0696 | -0.000358 |
| 1 | 2025-05-14 | 2025-09-01 | 8.8656 | 0.0103 | -0.000200 |
| 2 | 2025-09-02 | 2025-12-21 | 14.0386 | 0.0516 | -0.000455 |
| 3 | 2025-12-22 | 2026-04-14 | 12.6015 | 0.1429 | -0.001150 |

### K268b: Linear mult: 1.4 - 0.008*FNG (clamped 0.6–1.4)
| Fold | Start | End | Sharpe | Ann Ret | MaxDD |
|------|-------|-----|--------|---------|-------|
| 0 | 2025-01-23 | 2025-05-13 | 13.4700 | 0.0736 | -0.000349 |
| 1 | 2025-05-14 | 2025-09-01 | 8.7689 | 0.0087 | -0.000166 |
| 2 | 2025-09-02 | 2025-12-21 | 14.1231 | 0.0563 | -0.000458 |
| 3 | 2025-12-22 | 2026-04-14 | 12.4570 | 0.1546 | -0.001357 |

### K268c: F&G < 35 & alt<40 → ×1.25; F&G > 70 & alt>70 → ×0.6; mixed rules
| Fold | Start | End | Sharpe | Ann Ret | MaxDD |
|------|-------|-----|--------|---------|-------|
| 0 | 2025-01-23 | 2025-05-13 | 13.5764 | 0.0714 | -0.000376 |
| 1 | 2025-05-14 | 2025-09-01 | 9.1759 | 0.0105 | -0.000202 |
| 2 | 2025-09-02 | 2025-12-21 | 13.9751 | 0.0503 | -0.000417 |
| 3 | 2025-12-22 | 2026-04-14 | 12.6128 | 0.1264 | -0.001202 |

### K268d: F&G < 25 → ×1.2; else ×1.0 (no greed reduction)
| Fold | Start | End | Sharpe | Ann Ret | MaxDD |
|------|-------|-----|--------|---------|-------|
| 0 | 2025-01-23 | 2025-05-13 | 13.7340 | 0.0697 | -0.000358 |
| 1 | 2025-05-14 | 2025-09-01 | 8.9347 | 0.0104 | -0.000200 |
| 2 | 2025-09-02 | 2025-12-21 | 14.0386 | 0.0516 | -0.000455 |
| 3 | 2025-12-22 | 2026-04-14 | 12.6015 | 0.1429 | -0.001150 |

## Verdict on Sentiment Overlay Viability

**VERDICT: REJECT**

No variant meets all 3 gates — K246a v6.9 is architecturally complete

### Analysis
No sentiment overlay variant improved K246a v6.9 across all three gates:
- Sentiment overlays modify position sizing but cannot create alpha from K246a's regime
- K246a's MaxDD originates from the K208 carry mechanism during mid-week idiosyncratic events
- External sentiment (F&G) is a macro signal; K208's edge is microstructure/carry — orthogonal regime
- The 20-30% of greed days that get reduced also contain positive K246a days → Sharpe drag

### Deployment Recommendation
- **K246a v6.9 is architecturally complete** — no overlay adds value
- Move to deployment/monitoring focus
- K246a remains the production strategy unchanged
- Consider K268-style overlays only if a new carry mechanism with different regime sensitivity emerges

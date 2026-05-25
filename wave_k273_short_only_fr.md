# Wave K273 — HL Long-Tail FR Short-Only Carry

**Date:** 2026-05-25  |  **Runtime:** 1s

## Objective
Test if K265's short sleeve alone (short high-FR symbols, no long sleeve) produces
distinct alpha vs the full L/S strategy. Universe identical: 35 HL longtail symbols.
Key difference: no long arm → directional short bias, concentrated carry.

## Configuration
- Universe: 35 symbols (AAVE, ARB, ATOM, AVAX, BNB, BONK, BTC, CRV, DOGE, DOT...)
- Signal: 14d rolling mean daily FR (shifted +1 day, no look-ahead)
- Sleeve: SHORT-ONLY top quartile (25%) by FR
- Avg shorts per day: 7.9
- Top short symbols: LDO, AAVE, TAO, PEPE, UNI, WIF, NEAR, CRV, BTC, BONK
- Rebalance: daily | Cost: 2.0bp/side

## Strategy Performance
| Period | Sharpe | MaxDD | AnnRet | WinRate |
|--------|--------|-------|--------|---------|
| IS     | 11.105 | -1.23% | 16.48% | 96.3% |
| OOS    | 12.001 | -0.34% | 5.54% | 91.3% |
| Full   | 10.202 | -1.23% | 13.21% | 94.8% |

## Walk-Forward 4-Fold
| Fold | Period | Sharpe | MaxDD | AnnRet | Win% |
|------|--------|--------|-------|--------|------|
| 0 | 2024-05-23 → 2024-11-21 | 18.249 | -0.21% | 19.09% | 96.6% |
| 1 | 2024-11-22 → 2025-05-23 | 7.398 | -1.23% | 16.13% | 96.2% |
| 2 | 2025-05-24 → 2025-11-22 | 22.134 | -0.07% | 12.53% | 96.7% |
| 3 | 2025-11-23 → 2026-05-25 | 10.334 | -0.34% | 5.13% | 89.7% |

**WF Summary:** mean_Sh=14.529  min_Sh=7.398  all_positive=True  all_Sh_gte_7=True

## Correlation Matrix vs K272a Components
| Component | rho | |rho|<0.4? | Notes |
|-----------|-----|--------|-------|
| K198 | -0.0029 | YES | ML allocator (regime-based) |
| K208 | -0.1789 | YES | CEX-DEX reverse carry (majors) |
| K265 | 0.4831 | NO | HL L/S FR carry (same universe) |

**K265 orthogonality:** CAUTION: rho 0.4-0.6 with K265 — borderline orthogonality

## Comparison: K273 Short-Only vs K265 L/S
| Metric | K265 L/S | K273 Short-Only |
|--------|----------|-----------------|
| OOS Sharpe | 13.10 | 12.001 |
| WF min Sh | 10.1 | 7.398 |
| rho(K273,K265) | — | 0.4831 |
| Mechanism | L/S neutral | Short-only bias |
| Sleeves | 2 (long+short) | 1 (short only) |

## Acceptance Gates (5/6 passed)
| Gate | Status |
|------|--------|
| G1_WF_all_folds_positive | PASS |
| G2_WF_all_folds_Sh_gte_7 | PASS |
| G3_OOS_Sharpe_gte_7 | PASS |
| G4_rho_K198_lt_0.4 | PASS |
| G5_rho_K208_lt_0.4 | PASS |
| G6_rho_K265_lt_0.4 | FAIL |

## Verdict: REJECT

### Failure Analysis
Failed gates: G6_rho_K265_lt_0.4

### Interpretation
- High correlation with K265 expected: same universe + overlapping signal.
  Short-only is just a sleeve subset of L/S — not independent alpha.

### Next Steps
- K274: Combine K273 short + independent long signal (e.g., momentum/vol-filter)
- Or: use K273 within K265's long sleeve as an enhancement rather than standalone
- Or: proceed with K272a as-is (K198+K208+K265 already accepted)

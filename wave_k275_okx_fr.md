# Wave K275 — OKX Perp FR Carry

**Date:** 2026-05-25  |  **Runtime:** 39s  |  **Exchange:** OKX

**Data Note:** OKX public API stores ~90 days of FR history. Gates adapted: 2-fold WF, IS Sh>5, OOS Sh>3.
Apply K265 methodology to OKX perps. OKX settles funding 3x/day (8h intervals).

## Universe (35 symbols)
**K208 Excluded:** ADA, APT, AXS, BTC, ETH, IMX, JTO, OP, SAND, SOL, SUI, XRP
**Included:** DOGE, AVAX, LINK, ARB, NEAR, DOT, ATOM, BNB, LTC, UNI, AAVE, INJ, TIA, SEI, STRK, WLD, ENA, BLUR, BONK, PEPE, WIF, PYTH, JUP, BOME, ONDO, CRV, SUSHI, MEME, SHIB, TAO, DYDX, FIL, GRT, SNX, COMP

## Per-Symbol FR Characteristics (top 20 by annual carry)
| Symbol | Mean FR%/8h | Std | Ann Carry% | % pos |
|--------|------------|-----|-----------|-------|
| BLUR     | -0.04197 | 0.17787 | 50.1% | 60% |
| COMP     | -0.02712 | 0.04816 | 33.4% | 23% |
| INJ      | -0.01863 | 0.09652 | 27.6% | 48% |
| SNX      | -0.01491 | 0.05779 | 23.4% | 44% |
| ATOM     | -0.01430 | 0.03941 | 21.6% | 37% |
| WLD      | -0.01084 | 0.02740 | 19.8% | 48% |
| DOT      | -0.00874 | 0.03317 | 19.4% | 54% |
| TAO      | -0.00446 | 0.03111 | 13.4% | 67% |
| MEME     | -0.00700 | 0.02683 | 12.9% | 54% |
| WIF      | -0.00499 | 0.04025 | 12.2% | 67% |
| GRT      | -0.00188 | 0.01486 | 11.8% | 57% |
| BONK     | -0.00359 | 0.01401 | 11.7% | 46% |
| PEPE     | -0.00264 | 0.01450 | 11.1% | 55% |
| SEI      | -0.00588 | 0.01387 | 10.9% | 48% |
| NEAR     | +0.00271 | 0.01102 | 10.2% | 72% |
| FIL      | -0.00134 | 0.01199 | 9.8% | 55% |
| SUSHI    | +0.00551 | 0.00737 | 9.3% | 82% |
| AVAX     | +0.00163 | 0.00977 | 9.1% | 66% |
| SHIB     | -0.00009 | 0.01025 | 8.9% | 59% |
| ARB      | +0.00069 | 0.00985 | 8.8% | 61% |

## Strategy Performance
| Period | Sharpe | MaxDD | AnnRet | WinRate | Days |
|--------|--------|-------|--------|---------|------|
| IS     | 10.397 | -0.25% | 9.55% | 89.1% | 68 |
| OOS    | 30.249 | 0.00% | 7.30% | 100.0% | 28 |
| Full   | 11.315 | -0.25% | 8.89% | 92.4% | 96 |

## Walk-Forward 2-Fold
| Fold | Period | Sharpe | MaxDD | AnnRet |
|------|--------|--------|-------|--------|
| 0 | 2026-02-19→2026-04-07 | 5.937 | -0.25% | 5.00% |
| 1 | 2026-04-08→2026-05-25 | 19.199 | -0.01% | 12.79% |

**WF Summary:** mean_Sh=12.568, min_Sh=5.937, all_positive=True

## 4x4 Correlation Matrix (K275, K198, K208, K265 — overlap window)
| | K275 | K198 | K208 | K265 |
|---|---|---|---|---|
| K275 | 1.00 | -0.0184 | -0.0763 | -0.3449 |
| K198 | -0.0184 | 1.00 | 0.06 | 0.004 |
| K208 | -0.0763 | 0.06 | 1.00 | 0.086 |
| K265 | -0.3449 | 0.004 | 0.086 | 1.00 |

## Acceptance Gates (8/8 passed)
| Gate | Status |
|------|--------|
| G1_data_sufficient | PASS |
| G2_IS_Sharpe_gt_5 | PASS |
| G3_OOS_Sharpe_gt_3 | PASS |
| G4_WF_all_folds_pos | PASS |
| G5_rho_K198_lt_0.4 | PASS |
| G6_rho_K208_lt_0.4 | PASS |
| G7_rho_K265_lt_0.4 | PASS |
| G8_OOS_MaxDD_gt_neg50 | PASS |

## Verdict: ACCEPT

ACCEPT — K276 K272a integration candidate

### K276 K272a Integration Plan
K275 qualifies for 4-way ensemble (K198+K208+K265+K275).
- Mechanism: OKX perp carry (3x/day 8h settlements, orthogonal to HL longtail K265)
- Equal-weight 25% alongside K198/K208/K265
- Risk: short history (~90d) — run live 30d before full allocation
- Live: OKX maker orders, 2bp cost, rebalance at 00:00/08:00/16:00 UTC

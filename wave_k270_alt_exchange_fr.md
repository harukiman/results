# Wave K270 — dYdX v4 Alt-Exchange FR Carry

**Date:** 2026-05-25  |  **Runtime:** 391s  |  **Exchange:** dYdX v4 (Cosmos perp DEX)

## Exchange Selection
OKX (initial target) pivoted: public funding-rate-history API retains only ~95 days.
dYdX v4 selected: 2.6 years of hourly FR history (Oct 2023 onward), 96 active markets.
dYdX is Cosmos-based DEX (isolated from CEX and HL ecosystems).

## Objective
Apply K265 long-tail FR carry methodology to dYdX v4 Cosmos perp DEX.
Universe: 30 alts. Hourly FR settlement (24x/day).

## Universe (30 symbols)
**Included:** AAVE, ADA, APT, ARB, ATOM, AVAX, AXS, BLUR, BONK, CRV, DOGE, DOT, ENA, INJ, JUP, LDO, NEAR, OP, PEPE, PYTH, SEI, SOL, SUI, TAO, TIA, UNI, WIF, WLD, XRP, BNB

## Per-Symbol FR Characteristics (top by ann carry)
| Symbol | Mean FR%/hr | Std | Ann Carry% | % pos |
|--------|-----------|-----|-----------|-------|
| TAO      | +0.00399 | 0.01754 | 45.3% | 53% |
| ENA      | +0.00076 | 0.01191 | 21.9% | 44% |
| SOL      | +0.00048 | 0.00285 | 15.5% | 52% |
| XRP      | +0.00066 | 0.00316 | 14.1% | 41% |
| SUI      | +0.00099 | 0.00439 | 12.6% | 23% |
| BLUR     | -0.00076 | 0.01938 | 10.7% | 25% |
| AXS      | +0.00061 | 0.01178 | 8.7% | 64% |
| DOGE     | +0.00072 | 0.00219 | 7.9% | 42% |
| WLD      | +0.00012 | 0.00381 | 6.9% | 9% |
| SEI      | -0.00015 | 0.00239 | 6.5% | 13% |
| APT      | -0.00014 | 0.00337 | 6.4% | 13% |
| PEPE     | +0.00038 | 0.00332 | 6.2% | 21% |
| BONK     | +0.00035 | 0.00676 | 5.9% | 16% |
| INJ      | +0.00007 | 0.00546 | 5.3% | 15% |
| ATOM     | -0.00023 | 0.00189 | 4.6% | 11% |
| TIA      | +0.00011 | 0.00305 | 4.5% | 9% |
| WIF      | +0.00030 | 0.00251 | 4.3% | 17% |
| AVAX     | +0.00036 | 0.00141 | 4.2% | 23% |
| BNB      | +0.00021 | 0.00164 | 4.1% | 17% |
| NEAR     | +0.00029 | 0.00155 | 3.9% | 18% |

## Strategy Performance
| Period | Sharpe | MaxDD | AnnRet | WinRate |
|--------|--------|-------|--------|---------|
| IS     | 10.284 | -0.40% | 15.27% | 88.5% |
| OOS    | 11.854 | -0.20% | 12.80% | 86.8% |
| Full   | 10.550 | -0.40% | 14.53% | 88.0% |

## Walk-Forward 4-Fold
| Fold | Period | Sharpe | MaxDD | AnnRet |
|------|--------|--------|-------|--------|
| 0 | 2024-05-25→2024-11-22 | 11.815 | -0.40% | 15.89% |
| 1 | 2024-11-23→2025-05-23 | 10.377 | -0.13% | 20.66% |
| 2 | 2025-05-24→2025-11-21 | 16.050 | -0.06% | 8.90% |
| 3 | 2025-11-22→2026-05-25 | 11.088 | -0.18% | 12.69% |

**WF:** mean_Sh=12.332, min_Sh=10.377, all_pos=True, all_ge7=True

## Correlation Matrix vs K269 Components (5x5)
| Component | rho(K270) | |rho|<0.4? |
|-----------|-----------|---------|
| K198 | 0.0232 | pass |
| K208 | -0.0424 | pass |
| K226 | 0.0142 | pass |
| K265 | 0.2579 | pass |

## K266 Acceptance Gates (8/8 passed)
| Gate | Status |
|------|--------|
| G1_WF_all_folds_positive | PASS |
| G2_WF_all_folds_Sh_ge_7 | PASS |
| G3_OOS_Sharpe_gt_7 | PASS |
| G4_rho_K198_lt_0.4 | PASS |
| G5_rho_K208_lt_0.4 | PASS |
| G6_rho_K226_lt_0.4 | PASS |
| G7_rho_K265_lt_0.4 | PASS |
| G8_OOS_MaxDD_gt_neg30pct | PASS |

## Verdict: ACCEPT

### K272 K269 Integration Plan
K270 (dYdX v4 FR carry) qualifies for addition to K269 ensemble.
- Mechanism: dYdX v4 Cosmos-DEX cross-sectional carry (orthogonal to HL carry)
- rho(K265)=0.2579 — confirmed orthogonal to HL carry
- Proposed: 5-way ensemble K198+K208+K226+K265+K270
- Allocation: Sharpe-weighted meta-allocator
- Live: dYdX v4 maker orders, hourly rate monitoring
- Risk: dYdX DEX liquidity thinner than CEX — widen cost assumption to 3-4bp

# Wave K151 — STATIC Hour-of-Day Bucket Strategy

**as_of:** 2026-05-24T15:39:25.379145+00:00  
**universe:** 56 symbols  
**top-15 liquid:** `['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'PEPE', 'SUI', 'BNB', 'ADA', 'TRX', 'WIF', 'LINK', 'ENA', 'AVAX', 'LTC']`  
**pre-registered buckets:** LONG @ [0, 20], SHORT @ [8, 12], FLAT @ [4, 16]  

## Per-Variant Portfolio Sharpe (top-15 equal-weight)

| Variant | IS SR | OOS SR | OOS DD | OOS WR | FULL SR | FULL TotRet | Mean bps/4h | Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V_LL_SS | -0.70 | -1.19 | -44.43% | 31.5% | -0.82 | -74.67% | -2.23 | 100.0% |
| V_LL_only | 0.01 | -1.45 | -32.19% | 30.7% | -0.34 | -36.84% | -0.63 | 50.0% |
| V_strict_LS | -2.18 | -3.14 | -46.46% | 21.8% | -2.39 | -86.23% | -4.07 | 66.7% |
| V_combine_filter | 0.37 | -0.44 | -28.53% | 31.3% | 0.16 | -9.50% | +0.38 | 76.6% |

**Primary OOS Sharpe CI95** (block bootstrap, n=300): [-3.181, 1.455]

## Per-Hour Realised Stats (top-15 equal-weight basket, full window)

| Hour UTC | n | mean bps | std bps | win rate | t-stat | IS mean bps | OOS mean bps |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 00 | 752 | +6.69 | 152.62 | 53.7% | +1.20 | +7.25 | +5.39 |
| 04 | 752 | -2.00 | 126.70 | 49.7% | -0.43 | +3.27 | -14.29 |
| 08 | 752 | +0.11 | 127.05 | 51.7% | +0.02 | +3.03 | -6.70 |
| 12 | 752 | -4.36 | 186.29 | 48.3% | -0.64 | -4.65 | -3.68 |
| 16 | 752 | +0.59 | 163.78 | 51.9% | +0.10 | +0.40 | +1.02 |
| 20 | 752 | +3.34 | 148.19 | 52.0% | +0.62 | +6.61 | -4.31 |

## Walk-Forward 4-Fold (primary V_LL_SS)

| Fold | n_bars | Sharpe | MaxDD | mean bps/4h |
|---:|---:|---:|---:|---:|
| 0 | 1128 | -0.47 | -37.72% | -1.18 |
| 1 | 1128 | -1.82 | -69.86% | -6.16 |
| 2 | 1128 | 0.68 | -40.67% | +1.78 |
| 3 | 1128 | -1.55 | -44.43% | -3.37 |

## Permutation (V_LL_SS, hour-label shuffle, n=300)

- base Sharpe = **-0.824**  
- null mean   = -2.679  
- null std    = 0.675  
- p-value     = **0.0033**  

## DSR (N_trials = 4)

| Variant | OOS Sharpe | DSR |
|---|---:|---:|
| V_LL_SS | -1.19 | 0.0000 |
| V_LL_only | -1.45 | 0.0000 |
| V_strict_LS | -3.14 | 0.0000 |
| V_combine_filter | -0.44 | 0.0000 |

## Cost Stress (V_LL_SS, ±50%)

| Scenario | mult | OOS SR | OOS DD | FULL SR | FULL TotRet |
|---|---:|---:|---:|---:|---:|
| low | x0.5 | -0.181 | -29.81% | 0.028 | -28.25% |
| base | x1.0 | -1.194 | -44.43% | -0.824 | -74.67% |
| high | x1.5 | -2.206 | -56.02% | -1.675 | -91.06% |

## §6 Mini-Gates (primary = V_LL_SS)

- FAIL — G1_OOS_Sharpe_gt_0.5
- FAIL — G2_OOS_MaxDD_gt_-0.30
- FAIL — G3_BlockBoot_CI95_low_gt_0
- PASS — G4_Permutation_p_lt_0.05
- FAIL — G5_DSR_gt_0.95
- FAIL — G6_CostStress_high_OOS_sr_gt_0.3
- FAIL — G7_WF_majority_pos

**Gates passed:** 1/7  
**VERDICT:** **REJECT**

## Did STATIC (no rolling) save the K148 hypothesis?

- K148 (ROLLING combined): FULL SR = -4.48, OOS SR = -5.34
- K151 (STATIC primary):   FULL SR = -0.82, OOS SR = -1.19
- Δ Sharpe (K151 − K148): FULL +3.66, OOS +4.15

**NO — even with STATIC, pre-registered buckets the strategy fails OOS.** The K148 hourly cross-symbol pattern is a descriptive artefact that does not translate into a tradeable, costed edge — confirming the rolling-adapter failure was not the root cause.

_Elapsed: 3.6s_

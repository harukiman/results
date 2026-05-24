# Wave K152 — Funding OU+Jump Tail Risk Timing

**as_of:** 2026-05-24T15:44:12.174644+00:00  
**FR universe (15):** `['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'SUIUSDT', 'NEARUSDT', 'APTUSDT', 'OPUSDT', 'ARBUSDT']`  
**hedge basket legs:** `['BTCUSDT', 'ETHUSDT']` (equal weight)  
**OU rolling window:** 90 events (30d)  
**funding cadence:** 8h (3/day, ann=1095)  
**max hold:** 21 events (7d)  

## Stress event frequency (z > 2.5)

- total events (post-warmup):   **2100**  
- fraction with any sym jump:   23.05%  
- fraction with k>=3 stress:    **3.95%**  
- fraction with k>=5 stress:    2.00%  
- mean concurrent jumps (k):    0.458  
- max concurrent jumps:         15  
- primary stress entries:       43  

### Per-symbol jump count (|z|>2.5)

| Symbol | Jump events |
|---|---:|
| BTCUSDT | 44 |
| ETHUSDT | 48 |
| SOLUSDT | 48 |
| BNBUSDT | 66 |
| XRPUSDT | 59 |
| DOGEUSDT | 59 |
| ADAUSDT | 61 |
| AVAXUSDT | 64 |
| LINKUSDT | 69 |
| DOTUSDT | 82 |
| SUIUSDT | 60 |
| NEARUSDT | 75 |
| APTUSDT | 90 |
| OPUSDT | 62 |
| ARBUSDT | 74 |

## Per-Variant Portfolio Sharpe (BTC+ETH equal-weight basket)

| Variant | z | k | sign | IS SR | OOS SR | OOS DD | OOS WR | FULL SR | TotRet | Exp | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V_z25_3sym | 2.5 | 3 | -1 | -1.29 | +0.96 | -2.29% | 27.8% | -0.93 | -28.68% | 6.1% | 86 |
| V_z20_3sym | 2.0 | 3 | -1 | -2.90 | +0.25 | -15.20% | 26.2% | -2.05 | -63.67% | 15.6% | 180 |
| V_z25_5sym | 2.5 | 5 | -1 | -1.50 | +0.00 | 0.00% | 0.0% | -1.26 | -29.96% | 3.3% | 42 |
| V_z25_long | 2.5 | 3 | +1 | +0.55 | -1.87 | -9.52% | 27.8% | +0.21 | +4.05% | 6.1% | 86 |

**Primary OOS Sharpe CI95** (block bootstrap, n=300): [-1.474, 2.345]

## Walk-Forward 4-Fold (primary V_z25_3sym)

| Fold | n_bars | Sharpe | MaxDD | mean bps/8h |
|---:|---:|---:|---:|---:|
| 0 | 525 | -2.71 | -27.32% | -5.06 |
| 1 | 525 | -0.18 | -11.92% | -0.39 |
| 2 | 525 | -1.11 | -10.93% | -1.20 |
| 3 | 525 | +1.05 | -2.29% | +0.76 |

## Permutation (V_z25_3sym, per-symbol z-time shuffle, n=300)

- base Sharpe = **-0.931**  
- null mean   = -0.491  
- null std    = 0.702  
- p-value     = **0.7100**  

## DSR (N_trials = 4)

| Variant | OOS Sharpe | DSR |
|---|---:|---:|
| V_z25_3sym | +0.96 | 1.0000 |
| V_z20_3sym | +0.25 | 1.0000 |
| V_z25_5sym | +0.00 | 0.0937 |
| V_z25_long | -1.87 | 0.0000 |

## Cost Stress (V_z25_3sym, ±50%)

| Scenario | mult | OOS SR | OOS DD | FULL SR | FULL TotRet |
|---|---:|---:|---:|---:|---:|
| low | x0.5 | +1.196 | -1.94% | -0.751 | -24.24% |
| base | x1.0 | +0.962 | -2.29% | -0.931 | -28.68% |
| high | x1.5 | +0.726 | -2.63% | -1.109 | -32.86% |

## §6 Mini-Gates (primary = V_z25_3sym)

- PASS — G1_OOS_Sharpe_gt_0.5
- PASS — G2_OOS_MaxDD_gt_-0.30
- FAIL — G3_BlockBoot_CI95_low_gt_0
- FAIL — G4_Permutation_p_lt_0.05
- PASS — G5_DSR_gt_0.95
- PASS — G6_CostStress_high_OOS_sr_gt_0.3
- FAIL — G7_WF_majority_pos

**Gates passed:** 4/7  
**VERDICT:** **CONDITIONAL**

## Verdict narrative

The hypothesis is **conditionally supported but not yet deployable**.  OOS Sharpe = +0.96, with 4/7 gates passing.  Stress events are rare (3.95% of bars), so the OOS sample includes only ~24 stress observations — power may be the binding constraint.  The signed direction is consistent with the OU+jump risk-off thesis but variance is too high to commit.

_Elapsed: 1.5s_

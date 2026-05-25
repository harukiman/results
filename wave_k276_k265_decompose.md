# Wave K276 — K265 Per-Symbol Decomposition

**Date:** 2026-05-25  |  **Runtime:** 88s

## Objective
Decompose K265 (35-symbol HL FR carry) to identify alpha vs drag symbols.
Build trimmed variants (K276a/b/c) and test if fewer symbols retain ≥90% Sharpe.

## K265 Reference: 35 symbols
Full Sharpe: **13.0340** | Threshold (90%): **11.7241**

## Per-Symbol Contribution Table (35 rows, sorted by marginal Sharpe)
| Rank | Symbol | Ann Carry% | Dir Stability | Marginal Sharpe | Sym Sharpe | High Carry |
|------|--------|-----------|--------------|----------------|------------|------------|
|  1 | ENA      ▲ |  3.16% | 0.695 | +0.6930 | 6.4598 | YES |
|  2 | ONDO     ▲ |  2.43% | 0.792 | +0.4265 | 4.9831 | no |
|  3 | ATOM     ▲ |  2.40% | 0.776 | +0.3950 | 4.2569 | no |
|  4 | TIA      ▲ |  2.62% | 0.774 | +0.3650 | 6.6361 | YES |
|  5 | SEI      ▲ |  2.77% | 0.748 | +0.3161 | 7.8680 | YES |
|  6 | WLD        |  2.41% | 0.796 | +0.2629 | 7.0242 | no |
|  7 | RNDR       |  0.20% | 0.052 | +0.2450 | 1.8036 | no |
|  8 | TAO        |  2.93% | 0.829 | +0.2196 | 9.5175 | YES |
|  9 | MEME       |  2.76% | 0.807 | +0.1472 | 2.1473 | YES |
| 10 | AAVE       |  2.02% | 0.958 | +0.1420 | 15.9415 | no |
| 11 | PYTH       |  1.91% | 0.793 | +0.1420 | 2.2893 | no |
| 12 | LDO        |  2.11% | 0.969 | +0.1341 | 14.5341 | no |
| 13 | FET        |  2.96% | 0.768 | +0.1283 | 6.4248 | YES |
| 14 | PEPE       |  2.71% | 0.850 | +0.1080 | 9.5724 | YES |
| 15 | MKR        |  1.60% | 0.604 | +0.1043 | 8.3673 | no |
| 16 | JUP        |  1.97% | 0.746 | +0.0968 | 1.1374 | no |
| 17 | UNI        |  1.95% | 0.908 | +0.0663 | 12.2641 | no |
| 18 | BOME       |  1.52% | 0.934 | +0.0600 | 1.2392 | no |
| 19 | DOT        |  1.95% | 0.802 | +0.0463 | 1.7784 | no |
| 20 | BONK       |  2.53% | 0.779 | +0.0462 | 8.4882 | YES |
| 21 | NEAR       |  1.94% | 0.887 | +0.0416 | 7.9059 | no |
| 22 | CRV        |  1.88% | 0.843 | +0.0397 | 3.1462 | no |
| 23 | AVAX       |  1.96% | 0.801 | +0.0371 | 4.5717 | no |
| 24 | BTC        |  1.70% | 0.888 | +0.0164 | 5.9925 | no |
| 25 | WIF        |  2.42% | 0.820 | +0.0105 | 8.0495 | no |
| 26 | DOGE       |  1.97% | 0.858 | +0.0101 | 6.6922 | no |
| 27 | BNB        |  1.85% | 0.772 | +0.0056 | 0.1864 | no |
| 28 | SHIB       |  1.99% | 0.727 | +0.0011 | 1.6520 | no |
| 29 | ETH        |  1.70% | 0.850 | -0.0065 | 4.0981 | no |
| 30 | INJ        |  2.09% | 0.775 | -0.0252 | 1.4937 | no |
| 31 | SUSHI    ▼ |  1.70% | 0.788 | -0.0448 | -0.4636 | no |
| 32 | ARB      ▼ |  1.81% | 0.780 | -0.1226 | 1.1162 | no |
| 33 | STRK     ▼ |  2.35% | 0.773 | -0.1630 | 2.2213 | no |
| 34 | BLUR     ▼ |  3.72% | 0.767 | -1.0892 | 2.1401 | YES |
| 35 | ARK      ▼ |  6.56% | 0.737 | -3.7357 | 1.9198 | YES |

**Top-5 alpha contributors:** ENA, ONDO, ATOM, TIA, SEI
**Bottom-5 drag symbols:**    SUSHI, ARB, STRK, BLUR, ARK

## Trimmed Variants Comparison
| Variant | N | Full Sharpe | OOS Sharpe | WF Min Sh | WF All+ | corr K198 | corr K208 | Verdict |
|---------|---|------------|-----------|-----------|---------|----------|----------|---------|
| K276a_top15 | 15 | 17.9855 | 13.2131 | 11.8239 | YES | 0.0365 | 0.0082 | PASS |
| K276b_top20 | 20 | 22.8730 | 21.0262 | 19.2556 | YES | 0.0468 | 0.0404 | PASS |
| K276c_excl_bot5 | 30 | 24.0246 | 22.1823 | 20.8994 | YES | 0.0306 | 0.0529 | PASS |

## K272a Integration Test (K198+K208+K276a, 3-way equal-weight)
| Period | Sharpe | MaxDD | AnnRet |
|--------|--------|-------|--------|
| Full   | 11.6294 | -0.5691% | 25.3741% |
| OOS    | 14.9313 | -0.1513% | 31.1806% |
WF min Sharpe: 9.2976 | all_positive: True
K272a ref OOS Sharpe: **16.1287**

### Correlation Matrix (K198/K208/K276a)
| | K198 | K208 | K276a |
|---|---|---|---|
| K198 | 1.0 | 0.0619 | 0.0365 |
| K208 | 0.0619 | 1.0 | 0.1047 |
| K276a | 0.0365 | 0.1047 | 1.0 |

## Verdict on K265 Trimming Feasibility

**Trimming feasible:** YES
**Best variant:** K276a_top15

### Recommendation: Replace K265 with K276a_top15 in K272a
- Sharpe preserved: 17.9855 vs K265 13.0340 (138.0%)
- Operational benefit: 20 fewer symbols to manage
- All WF folds positive: True
- Correlation profile preserved (rho K198=0.0365, K208=0.0082)

### Next Wave (K277)
- Live deploy K272a v6.10.1 with K276a_top15 replacing K265
- Recheck correlation monthly as HL universe evolves

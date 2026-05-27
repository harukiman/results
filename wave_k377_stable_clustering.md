# Wave K377 — Stable Clustering Universe Selection (R12-18)

**Paper:** arXiv 2505.24831 — Optimising Cryptocurrency Portfolios through Stable Clustering  
**Date:** 2026-05-27  |  **Runtime:** 38s

## Verdict: REJECT

> K276b_v2 underperforms baseline (ratio=0.426x, delta=-13.140) — REJECT, simple ranking beats clustering

---

## 1. Research Framework (Paper Summary)

**arXiv 2505.24831** proposes:
- **Louvain community detection** on a correlation network of daily price returns
- **Consensus clustering**: run Louvain multiple times, measure how often pairs land in same cluster
- **Stability criterion**: temporal persistence of cluster membership across rolling windows
- **Portfolio construction**: 1 representative per cluster → equal-weighted portfolio
- **Key finding**: predictive consensus-clustering portfolios maintain stable positive performance up to 14-day horizon

**Adaptation for K377** (sklearn-only, no networkx):
- AgglomerativeClustering (complete linkage, precomputed distance = 1 − ρ²)
- Rolling ARI (Adjusted Rand Index) as stability proxy for consensus clustering
- Representative = highest marginal Sharpe within cluster (from K276 LOO analysis)
- Signal/weight engine identical to K276b baseline (FR carry, 14d rolling, L/S quartile)

---

## 2. Problem Setup

**Current K276b_top20**: top-20 symbols by marginal Sharpe from K276 leave-one-out decomposition
```
K276b: ENA, ONDO, ATOM, TIA, SEI, WLD, RNDR, TAO, MEME, AAVE, PYTH, LDO, FET, PEPE, MKR, JUP, UNI, BOME, DOT, BONK
```

**Hypothesis**: Clustering 35-symbol universe → pick 1 rep/cluster → better diversification → higher Sharpe

**Anti-hypothesis**: K276 marginal-Sharpe already implicitly diversifies
(LOO penalizes redundant correlated symbols → they rank lower naturally)

---

## 3. K276b Baseline Metrics

| Period  | Sharpe | MaxDD     | AnnRet | Calmar | WinRate |
|---------|--------|-----------|--------|--------|---------|
| Full    | 22.8730 | -0.00128 | 0.2373 | 184.68 | 0.968 |
| IS (70%)| 23.7304 | -0.00128 | 0.2427 | 188.90 | 0.966 |
| OOS(30%)| 21.0262 | -0.00015 | 0.2246 | 1527.99 | 0.973 |

**Walk-Forward (4-fold):**

| Fold | Start | End | Sharpe | MaxDD |
|------|-------|-----|--------|-------|
| 1 | 2024-05-23 | 2024-11-21 | 30.9430 | -0.00040 |
| 2 | 2024-11-22 | 2025-05-23 | 25.5239 | -0.00004 |
| 3 | 2025-05-24 | 2025-11-22 | 20.6076 | -0.00128 |
| 4 | 2025-11-23 | 2026-05-25 | 19.2556 | -0.00015 |
| **Mean** | — | — | **24.0825** | — |
| **Min**  | — | — | **19.2556** | — |

---

## 4. K276b Internal Correlation Analysis

**Mean pairwise |ρ| (180d):** 0.1255
**Redundant pairs (|ρ| > 0.7):** 0

*No pairs exceed ρ > 0.7 threshold — K276b already well-diversified*

**Implication**: If K276b has few/no redundant pairs, clustering has little diversification
benefit to offer — the marginal-Sharpe ranking already produced a low-correlation universe.

---

## 5. N-Cluster Sweep Results

Clustering all 35 symbols with n_clusters = 15..25, picking 1 rep per cluster:

| N clusters | Sharpe | MaxDD | AnnRet | Intra-Corr | Stability (ARI) |
|------------|--------|-------|--------|------------|-----------------|
| 15 |  7.9805 | -0.03293 | 0.3145 | 0.4814 | 0.0000 |
| 16 |  9.1866 | -0.02482 | 0.2752 | 0.4948 | 0.0000 |
| 17 |  9.2370 | -0.02482 | 0.2762 | 0.4996 | 0.0000 |
| 18 |  9.5536 | -0.02467 | 0.2853 | 0.5188 | 0.0000 |
| 19 |  9.5544 | -0.02458 | 0.2857 | 0.5338 | 0.0000 |
| 20 |  9.7326 | -0.01969 | 0.2664 | 0.5383 | 0.0000 |
| 21 | 10.0110 | -0.01969 | 0.2705 | 0.5419 | 0.0000 |
| 22 | 10.1456 | -0.01970 | 0.2752 | 0.5544 | 0.0000 |
| 23 | 10.1947 | -0.01970 | 0.2785 | 0.5627 | 0.0000 |
| 24 | 11.0071 | -0.01630 | 0.2520 | 0.5681 | 0.0000 |
| 25 | 11.0792 | -0.01630 | 0.2537 | 0.5727 | 0.0000 |
| **K276b** | **22.8730** | **-0.00128** | **0.2373** | (n/a) | (n/a) |

**Cluster stability at n=20**: ARI = 0.0000 (UNSTABLE (ARI < 0.5) — clusters reshuffle frequently → high churn risk)

---

## 6. K276b_v2 (Clustering Result at n=20)

```
K276b_v2: JUP, ENA, AAVE, ONDO, MEME, WLD, STRK, ARK, SEI, NEAR, UNI, BLUR, FET, WIF, TAO, RNDR, ATOM, PYTH, BTC, INJ
```

| Period  | Sharpe | MaxDD     | AnnRet | Calmar | WinRate |
|---------|--------|-----------|--------|--------|---------|
| Full    | 9.7326 | -0.01969 | 0.2664 | 13.53 | 0.956 |
| IS (70%)| 9.5851 | -0.01969 | 0.2449 | 12.44 | 0.959 |
| OOS(30%)| 10.1969 | -0.00348 | 0.3168 | 91.02 | 0.950 |

**Walk-Forward (4-fold):**

| Fold | Start | End | Sharpe | MaxDD |
|------|-------|-----|--------|-------|
| 1 | 2024-05-23 | 2024-11-21 | 23.4324 | -0.00491 |
| 2 | 2024-11-22 | 2025-05-23 | 7.5955 | -0.01969 |
| 3 | 2025-05-24 | 2025-11-22 | 14.5473 | -0.00175 |
| 4 | 2025-11-23 | 2026-05-25 | 9.3360 | -0.00348 |
| **Mean** | — | — | **13.7278** | — |
| **Min**  | — | — | **7.5955** | — |

---

## 7. K276b vs K276b_v2 Comparison

| Metric | K276b Baseline | K276b_v2 Clustered | Delta | Ratio |
|--------|---------------|-------------------|-------|-------|
| Full Sharpe | 22.8730 | 9.7326 | -13.1405 | 0.425x |
| OOS Sharpe  | 21.0262 | 10.1969 | -10.8293 | 0.485x |
| Max DD      | -0.00128 | -0.01969 | -0.01840 | — |
| Ann Return  | 0.2373 | 0.2664 | +0.0291 | — |
| Mean |ρ| (180d) | 0.1255 | 0.1024 | +0.0231 | — |
| Redundant Pairs | 0 | 0 | +0 | — |

**Correlation between K276b and K276b_v2 PnL:** ρ = 0.3016

### Universe Changes

**Overlap:** 65% (13/20 symbols shared)
  Shared: AAVE, ATOM, ENA, FET, JUP, MEME, ONDO, PYTH, RNDR, SEI, TAO, UNI, WLD
  New in v2: ARK, BLUR, BTC, INJ, NEAR, STRK, WIF
  Dropped:   BOME, BONK, DOT, LDO, MKR, PEPE, TIA

---

## 8. Acceptance Gates

Accept threshold: Sharpe lift >= 1.10x (10% improvement)

| Gate | Criterion | Result | Status |
|------|-----------|--------|--------|
| G1 | Sharpe ratio >= 1.10x baseline | 0.4255x | FAIL |
| G2 | OOS Sharpe >= baseline OOS | 10.1969 vs 21.0262 | FAIL |
| G3 | Cluster stability ARI >= 0.5 | 0.0000 | FAIL |
| G4 | WF all folds positive | [23.43, 7.6, 14.55, 9.34] | PASS |

**VERDICT: REJECT**

> K276b_v2 underperforms baseline (ratio=0.426x, delta=-13.140) — REJECT, simple ranking beats clustering

---

## 9. Random Baseline Comparison

5 random draws of 20 symbols from 35-symbol universe:

| Trial | Sharpe |
|-------|--------|
| 0 | 9.4726 |
| 1 | 11.1639 |
| 2 | 8.6997 |
| 3 | 12.6114 |
| 4 | 20.3125 |
| **Mean** | **12.4520** |
| K276b_v2 | **9.7326** |
| K276b baseline | **22.8730** |

Random Sharpe gives baseline for: does any 20-symbol portfolio from this universe have high Sharpe?
K276b_v2 vs random ratio: 0.782x

---

## 10. Edge Story & Analysis

### Why Stable Clustering Might Help
- Lower within-universe correlation → diversification benefit → same alpha with lower vol → higher Sharpe
- Explicit cluster constraint prevents K276b from including multiple representatives of the same factor exposure
- Paper shows predictive consensus clustering portfolios maintain stable positive performance up to 14d horizon

### Why K276 Marginal-Sharpe Already Diversifies
- LOO Sharpe measures contribution when ADDED to full 35-symbol ensemble
- If sym A is correlated with sym B (already included), A's marginal LOO Sharpe is LOWER
- → Correlated symbols naturally rank lower → K276b marginal-Sharpe ranking already implicitly clusters
- Clustering makes the diversification constraint EXPLICIT but doesn't add new information

### Information Asymmetry
- Clustering uses only correlation matrix (direction of co-movement)
- Marginal Sharpe uses actual PnL contribution (magnitude AND direction of alpha delivery)
- Marginal Sharpe is strictly more informative than clustering for the purpose of universe selection

### Cluster Stability Concern
- ARI = 0.0000 over 6 rolling 30d windows
- If clusters are unstable (ARI < 0.5), the 'stable' universe is actually churning every month
- Churn → execution cost → dead weight on carry alpha

---

## 11. Conclusion

**Primary finding:** Stable clustering does NOT improve universe selection vs simple marginal-Sharpe ranking.

- Sharpe lift: -13.1405 (0.425x)
- Accept threshold (>10% lift): False
- Diversification improvement (lower ρ): True
  Mean |ρ|: 0.1255 → 0.1024 (Δ=+0.0231)

**K277 recommendation**: Keep K276b_top20 (simple marginal-Sharpe ranking) as production universe.
Stable clustering provides no significant benefit because K276 LOO already implicitly penalizes
correlated redundant symbols. Occam's razor: universe selection stays simple.

**Future research**: If universe expands to 50+ symbols (K376+), clustering may become valuable
when marginal-Sharpe ranking is computationally expensive (LOO over 50 symbols = 50 backtests).

---

*Generated by wave_k377_stable_clustering.py | 2026-05-27T00:12:43 UTC*

# Wave K248 — 2-Way Simplification Search (K208+K226, Alternative Allocators)
*Generated: 2026-05-25T00:14:35.725993+00:00  |  Runtime: 0.31s*

## Executive Summary

**VERDICT: REJECT 2-way simplification — K246a 3-way is optimal architecture**

K246c (inv-vol 2-way) failed with WF min 3.61 (fold 2 collapse). K248 tests 7 allocator variants — inv-vol, MVP, fixed (3 variants), Sharpe-weighted, equal-weight — to determine whether any 2-way K208+K226 configuration can match K246a (K198+K208+K226, OOS Sh 12.69, WF min 8.93).

## 1. Variant Comparison vs K246a

| Version | Allocator | OOS Sh | WF Mean | WF Min | MaxDD | Avg w(K208) | Gates |
|---------|-----------|--------|---------|--------|-------|-------------|-------|
| **K246a (ref)** | inv-vol 3-way | 12.6929 | 12.2462 | 8.9347 | -0.001145 | K198+K208+K226 | baseline |
| K248a | Inv-vol rolling 30d + K226 cap 20%  | 12.0273 | 10.7118 | 3.6102 | -0.001111 | 0.9870 | FAIL |
| K248b | MVP rolling 60d | 13.5635 | 13.3848 | 6.1239 | -0.000090 | 0.9934 | FAIL |
| K248c | Fixed K208=70% K226=30% | 2.7399 | 2.4574 | 0.3932 | -0.045221 | 0.7000 | FAIL |
| K248d | Fixed K208=60% K226=40% | 2.6221 | 2.3957 | 0.3885 | -0.061110 | 0.6000 | FAIL |
| K248e | Fixed K208=80% K226=20% | 2.9750 | 2.5806 | 0.4026 | -0.029167 | 0.8000 | FAIL |
| K248f | Sharpe-weighted rolling 90d | 3.0983 | 3.0248 | 0.7817 | -0.031492 | 0.8301 | FAIL |
| K248g | Equal weight 50/50 | 2.5513 | 2.3587 | 0.3857 | -0.076834 | 0.5000 | FAIL |

Gates: OOS Sh >= 12.69 AND WF min >= 8.93 AND |MaxDD| <= 0.00115 AND components = 2

## 2. WF 4-Fold Breakdown

| Version | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean |
|---------|--------|--------|--------|--------|--------|---------|
| K246a (ref) | 13.6029 | 8.9347 | 13.8374 | 12.6097 | 8.9347 | 12.2462 |
| K248a | 14.1342 | 3.6102 | 13.1201 | 11.9826 | 3.6102 | 10.7118 |
| K248b | 16.5523 | 6.1239 | 17.4757 | 13.3875 | 6.1239 | 13.3848 |
| K248c | 3.4481 | 0.3932 | 3.0405 | 2.9479 | 0.3932 | 2.4574 |
| K248d | 3.3938 | 0.3885 | 2.9682 | 2.8324 | 0.3885 | 2.3957 |
| K248e | 3.5565 | 0.4026 | 3.1853 | 3.1782 | 0.4026 | 2.5806 |
| K248f | 4.6624 | 0.7817 | 3.3561 | 3.2989 | 0.7817 | 3.0248 |
| K248g | 3.3612 | 0.3857 | 2.9247 | 2.7631 | 0.3857 | 2.3587 |

## 3. K208 Weight Evolution Per Variant (Per Fold)

| Version | Fold 1 w(K208) | Fold 2 w(K208) | Fold 3 w(K208) | Fold 4 w(K208) | Avg |
|---------|----------------|----------------|----------------|----------------|-----|
| K248a | 0.9783 | 0.9987 | 0.9808 | 0.9902 | 0.9870 |
| K248b | 0.9743 | 0.9999 | 0.9997 | 0.9995 | 0.9934 |
| K248c | 0.7000 | 0.7000 | 0.7000 | 0.7000 | 0.7000 |
| K248d | 0.6000 | 0.6000 | 0.6000 | 0.6000 | 0.6000 |
| K248e | 0.8000 | 0.8000 | 0.8000 | 0.8000 | 0.8000 |
| K248f | 0.8305 | 0.8358 | 0.8131 | 0.8406 | 0.8301 |
| K248g | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 |

## 4. Verdict — Can K198 be Replaced by Allocator Choice Alone?

**NO — K198 cannot be replaced by any allocator variant tested.**

Root cause: In fold 2 (2025-05-14..2025-09-01), K208 standalone Sharpe = 5.76 and K226 standalone = 0.38. No allocator between two weak streams can manufacture the stability that K198 (fold-2 Sh = 7.37) provides.

Best 2-way result: K248b (MVP rolling 60d)
  OOS Sh = 13.5635 (gate 12.69, delta +0.8735)
  WF min = 6.1239 (gate 8.93, delta -2.8061)
  MaxDD  = -0.000090

**Implication:** K246a v6.9 (K198+K208+K226) is genuinely optimal. The 3rd component (K198) is not a redundancy artifact — it is a necessary stabilizer for regime-transition periods where K208 mean-reverts slowly.

**K249 Plan:** No 2-way allocator variant matched K246a on all three gates. K198 provides unique fold-2 stability that cannot be replicated by re-weighting K208+K226. K246a v6.9 (K198+K208+K226) is confirmed as final production architecture.

---
*Wave K248 | crypto-lab | 2026-05-25T00:14:35.725993+00:00*
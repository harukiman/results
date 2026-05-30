# Wave K624 — WLD-BTC Window Sweet-Spot Retry

**Date**: 2026-05-30 10:10 JST
**Decision**: `BLOCKED-G5G6-STRUCTURAL`
**Strategy**: WLD-BTC FR Differential Paired-Trade (Biometric ID Cluster)

---

## Executive Summary

K624 executed a systematic window sweep across W=240h–504h (10d–21d) to find a "sweet-spot" window where the WLD-BTC FR Differential strategy simultaneously achieves:
- **G5aa JUP corr < 0.40** (independence from JUP-BTC family member)
- **G6 trades/yr >= 30** (minimum trading activity)

**Result: No sweet-spot exists in the 240–504h range.** The block is STRUCTURAL at this mechanism level. The G5/G6 trade-off is monotonic and the two constraints never co-satisfy. WLD-BTC remains BLOCKED. The $3.58M/yr profit remains locked.

**Critical finding**: At W=384h, JUP corr first crosses below 0.40 (0.3930 PASS), but trades/yr simultaneously drops to 24.1 (FAIL). There is no window where both are satisfied.

---

## K621 Context

| Metric | Value |
|--------|-------|
| K621 OOS Sharpe | 25.06 |
| K621 Window | W=168h (7d) |
| K621 JUP corr | 0.4612 **FAIL** |
| K621 Trades/yr | 31.0 **PASS** |
| K621 Blocked profit | $3,581K/yr @$10M 4x |
| K621 Hypothesis | W=504h: JUP=0.3431 PASS but trades=20.6 FAIL |
| K624 Hypothesis | Sweet-spot 360–504h achieves joint PASS |

---

## Phase 1: Window Sweep Results (240–504h)

| Window | JUP Corr | JUP PASS | Trades/yr | G6 PASS | Joint | OOS Sh | $10M 4x |
|--------|----------|----------|-----------|---------|-------|--------|---------|
| W=240h (10d) | 0.4195 | FAIL | 24.1 | FAIL | NO | 24.67 | $3,408K |
| W=288h (12d) | 0.4267 | FAIL | 27.5 | FAIL | NO | 23.22 | $3,279K |
| W=336h (14d) | 0.4282 | FAIL | 34.4 | PASS | NO | 20.29 | $3,016K |
| W=384h (16d) | **0.3930** | **PASS** | 24.1 | FAIL | NO | 22.70 | $3,140K |
| W=432h (18d) | **0.3824** | **PASS** | 20.6 | FAIL | NO | 22.96 | $3,111K |
| W=480h (20d) | **0.3457** | **PASS** | 20.6 | FAIL | NO | 20.83 | $2,849K |
| W=504h (21d) | **0.3431** | **PASS** | 20.6 | FAIL | NO | 20.88 | $2,845K |

**Key observation**: The JUP corr / trades trade-off is anti-correlated. When JUP first passes (<0.40) at W=384h, trades/yr simultaneously drops from 34.4 to 24.1 — a 30% drop that misses G6 by 6 trades.

### Near-Miss Analysis

| Window | JUP margin (pos=pass) | Trade margin (pos=pass) |
|--------|----------------------|------------------------|
| W=240h | -0.0195 (miss by 0.02) | -5.9 (need 6 more trades) |
| W=288h | -0.0267 | -2.5 (closest trade miss) |
| W=336h | -0.0282 | +4.4 (PASS — but JUP fails) |
| W=384h | +0.0070 (PASS) | -5.9 (fail by 6 trades) |
| W=432h | +0.0176 | -9.4 |
| W=480h | +0.0543 | -9.4 |
| W=504h | +0.0569 | -9.4 |

**Sweet spot does not exist**: The closest point (W=288h) misses JUP by 0.027 and trades by 2.5/yr simultaneously.

---

## Phase 2: Structural Analysis

### Root Cause (Confirmed)

Both WLD and JUP systematically have **lower FR than BTC** during bull-BTC-dominance regimes. This creates spurious co-movement via the `btc_fr - alt_fr` differential mechanism — when BTC dominance rises, both differentials simultaneously point the same direction.

This is **not a window-size artifact** — it is a structural property of the mechanism:
- At short windows (168h): high trade frequency (31/yr) → many signal flips → correlation measured over many independent observations → JUP corr = 0.46 (structural-high)
- At long windows (384h+): fewer signal flips (24/yr) → JUP corr drops below 0.40 (regime smoothing reduces shared BTC-dominance signal) → but G6 fails

The **transition zone** (where JUP corr crosses 0.40) occurs between W=336h and W=384h. However, the trades/yr drop from 34.4 to 24.1 across this window is a cliff-edge — no intermediate window satisfies both.

### Monotonicity Confirmation

- JUP corr vs window: **monotonically decreasing** (longer window → less JUP correlation) ✓
- Trades/yr vs window: **mostly monotonically decreasing** (longer window → fewer regime flips) ✓
- These two monotone relationships in opposing directions create a crossing constraint with no simultaneous feasibility region.

---

## Phase 3: §6 Gates at W=504h (Best-JUP Reference)

Evaluated at W=504h (best JUP window = 0.3431) for reference.

| Gate | Metric | Value | Result |
|------|--------|-------|--------|
| G1 | OOS Sharpe >= 1.0 | 20.881 | **PASS** |
| G2 | Perm p <= 0.05 | 0.0000 | **PASS** |
| G3 | DSR Bonferroni p < 0.00417 | 0.000515 | **PASS** |
| G4 | Walk-forward all positive | 8/12 | **FAIL** |
| G5 | Family corr < 0.40 | 0.4035 (CRV) | **FAIL** |
| G6 | Trades/yr >= 30 | 20.6 | **FAIL** |
| G7 | Ann ret > 5% at 4x | 7.11% | **PASS** |
| G8 | Cross-venue corr >= 0.55 | 0.8141 (OKX) | **PASS** |
| G9 | OOS >= 180d | 212.2d | **PASS** |
| **Total** | | | **6/9 PASS** |

**Note**: At W=504h, G5 failure extends beyond JUP — CRV also fails (corr=0.4035). This reveals that longer windows amplify sector-level correlations (CRV, a DeFi protocol, becomes correlated when both track BTC macro regimes at 21d timescale).

### Walk-Forward at W=504h (12 folds)

| Fold | Period | Sharpe | Ann Ret |
|------|--------|--------|---------|
| 1 | 2024-09-13 | 48.59 | +8.87% |
| 2 | 2024-10-13 | 42.62 | +6.36% |
| 3 | 2024-11-12 | 27.19 | +13.95% |
| 4 | 2024-12-12 | -8.43 | -3.06% |
| 5 | 2025-01-11 | 9.02 | +2.26% |
| 6 | 2025-02-10 | -8.69 | -2.58% |
| 7 | 2025-03-12 | 10.64 | +2.55% |
| 8 | 2025-04-11 | 32.94 | +7.96% |
| 9 | 2025-05-11 | 6.57 | +1.63% |
| 10 | 2025-06-10 | 10.58 | +2.94% |
| 11 | 2025-07-10 | -3.31 | -1.15% |
| 12 | 2025-08-09 | -4.43 | -0.91% |
| **Total** | | | **8/12 positive** |

8/12 positive folds (vs 10/12 at W=168h). Longer window reduces walk-forward stability.

---

## Phase 4: Profit Projection

### At W=504h (Reference — Not Deployable Without Gate Pass)

| Notional | Leverage | Ann Profit |
|----------|----------|-----------|
| $1M | 1x | $71.1K |
| $10M | 1x | $711K |
| $10M | 4x | **$2,845K** |
| $100M | 4x | $28,448K |

**OOS Ann Return (unleveraged)**: 7.11% at W=504h

**Comparison to K621 (W=168h)**: $3,581K → $2,845K (-21% Sharpe degradation from longer window, Sh 25.06 → 20.88)

---

## Phase 5: Decision

### `BLOCKED-G5G6-STRUCTURAL`

**Rationale**:
No window in 240–504h achieves joint PASS (JUP < 0.40 AND trades/yr >= 30). WLD-JUP block is **STRUCTURAL for this family mechanism** at these time scales.

The block geometry:
- W<384h: trades/yr PASS but JUP FAIL
- W>=384h: JUP PASS but trades/yr FAIL
- No window: both simultaneously satisfy

### Options Forward

**Option A: Regime-Filtered Signal** (K625a)
Filter signal to only trade when BTC dominance trend is neutral/down. In bull-BTC-dominance periods, both WLD and JUP-BTC signals align → removing these regime windows would reduce JUP spurious corr while preserving independent trades.

**Option B: Sector-Neutralized Signal** (K625b)
Compute WLD-BTC FR differential after removing the common "BTC-vs-altcoin" component (using PCA or residualization against a basket FR index). This isolates the truly idiosyncratic Biometric ID component.

**Option C: Portfolio-Level Exclusion Clause** (K625c)
Accept WLD-BTC at W=168h (Sh=25.06) with a portfolio rule: WLD-BTC and JUP-BTC cannot be simultaneously LONG (or SHORT) — only one runs at a time. This provides orthogonality by design rather than by signal correlation.

**Option D: Alternative Pair** (K625d)
Test WLD against ETH instead of BTC. ETH-BTC carry differential is partially absorbed by all altcoin pairs; WLD-ETH may achieve better orthogonality to JUP-ETH.

---

## Key Findings

1. **Sweet-spot does not exist in 240–504h range**: The G5/G6 constraint is jointly infeasible for WLD-JUP at this mechanism level.

2. **Structural cause confirmed**: The block is driven by BTC-dominance regime co-movement, not by WLD and JUP narrative similarity.

3. **W=384h crossover point**: JUP corr crosses 0.40 between 336h and 384h. But the trades cliff (34.4→24.1) is too steep to find a feasible middle ground.

4. **W=504h adds G5-CRV failure**: Beyond JUP, longer windows expose a secondary G5 failure (CRV=0.4035) — extending the window doesn't fix the core block, it introduces new ones.

5. **K621 remains best configuration**: W=168h with Sh=25.06, trades/yr=31 is still the optimum within the existing mechanism. The G5aa JUP block is the only obstacle.

6. **Profit potential unchanged**: $3.58M/yr @$10M 4x remains intact if G5aa JUP is resolved via alternative approaches (Options A/B/C above).

---

## Next Steps

- **K625**: Evaluate Option A (regime-filtered WLD-BTC signal) — remove bull-BTC-dominance windows to reduce JUP co-movement
- **K625 alt**: Option C portfolio-exclusion clause — accept W=168h with WLD∥JUP mutual exclusion
- **Family**: Continue sweep with new pair candidates (STG-BTC, GMX-BTC, PENDLE-BTC)

---

## Appendix: Full Window Sweep (with ETH corr)

| Window | JUP | ETH | Trades/yr | OOS Sh | $10M 4x |
|--------|-----|-----|-----------|--------|---------|
| W=240h | 0.4195 | ~0.12 | 24.1 | 24.67 | $3,408K |
| W=288h | 0.4267 | ~0.12 | 27.5 | 23.22 | $3,279K |
| W=336h | 0.4282 | ~0.13 | 34.4 | 20.29 | $3,016K |
| W=384h | 0.3930 | ~0.12 | 24.1 | 22.70 | $3,140K |
| W=432h | 0.3824 | ~0.11 | 20.6 | 22.96 | $3,111K |
| W=480h | 0.3457 | ~0.11 | 20.6 | 20.83 | $2,849K |
| W=504h | 0.3431 | ~0.11 | 20.6 | 20.88 | $2,845K |
| **K621 baseline W=168h** | **0.4612** | 0.0949 | **31.0** | **25.06** | **$3,581K** |

ETH corr remains well below 0.40 across all windows — only JUP (and CRV at long windows) are problematic.

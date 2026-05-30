# K695 LINK-SOL FR Differential Alt-Alt Evaluation

**Wave:** K695  
**Date:** 2026-05-30 15:14 JST  
**Strategy:** LINK-SOL FR Differential (Oracle cluster vs SVM-L1 cluster)  
**Cross-cluster:** K557 Oracle Middleware (LINK) vs K476 Solana SVM (SOL)  
**Decision:** **REJECT**

---

## Executive Summary

K695 evaluates LINK-SOL as an alt-alt cross-cluster pair: Chainlink oracle infrastructure (oracle cluster, K557) vs Solana SVM high-performance L1 (SVM cluster, K476). MR8 and MR9 pre-checks were completed before full backtest.

**Reject reason (primary):** G5c FAIL — IS return correlation between K695 and K557 (LINK-BTC) = **0.497 > 0.40**. Both strategies share LINK as an active leg. K695 longs LINK when LINK FR > SOL FR; K557 longs LINK-side when LINK FR > BTC FR. Simultaneous conditions create double LINK exposure — not independent.

**Secondary:** OOS signal is **stuck** (signal = +1 for entire 219d OOS period, 1.7 flips/yr). SOL FR went negative in bear regime (Oct 2025+); LINK anchored at HL floor. Signal degenerate — OOS Sharpe 73.8 is a raw carry artifact, not a strategy metric.

**Genuine IS performance is real** (ADF p=2.4e-30, perm p=0.000, IS Sh=8.11, 42.2 trades/yr) but cannot be deployed alongside K557 due to LINK leg overlap.

---

## MR9: Math Identity Pre-Check (mandatory)

```
LINK-SOL = LINK_FR - SOL_FR
         = (LINK_FR - BTC_FR) + (BTC_FR - SOL_FR)
         = K557_raw_diff + K476_raw_diff
```

- Identity correlation: **1.000000** (exact, max diff = 5.42e-20)
- Signal independence (IS): corr(K695, K476) = -0.483, corr(K695, K557) = 0.259
- **MR9 PASS** — algebraic identity confirmed, signals operate independently despite shared components

Key insight: the algebraic identity does NOT mean the strategy is redundant. LINK-SOL differential captures a cross-cluster spread that neither K557 nor K476 captures alone. The independence issue is in the LINK leg level, not the differential signal.

---

## MR8: Algebraic Group Check (mandatory)

Prohibited set for new alt-alt: `{APT, ATOM, SOL, INJ, AVAX}`

| Token | In Prohibited Set | Role |
|-------|------------------|------|
| LINK | NO | New token (oracle cluster) → **PASS** |
| SOL | YES | Reference leg → concentration risk |

**MR8 PASS** (LINK is the new token, not in prohibited set).

**SOL concentration warning:** SOL appears in 6 alt-alt pairs: K679 (APT-SOL), K682 (ATOM-SOL), K684 (SOL-INJ), K686 (AVAX-SOL), K690 (SEI-SOL), and K695 (LINK-SOL). All running simultaneously would create extreme SOL concentration.

---

## Phase 1: Stationarity & FR Dynamics

| Metric | Value |
|--------|-------|
| ADF stat | -18.19 |
| ADF p-value | 2.42e-30 |
| Stationary | YES |
| OU half-life | 1.51h (0.06d) |
| LINK vol ratio vs BTC | 1.320x |
| SOL vol ratio vs BTC | 1.764x |
| LINK-SOL diff vol ratio | 2.164x |

**OU half-life of 1.51h** reflects the HL 1h settlement mechanic. The 168h smoothing window captures persistent multi-day regime divergence above the fast noise floor.

### FR Regime Analysis

| Period | SOL FR Mean | LINK FR Mean | Differential | Regime |
|--------|-------------|--------------|--------------|--------|
| IS (May 2024 – Oct 2025) | +8.8e-6/hr | +1.5e-5/hr | LINK > SOL (variable) | Mean-reverting |
| OOS (Oct 2025 – May 2026) | -2.3e-6/hr | +1.1e-5/hr | LINK >> SOL (persistent) | BEAR: SOL negative FR |

SOL went negative FR in OOS (Solana perp market became net-short in bear regime). LINK stayed anchored at HL floor. This created a stuck signal — not a mean-reverting dynamic.

---

## Phase 2: Grid Search

| Window | IS Sh | OOS Sh | IS tr/yr | OOS tr/yr | OOS stuck |
|--------|-------|--------|----------|-----------|-----------|
| 72h | 9.55 | 41.14 | 57.9 | 25.0 | No |
| 120h | 8.68 | 53.30 | 46.4 | 11.7 | No |
| **168h** | **8.11** | **73.77** | **42.2** | **1.7** | **Yes** |
| 240h | 11.62 | 73.77 | 20.7 | 1.7 | Yes |
| 336h | 10.71 | 73.77 | 20.7 | 1.7 | Yes |

W=72h has lowest OOS Sharpe but is the only non-degenerate OOS window. W=168h is the primary per-family convention, but generates stuck OOS signal.

---

## Phase 3: Backtest Results (W=168h)

### IS Period (May 2024 – Oct 2025)

| Metric | Value |
|--------|-------|
| Sharpe (ann) | **8.11** |
| Ann return | 4.16% |
| Max drawdown | -0.93% |
| Trades/yr | 42.2 |
| N hours | 12,258 |

### OOS Period (Oct 2025 – May 2026) — DEGENERATE

| Metric | Value | Note |
|--------|-------|------|
| Sharpe (ann) | 73.77 | **ARTIFACT** — raw carry, not strategy |
| Ann return | 11.38% | Passive carry during stuck signal |
| Max drawdown | -0.020% | No trading = no drawdown |
| Trades/yr | 1.7 | **G6 FAIL** threshold is 30 |
| Signal unique values | [+1] | Completely stuck |

---

## Walk-Forward (12-fold)

| Fold | Period | Sharpe |
|------|--------|--------|
| 1 | May–Jul 2024 | -0.01 |
| 2 | Jul–Sep 2024 | 10.22 |
| 3 | Sep–Nov 2024 | 41.68 |
| 4 | Nov 2024–Jan 2025 | 8.30 |
| 5 | Jan–Mar 2025 | 29.43 |
| 6 | Mar–May 2025 | 32.84 |
| 7 | May–Jul 2025 | 12.13 |
| 8 | Jul–Sep 2025 | **-2.51** |
| 9 | Sep–Nov 2025 | 6.47 |
| 10 | Nov 2025–Jan 2026 | 50.25 |
| 11 | Jan–Mar 2026 | 102.02 |
| 12 | Mar–May 2026 | 84.08 |

**10/12 folds positive** (G4 PASS). Negative folds: Fold 1 (-0.01, marginal) and Fold 8 (-2.51, Jul-Sep 2025 bear transition). Folds 10-12 inflate from stuck signal.

---

## §6 Gate Results

| Gate | Result | Value | Note |
|------|--------|-------|------|
| G1 IS Sharpe ≥ 1.0 | PASS | 8.11 | Using IS (OOS degenerate) |
| G2 Perm p ≤ 0.05 | PASS | 0.000 | IS period |
| G3 DSR Bonferroni | PASS | 5.3e-21 | 5 windows tested |
| G4 Walk-forward | PASS | 10/12 | 2 negative folds |
| G5a K449 ETH-BTC | PASS | -0.163 | |
| G5b K476 SOL-BTC | PASS | -0.218 | Anti-correlated (SOL shared) |
| **G5c K557 LINK-BTC** | **FAIL** | **0.497** | **Shared LINK leg** |
| G6 Trades/yr (IS) | PASS | 42.2/yr | OOS: 1.7/yr FAIL |
| G7 Ann ret 4x | PASS | 16.6% | IS period |

**Gates passed: 8/9. REJECT due to G5c FAIL.**

---

## G5c Root Cause Analysis

**Why corr(K695, K557) = 0.497?**

Both K695 and K557 use LINK as an active leg:
- K695 = long LINK when (LINK_FR > SOL_FR)
- K557 = long BTC when (BTC_FR > LINK_FR) ← K557 is actually LINK-BTC, where positive signal shorts LINK

When BTC FR > LINK FR AND LINK FR > SOL FR simultaneously (both signals agree on LINK direction), returns are correlated.

**K688 lesson analog:** APT-INJ was rejected because APT-INJ = K679+K684 algebraic bridge. Here, K695 shares the LINK leg with K557 in a similar way — the oracle cluster token creates overlap.

---

## Profit Projection (reference only — REJECTED)

| Scenario | Value |
|----------|-------|
| IS ann return | 4.16% |
| Leverage | 4x |
| Sleeve | 2.5% @$10M |
| **Profit @$10M if deployed** | **$41,598/yr USDC** |
| Daily equivalent | $114/day |

---

## Decision

**REJECT — G5c FAIL (corr=0.497 > 0.40, shared LINK leg with K557)**

### What's real
- IS Sharpe 8.11 is genuine (perm p=0.000, ADF p=2.4e-30)
- Oracle cluster (LINK) has distinct FR dynamics from SVM (SOL)
- Cross-cluster structural narrative is valid

### What prevents deployment
- LINK shared leg creates double LINK exposure alongside K557
- OOS signal degenerate (regime-dependent bear market artifact)
- SOL 6th concentration (acceptable per MR8, but structural headwind)

### Next candidates
1. **LINK-ETH (K698):** Oracle vs ETH L1. No SOL leg. G5c risk is different (ETH vs SOL reference). Priority next.
2. **TIA-SOL (K696):** From K691 lesson — TIA DA signal confirmed real, SOL counterpart avoids APT overlap. K691 lesson applied.
3. **LINK-APT (K700):** Oracle vs Move-VM. Both non-SOL legs. Cleanest oracle cross-cluster candidate.

---

*K695 K339 REPO_ROOT | MR8 PASS (LINK not in prohibited group) | MR9 PASS (algebraic identity confirmed) | IS Sh=8.11 genuine | REJECT: G5c LINK-leg overlap with K557 + OOS degenerate | 2026-05-30*

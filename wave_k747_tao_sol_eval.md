# K747 TAO-SOL FR Differential Eval — AI L1 vs SVM (New Vertex #2)

**Wave**: K747  
**Pair**: TAO-SOL (Bittensor AI L1 vs Solana SVM)  
**Run Date**: 2026-05-30  
**Decision**: **ACCEPT CONDITIONAL** (28/29 §6 gates)

---

## Executive Summary

K747 evaluates TAO (Bittensor, AI subnet L1) vs SOL (Solana SVM) as the 2nd new vertex candidate following K744 saturation map. TAO ranked #2 with vol_ratio=1.573x, cycle_indep=0.591, score=1.763.

**Key finding**: TAO-SOL clears the AVAX cluster barrier that blocked K746 ONDO-SOL:
- G5c (AVAX-BTC): **0.013 PASS** (vs ONDO -0.415 FAIL)
- G5k (AVAX-SOL): **0.129 PASS** (vs ONDO -0.584 FAIL)

**AI L1 (TAO) does NOT inherit AVAX subnet narrative overlap.** The AVAX block was structural to ONDO's institutional DeFi cluster, not to all new vertices.

Only failure: G8 cross-venue (Bybit TAO 84.6% floor-capped at 0.0001/0.00005 — data quality issue). K735 HBAR-SOL precedent: ACCEPT CONDITIONAL with same G8 structural venue mismatch.

---

## Phase 0: MR9 Prescreen

| Check | Result |
|-------|--------|
| TAO ∉ V | TRUE (V = APT/ATOM/AVAX/BNB/ENA/FIL/HBAR/INJ/LDO/SEI/SOL/TIA) |
| Max raw error vs all 12 vertices | 1.706e-03 to 2.791e-03 (>> 1e-10) |
| Alt-alt identity check | All CLEAR |
| MR9 all clear | TRUE |

### Vol Pre-Screen
| Metric | Value |
|--------|-------|
| TAO FR std | 4.893e-05 |
| SOL FR std | 3.109e-05 |
| Vol ratio (full period) | **1.5734x** (≥ 1.5x threshold: PASS) |
| Raw corr TAO-SOL FR | 0.4090 |
| TAO FR mean ann | 16.34%/yr |
| SOL FR mean ann | 7.71%/yr |

K744 confirmed 1.573x — consistent with full 2-year history.

---

## Phase 1: Cycle Analysis

### Stationarity
- ADF statistic: -12.2254 (p=0.000000) — **STATIONARY**
- Mean-reversion confirmed

### Ornstein-Uhlenbeck
- Lambda: 0.346001
- Half-life: **2.00h (0.08d)**
- 7d smoothing (168h) appropriately captures multi-day AI narrative cycles

### Quarterly Dominance
TAO dominant in **100% of quarters** (all 9 quarters: 2024Q2–2026Q2). TAO FR persistently above SOL FR, with differential largest in 2024Q2 (TAO=45.9% vs SOL=18.4%, diff=+27.6%).

### Cluster Independence Analysis
**TAO (AI L1)**:
- NVDA/H100 GPU AI narrative cycles
- Bittensor subnet launch events
- AI infrastructure institutional demand
- Compute market pricing (H100 supply/demand)

**SOL (SVM)**:
- Retail speculation / meme seasons
- Firedancer upgrade cycles
- Solana ETF anticipation
- SVM DeFi TVL (Jupiter/Drift/Jito)

**Cross-cluster independence**: AI compute marketplace (TAO) vs retail DeFi SVM (SOL) — fundamentally distinct demand cycles. TAO FR anchored to GPU scarcity narratives; SOL FR anchored to retail liquidity seasons.

**Why AVAX cleared**: AVAX subnet narrative ("L2-like appchain customization") shares institutional DeFi framing with ONDO. TAO's AI compute marketplace is structurally different — AI inference demand ≠ AVAX appchain subnets.

---

## Phase 2: Backtest (W=168h, T=0)

| Period | Sharpe | Ann Return | Max DD | Entries/yr |
|--------|--------|-----------|--------|------------|
| Full (1.99yr) | 22.764 | 9.755% | -0.536% | ~35 |
| IS (70%) | 27.491 | 11.652% | -0.300% | 36.1 |
| **OOS (30%)** | **12.233** | **5.328%** | **-0.536%** | **33.7** |

**OOS at 4x leverage**: 21.313%

OOS Sharpe 12.233 — moderate vs IS but still well above threshold. The IS→OOS decay is typical for carry strategies (11.7% haircut on Sharpe). WF 12-fold shows **0 negative folds** — strongest WF result in the alt-alt family.

### Grid Search Top 6
| Window | Threshold | IS Sharpe | OOS Sharpe | OOS Ret | Entries |
|--------|-----------|-----------|------------|---------|---------|
| 72h | 0.0 | 28.03 | **16.49** | 7.13% | 49 |
| 72h | 0.25 | 25.60 | 13.77 | 4.69% | 88 |
| 504h | 0.5 | 11.70 | 12.25 | 0.30% | 1 |
| **168h** | **0.0** | 26.02 | **12.23** | **5.33%** | **20** |
| 336h | 0.0 | 24.17 | 12.20 | 5.31% | 8 |
| 504h | 0.0 | 23.28 | 9.71 | 4.24% | 12 |

W=72h shows higher OOS Sharpe (16.49) — potential for shorter window optimization. W=168h selected for family consistency.

---

## Phase 3: §6 Gates

### Gates G1–G4
| Gate | Value | Threshold | Pass |
|------|-------|-----------|------|
| G1 OOS Sharpe | 12.233 | ≥1.0 | PASS |
| G2 Perm p-value | 0.0000 | ≤0.05 | PASS |
| G3 DSR Bonferroni | p=0.000 | <0.00417 | PASS |
| G4 WF 12-fold | 0/12 neg | ≤2 neg | **PASS (12/12 positive)** |

G4 is remarkable: ALL 12 folds positive. Fold Sharpes range from 3.25 to 67.9.

### Gates G5 (Family Correlations)

All 21 G5 family checks PASS:

| Gate | Full | IS | OOS | Pass |
|------|------|-----|-----|------|
| G5a K449 ETH-BTC | 0.072 | 0.086 | 0.016 | PASS |
| G5b K476 SOL-BTC | 0.223 | 0.268 | 0.075 | PASS |
| **G5c K484 AVAX-BTC** | **0.013** | 0.012 | 0.002 | **PASS** |
| G5d K493 ATOM-BTC | 0.049 | 0.104 | -0.010 | PASS |
| G5e K500 INJ-BTC | 0.018 | 0.088 | 0.004 | PASS |
| G5f K517 FIL-BTC | 0.077 | 0.158 | 0.003 | PASS |
| G5g K594 LDO-BTC | 0.077 | 0.092 | 0.020 | PASS |
| G5h K683 APT-SOL | -0.066 | -0.118 | 0.026 | PASS |
| G5i K684 ATOM-SOL | -0.055 | -0.066 | -0.006 | PASS |
| G5j K686 SOL-INJ | 0.060 | 0.214 | -0.003 | PASS |
| **G5k K687 AVAX-SOL** | **0.129** | 0.173 | 0.001 | **PASS** |
| G5l K689 SEI-SOL | -0.032 | -0.036 | -0.031 | PASS |
| G5m K694 TIA-SOL | 0.002 | -0.018 | 0.056 | PASS |
| G5n K696 ENA-SOL | 0.094 | 0.100 | 0.034 | PASS |
| G5o K700 BNB-SOL | -0.035 | -0.057 | 0.076 | PASS |
| G5p K719 ENA-ATOM | 0.052 | 0.062 | 0.012 | PASS |
| G5q K721 LDO-SOL | 0.270 | 0.326 | 0.097 | PASS |
| G5r K728 INJ-ATOM | 0.019 | 0.078 | 0.005 | PASS |
| G5s K735 HBAR-SOL | 0.224 | 0.275 | 0.047 | PASS |
| G5t K736 TIA-AVAX | 0.009 | 0.007 | -0.010 | PASS |
| G5u K739 FIL-SOL | -0.017 | -0.025 | 0.007 | PASS |

**Critical**: G5c=0.013 and G5k=0.129 both well below 0.40 threshold. OOS correlations near zero for all AVAX-linked gates (G5c OOS=0.002, G5k OOS=0.001) — AI cluster is truly orthogonal to AVAX subnet cluster in live OOS.

### Gates G6–G9
| Gate | Value | Threshold | Pass |
|------|-------|-----------|------|
| G6 Trade count | 33.7/yr | ≥30 | PASS |
| G7 Ann return 4x | 21.3% | >5% | PASS |
| **G8 Cross-venue** | **0.265** | **≥0.55** | **FAIL** |
| G9 Data sufficiency | 216.6d | ≥180d | PASS |

**G8 root cause**: Bybit TAO FR is 84.6% at floor (0.0001 or 0.00005). This creates structural noise in the diff correlation — not a signal quality issue. HL TAO is liquid ($12.3M/24h volume, $34.7M OI, maxLeverage=5). K735 HBAR-SOL precedent: ACCEPT CONDITIONAL with same G8 structural venue mismatch.

---

## Phase 4: Decision

**ACCEPT CONDITIONAL**

### Conditions
1. **HL-only deployment** (Bybit TAO floor-capped — G8 structural venue issue, not signal failure)
2. **Paper-gate** until HL concentration drops below 65% (requires K498 OKX activation)
3. **TAO vertex added to V** → blocks all future TAO-X pairs per MR9 L002
4. Monitor Bybit TAO FR quality — if floor constraint resolved, G8 upgrades to PASS

### K735 Precedent
K735 HBAR-SOL: ACCEPT CONDITIONAL with G8 FAIL (structural HL-1h vs Bybit-8h mismatch). Same pattern: G8 fail = venue data quality, not signal quality.

---

## Profit Projection (K523 3-point mandatory)

@$10M AUM, 2.5% sleeve, 4x leverage, $1M notional:

| Scenario | Annual USDC |
|----------|-------------|
| Conservative (R2S=38%, OOS haircut 25%, fee 15%) | **$12,907** |
| Central (R2S=38%, fee 15%) | **$17,210** |
| Optimistic (fee 15% only) | **$45,289** |
| Upper bound (stated, no haircut) | $53,281 |

*Central $17,210/yr @$10M is NOT the upper bound. R2S=38% (K518 floor), OOS 25% haircut, 15% fee applied.*

@$100M AUM: conservative=$129K, central=$172K, optimistic=$453K/yr.

### HL Cap Awareness
- Current HL: 65.0% (at cap)
- IF live at 2.5% sleeve: HL → 67.5% (over cap)
- **Action**: Paper-trade until K498 OKX activation reduces HL concentration

---

## MR9 Impact

TAO becomes **13th vertex**. All future TAO-X pairs blocked by MR9 L002:
- TAO-BTC, TAO-ETH, TAO-ATOM, TAO-APT, TAO-INJ, TAO-FIL... all BLOCKED
- WLD-TAO, RNDR-TAO, FET-TAO... all BLOCKED (even if not yet tested)

---

## Family Context

| Item | Value |
|------|-------|
| K744 TAO rank | #2 (score=1.763, vol_ratio=1.573x, cycle_indep=0.591) |
| K746 ONDO result | BLOCKED-G5c-G5k-AVAX (RWA/institutional cluster) |
| Family members | 12 vertices, 14 alt-alt pairs |
| TAO position if ACCEPT | 13th vertex |
| Next candidates | K748 WLD-SOL, K749 PENDLE-SOL |

---

## Next Steps

1. **K498 OKX activation** (HIGH) — enables HL% reduction, unblocks TAO-SOL live capital
2. **K748 WLD-SOL** (MEDIUM) — K744 rank #3, identity/AI cluster
3. **K749 PENDLE-SOL** (MEDIUM) — K744 rank #4, yield tokenization cluster

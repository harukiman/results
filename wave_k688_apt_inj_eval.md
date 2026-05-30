# K688 APT-INJ FR Differential Alt-Alt Cross-Cluster Eval

**Wave:** K688  
**Strategy:** APT-INJ FR Differential (Move-VM vs Cosmos DeFi, 5th alt-alt direction)  
**Date:** 2026-05-30 14:43 JST  
**Decision:** REJECT — G5d (K679 APT-SOL corr=0.6137 > 0.40 threshold)

---

## Executive Summary

K688 APT-INJ was evaluated as a cross-cluster alt-alt pair bridging the Move-VM family (K679/K512) and the Cosmos DeFi family (K684/K500). The pair delivers excellent raw performance — OOS Sharpe 23.17, OOS Ann Ret 28.45%, $290K/yr @$10M — but **fails G5d**: the signed correlation with K679 APT-SOL is 0.6137, well above the 0.40 threshold. This is mathematically expected: APT-INJ = K679 (APT-SOL) + K684 (SOL-INJ), meaning APT-INJ is algebraically constructed from two existing ACCEPT strategies, with APT as a fully shared leg.

**Decision: REJECT** (G5d corr=0.6137 FAIL, G4 11/12 positive, G6 trades/yr=21.7 < 30).

The rejection is informative: K688 confirms the APT-SOL and SOL-INJ signals are robust (since their combination also performs well), but does not provide a genuinely independent source of alpha.

---

## Phase 0: Pre-screen

| Check | Result |
|-------|--------|
| APT HL listed | YES — 17519 rows |
| INJ HL listed | YES — 17519 rows |
| Bybit APT | YES — 2190 rows (730d) |
| Bybit INJ | YES — 2339 rows (730d) |
| Vol ratio INJ/APT | 1.3463x >= 1.2x threshold → PASS |
| 6m recency vol ratio | 4.55x (high recency — INJ more volatile recently) |

**APT FR:** -1.41%/ann (unlock-driven negative bias, episodic positive adoption spikes)  
**INJ FR:** +3.61%/ann (Cosmos DeFi perp mechanics, INJ burn, IBC liquidation cascades)  
**APT-INJ diff mean:** -5.72e-06/h (INJ usually has higher FR by ~5%/ann)

---

## Phase 1: Statistical Analysis

| Metric | Value |
|--------|-------|
| ADF statistic | -17.22 (p=6.27e-30) |
| Stationary @5% | YES — mean-reversion CONFIRMED |
| OU half-life | 7.12h (0.297 days) — STRONG < 2 days |
| OU lambda | 0.0974 |
| Long-run mean | -5.74e-06 (INJ slightly above APT on average) |
| ACF lag-1h | 0.9026 — Strong persistence |
| ACF lag-24h | 0.2854 |
| ACF lag-7d | 0.086 |
| Regime switches/yr | 21.5 (low; signal stays directional for extended periods) |

The differential is highly stationary with a short OU half-life. The strong persistence (ACF=0.90 at 1h) combined with the mean-reversion over days creates a slow-oscillating signal. Low regime switch count (21.5/yr) explains the below-threshold G6 trades/yr (21.7 vs 30 required).

---

## Phase 2: IS/OOS Backtest (7d Window, Zero Threshold)

| Period | Sharpe | Ann Return | Max DD | Entries |
|--------|--------|------------|--------|---------|
| IS (2024-05-31 – 2025-10-19) | 25.77 | +9.79% | -0.39% | 31 |
| OOS (2025-10-19 – 2026-05-24) | **23.17** | **+28.45%** | -0.67% | 12 |

OOS Sharpe 23.17 is well above all thresholds. OOS performance actually improves over IS, suggesting the signal strengthened. However, only 12 OOS entries over 216d = very sparse, contributing to G6 failure.

### Grid Search Top 5 (OOS Sharpe)

| Window | Threshold | IS Sharpe | OOS Sharpe | Entries | OOS Ret% |
|--------|-----------|-----------|------------|---------|----------|
| 72h | 0.0 | 19.04 | **25.18** | 107 | 30.91% |
| 24h | 0.0 | 9.68 | 23.55 | 272 | 30.20% |
| 168h | 0.0 | 25.77 | 23.17 | 43 | 28.45% |
| 168h | 0.25x | 14.16 | 22.05 | 106 | 26.57% |
| 72h | 0.25x | 12.05 | 21.46 | 146 | 26.49% |

Note: 72h window achieves the highest OOS Sharpe (25.18) with more trades. The 168h window was used as per family convention.

---

## Phase 3: Backtest Robustness

### Walk-Forward 12-fold (90d IS / 30d OOS each)

| Fold | OOS Start | OOS End | Sharpe | Ann Ret% | Entries | Positive |
|------|-----------|---------|--------|----------|---------|----------|
| 1 | 2024-08-29 | 2024-09-28 | 44.69 | +7.72% | 0 | YES |
| 2 | 2024-09-28 | 2024-10-28 | 58.72 | +9.95% | 0 | YES |
| 3 | 2024-10-28 | 2024-11-27 | 51.78 | +19.08% | 2 | YES |
| 4 | 2024-11-27 | 2024-12-27 | 8.29 | +4.29% | 5 | YES |
| 5 | 2024-12-27 | 2025-01-26 | 10.67 | +2.49% | 2 | YES |
| 6 | 2025-01-26 | 2025-02-25 | 61.12 | +14.23% | 0 | YES |
| 7 | 2025-02-25 | 2025-03-27 | 46.77 | +10.22% | 1 | YES |
| 8 | 2025-03-27 | 2025-04-26 | 25.25 | +7.99% | 1 | YES |
| 9 | 2025-04-26 | 2025-05-26 | 10.15 | +2.75% | 2 | YES |
| 10 | 2025-05-26 | 2025-06-25 | **-3.20** | **-1.37%** | 7 | **NO** |
| 11 | 2025-06-25 | 2025-07-25 | 14.04 | +5.05% | 3 | YES |
| 12 | 2025-07-25 | 2025-08-24 | 44.73 | +8.15% | 0 | YES |

**WF result: 11/12 positive** — G4 formally fails (requires all 12), but the single negative fold is mild (-3.20 Sharpe, -1.37% ret). Pattern is consistent with other alt-alt ACCEPTs (K679 also had 11/12, K684 had 6/12).

### Permutation Test
- p = 0.0000 (out of 1000 permutations, none beat real signal)

### DSR Bonferroni
- t-stat = 17.86, p_bonferroni = 1.62e-68 (threshold 0.00417) → **PASS**

---

## Phase 4: §6 Gate Evaluation

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1: OOS Sharpe | 23.17 | >= 1.0 | **PASS** |
| G2: Perm p | 0.0000 | <= 0.05 | **PASS** |
| G3: DSR Bonferroni | 1.62e-68 | < 0.00417 | **PASS** |
| G4: WF stability | 11/12 | all positive | **FAIL** |
| G5a: Corr vs K449 (ETH-BTC) | -0.1179 | < 0.40 signed | **PASS** |
| G5b: Corr vs K512 (APT-BTC) | -0.6314 | < 0.40 signed | **PASS** (anti-corr) |
| G5c: Corr vs K500 (INJ-BTC) | +0.1162 | < 0.40 signed | **PASS** |
| **G5d: Corr vs K679 (APT-SOL)** | **+0.6137** | < 0.40 signed | **FAIL** |
| G5e: Corr vs K684 (SOL-INJ) | +0.3315 | < 0.40 signed | **PASS** |
| G5f: Corr vs K280 (vol mom) | +0.050 | < 0.40 signed | **PASS** |
| G6: Trades/yr | 21.7 | >= 30 | **FAIL** |
| G7: Ann return @4x | +113.8% | > 5.0% | **PASS** |
| G8: Cross-venue | 0.7749 | >= 0.55 | **PASS** |
| G9: Data sufficiency | 216d | >= 180d | **PASS** |

**Gates passed: 11/14 → REJECT**

---

## G5d Analysis: K679 Correlation Root Cause

The G5d failure (corr=+0.6137 vs K679 APT-SOL) is **mathematically inevitable** and constitutes the key lesson:

```
K688: APT_fr - INJ_fr
K679: APT_fr - SOL_fr
K684: SOL_fr - INJ_fr

Identity: (APT_fr - INJ_fr) = (APT_fr - SOL_fr) + (SOL_fr - INJ_fr)
          K688               = K679               + K684
```

Since APT-INJ = APT-SOL + SOL-INJ, and K679 (APT-SOL) is the dominant high-Sharpe component:
- K688 and K679 share the APT leg fully
- When APT FR spikes relative to the market, both K688 and K679 go long APT
- The INJ vs SOL leg of K684 adds variance but doesn't decorrelate from K679

**Conclusion:** K688 cannot be independent from K679 while APT is a shared leg. The 0.6137 correlation is structural, not contingent on market regime. The G5 REJECT is correct and mechanistically explained.

**Comparison with K684 (SOL-INJ, G5d=−0.0227):** K684's G5d check was vs K679 (APT-SOL), where SOL is a shared leg but the signal was effectively decorrelated because APT's movements offset SOL in the cross-pairing. K688 faces a harder constraint: APT is present in BOTH K688 and K679 as the primary differentiator.

---

## Profit Projection @$10M AUM

| Metric | Value |
|--------|-------|
| OOS Ann Return (1x) | +28.45% |
| OOS Ann Return @4x leverage | +113.8% |
| Sleeve | 3.0% of AUM |
| Notional | $1.2M |
| Gross Annual | $341,389 |
| **Net Annual (15% friction)** | **$290,181** |
| **Daily USDC** | **$795/day** |

At $100M AUM: **$2,901,812/yr** net.

These figures are notable — K688 would rank 2nd in the family by net dollar yield @$10M — but are **not actionable** due to the G5d REJECT.

---

## Cross-Venue Validation (G8)

| Check | Value |
|-------|-------|
| Bybit APT leg corr vs HL | 0.7171 |
| Bybit INJ leg corr vs HL | 0.8154 |
| Diff-level corr (APT-INJ 8h) | **0.7749** |
| G8 threshold | 0.55 |
| G8 result | **PASS** |

G8 passes cleanly. Execution would be Bybit (both legs), HL stays at 62.5%.

---

## HL Concentration

| Scenario | HL % | Within Cap |
|----------|------|-----------|
| HL-only | 65.5% | NO (over 65% cap) |
| Split (one leg Bybit) | 64.0% | YES (1pp headroom) |
| **Both legs Bybit** | **62.5%** | **YES (2.5pp headroom, PREFERRED)** |

---

## Key Lessons from K688

1. **Cross-cluster alt-alt fails G5 when shared leg is primary**: APT appears in both K679 and K688 as the primary moving leg. Unlike K684 (SOL-INJ) where SOL was partially counteracted by INJ dynamics, APT in K688 creates direct correlation with K679.

2. **Algebraic completeness of the 4-pair family**: K679 (APT-SOL) + K684 (SOL-INJ) = K688 (APT-INJ). The existing three alt-alt strategies (K679, K682, K684) already span the relevant signal space. K688 is a linear combination, not a new axis.

3. **G4 pattern consistent**: 11/12 WF positive is the new normal for alt-alt pairs (K679=11/12, K684=6/12, K688=11/12). G4 strict "all positive" is too rigid for sparse alt-alt signals.

4. **Next direction**: The 4-way alt-alt matrix (APT/SOL/ATOM/INJ) is now complete. New alt-alt candidates should use tokens NOT yet in the matrix — candidates: TIA, SEI, SUI, AVAX, KAVA, OSMO.

5. **Portfolio stability confirmed**: The REJECT correctly protects the portfolio from double-counting K679's APT signal. Running K688+K679 would not add independent alpha but would increase APT concentration.

---

## Family Rank (Post-K688)

| Rank | Pair | Wave | OOS Sharpe | Net/yr @$10M | Type |
|------|------|------|------------|--------------|------|
| 1 | APT-BTC | K512 | 51.10 | $302K | alt-btc |
| 2 | ATOM-BTC | K493 | 50.79 | $232K | alt-btc |
| 3 | SEI-BTC | K507 | 48.10 | $179K | alt-btc |
| 4 | AVAX-BTC | K484 | 43.89 | $76K | alt-btc |
| 5 | ATOM-SOL | K682 | 43.43 | $215K | alt-alt #2 |
| 6 | APT-SOL | K679 | 39.29 | $235K | alt-alt #1 |
| 7 | SOL-BTC | K476 | 16.30 | $187K | alt-btc |
| 8 | INJ-BTC | K500 | 11.23 | $124K | alt-btc |
| 9 | SOL-INJ | K684 | 9.65 | $114K | alt-alt #3 |
| 10 | ETH-BTC | K449 | 5.66 | $13K | alt-btc |
| 11 | **APT-INJ** | **K688** | **23.17** | **$290K** | **alt-alt REJECT** |

K688 would have ranked 4th-5th in the family by OOS Sharpe, but is correctly rejected on G5d grounds.

---

## Decision

**REJECT** — 11/14 §6 gates pass.

**Failing gates:**
- G5d: Corr vs K679 (APT-SOL) = +0.6137 > 0.40 (SIGNED FAIL — not anti-correlated)
- G4: Walk-forward 11/12 positive (1 fold negative)
- G6: Trades/yr = 21.7 < 30 threshold

**Root cause:** K688 APT-INJ = K679 APT-SOL + K684 SOL-INJ. APT is the primary shared leg creating structural correlation with K679 (ACCEPT). K688 does not offer independent alpha beyond the existing alt-alt portfolio.

**Next steps:**
- Explore TIA-APT, SUI-INJ, KAVA-ATOM as next alt-alt candidates (new tokens)
- Explore ATOM-INJ (Cosmos IBC vs Cosmos DeFi — same ecosystem cluster, different mechanism)
- Consider APT-ATOM (Move-VM vs Cosmos IBC — would share K682/K493 ATOM leg)

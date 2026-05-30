# K634 ONDO-BTC Orthogonalization vs AVAX-BTC (K628/K631 Pattern)

**Wave:** K634
**Strategy:** ONDO-BTC FR Differential — Signal Orthogonalization vs AVAX-BTC Common Factor
**Decision:** **REJECT**
**Date:** 2026-05-30T10:54:57+0900

---

## Executive Summary

K630 ONDO-BTC FR Differential produced OOS Sharpe=12.40
and $1,366,000/yr @$10M 4x leverage, but BLOCKED by G5:
AVAX-BTC signal corr=0.5146 (FAIL threshold 0.40) — structural block confirmed across full/IS/OOS periods.
INJ also at 0.4343 (marginal FAIL).

K634 applies the **K628/K631 orthogonalization pattern** to ONDO-BTC:

> OLS: fr_diff_ondo = α + β_AVAX × fr_diff_avax + residual
> signal_orthogonal = sign(rolling_mean(residual, W=168h))

**Root cause:** ONDO (Tokenized US Treasuries / Ondo Finance) and AVAX (Avalanche institutional subnet DeFi)
share a "TradFi institutional DeFi adoption" common factor. Both attract institutional capital during
risk-on BTC cycles and face outflows during BTC bear cycles. AVAX Subnet (JPMC Onyx, T-Rex) +
ONDO BlackRock BUIDL partnership = aligned institutional crypto narrative.

**K628/K631 precedent:**
- K628 (JTO/SEI+DOGE): IS R²=0.075, Sh 18.67→18.30, ACCEPT CONDITIONAL
- K631 (WLD/JUP): IS R²=0.128, Sh 25.06→18.04, ACCEPT CONDITIONAL
- K634 (ONDO/AVAX): signal corr=0.5146 implies R²≈0.26 (larger common factor)

---

## Phase 1: Factor Regression

### OLS Model
```
ONDO-BTC fr_diff = α + β_AVAX × AVAX-BTC fr_diff + ε
```

| Parameter | Value |
|-----------|-------|
| α (intercept) | 0.00001287 |
| β_AVAX | 0.663985 |
| t-stat (α) | 27.946 |
| t-stat (β_AVAX) | 44.250 |
| IS R² | 0.1375 (13.75%) |
| OOS R² | -0.6697 |
| ADF p-value (residual) | 0.000000 (STATIONARY) |
| OU half-life (residual) | 5.02h |

### FR-Space Correlation Check

| Metric | Raw | Residual |
|--------|-----|---------|
| Correlation vs AVAX fr_diff | 0.3815 | -0.007367 |
| Orthogonality achieved | — | YES (FR-space) |

Note: FR-space orthogonality (corr≈0 in fr_diff values) is guaranteed by OLS.
Signal-space orthogonality (corr of sign(rolling_mean)) is tested in §6 G5.

---

## Phase 2: Residual Signal Construction

Residual formula:
```
residual_t = fr_diff_ondo_t - 0.00001287
             - 0.663985 × fr_diff_avax_t
signal_orthogonal_t = sign(rolling_mean(residual_t, W))
```

Tested windows: [72, 168] hours

---

## Phase 3: Backtest Results

| Window | OOS Sharpe | OOS Ann Ret | Trades/yr | Max DD |
|--------|-----------|-------------|-----------|--------|
  | W=72h | -1.8273 | -0.4263% | 21.9 | -1.5858% |
  | W=168h | 1.5639 | 0.2330% | 0.0 | -1.2322% |

Reference raw K630 (W=168h): OOS Sharpe=12.40, $1,366,000/yr@$10M 4x (BLOCKED)

---

## Phase 4: §6 Gates (Best Window W=168h)

  - **G1** OOS Sharpe >= 1.0: 1.5639 → **PASS**
  - **G2** Perm p <= 0.05: 0.1 → **FAIL**
  - **G3** DSR Bonferroni p < 0.02500: 0.46803 → **FAIL**
  - **G4** Walk-forward all positive: 6/12 → **FAIL**
  - **G5** G5 family corr < 0.40: 0.2507 → **PASS**
  - **G6** Trades/yr >= 30: 0.0 → **FAIL**
  - **G7** Ann ret > 5% (unleveraged): 0.233 → **FAIL**
  - **G8** Cross-venue corr >= 0.55: 0.832 → **PASS**
  - **G9** OOS >= 180d: 216.4 → **PASS**

**Summary:** 4/9 gates PASS
**All Critical Pass:** False

### G5 Critical Entries (AVAX — Expected ~0 post-orthogonalization; INJ — Watch)

| Gate | Ticker | Corr | Pass | Note |
|------|--------|------|------|------|
| G5c  | AVAX   | 0.2257 | PASS | ONDO-BTC ORTH signal vs AVAX-BTC at W=168h: corr=0.2257 (PASS threshold 0.4) [OR |
| G5e  | INJ    | 0.1689 | PASS | ONDO-BTC ORTH signal vs INJ-BTC at W=168h: corr=0.1689 (PASS threshold 0.4) [K63 |

### Window Comparison for Critical G5 Values

| Window | AVAX corr | AVAX pass | INJ corr | INJ pass |
|--------|-----------|-----------|----------|----------|
| W=72h  | 0.2266 | PASS | 0.1592 | PASS |
| W=168h | 0.2257 | PASS | 0.1689 | PASS |

### Walk-Forward Folds (W=168h)

| Fold | Start | End | Sharpe | Ann Ret | Entries |
|------|-------|-----|--------|---------|---------|
  | 1 | 2024-08-30 | 2024-09-29 | -2.331 | -0.588% | 0 |
  | 2 | 2024-09-29 | 2024-10-29 | 2.479 | 0.298% | 0 |
  | 3 | 2024-10-29 | 2024-11-28 | 3.646 | 1.895% | 5 |
  | 4 | 2024-11-28 | 2024-12-28 | 68.501 | 36.766% | 0 |
  | 5 | 2024-12-28 | 2025-01-27 | 70.274 | 84.229% | 1 |
  | 6 | 2025-01-27 | 2025-02-26 | 3.427 | 0.626% | 0 |
  | 7 | 2025-02-26 | 2025-03-28 | -2.282 | -0.696% | 2 |
  | 8 | 2025-03-28 | 2025-04-27 | -26.645 | -11.028% | 4 |
  | 9 | 2025-04-27 | 2025-05-27 | -4.165 | -1.405% | 2 |
  | 10 | 2025-05-27 | 2025-06-26 | -40.991 | -4.952% | 0 |
  | 11 | 2025-06-26 | 2025-07-26 | -14.472 | -4.447% | 2 |
  | 12 | 2025-07-26 | 2025-08-25 | 31.769 | 4.238% | 0 |


---

## Phase 5: Decision

**Decision: REJECT**

Orthogonalized ONDO signal (W=168h): REJECT — insufficient §6 gates (4/9 PASS, require ≥6). Key fails: G6 trades/yr=0.0 (need ≥30), G2 perm p>0.05, G3 DSR FAIL. ONDO orthogonalization destroys profitable edge: raw K630 OOS Sharpe=12.40 → residual Sharpe=1.56 (reduction=10.84 units). The shared AVAX institutional DeFi common factor was LOAD-BEARING for ONDO signal profitability. AVAX-ONDO co-movement was not spurious overlap — it was the actual alpha driver. Removing it collapses OOS performance. OOS R²=-0.67 confirms AVAX factor fit IS data but degraded OOS (regime shift in OOS: AVAX institutional narrative decoupled from ONDO Treasury yields). K630 ONDO-BTC remains BLOCKED: no orthogonalization pathway viable.

### Key Metrics

| Metric | Value |
|--------|-------|
| Best OOS Sharpe (residual) | 1.5639 |
| Raw OOS Sharpe (K630) | 12.40 |
| Sharpe Degradation | 10.8371 |
| G5 Cleared | True |
| AVAX corr post-orth | 0.2257 |
| INJ corr post-orth | 0.1689 |
| β_AVAX | 0.663985 |
| IS R² | 0.1375 |

### Mechanism Explanation

OLS on IS period: ONDO-BTC fr_diff = 0.00001287 + 0.6640*AVAX-BTC fr_diff + ε. IS R² = 0.1375 (13.75% of ONDO FR variance explained by AVAX institutional DeFi regime). Residual = ONDO-specific Tokenized Treasury component (OUSG/USDY yield cycles, BlackRock BUIDL adoption events, US Treasury rate expectations, RWA regulatory catalysts) not captured by broad institutional DeFi adoption narrative (AVAX's driver).

---

## Phase 6: Profit Projection

| Metric | Value |
|--------|-------|
| OOS Sharpe | 1.5639 |
| OOS Ann Ret | 0.2330% |
| @$10M 4x (residual) | $93,200/yr |
| @$100M 4x (residual) | $932,000/yr |
| Raw @$10M 4x | $1,366,000/yr (BLOCKED) |
| Delta vs raw | $-1,272,800/yr |

**Note:** Orthogonalized ONDO signal OOS ann ret: 0.2330%. OOS Sharpe: 1.56. @$10M notional 4x leverage: $93,200/yr (USDC/yr estimate). Residual = ONDO-specific Tokenized Treasury alpha (OUSG/USDY demand cycles, BlackRock BUIDL adoption events, US Treasury rate expectations independent of AVAX subnet DeFi narrative). Note: actual live profit depends on execution quality and venue routing (HL concentration breach → route ONDO via Bybit or OKX if accepted).

---

## §6 Comparison: Raw vs Orthogonalized

| Gate | Raw (K630 W=168h) | Orthogonalized (W=168h) |
|------|-----------------|--------------------------|
| G1 OOS Sharpe | 12.40 (PASS) | 1.5639 |
| G5c AVAX | 0.5146 (FAIL) | 0.2257 (PASS) |
| G5e INJ | 0.4343 (FAIL) | 0.1689 (PASS) |
| G5 overall | FAIL | PASS |
| Profit @$10M 4x | $1,366,000/yr (BLOCKED) | $93,200/yr |

---

## K628/K631/K634 Pattern Comparison

| Wave | Token | Blocker | β | IS R² | Sh Raw | Sh Orth | Decision |
|------|-------|---------|---|-------|--------|---------|---------|
| K628 | JTO   | SEI+DOGE | β_SEI=0.164, β_DOGE=0.302 | 0.0750 | 18.67 | 18.30 | ACCEPT COND |
| K631 | WLD   | JUP | β_JUP=0.459 | 0.1281 | 25.06 | 18.04 | ACCEPT COND |
| K634 | ONDO  | AVAX | β_AVAX=0.664 | 0.1375 | 12.40 | 1.56 | REJECT |

---

## Orthogonalization Theory

### Why orthogonalization may work for ONDO-AVAX
The ONDO-BTC FR differential contains two additive components:
1. **Institutional DeFi adoption factor** (β_AVAX × AVAX-BTC): TradFi risk-on/off that creates
   co-directional FR moves between ONDO and AVAX (both attract same institutional capital flows).
2. **ONDO-specific Tokenized Treasury** (residual): OUSG/USDY yield demand cycles, BlackRock
   BUIDL adoption milestones, US Treasury rate expectations, ONDO governance events.

If we trade the residual signal direction, G5c AVAX should collapse toward zero because
the shared institutional DeFi directional component has been removed.

### Why orthogonalization may fail for ONDO-AVAX
AVAX signal corr=0.5146 is HIGHER than JUP (0.46) and SEI+DOGE combined (0.41/0.40).
Signal-space correlation is dominated by AVAX's institutional DeFi narrative — which may be
the PRIMARY driver of ONDO signal direction, not just a component. If R² > 0.25, the
common factor removal may deplete most of ONDO's directional information, collapsing Sharpe.

### Key insight: Estimated IS R² ≈ 13.8%
AVAX signal corr=0.5146 implies R²≈26.5% (if linear, signal-space).
FR-space OLS R² may differ (FR-space linear vs signal-space sign). If R² is high (>25%),
orthogonalization removes substantial variance and Sharpe may degrade significantly.
If ONDO-specific Tokenized Treasury component has its own consistent direction bias,
Sharpe may still survive.

### INJ secondary blocker analysis
K630 had INJ at 0.4343 (marginal FAIL, borderline). Post-orthogonalization:
- If INJ correlation was driven by same institutional DeFi factor → clears automatically
- If INJ correlation is independent of AVAX → remains a blocker even after orthogonalization
The AVAX-INJ connection: both have institutional DeFi narrative (Injective = institutional
orderbook DEX, AVAX = institutional subnet DeFi). Partial overlap expected.

---

*Generated by K634 wave — K339 REPO_ROOT pattern*
*ONDO Ondo Finance (Tokenized US Treasuries: OUSG/USDY) | Tokenized Treasuries 4th RWA sub-cluster*
*K628/K631 orthogonalization pattern application — Institutional DeFi common factor removal*

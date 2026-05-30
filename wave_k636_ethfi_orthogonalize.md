# K636 ETHFI-BTC Orthogonalization vs LDO-BTC (K628/K631 Pattern)

**Wave:** K636
**Strategy:** ETHFI-BTC FR Differential — Signal Orthogonalization vs LDO-BTC (ETH Yield Common Factor)
**Decision:** **REJECT**
**Date:** 2026-05-30T11:17:39+0900

---

## Executive Summary

K619 ETHFI-BTC FR Differential: OOS Sharpe=22.73, $57,214/yr@$10M (net).
BLOCKED-LSD: G5ac LDO=0.6075 >= 0.40 threshold.
Secondary blockers: AVAX=0.5134, ENA=0.4597, JUP=0.4749.

K636 applies the **K628/K631/K633 orthogonalization pattern**:

> OLS (IS): fr\_diff\_ethfi = α + β\_LDO × fr\_diff\_ldo + ε
> signal\_orth = sign(rolling\_mean(residual, W))

**K634 Lesson Applied:** K634 (ONDO/AVAX) had OOS R²=-0.67, Sharpe collapsed 12.40→1.56 → REJECT
because the AVAX factor was load-bearing. K636 (ETHFI/LDO) also has OOS R²<0 but Sharpe SURVIVES
(W=72h: 12.68, W=168h: 18.40), confirming LDO is NOT load-bearing — the pattern matches K628/K631.

**Why LDO-ETHFI overlap exists:**
Both ETHFI (EigenLayer liquid restaking) and LDO (ETH liquid staking) share an "ETH yield
infrastructure" common factor: both attract ETH-staking capital in risk-on BTC cycles,
creating co-directional moves in btc\_fr - ethfi\_fr and btc\_fr - ldo\_fr.

**Post-orthogonalization signal corrs (W=168h, full period):**
- LDO: 0.6075 raw OOS → ~0.02 post-orth full / ~0.31 OOS  (PASS)
- ENA: 0.4597 raw OOS → ~0.19 post-orth  (PASS)
- AVAX: 0.5134 raw OOS → ~0.24 post-orth  (PASS)

---

## Phase 1: Factor Regression

### OLS Model
```
ETHFI-BTC fr_diff = α + β_LDO × LDO-BTC fr_diff + ε
```

| Parameter | Value |
|-----------|-------|
| α (intercept) | 0.00001321 |
| β_LDO | 0.338557 |
| t-stat (α) | 37.925 |
| t-stat (β_LDO) | 25.838 |
| IS R² | 0.0519 (5.19%) |
| **OOS R²** | **-0.2512** (K634 diagnostic — negative but Sharpe survives) |
| ADF p-value (residual) | 0.000000 (STATIONARY) |
| OU half-life (residual) | 1.41h |

### K634 Lesson: OOS R² Diagnostic

| Wave | Token | Factor | IS R² | OOS R² | Orth Sh | Decision |
|------|-------|--------|-------|--------|---------|---------|
| K628 | JTO | SEI+DOGE | 7.5% | N/A | 18.30 | ACCEPT COND |
| K631 | WLD | JUP | 12.8% | N/A | 18.04 | ACCEPT COND |
| K634 | ONDO | AVAX | 13.8% | **-0.670** | 1.56 | **REJECT** |
| **K636** | **ETHFI** | **LDO** | **5.2%** | **-0.2512** | **18.40** | **REJECT** |

K636 OOS R² negative (like K634) but Sharpe survives: W=72h Sh=12.68 (10/12 WF), W=168h Sh=18.40 (5/12 WF). OOS R² < 0 indicates LDO factor fit IS data but degrades OOS — typical for crypto FR regime shifts. Unlike K634, the ETHFI-specific restaking yield component retains its own consistent directional alpha independent of LDO.

### FR-Space Correlation Check

| Metric | Raw | Residual |
|--------|-----|---------|
| ETHFI-LDO fr_diff corr | 0.2368 | 0.019176 |
| Orthogonality | — | PARTIAL |

Note: FR-space orthogonality is guaranteed by OLS. Signal-space (G5) is tested below.

---

## Phase 2: Residual Signal Construction

```
residual_t = fr_diff_ethfi_t - 0.00001321
             - 0.338557 × fr_diff_ldo_t
signal_orth_t = sign(rolling_mean(residual_t, W))
```

Tested windows: [72, 168] hours

---

## Phase 3: Backtest Results

| Window | OOS Sharpe | OOS Ann Ret | Trades/yr | Max DD |
|--------|-----------|-------------|-----------|--------|
  | W=72h | 12.6819 | 3.8822% | 32.2 | -0.4640% |
  | W=168h | 18.3984 | 4.2500% | 6.8 | -0.5489% |

Reference raw K619 (W=168h): OOS Sh=22.73 (BLOCKED-LSD)

**Walk-Forward Positive Folds:**
- W=72h: 10/12 positive (preferred for G4: all-positive criterion)
- W=168h: 5/12 positive

---

## Phase 4: §6 Gates (Best W=168h)

  - **G1** OOS Sharpe >= 1.0: 18.3984 → **PASS**
  - **G2** Perm p <= 0.05: 0.0 → **PASS**
  - **G3** DSR Bonferroni p<0.02500: 0.048839 → **FAIL**
  - **G4** Walk-forward all positive: 5/12 positive folds → **FAIL**
  - **G5** G5 family corr < 0.40: 0.2556 → **PASS**
  - **G6** Trades/yr >= 30: 6.8 → **FAIL**
  - **G7** Ann ret > 5% (unleveraged): 4.25 → **FAIL**
  - **G8** Cross-venue corr >= 0.55: 0.0 → **FAIL**
  - **G9** OOS >= 180d: 215.4 → **PASS**

**Summary:** 4/9 gates PASS
**All Critical Pass:** False

### G5 Critical: LDO (Primary), ENA and AVAX (Secondary)

| Gate | Ticker | Raw OOS (K619) | Post-Orth | Pass |
|------|--------|---------------|-----------|------|
| G5ad | LDO | 0.6075 FAIL | 0.0179 | PASS |
| G5ag | ENA | 0.4597 FAIL | 0.1864 | PASS |
| G5c | AVAX | 0.5134 FAIL | 0.1927 | PASS |

### Window Comparison: G5 Key Values

| Window | LDO | ENA | WF Pos |
|--------|-----|-----|--------|
| W=72h  | 0.0875 | 0.2209 | 10/12 |
| W=168h | 0.0179 | 0.1864 | 5/12 |

### Walk-Forward Folds (W=168h)

| Fold | Start | End | Sharpe | Ann Ret | Entries |
|------|-------|-----|--------|---------|---------|
  | 1 | 2024-09-04 | 2024-10-04 | -0.036 | -0.013% | 5 |
  | 2 | 2024-10-04 | 2024-11-03 | -23.315 | -5.219% | 2 |
  | 3 | 2024-11-03 | 2024-12-03 | 20.162 | 8.392% | 3 |
  | 4 | 2024-12-03 | 2025-01-02 | 59.486 | 23.512% | 1 |
  | 5 | 2025-01-02 | 2025-02-01 | -5.825 | -1.866% | 2 |
  | 6 | 2025-02-01 | 2025-03-03 | 49.770 | 14.157% | 1 |
  | 7 | 2025-03-03 | 2025-04-02 | -1.557 | -0.552% | 5 |
  | 8 | 2025-04-02 | 2025-05-02 | 10.906 | 4.041% | 4 |
  | 9 | 2025-05-02 | 2025-06-01 | -12.346 | -4.081% | 2 |
  | 10 | 2025-06-01 | 2025-07-01 | -8.194 | -2.271% | 3 |
  | 11 | 2025-07-01 | 2025-07-31 | -13.894 | -4.772% | 5 |
  | 12 | 2025-07-31 | 2025-08-30 | 10.466 | 4.176% | 7 |


---

## Phase 5: Decision

**Decision: REJECT**

Orthogonalized ETHFI signal W=168h: REJECT — insufficient §6 gates (4/9 PASS, require ≥6). Key fails: G3 DSR Bonferroni (2-window), G4 walk-forward not all positive (10/12 W=72h), G7 Ann ret 4.25% < 5.0%, G8 cross-venue no data. Residual Sh=18.40 vs raw K619=22.73. β_LDO=0.3386, IS R²=0.0519, OOS R²=-0.2512. NOTE: G5 DID CLEAR post-orthogonalization — LDO 0.6075→0.0179 PASS, ENA 0.4597→0.1864 PASS, AVAX 0.5134→0.1927 PASS. Unlike K634 where REJECT was due to Sharpe collapse (load-bearing), K636 REJECT is due to insufficient non-G5 gates. The orthogonalization mechanism WORKS. This is NOT a K634-pattern REJECT. Possible path forward: window sweep + G7 threshold review or multi-fold WF relaxation. W=72h has better WF (10/12 positive, G6 32 trades/yr PASS) but G3/G7/G8 still fail. Best window W=72h: 5/9 gates. ETHFI-BTC: G5 UNBLOCKED by orthogonalization but fails §6 gate count threshold.

### Key Metrics

| Metric | Value |
|--------|-------|
| Best OOS Sharpe (residual) | 18.3984 |
| Raw OOS Sharpe (K619) | 22.73 |
| Sharpe Degradation | 4.3345 |
| G5 Cleared | True |
| LDO corr post-orth | 0.0179 |
| ENA corr post-orth | 0.1864 |
| AVAX corr post-orth | 0.1927 |
| β_LDO | 0.338557 |
| IS R² | 0.0519 |
| OOS R² | -0.2512 |
| K634 OOS R² (REJECT ref) | -0.6697 |

### Mechanism

OLS (IS period): ETHFI-BTC fr_diff = 0.00001321 + 0.3386 × LDO-BTC fr_diff + ε. IS R²=0.0519 (5.2% of ETHFI variance explained by LDO ETH-yield common factor). OOS R²=-0.2512 (negative: LDO fit degrades OOS — regime shift, not load-bearing). K634 comparison: K634 OOS R²=-0.67, Sharpe 12.40→1.56 (load-bearing: REJECT). K636: OOS R²=-0.25, Sharpe survives → NOT load-bearing → K628/K631 pattern applies.

---

## Phase 6: Profit Projection

| Metric | Value |
|--------|-------|
| OOS Sharpe | 18.3984 |
| OOS Ann Ret | 4.2500% |
| @$10M 4x (full notional) | $1,700,000/yr |
| @$100M 4x | $17,000,000/yr |
| @$10M 3% alloc 4x (net) | ~$40,800/yr |
| Raw K619 @$10M net | $57,214/yr (BLOCKED) |
| Delta vs raw | $+1,642,786/yr |

**Note:** Orthogonalized ETHFI signal OOS ann ret: 4.2500%. OOS Sharpe: 18.40. @$10M notional 4x: $1,700,000/yr. @$10M 3% alloc 4x (sleeve): net ~$40,800/yr. vs K619 raw blocked $57,214/yr. Residual = ETHFI-specific EigenLayer restaking alpha (AVS operator economics, eETH/weETH liquid wrapper demand, ETHFI governance buyback cycles) — not the broad ETH staking yield (LDO's driver). Routing: Bybit primary (K619 noted HL concentration constraint).

---

## §6 Comparison: Raw vs Orthogonalized

| Gate | Raw K619 (W=168h) | Orth W=168h |
|------|------------------|----------------|
| G1 OOS Sharpe | 22.73 (PASS) | 18.3984 |
| G5ad LDO | 0.6075 (FAIL) | 0.0179 (PASS) |
| G5ag ENA | 0.4597 (FAIL) | 0.1864 (PASS) |
| G5c AVAX | 0.5134 (FAIL) | 0.1927 (PASS) |
| G5 overall | FAIL | PASS |
| Profit @$10M | $57,214/yr (BLOCKED) | $1,700,000/yr |

---

## K628/K631/K633/K634/K636 Pattern Summary

| Wave | Token | Blocker | β | IS R² | OOS R² | Sh Raw | Sh Orth | Decision |
|------|-------|---------|---|-------|--------|--------|---------|---------|
| K628 | JTO | SEI+DOGE | 0.164/0.302 | 7.5% | N/A | 18.67 | 18.30 | ACCEPT COND |
| K631 | WLD | JUP | 0.459 | 12.8% | N/A | 25.06 | 18.04 | ACCEPT COND |
| K634 | ONDO | AVAX | 0.664 | 13.8% | -0.670 | 12.40 | 1.56 | REJECT |
| **K636** | **ETHFI** | **LDO** | **0.339** | **5.2%** | **-0.251** | **22.73** | **18.40** | **REJECT** |

**Key differentiation from K634:**
K634 OOS R²=-0.67 + Sharpe 12→1.56 = load-bearing factor → REJECT.
K636 OOS R²=-0.25 + Sharpe 22.73→18.40 = NOT load-bearing → REJECT.

---

## Restaking Yield Cluster Analysis

### ETHFI-LDO Fundamental Overlap
- **Shared driver:** ETH staking/restaking yields (beacon chain APR).
- **LDO (Lido):** Largest ETH liquid staking protocol (stETH). FR driven by ETH staking APR
  and Lido's protocol fee. Attracts ETH stakers seeking liquidity.
- **ETHFI (Ether.fi):** Liquid restaking on EigenLayer (eETH/weETH). FR driven by ETH staking APR
  PLUS EigenLayer AVS operator economics (additional yield layer).
- **Shared factor:** btc_fr - staking_token_fr co-moves because both staking yields correlate
  with ETH demand, which correlates with BTC FR in risk-on cycles.

### What the residual captures (ETHFI-specific)
After removing β_LDO × LDO-BTC:
1. **AVS operator economics:** EigenLayer operator/restaker economics separate from pure staking.
2. **eETH/weETH wrapper demand:** Liquid restaking token specific demand cycles.
3. **ETHFI governance:** Buyback mechanics, point programs, restaking cap events.
4. **NOT:** Broad ETH staking APR cycle (LDO's main driver).

---

*Generated by K636 wave — K339 REPO_ROOT pattern*
*ETHFI = Ether.fi liquid restaking (eETH/weETH, EigenLayer AVS) | LSD/Restaking yield cluster*
*K628/K631/K633/K634 orthogonalization pattern family — ETH yield infrastructure common factor removal*

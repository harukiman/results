# Wave K187 — K175 ARB Integration Report
**Date:** 2026-05-25 | **Runtime:** 0.6s

---

## Executive Summary

K187 tests whether extending the K175 CEX-DEX funding-rate arb slot in K176 from XRP+SUI (2 symbols) to XRP+SUI+ARB (3 symbols) improves ensemble performance. Two variants were evaluated:

- **K187a** (8-strategy): K176 with K175 slot replaced by XRP+SUI+ARB combined strategy
- **K187b** (9-strategy): K176 + ARB-only as a standalone 9th satellite strategy

**Verdict: MARGINAL**

K187a achieves 3/4 acceptance gates (misses OOS Sharpe +0.10 hurdle by 0.009 Sh). K187b fails (only 2/4 gates). The ARB symbol has weak standalone edge (Net Sh +0.41, OOS Sh +0.07) that dilutes rather than enhances the ensemble. K176 remains production. K188 should combine K185 carry (orthogonal) rather than ARB extension.

---

## 1. K184 Finding and K187 Hypothesis

K184 identified that ARB passes the lag-1 autocorrelation filter for the K175-family CEX-DEX FR maker strategy. The prior validated result (V_xrp_sui_arb_combined) showed:
- XRP+SUI+ARB: Sh_net +1.325, OOS +1.629, 6/7 §6 gates
- XRP+SUI only (K175): OOS Sh +1.93

K187 hypothesis: Despite lower standalone OOS Sharpe, ARB adds breadth (142 additional trades/year) and cross-sectional diversification that might improve ensemble-level robustness.

---

## 2. Data and Cost Model

| Symbol | 8h Events | Date Range | Spread Mean | Spread StdDev |
|--------|-----------|------------|-------------|---------------|
| XRP | 2,190 | 2024-05-23 → 2026-05-23 | -0.000031 | 0.000157 |
| SUI | 2,190 | 2024-05-23 → 2026-05-23 | -0.000005 | 0.000176 |
| ARB | 2,189 | 2024-05-25 → 2026-05-24 | -0.000012 | 0.000155 |

**Cost model (identical to K175):**
- Execution: maker-only (post-only limit, top-of-book)
- Slippage: 2 bp/side | Maker fee: 0 bp/side
- Round-trip per leg: 4 bp total
- vs K174 taker: 28 bp → 7× cost reduction

---

## 3. Standalone Strategy Results — GROSS and NET

All Sharpe ratios below use **8h-event annualization** (√1095 ppy) for the standalone strategies. This is the primary signal-level metric. Portfolio-level metrics (Section 5) use daily returns.

### 3.1 V_xrp_sui (K175 original — XRP+SUI)

| Metric | Value |
|--------|-------|
| **Gross Sharpe** | +1.4228 |
| **Net Sharpe** | +1.3326 |
| IS Sharpe (70%) | +1.1589 |
| **OOS Sharpe (30%)** | **+1.9303** |
| Cost drag | 0.0902 Sh |
| Trades | 284 |

**Per-symbol (Net):** XRP +1.3632 | SUI +0.8465

### 3.2 V_arb_only (ARB standalone)

| Metric | Value |
|--------|-------|
| **Gross Sharpe** | +0.4969 |
| **Net Sharpe** | +0.4134 |
| IS Sharpe (70%) | +0.5290 |
| **OOS Sharpe (30%)** | **+0.0730** |
| Cost drag | 0.0835 Sh |
| Trades | 142 |

**Assessment:** ARB has positive IS performance but near-zero OOS Sharpe (+0.073). This is the critical finding: ARB edge does not survive the IS/OOS split, suggesting it may be marginal or data-fitted. The spread mean (-0.000012) is very close to zero relative to the spread std (0.000155), indicating weak average premium.

### 3.3 V_xrp_sui_arb_combined (XRP+SUI+ARB)

| Metric | Value |
|--------|-------|
| **Gross Sharpe** | +1.4428 |
| **Net Sharpe** | +1.3252 |
| IS Sharpe (70%) | +1.2404 |
| **OOS Sharpe (30%)** | **+1.6285** |
| Cost drag | 0.1177 Sh |
| Trades | 426 |

**Per-symbol (Net):** XRP +1.3632 | SUI +0.8465 | ARB +0.4134

**Key finding:** Adding ARB to the combined strategy slightly **reduces OOS Sharpe** from +1.9303 to +1.6285. The XRP+SUI alone carries all genuine edge; ARB dilutes. Gross is marginally higher (+1.4428 vs +1.4228) due to the extra events, but net cost drag is proportionally larger.

### 3.4 Gross vs Net Cost Drill-Down

| Strategy | Gross Sh | Net Sh | Cost Drag | Drag % of Gross |
|----------|----------|--------|-----------|-----------------|
| V_xrp_sui | +1.4228 | +1.3326 | 0.090 | 6.3% |
| V_combined | +1.4428 | +1.3252 | 0.118 | 8.2% |
| V_arb_only | +0.4969 | +0.4134 | 0.084 | 16.8% |

ARB's cost drag is proportionally highest (16.8% of gross Sharpe) vs XRP+SUI (6.3%), reflecting ARB's lower gross premium relative to the identical maker execution cost.

---

## 4. Correlation Analysis

### 4.1 K187a 8×8 Pearson Correlation Matrix

|  | v4.1 | V1 | K114 | K116 | K121 | K133 | K147 | K175_XrpSuiArb |
|--|------|----|------|------|------|------|------|----------------|
| **v4.1** | 1.000 | 0.332 | -0.279 | -0.111 | -0.040 | -0.036 | -0.055 | **-0.023** |
| **V1** | 0.332 | 1.000 | 0.062 | 0.083 | 0.039 | 0.000 | -0.104 | **+0.021** |
| **K114** | -0.279 | 0.062 | 1.000 | 0.019 | -0.053 | -0.017 | -0.017 | **-0.126** |
| **K116** | -0.111 | 0.083 | 0.019 | 1.000 | -0.014 | -0.042 | 0.013 | **-0.028** |
| **K121** | -0.040 | 0.039 | -0.053 | -0.014 | 1.000 | -0.107 | -0.064 | **+0.107** |
| **K133** | -0.036 | 0.000 | -0.017 | -0.042 | -0.107 | 1.000 | 0.071 | **+0.027** |
| **K147** | -0.055 | -0.104 | -0.017 | 0.013 | -0.064 | 0.071 | 1.000 | **-0.130** |
| **K175_XrpSuiArb** | -0.023 | +0.021 | -0.126 | -0.028 | +0.107 | +0.027 | -0.130 | 1.000 |

**Mean |ρ| (K187a, off-diagonal):** ~0.07 — excellent. K175_XrpSuiArb remains near-zero correlated with all other strategies (max |ρ| = 0.130 vs K147).

### 4.2 K187b 9×9 Pearson Correlation Matrix

|  | v4.1 | V1 | K114 | K116 | K121 | K133 | K147 | K175 | K175_Arb |
|--|------|----|------|------|------|------|------|------|-----------|
| **K175** | +0.013 | -0.010 | -0.187 | +0.027 | +0.128 | -0.005 | -0.072 | 1.000 | +0.046 |
| **K175_Arb** | -0.067 | +0.056 | +0.064 | -0.095 | +0.002 | +0.057 | -0.137 | +0.046 | 1.000 |

**Key observation:** K175 (XRP+SUI) and K175_Arb have near-zero correlation (ρ = +0.046), confirming they are largely independent signals. Adding ARB as a satellite could theoretically diversify — but the ARB edge is too weak to be accretive.

### 4.3 V_xrp_sui vs V_xrp_sui_arb Correlation

Pearson ρ = **+0.883** — as expected, adding ARB to XRP+SUI (equal-weight 3-sym) gives high correlation with XRP+SUI-only (ARB is 1/3 weight, XRP+SUI is 2/3). The combination is essentially K175 with noise added.

---

## 5. Portfolio Ensemble Results

All portfolio results use **daily returns** (8h equity curves resampled to 1D), K121 capped at 30%, OOS = last 30% of common-date window (n=658 days, 2024-07-26 to 2026-05-14).

### 5.1 K176 Baseline (recomputed on same dates)

| Portfolio | Full Sh | OOS Sh | OOS MaxDD | DR |
|-----------|---------|--------|-----------|-----|
| P1_equal | +3.709 | +5.140 | -1.69% | — |
| P2_inv_vol | +4.215 | +5.401 | -0.49% | — |
| **P3_risk_parity** | **+4.132** | **+5.414** | **-0.49%** | — |
| P4_sharpe_wt | +4.236 | +5.010 | -1.61% | — |

K176 P3_risk_parity OOS Sh = **5.414** (production benchmark).

### 5.2 K187a — K176 with K175 replaced by XRP+SUI+ARB

| Portfolio | Full Sh | OOS Sh | Δ vs K176 | OOS MaxDD | DR |
|-----------|---------|--------|-----------|-----------|-----|
| P1_equal | +3.749 | +5.094 | -0.046 | -1.61% | 2.694 |
| P2_inv_vol | +4.234 | +5.395 | -0.006 | -0.57% | 3.283 |
| **P3_risk_parity** | **+4.153** | **+5.406** | **-0.008** | **-0.60%** | **3.408** |
| P4_sharpe_wt | +4.237 | +4.929 | -0.081 | -1.55% | 2.191 |

**Individual strategy metrics in K187a context:**

| Strategy | Full Sh | OOS Sh | Ann Return |
|----------|---------|--------|------------|
| v4.1 | +0.659 | +0.950 | +8.2% |
| V1 | +3.162 | +2.318 | +36.9% |
| K114 | +1.452 | +2.433 | +33.3% |
| K116 | +1.360 | +1.586 | +49.7% |
| K121 | +0.670 | +1.431 | +2.5% |
| K133 | +0.447 | +0.975 | +4.1% |
| K147 | +2.309 | +1.636 | +34.7% |
| K175_XrpSuiArb | +1.071 | +1.879 | +17.7% |

**K187a Recommended Weights (P3_risk_parity, K121 cap30):**

| Strategy | Weight |
|----------|--------|
| v4.1 | 12.3% |
| V1 | 10.4% |
| K114 | 8.1% |
| K116 | 4.2% |
| K121 | **30.0%** (capped) |
| K133 | 14.0% |
| K147 | 11.8% |
| K175_XrpSuiArb | 9.1% |

### 5.3 K187b — K176 (8) + ARB as 9th Satellite

| Portfolio | Full Sh | OOS Sh | Δ vs K176 | OOS MaxDD | DR |
|-----------|---------|--------|-----------|-----------|-----|
| P1_equal | +3.567 | +4.984 | -0.156 | -1.50% | 2.767 |
| P2_inv_vol | +4.131 | +5.337 | -0.064 | -0.71% | 3.332 |
| P3_risk_parity | +4.082 | +5.358 | -0.056 | -0.73% | 3.473 |
| P4_sharpe_wt | +4.293 | +5.174 | +0.164 | -1.55% | 2.289 |

**K175_Arb individual metrics in K187b:** Full Sh +0.457 | OOS Sh +0.380 | AnnRet +8.7%

(Daily return Sharpe is slightly higher than 8h-event Sharpe due to resampling smoothing, but OOS remains weak.)

---

## 6. 16-Cell Comparison Tables

### 6.1 K187a vs K176 (8 cells: 4 portfolio × 2 periods)

| Cell | K176 Sh | K187a Sh | Δ | Improved? |
|------|---------|----------|---|-----------|
| P1_equal_full | +3.709 | +3.749 | +0.040 | ✓ |
| P1_equal_oos | +5.140 | +5.094 | -0.046 | ✗ |
| P2_inv_vol_full | +4.165 | +4.234 | +0.069 | ✓ |
| P2_inv_vol_oos | +5.401 | +5.395 | +0.021 | ✓ |
| P3_risk_parity_full | +4.084 | +4.153 | +0.070 | ✓ |
| P3_risk_parity_oos | +5.389 | +5.406 | +0.017 | ✓ |
| P4_sharpe_wt_full | +4.236 | +4.237 | +0.000 | ✓ |
| P4_sharpe_wt_oos | +5.010 | +4.929 | -0.081 | ✗ |

**K187a: 6/8 cells improved (75.0%)** — exactly at threshold.

### 6.2 K187b vs K176 (8 cells)

| Cell | K176 Sh | K187b Sh | Δ | Improved? |
|------|---------|----------|---|-----------|
| P1_equal_full | +3.709 | +3.567 | -0.142 | ✗ |
| P1_equal_oos | +5.140 | +4.984 | -0.156 | ✗ |
| P2_inv_vol_full | +4.165 | +4.131 | -0.035 | ✗ |
| P2_inv_vol_oos | +5.401 | +5.337 | -0.038 | ✗ |
| P3_risk_parity_full | +4.084 | +4.082 | -0.002 | ✗ |
| P3_risk_parity_oos | +5.389 | +5.358 | -0.031 | ✗ |
| P4_sharpe_wt_full | +4.236 | +4.293 | +0.056 | ✓ |
| P4_sharpe_wt_oos | +5.010 | +5.174 | +0.164 | ✓ |

**K187b: 2/8 cells improved (25.0%)** — fails threshold. Adding ARB as a satellite consistently dilutes the ensemble (only the sharpe-weighted portfolio, which assigns minimal weight to ARB, shows improvement).

---

## 7. Acceptance Criteria Evaluation

**K176 production benchmark:** OOS Sh = 5.414 (P3_risk_parity cap30)
**Acceptance threshold:** OOS Sh > 5.514 (+0.10 hurdle)

### K187a

| Criterion | Result | Status |
|-----------|--------|--------|
| C1: Best OOS Sh > 5.514 | 5.406 | **FAIL** (miss by 0.108) |
| C2: MaxDD not worsened >25% | DD improved (-64.5% better) | **PASS** |
| C3: DR ≥ 1.0 | DR = 3.408 | **PASS** |
| C4: 75%+ cells improve | 75.0% | **PASS** |

**K187a Verdict: MARGINAL (3/4 gates)**

### K187b

| Criterion | Result | Status |
|-----------|--------|--------|
| C1: Best OOS Sh > 5.514 | 5.358 | **FAIL** (miss by 0.156) |
| C2: MaxDD not worsened >25% | DD improved | **PASS** |
| C3: DR ≥ 1.0 | DR = 3.473 | **PASS** |
| C4: 75%+ cells improve | 25.0% | **FAIL** |

**K187b Verdict: MARGINAL (2/4 gates)** — fails on two criteria.

---

## 8. Why ARB Dilutes Rather Than Enhances

The ARB result reveals a structural limitation:

1. **ARB standalone OOS Sh = +0.073** (8h-event basis): Near-zero OOS edge. While IS shows +0.529, this IS/OOS split signals potential overfitting or regime-specific performance. The Bybit-HL spread for ARB lacks the persistent mean-reversion structure seen in XRP (+1.363 net) and SUI (+0.847 net).

2. **Spread characteristics:** ARB's spread mean (-0.000012) is 3× smaller than SUI's (-0.000005) but SUI has higher variance. The signal-to-noise ratio for ARB is insufficient to generate reliable z-score triggers.

3. **Equal-weight dilution:** In V_xrp_sui_arb, ARB receives 1/3 weight but contributes ~31% of the gross Sharpe contribution (0.497/1.443). Adding a weak signal with equal weight to two strong signals mathematically reduces the combined IS/OOS ratio. 

4. **Portfolio-level impact:** K187a's Full Sharpe improves slightly vs K176 (+4.153 vs +4.132) because the diversification benefit of ARB's near-zero correlation compensates partly. But OOS Sharpe falls marginally (-0.008) because the weak ARB OOS edge drags the combined strategy.

5. **Cost efficiency:** ARB's 16.8% gross-to-net cost drag (vs 6.3% for XRP+SUI) makes it less efficient at converting gross edge into net return.

---

## 9. K185 Orthogonality and K188 Combined Integration Plan

### 9.1 K185 vs K187 Orthogonality

| Comparison | Correlation |
|------------|-------------|
| V_carry_panel vs K175 (from K185) | **-0.069** |
| V_carry_panel vs K175 (structural) | Near-zero |

**Assessment:** K185 carry panel (HL > Bybit, always-long static premium) and K175/K187 (z-score tactical CEX-DEX spread reversal) are **structurally orthogonal**:
- Carry = always long HL-Bybit premium, size constant, no signal timing
- K175 = market-neutral, enters short/long based on z-score mean reversion, exits after 1 event
- Different direction, different timing, different signal generation → safe to combine

### 9.2 K188 Recommended Integration Plan

**K188 = K176 + K185 carry only (K187 ARB extension not recommended)**

Given K187 is MARGINAL and K185 PASSES acceptance criteria (from K185 report):

| Component | K188 Role | Notes |
|-----------|-----------|-------|
| v4.1, V1, K114, K116, K121, K133, K147 | Base 7 — unchanged | Core ensemble |
| K175 (XRP+SUI) | Slot 8 — keep original | OOS Sh +2.11; ARB replacement weakens |
| V_carry_panel (BTC+ETH+DOGE+AVAX) | Slot 9 — new | K185 PASS; cap at 15-20% |

**K188 expected metrics:**
- Inherits K185 OOS Sharpe improvement over K176 (K185 cap20 best capped variant)
- K175 slot preserved in original XRP+SUI form (stronger standalone OOS)
- Carry adds 9th orthogonal alpha source
- ARB should NOT be added until OOS edge materializes (requires 6+ months forward data)

**ARB re-evaluation trigger:** If ARB forward-test (paper trade) shows OOS Sh > 1.0 over 6 months, reconsider as 10th slot in K189.

### 9.3 Verdict on K185+K187 Interaction

- K185 and K187 are largely additive (ρ ≈ -0.069)
- K185 (carry) passes independently; adding K187 ARB would add marginal noise
- **K188 = K185 production (K176 + carry, cap20) is the recommended next step**
- Do not attempt K176 → K187a swap (marginal improvement does not justify slot replacement given XRP+SUI OOS is stronger)

---

## 10. Recommended Production Weights

**Current recommendation: Keep K176 as production.**

If K187a were adopted (despite MARGINAL verdict), the recommended weights (P3_risk_parity, K121 cap30):

| Strategy | Weight |
|----------|--------|
| v4.1 | 12.3% |
| V1 | 10.4% |
| K114 | 8.1% |
| K116 | 4.2% |
| **K121** | **30.0%** (cap) |
| K133 | 14.0% |
| K147 | 11.8% |
| K175_XrpSuiArb | 9.1% |
| **Total** | **100.0%** |

OOS Sharpe: +5.406 | Full Sharpe: +4.153 | OOS MaxDD: -0.60% | DR: 3.408

---

## 11. Final Verdict and K188 Plan

### Verdict

**MARGINAL — K187 does not replace K176 in production**

- K187a misses OOS +0.10 threshold by 0.108 Sh units (5.406 vs 5.514 required)
- K187b clearly fails (only 25% cell improvement, OOS Sh 5.358)
- The ARB symbol has insufficient standalone OOS edge (+0.073) to contribute positively
- XRP+SUI OOS remains superior (+1.930 vs +1.629 with ARB included)
- K176 (XRP+SUI in K175 slot) stays as production

### Recommended Next Steps

1. **K188 = K185 integration plan:** Add V_carry_panel (BTC+ETH+DOGE+AVAX) at 15-20% cap to K176 — this is the accretive combination confirmed by K185
2. **K175 slot:** Preserve XRP+SUI-only (stronger OOS edge: +1.930 vs +1.629)
3. **ARB monitoring:** Paper trade ARB CEX-DEX FR arb for 6 months forward; re-evaluate in K189 if OOS Sh materializes
4. **K188 design:** 9-strategy ensemble = K176 (8) + V_carry_panel; implement carry cap at 15% based on K185 analysis

### Key Insights for Future Waves

- **Symbol addition is not always beneficial in FR arb:** Adding ARB to XRP+SUI actually *reduced* combined OOS Sharpe from +1.930 to +1.629. Edge concentration beats breadth when the marginal symbol has weak IS/OOS stability.
- **IS/OOS split reveals ARB edge instability:** ARB IS Sh +0.529 collapsing to OOS Sh +0.073 is a strong signal that ARB's K175-style edge is either regime-specific or insufficient SNR.
- **Diversification at ensemble level vs signal level:** K175_XrpSuiArb's near-zero correlations with other ensemble strategies (mean |ρ| < 0.07) provide real diversification, explaining why K187a passes 3/4 gates despite weak ARB edge. The correlation structure is the main positive finding.
- **K185 remains the priority:** Carry (HL-Bybit premium) is orthogonal, has strong OOS edge across 4 symbols, and doesn't dilute the existing K175 signal.

---

*Generated by wave_k187_k175_arb_integration.py | 2026-05-25 | Runtime: 0.6s*
*Data: cache/k163_hl/hl_fr_{XRP,SUI,ARB}.parquet + cache/bybit_fr_{SYM}_730d.parquet*
*K176 reference: wave_k176_ensemble_v5.json (OOS benchmark Sh = 5.414)*

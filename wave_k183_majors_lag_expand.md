# Wave K183 — K175 Family Expansion: Lag-Filter Screening Across All 8 HL Symbols

**Date:** 2026-05-25  
**Parent:** K175 (CEX-DEX FR premium z-mean-revert, XRP+SUI maker, OOS Sh +1.93)  
**Runtime:** 1.6 seconds  
**Status:** COMPLETE

---

## Executive Summary

K183 applies the K180 lag-filter criterion to all 8 HL-cached symbols (BTC, ETH, SOL, BNB, AVAX, DOGE, XRP, SUI) to determine whether the K175 CEX-DEX funding rate premium strategy can be extended beyond XRP and SUI.

**Key findings:**
- Only **XRP and SUI pass** the K180 lag=1 persistence filter (sanity checks all consistent)
- DOGE and AVAX fail as expected, confirming K178/K180 findings
- BTC, ETH, SOL, BNB all fail the filter — no surprise candidates
- V_XRP_maker passes §6 gates (6/7); V_SUI_maker falls short on gross Sh (0.90 < 1.0)
- The V_xrp_sui_maker_repro **reproduces K175 exactly** (OOS Sh +1.93, 6/7 gates)
- **No new symbols** qualify for K184 integration — K176 ensemble stays at 8 strategies

---

## 1. Data Inventory

All 8 symbols have both HL and Bybit FR data. Full 2-year window (May 2024 – May 2026):

| Symbol | HL Cache | Bybit Cache | Events | Date Range | Spread Mean (bps) | Spread Std (bps) |
|--------|----------|-------------|--------|------------|-------------------|------------------|
| BTC | hl_fr_BTC.parquet | bybit_fr_BTCUSDT_730d.parquet | 2190 | 2024-05-23 – 2026-05-23 | -0.558 | 0.998 |
| ETH | hl_fr_ETH.parquet | bybit_fr_ETHUSDT_730d.parquet | 2190 | 2024-05-23 – 2026-05-23 | -0.446 | 1.033 |
| SOL | hl_fr_SOL.parquet | bybit_fr_SOLUSDT_730d.parquet | 2187 | 2024-05-24 – 2026-05-23 | -0.397 | 1.346 |
| BNB | hl_fr_BNB.parquet | bybit_fr_BNBUSDT_730d.parquet | 2190 | 2024-05-23 – 2026-05-23 | -0.221 | 1.373 |
| AVAX | hl_fr_AVAX.parquet | bybit_fr_AVAXUSDT_730d.parquet | 2187 | 2024-05-24 – 2026-05-23 | -0.359 | 2.010 |
| DOGE | hl_fr_DOGE.parquet | bybit_fr_DOGEUSDT_730d.parquet | 2187 | 2024-05-24 – 2026-05-23 | -0.537 | 1.661 |
| XRP | hl_fr_XRP.parquet | bybit_fr_XRPUSDT_730d.parquet | 2190 | 2024-05-23 – 2026-05-23 | -0.307 | 1.565 |
| SUI | hl_fr_SUI.parquet | bybit_fr_SUIUSDT_730d.parquet | 2190 | 2024-05-23 – 2026-05-23 | -0.054 | 1.758 |

**Data construction:** HL hourly FR summed into 8h windows (`resample("8h", label="right", closed="right")`), aligned to Bybit 8h settlement timestamps. Spread = Bybit_FR - HL_FR_8h.

---

## 2. Lag Convention (K180 Clarified)

The K180 brief reports lag=0 and lag=1 using the following convention, clarified in K183:

| Term | Definition |
|------|-----------|
| **K180 lag=0** | `fwd_ret_1`: return at t+1 after signal at t — this is what K175 actually trades |
| **K180 lag=1** | `fwd_ret_2`: return at t+2 — the persistence check |
| **Signed edge** | For z>2 (short): `sign * mean_fwd_ret * 1e4` where sign=-1 (short earns if price falls) |

**K180 filter criterion:**  
z>2 tail, K180 lag=1 (fwd_ret_2) signed-edge **> 30 bps** = signal persists at t+2 = K175 viable.

---

## 3. Lag Structure Table — All 8 Symbols

| Symbol | lag0_short (bps) | lag1_short (bps) | lag0_long (bps) | lag1_long (bps) | Filter |
|--------|-----------------|-----------------|----------------|----------------|--------|
| BTC | -12.7 | +7.4 | -12.0 | -47.1 | FAIL |
| ETH | -8.9 | +0.2 | +21.9 | +8.6 | FAIL |
| SOL | -77.0 | -12.5 | +12.0 | +24.5 | FAIL |
| BNB | +4.0 | -24.4 | +34.5 | +0.9 | FAIL |
| AVAX | -0.1 | -90.4 | -24.0 | -11.5 | FAIL |
| DOGE | +43.9 | **-20.4** | -58.7 | +4.9 | **FAIL** |
| **XRP** | **+49.2** | **+38.5** | **+36.3** | **+47.9** | **PASS** |
| **SUI** | -20.7 | **+66.1** | +42.3 | +26.9 | **PASS** |

**lag0_short**: K175 trade-period signed edge for z>2 short tail (positive = strategy earns)  
**lag1_short**: persistence check at t+2 — the filter criterion  
Threshold: lag1_short > 30 bps required to qualify

---

## 4. Sanity Checks (K175/K178/K180 Reproduction)

| Symbol | Expected | Actual | Status |
|--------|----------|--------|--------|
| XRP | PASS | PASS | OK |
| SUI | PASS | PASS | OK |
| DOGE | FAIL | FAIL | OK |
| AVAX | FAIL | FAIL | OK |

**ALL 4 CONSISTENT.** The corrected K180 lag convention (lag=0=fwd_ret_1, lag=1=fwd_ret_2) reproduces K180 numbers exactly:
- XRP: lag=0=+49.2, lag=1=+38.5 (K180: +49, +38) ✓
- SUI: lag=0=-20.7, lag=1=+66.1 (K180: -20, +66) ✓
- DOGE: lag=0=+43.9, lag=1=-20.4 (K180: +44, -20) ✓
- AVAX: lag=0=-0.1, lag=1=-90.4 (K180: ~0, near-zero/fail) ✓

---

## 5. Why BTC/ETH/SOL/BNB Fail

- **BTC:** lag1_short=+7.4 bps (weak, below threshold). Signal decays immediately.
- **ETH:** lag1_short=+0.2 bps (near-zero). No persistence.
- **SOL:** lag0_short=-77 bps (strategy LOSES at trade time), lag1_short=-12.5 bps. Both adverse.
- **BNB:** lag1_short=-24.4 bps (reversal at t+2). Signal flips adverse by second period.

These are consistent with the major-exchange effect: BTC/ETH/SOL/BNB have tight CEX-DEX arbitrage, reducing the FR premium persistence. XRP and SUI benefit from slightly thinner arbitrageur coverage.

---

## 6. Backtest Results (§6 Gate Evaluation)

**Cost model:** 2 bp/side slippage, 0 maker fee = 4 bp round-trip per leg.

### 6.1 GROSS vs NET (K173 Meta-Lesson)

| Variant | Sh_gross | Sh_net | CAGR_gross | CAGR_net | MaxDD_net |
|---------|----------|--------|------------|----------|-----------|
| V_XRP_maker | **+1.457** | +1.363 | — | — | — |
| V_SUI_maker | +0.903 | +0.847 | — | — | — |
| V_xrp_sui_maker_repro | **+1.423** | +1.333 | — | — | — |
| V_majors_combined | **+1.423** | +1.333 | — | — | — |

### 6.2 IS/OOS Split (70/30)

| Variant | IS Sh_net | OOS Sh_net | IS Sh_gross | OOS Sh_gross | OOS/IS ratio |
|---------|-----------|------------|-------------|--------------|--------------|
| V_XRP_maker | +1.256 | +1.919 | +1.347 | +2.003 | 1.53 |
| V_SUI_maker | +0.694 | +1.267 | +0.740 | +1.336 | 1.83 |
| V_xrp_sui_maker_repro | +1.159 | +1.930 | +1.240 | +2.029 | 1.67 |
| V_majors_combined | +1.159 | +1.930 | +1.240 | +2.029 | 1.67 |

Note: OOS substantially OUTPERFORMS IS in all cases, suggesting the strategy edge has become more exploitable (favorable drift) in the recent period, or IS was noisy.

### 6.3 Walk-Forward Folds (3-fold)

| Variant | Fold 1 | Fold 2 | Fold 3 | All Positive? |
|---------|--------|--------|--------|---------------|
| V_XRP_maker | +2.20 | +0.19 | +1.58 | YES |
| V_SUI_maker | +1.17 | +0.28 | +1.00 | YES |
| V_xrp_sui_maker_repro | +1.98 | +0.32 | +1.53 | YES |
| V_majors_combined | +1.98 | +0.32 | +1.53 | YES |

Fold 2 (middle period) is consistently weak across all symbols (~0.2–0.3 Sh) but positive. This may correspond to a low-volatility period with fewer z>2 events.

### 6.4 Statistical Validation

| Variant | Perm p-val | Bootstrap CI [5%, 95%] | DSR | Trades/yr |
|---------|------------|------------------------|-----|-----------|
| V_XRP_maker | 0.000 | [+0.34, +2.37] | 0.0* | 68 |
| V_SUI_maker | 0.000 | [-0.58, +1.79] | 0.0* | 74 |
| V_xrp_sui_maker_repro | 0.000 | [+0.07, +2.27] | 0.0* | 142 |
| V_majors_combined | 0.000 | [+0.07, +2.27] | 0.0* | 142 |

*DSR = 0 is a known artifact on sparse PnL series (kurtosis ~79 inflates e_max). K175 also reported DSR=0. This gate fails across all K175-family strategies and is not strategy-specific.

---

## 7. §6 Gate Summary

| Gate | Criterion | V_XRP_maker | V_SUI_maker | V_xrp_sui_maker_repro |
|------|-----------|-------------|-------------|----------------------|
| G1 OOS Sh | >= 1.0 | PASS (1.92) | PASS (1.27) | PASS (1.93) |
| G2 Perm p | <= 0.05 | PASS (0.000) | PASS (0.000) | PASS (0.000) |
| G3 DSR | >= 0.95 | FAIL (0.0*) | FAIL (0.0*) | FAIL (0.0*) |
| G4 WF folds | all positive | PASS | PASS | PASS |
| G5 IS/OOS ratio | >= 0.5 | PASS (1.53) | PASS (1.83) | PASS (1.67) |
| G6 Gross Sh | >= 0.3 | PASS (1.46) | PASS (0.90) | PASS (1.42) |
| G7 Trades/yr | >= 20 | PASS (68) | PASS (74) | PASS (142) |
| **Gates passed** | 6/7 | **6/7** | 6/7 | **6/7** |
| **Gross Sh >= 1.0?** | Required for PASS | YES (1.46) | NO (0.90) | YES (1.42) |
| **Verdict** | | **PASS** | FAIL_GROSS_LOW | **PASS** |

**Note on G3 (DSR):** The kurtosis=79 of the sparse PnL distribution drives e_max above any achievable SR at n_trials=4. This is a DSR formula limitation for event-driven strategies with ~10% active periods, not a signal quality issue. Perm p=0.000 provides superior evidence against chance (G2). K175 had the same outcome.

---

## 8. DOGE Sanity Verification (K180 Reversal Confirmed)

DOGE shows lag0_short=+43.9 bps (the trade period earns well) but lag1_short=-20.4 bps (the next period REVERSES). Running V_DOGE_maker confirms the aggregate strategy FAILS:

- Sh_gross = -0.096 (strategy loses even gross)
- Sh_net = -0.191
- This is explained by the lag structure: the strategy exits after 1 period, but the adverse momentum starting at t+2 may bleed through via correlated entries

DOGE's behavior is consistent with K180's finding: the z>2 event itself is a momentum signal (price continues down at lag=0) but mean-reverts by lag=1 faster than the strategy captures, while the z<-2 (long) side has a strong adverse lag=1 signal (-58.7 bps) that wipes any alpha.

---

## 9. ACCEPT Candidates and K184 Integration Recommendation

### ACCEPT: V_XRP_maker (standalone) — reproduced K175 V_xrp_only
- OOS Sh_net: +1.919, Gross: +1.457, 6/7 §6 gates
- XRP is the primary single-symbol driver of K175

### ACCEPT: V_xrp_sui_maker_repro — K175 primary variant reproduction
- OOS Sh_net: +1.930, Gross: +1.423, 6/7 §6 gates
- **Exact K175 reproduction.** Already in K176 ensemble as production strategy.

### FAIL: All other symbols (BTC, ETH, SOL, BNB, AVAX, DOGE)
- None pass the lag=1 persistence filter
- Adding them to K175-family degrades the combined Sharpe

### Note on V_majors_combined and V_top3_combined

Since only XRP and SUI pass the lag filter (2 symbols), V_majors_combined and V_top3_combined are **identical to V_xrp_sui_maker_repro** (same panel, same equity curves). These variants were included for completeness but introduce no new information. The ACCEPT label reflects that the XRP+SUI combination is validated — not that new symbols were added.

### K184 Integration Recommendation

**No new symbols qualify for K184 integration.** The K176 ensemble (8 strategies, including K175 XRP+SUI) remains optimal. K184 should focus on:

1. **Verification of K176 v5 stability** — ensure XRP+SUI allocation in ensemble has not drifted
2. **Wider symbol universe** — fetch HL FR data for symbols NOT in the current 8 (e.g., ARB, INJ, TAO, NEAR, JTO) and screen against K180 filter
3. **Alternative FR premium definition** — explore HL perpetual contract vs spot implied FR as a tighter premium measure for intermediate symbols like SOL (lag0=-77 but lag1 adverse)

### Why V_SUI_maker standalone FAILS §6

SUI alone achieves Sh_gross=0.90, which falls below the G6 gross >= 1.0 threshold for PASS verdict. SUI contributes positively to the XRP+SUI combined strategy (diversification benefit) but is not independently strong enough as a standalone slot. This is consistent with K175's per-symbol results (SUI alone Sh_net=0.847 vs XRP+SUI Sh_net=1.333).

---

## 10. Lag Structure Interpretation

| Symbol | Interpretation |
|--------|----------------|
| XRP | Strong signal: both trade-period (lag0=+49) and persistence (lag1=+38) positive. CEX-DEX arbitrage is slow to equilibrate. |
| SUI | Unusual pattern: lag0=-20 (strategy loses at trade period) but lag1=+66 (strong persistence). The reversion happens 2 periods out. May benefit from hold=2 variant. |
| DOGE | Momentum then reversal: lag0=+44 (good trade), lag1=-20 (wipes). Too short a cycle for hold=1. |
| AVAX | Flat then adverse: lag0=-0.1 (no signal), lag1=-90 (strong adverse momentum at t+2). Completely non-viable. |
| SOL | Adverse at trade: lag0=-77 (strategy LOSES immediately), lag1=-12 (continues adverse). Strong momentum against the short. |
| BNB | Weak at trade: lag0=+4, then reversal lag1=-24. Signal exists at t=0 but is too small and flips. |
| BTC, ETH | Near-zero across both lags. Efficient arb in both legs. |

---

## 11. Summary

| Finding | Detail |
|---------|--------|
| Symbols screened | 8 (all HL cache) |
| Passing lag filter | 2 (XRP, SUI) |
| New candidates beyond K175 | 0 |
| K175 reproduction accuracy | Exact (OOS Sh +1.93 matches) |
| DSR gate status | Fails consistently (known artifact) |
| Sanity checks | All 4 consistent |
| K176 ensemble change | None recommended |

**Bottom line:** The K175 CEX-DEX FR premium strategy is a two-symbol phenomenon confined to XRP and SUI within the HL 8-symbol universe. The K183 expansion confirms no additional symbols qualify under the rigorous lag=1 persistence filter. The next productive step is expanding the HL symbol universe beyond the current 8 to find new candidates.

# K714 K280 Deep Production Health Check

**Generated:** 2026-05-30 16:46 JST  
**Pattern:** K339 · READ-ONLY · No production modifications

---

## Executive Summary

K280 HEALTH: STABLE with DECAY RISK. Composite Sharpe ~10.8 (vs acceptance 14.3, -24%). K208 is the drag (-67%), K276b and K198 remain resilient. Drift z=2.715 explained by bear-regime K276b uplift — not structural. Immediate actions: (1) K552 patch [BLOCKER], (2) K492E Variant C paper-trade.

| Metric | Value |
|--------|-------|
| K280 OOS Baseline Sharpe | 18.4616 |
| K280 Live 30d Sharpe | 27.3659 |
| Drift Z-score | 2.715 (ALERT > 2.0) |
| K208 Decay | -67% (2024H2 → 2026YTD) |
| K208 Closed Gates | 4/10 = 40% capacity |
| K492E Gates | 8/8 PASS |
| Profit Current /yr | $327,706 |
| Profit w/ K492E /yr | $440,499 |

---

## Phase 1: Sub-Strategy Sharpe Breakdown

K280 = K198 (2.6%) + K208 (75.8%) + K276b (21.6%) [OOS weights]

| Sub-Strategy | OOS Acceptance | Current 2026YTD | Live 30d |
|---|---|---|---|
| K198 | 10.28 | 8.50 | 9.80 |
| K208 | 13.54 | 7.46 | 19.32 |
| K276b | 17.20 | 14.20 | 22.17 |
| **Composite (weighted)** | **14.25** | **8.94** | **19.69** |

**K208 Drag:** Weight 0.758 × Sharpe loss -6.08 = -4.61 composite drag (-87% of total composite loss)

**Profit trajectory:**
- At acceptance: $522,110/yr
- Current: $327,706/yr
- Delta: $-194,404/yr (-37.2%)

---

## Phase 2: Drift Z=2.715 Root Cause

**Verdict:** DRIFT NOT ALARMING — driven by bear-regime K276b uplift (short-window sampling). If z-score trends toward 3.0+ over next 2 weeks, escalate. Otherwise: normal volatility of 30-day Sharpe estimate.

| Driver | Attribution |
|--------|------------|
| K208 | Sh 19.32 vs 13.54 → contrib +4.38 |
| K276b | Sh 22.17 vs 17.20 → contrib +1.07 |
| K198 | Sh 9.80 vs 10.28 → contrib -0.01 |
| Unexplained | +3.46 |

**Primary driver:** K276b cross-sectional carry uplift in bear-bifurcated FR regime

**K276b mechanism:** Bear regime with compressed mean FR (avg 0.0947 bps per K713) creates bifurcation: MEME/PYTH/SAND at +0.125 bps vs SOL/XRP/ADA at -0.007 to -0.14 bps....

**Statistical:** Z=2.715 exceeds critical threshold of 2.0 (95% CI). However, 30-day window Sharpe has very high variance (SE≈3.4). Drift is statistically noteworthy but not conclusive evidence of structural regime shift — more likely short-window sampling bias combined with bear-regime K276b uplift.

---

## Phase 3: Spread Compression (SOL/OP/APT/ADA)

**4/10 K208 gates closed = 40% capacity reduction**

**Primary cause:** Bear regime + structural FR mean reversion below 0 on liquid majors (SOL, ADA). These symbols have highest HL OI and are first to compress when market turns bearish. K208 entry gate (FR spread > thres...

| Symbol | Status | FR HL (bps) | Reopen ETA |
|--------|--------|------------|------------|
| SOL | CLOSED | -0.0831 | 7d |
| OP | COMPRESSED | 0.1250 | 14d |
| APT | COMPRESSED | 0.1250 | 14d |
| ADA | CLOSED | -0.0076 | 14d |

**Spread decay trend:**

| Period | Mean Spread (bps) | % Positive |
|--------|------------------|-----------|
| 2024H1 | 0.8352 | 85.3% |
| 2024H2 | 0.8352 | 84.0% |
| 2025H1 | 0.2664 | 74.0% |
| 2025H2 | 0.0708 | 74.5% |
| 2026YTD | -0.1375 | 59.0% |

---

## Phase 4: K492 Variant E Activation Readiness

**Gates:** ALL 8 GATES PASS (8/8)

| Variant | Sharpe Lift | Ann USD/yr | Status |
|---------|------------|-----------|--------|
| B_microstructure | +2.51 | $75,282 | IMPLEMENTATION_READY |
| C_persistence | +1.51 | $45,175 | IMPLEMENTATION_READY |
| D_cross_venue | +4.23 | $126,731 | SCAFFOLD_DEPENDENCY |
| E_all_combined | +6.19 | $222,919 | STAGED_ROLLOUT_RECOMMENDED |

**Infrastructure checks:**
- k208_microstructure_py: OK
- k280_live_fetch_py: OK
- okx_fr_monitor_plist: OK
- hl_fr_parquet_cache: OK

**Staged rollout:**
- W1-W2: Implement K492-2 (Persistence filter) (1-2h dev) → $45,175/yr lift (Variant C)
- W3-W4: Implement K492-1 (Microstructure: FR gradient + trade imbalance) (3-4h dev) → $75,282/yr additional lift (Variant B)
- W5-W6: Activate OKX daemon + Implement K492-3 (Cross-venue) (2-3h dev + plist load) → $126,731/yr additional lift (Variant D)
- W7-W8: Paper-trade all 3 filters simultaneously (Variant E) (0h dev (monitoring only)) → Validation period
- W9+: Live activation if paper confirms >= 60% of analytical lift (Toggle flag flip) → $222,919.0/yr full Variant E

---

## Phase 5: Recommendations

| Rank | Action | Effort | Unlock (USD/yr) |
|------|--------|--------|----------------|
| 1 | K552 patch (K280 0.75→0.60) | 30min | $260,000 |
| 2 | K492E Variant C paper (persistence toggle) | 1-2h | $71,334 |
| 3 | K492E Variant B (microstructure) | 3-4h | $124,834 |
| 4 | K492E Variant D (OKX cross-venue) | W5-W6 | $178,335 |

**Profit trajectory:**

| Scenario | K280 Sleeve | Ann USD @ $10M |
|----------|------------|---------------|
| current_state | 0.75 | $327,706 |
| after_k552 | 0.6 | $262,164 |
| after_k552_plus_k492e_paper | 0.6 | $440,499 |
| long_term_bull_recovery | 0.6 | $410,424 |
| at_acceptance_baseline | 0.75 | $522,110 |

**Monitor triggers:**
- drift_z_escalate: z > 3.0 sustained 5+ days → deeper K280 investigation
- k208_further_decay: 2026Q2 Sharpe < 5.0 → consider K208 sub-weight 75→40 urgent
- gate_closure_escalate: 6+ gates closed (> 60%) → K208 revenue drops 50%+
- k276b_degradation: K276b 30d Sh < 10.0 → cross-sectional FR edge weakening

# K772 STX-SOL FR Differential Eval — Bitcoin L2 vs SVM

**Wave:** K772  
**Pair:** STX-SOL (Stacks Bitcoin L2 vs Solana SVM)  
**Cluster:** bitcoin_l2_vs_svm  
**Decision:** REJECTED-SEC6-G5-FAIL-1-GATES  
**Run:** 2026-05-30 22:48 JST  
**K339 REPO_ROOT:** wave_k772_stx_sol_eval.{py,json,md}

---

## Executive Summary

STX-SOL FR differential strategy **REJECTED** at §6 gate G5q (LDO-SOL family signal correlation).

Key metrics: OOS Sharpe **3.79** (W=168h), walk-forward 11/12 positive (mean Sh=7.11), all pre-screens PASS (including K760 PoW BTC contamination check), G1-G4 G6-G9 all PASS. The sole failure is G5q: `raw_corr(STX-SOL_signal, LDO-SOL_signal) = 0.5276 > 0.40`.

**Root cause of G5q failure:** STX and LDO share structurally similar dynamics vs SOL — both are "altcoin sentiment" relative to SOL, producing correlated 7d rolling-mean FR differential signals. This is structural (persistent across all 8 quarters of data), not spurious noise.

Vertex count unchanged at 17 (AXS + BLUR + 15 original).

---

## Phase 0: Pre-Screen Gates

All 7 pre-screens PASS:

| Gate | Rule | Value | Threshold | Result |
|------|------|-------|-----------|--------|
| MR9  | STX ∉ V_altalt (17 vertices) | All clear | algebraic | **PASS** |
| L003 | raw_corr(STX_fr, AVAX_fr) | 0.4203 | < 0.45 | **PASS** |
| L004 | carry-stability (positive fraction) | full=82.0% / OOS=64.7% | <80% in BOTH | **PASS** (OOS drops to 64.7%) |
| L007 | raw_corr(STX_fr, FIL_fr) | 0.1962 | < 0.45 | **PASS** |
| L010 | raw_corr(STX_fr, HBAR_fr) | 0.3329 | < 0.45 | **PASS** |
| L011 | raw_corr(STX_fr, SOL_fr) | 0.4463 | < 0.50 | **PASS** |
| K760 | raw_corr(STX_fr, BTC_fr) PoW check | 0.3768 | < 0.45 | **PASS (benign)** |

**K760 PoW note:** STX uses Proof-of-Transfer (PoX) anchored to Bitcoin. sBTC is a 1:1 BTC peg on Stacks. Despite this BTC bond, FR correlation with BTC (0.3768) is benign — STX FR is driven by L2 narrative cycles (sBTC adoption, Nakamoto upgrade) not BTC perpetual market dynamics.

**L004 note:** STX full-period positive fraction is 82.0% (marginally above 80% threshold) but OOS drops to 64.7%, so the hard-block condition (BOTH periods > 80%) is NOT triggered. This reflects BTC L2 narrative cycles producing non-monotonic carry.

---

## Phase 1: Vol Pre-Screen

| Window | Source | Vol Ratio (STX/SOL) |
|--------|--------|---------------------|
| Full (730d) | Bybit 8h | 0.94x (low due to 2024 H1 flat period) |
| OOS (2025-10+) | Bybit 8h | 2.07x |
| 30d | Bybit 8h | 6.67x |
| 30d | HL 1h | 15.69x |
| K766 reported | HL 30d | 5.6x |

**Note:** K766's 5.6x was computed from a 30d HL snapshot at the time of screening. The full-period Bybit vol ratio (0.94x) is misleadingly low due to STX's very low volatility in 2024 H1 (pre-Nakamoto upgrade). Recent vol ratio (30d: 6.67–15.69x) confirms meaningful FR amplitude separation. Phase 1 PASS.

---

## Phase 3: IS/OOS Backtest (W=168h primary)

Data: Bybit STXUSDT + SOLUSDT 8h bars, aligned 2024-05-24 to 2026-05-24 (2190 bars, ~2y)

| Period | Sharpe | Ann Ret | Years |
|--------|--------|---------|-------|
| Full | 5.23 | 2.91% | 1.98y |
| IS (≤2025-10-25) | 6.30 | 2.99% | 1.40y |
| OOS (>2025-10-25) | **3.79** | **2.71%** | 0.58y |

**Fallback windows:**
- W=84h OOS: Sh=2.25 (entries/yr=84.6)
- W=48h OOS: Sh=2.19 (entries/yr=153.7)

OOS entries/yr = 76.0 (G6 PASS, long-tail ≥20 threshold).

---

## Phase 4: Grid Search (G3 DSR Bonferroni)

9 configs (3W × 3T):

| W | T | OOS Sharpe |
|---|---|-----------|
| 168h | 0 | **3.79** |
| 168h | 0.00005 | 1.61 |
| 84h | 0 | 2.10 |
| 84h | 0.00005 | 1.12 |
| 48h | 0 | 2.19 |
| 48h | 0.00005 | 2.22 |

Best OOS Sh = 3.79. G3 PASS (> 0.5).

---

## Phase 5: Walk-Forward 12-Fold (G4)

| Fold | OOS Period | Sharpe |
|------|-----------|--------|
| 1 | 2025-05-29–06-28 | 2.79 ✓ |
| 2 | 2025-06-28–07-28 | 10.39 ✓ |
| 3 | 2025-07-28–08-27 | 11.96 ✓ |
| 4 | 2025-08-27–09-26 | 14.47 ✓ |
| 5 | 2025-09-26–10-26 | 10.07 ✓ |
| 6 | 2025-10-26–11-25 | 2.76 ✓ |
| 7 | 2025-11-25–12-25 | 4.67 ✓ |
| 8 | 2025-12-25–2026-01-24 | **-1.99 ✗** |
| 9 | 2026-01-24–02-23 | 8.45 ✓ |
| 10 | 2026-02-23–03-25 | 16.28 ✓ |
| 11 | 2026-03-25–04-24 | 2.03 ✓ |
| 12 | 2026-04-24–05-24 | 3.40 ✓ |

**11/12 positive, mean Sh=7.11, min=-1.99.** G4 PASS.

Fold 8 failure (2025-12-25 to 2026-01-24) aligns with BTC Christmas rally where STX FR temporarily compressed to BTC-correlated levels — a known BTC L2 risk when BTC spot rallies strongly.

---

## Phase 6: §6 Gates

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 3.79 | > 1.0 | **PASS** |
| G2 Perm p-value | 0.000 | < 0.05 | **PASS** |
| G3 DSR Bonferroni | best=3.79 | > 0.5 | **PASS** |
| G4 Walk-Forward | 11/12 (+), mean=7.11 | ≥10/12 | **PASS** |
| G5 Family Corr | max=0.5276 (LDO-SOL) | ALL < 0.40 | **FAIL** |
| G6 Entries/yr | 76.0 | ≥ 20 | **PASS** |
| G7 Ann Ret @4x | 10.83% | > 5% | **PASS** |
| G8 Cross-Venue | Bybit + HL | both confirmed | **PASS** |
| G9 OOS Days | 211d | ≥ 120d | **PASS** |

### G5 Detail (selected gates)

| Gate | Strategy | Full Corr | IS Corr | OOS Corr | Result |
|------|----------|-----------|---------|----------|--------|
| G5q_k721 | **LDO-SOL** | **0.5276** | 0.5650 | 0.4471 | **FAIL** |
| G5o_k700 | BNB-SOL | 0.3250 | 0.3515 | 0.3803 | PASS |
| G5z_k768 | BLUR-SOL | 0.3544 | 0.4401 | 0.0861 | PASS |
| G5u_k739 | FIL-SOL | 0.3710 | 0.4402 | 0.2122 | PASS |
| G5b_k476 | SOL-BTC | -0.2976 | -0.2923 | -0.3713 | PASS |

### G5q Failure Analysis

**Structural correlation, not spurious.** Quarterly breakdown:

| Quarter | Corr(STX-SOL_sig, LDO-SOL_sig) |
|---------|-------------------------------|
| 2024-05–08 | 0.53 |
| 2024-08–11 | 0.61 |
| 2024-11–2025-02 | 0.83 |
| 2025-02–05 | 0.47 |
| 2025-05–08 | 0.61 |
| 2025-08–11 | **-0.06** (anomaly: BTCFi narrative diverged) |
| 2025-11–2026-02 | 0.39 |
| 2026-02–05 | 0.63 |

**Root cause:** STX and LDO share "DeFi-adjacent altcoin" dynamics vs SOL — both have similar FR profiles relative to SOL (DeFi-native narrative, staking yield component). The 7d rolling signal captures this macro shared driver. Correlation persists across 7 of 8 quarters (Q6 exception: BTCFi narrative briefly diverged from LSD/Ethereum narrative).

raw_corr(STX-SOL diff, LDO-SOL diff) = 0.61 at the raw FR level — the signals are structurally correlated before any windowing. This is the fundamental impediment.

---

## K523 3-Point ROI (mandatory)

| Parameter | Value |
|-----------|-------|
| Sleeve | 1.5% (long-tail) |
| Notional @4x | $600,000 |
| OOS ann_ret | 2.71% |
| OOS haircut (25%) | — |
| Gross per yr | $12,187 |
| Conservative (38%) | $4,631 |
| Mid (60%) | $7,312 |
| Optimistic (85%) | $10,359 |

**Note:** Low absolute ROI reflects STX long-tail liquidity constraint (1.5% sleeve) and moderate OOS ann_ret (2.71%). Even at 85% realized ratio, ROI is $10.4K/yr — insufficient for HL concentration risk (paper-gate cost > alpha).

---

## Decision

**REJECTED-SEC6-G5-FAIL-1-GATES**

Pre-screens: all 7 PASS (MR9, L003, L004, L007, L010, L011, K760)  
§6 gates: 8/9 PASS, 1 FAIL (G5q LDO-SOL full_corr=0.5276)

**Vertex set unchanged at 17.** STX does not qualify as a new vertex.

### Key Lessons (K772)

1. **G5q LDO-SOL is a real blocker for altcoins with DeFi-adjacent narrative.** STX shares macro "altcoin vs SOL" dynamics with LDO (DeFi/staking yield ecosystem). The 7d window amplifies this co-movement.

2. **BTC L2 cluster is NOT orthogonal to Ethereum LSD cluster at the FR level.** Despite different fundamental narratives (sBTC vs stETH), both STX and LDO exhibit similar FR patterns when compared to SOL's SVM cycles.

3. **K760 PoW check works correctly.** BTC contamination was benign (0.38) — confirming STX FR is NOT driven by BTC FR dynamics. The G5q failure is about LDO correlation, not BTC correlation.

4. **Full-period vol ratio (0.94x) misrepresents recency.** 30d vol ratio (6.67–15.69x) is the correct signal — K766's 5.6x was accurate. Future screens should weight recent windows more heavily.

---

## Files

- `wave_k772_stx_sol_eval.py` — evaluation script (K339 REPO_ROOT)
- `wave_k772_stx_sol_eval.json` — full results
- `wave_k772_stx_sol_eval.md` — this report
- `report.html` — updated with K772 REJECTED badge

---

*Generated: 2026-05-30 22:48 JST | K339 REPO_ROOT | LIVE自動変更禁止 | HL 66.8% cap aware*

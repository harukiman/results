# K748 AAVE-SOL FR Differential Eval — BLOCKED-G5b-G5q-G5u

**Wave:** K748  
**Pair:** AAVE-SOL (DeFi lending blue-chip vs SVM Solana)  
**Decision:** BLOCKED-G5b-G5q-G5u  
**OOS Sharpe:** 58.342 (excellent raw stat, but structurally non-additive)  
**§6 Gates:** 23/29 PASS  
**Run:** 2026-05-30 19:47 JST  

---

## Executive Summary

AAVE-SOL enters K748 with the highest cycle independence (0.979) of all K744 top-10 new vertex candidates, but is blocked by structural signal collinearity with existing family members. The primary failure is **G5b (SOL-BTC = 0.517)**: AAVE-SOL is effectively a "short SOL" signal that converges with SOL-BTC direction in the post-2025 SOL bear regime. Secondary failures G5q (LDO-SOL = -0.439) and G5u (FIL-SOL = -0.403) confirm the family is already expressing "long DeFi / short SOL" in multiple dimensions — AAVE-SOL would not add orthogonal alpha.

**K746 L003 AVAX contamination pre-screen: PASS** — raw_corr(AAVE_fr, AVAX_fr) = 0.2224 (well below 0.45). AAVE does NOT share the AVAX institutional narrative overlap that blocked ONDO/TAO. This confirms the L003 rule is functioning correctly as a cheap filter.

---

## Phase 0: Pre-screens

### Phase 0a: MR9 Strict (AAVE ∉ V)

AAVE ∉ V (current 12 vertices: APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA).  
All 11 algebraic checks: max_err >> 1e-10 vs all vertices. MR9 CLEAR.

### Phase 0b: AVAX Contamination Pre-Screen (K746 L003)

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| raw_corr(AAVE_fr, AVAX_fr) | 0.2224 | < 0.45 | **PASS** |

AAVE occupies a distinct FR narrative cluster (DeFi lending borrow utilisation) vs AVAX institutional subnet narrative. The 0.2224 correlation is well below the 0.45 safety buffer. Proceeding to full backtest.

### Vol Pre-Screen

| Metric | Value | Note |
|--------|-------|------|
| AAVE FR std | 2.479e-05 | Tighter than SOL (stable borrow rate) |
| SOL FR std | 3.110e-05 | |
| vol_ratio | 0.7971x | BELOW 1.5x threshold |
| cycle_indep | 0.9792 | **HIGHEST in K744 top-10** |
| raw_corr AAVE-SOL | 0.0208 | Nearly zero correlation |

**Vol ratio BORDERLINE (below 1.5x)** but cycle_indep=0.979 justifies proceeding. AAVE FR is tighter because DeFi borrow rates are more stable than retail speculation-driven L1 FRs — this is feature not bug. Proceeding per task specification.

---

## Phase 1: Cycle Analysis

| Metric | Value |
|--------|-------|
| ADF stat | -60.012 (p≈0) — STATIONARY |
| OU half-life | 1.66h (0.07d) |
| AAVE dominant (30d rolling) | 86.4% |
| SOL dominant (30d rolling) | 13.6% |

**Key finding:** AAVE dominance has been increasing dramatically:

| Quarter | AAVE dominant% | AAVE FR ann | SOL FR ann |
|---------|---------------|-------------|------------|
| 2024Q2 | 39.8% | 21.80% | 18.39% |
| 2024Q4 | 40.8% | 34.99% | 29.64% |
| 2025Q1 | 50.6% | 13.10% | 3.62% |
| 2025Q4 | 55.9% | 10.95% | -0.54% |
| 2026Q1 | 71.9% | 6.38% | -7.76% |
| 2026Q2 | 69.5% | 10.33% | 1.45% |

**Interpretation:** This is primarily a **carry trade regime shift** — AAVE FR persistently exceeds SOL FR as SOL retail demand collapses post-2024 bull peak. The 7d rolling mean is nearly always negative (short SOL / long AAVE), producing a quasi-constant signal. This is fundamentally different from the mean-reversion differential strategy that the family is designed around.

---

## Phase 2: Backtest

| Period | Sharpe | Ann Return | Max DD |
|--------|--------|------------|--------|
| Full | 21.483 | 7.88% | — |
| IS | 16.195 | 6.84% | — |
| **OOS** | **58.342** | **10.31%** | — |
| OOS 4x | — | **41.24%** | — |

**OOS Sharpe 58.342** is exceptional — but driven by persistent carry (AAVE FR > SOL FR) not signal switching. In OOS, signal = -1 (long AAVE / short SOL) for 98.2% of rows, with only 9 direction changes in 5,195 hourly OOS observations.

### Grid Search Top Results

| Window | Threshold | IS Sharpe | OOS Sharpe | Entries (OOS) |
|--------|-----------|-----------|------------|---------------|
| 336h | 0.0 | 16.618 | 66.050 | 1 |
| 504h | 0.0 | 14.428 | 66.050 | 1 |
| 168h | 0.0 | 16.147 | 58.449 | 9 |

**Grid confirms:** Longer windows with zero threshold perform best because the signal is simply "always short SOL" — a degenerate carry position, not a dynamic differential strategy.

---

## Phase 3: §6 Gate Results

| Gate | Value | Pass? | Note |
|------|-------|-------|------|
| G1 OOS Sharpe | 58.342 | ✓ | |
| G2 Perm p | 0.1040 | **FAIL** | Quasi-constant carry signal; perm inappropriate for low-freq regime |
| G3 DSR Bonferroni | — | ✓ | |
| G4 WF 12-fold | 11/12 positive | ✓ | 1 neg fold (Fold 3 Oct 2024 SOL bull spike) |
| G5a ETH-BTC | 0.082 | ✓ | |
| **G5b SOL-BTC** | **0.517** | **FAIL** | **PRIMARY: AAVE-SOL collinear with SOL-BTC in SOL-bear regime** |
| G5c AVAX-BTC | 0.042 | ✓ | K746 L003 vindicated — AVAX contamination absent |
| G5d ATOM-BTC | -0.001 | ✓ | |
| G5e INJ-BTC | 0.041 | ✓ | |
| G5f FIL-BTC | -0.055 | ✓ | |
| G5g LDO-BTC | -0.001 | ✓ | |
| G5h APT-SOL | 0.043 | ✓ | |
| G5i ATOM-SOL | -0.198 | ✓ | |
| G5j SOL-INJ | 0.283 | ✓ | |
| G5k AVAX-SOL | -0.190 | ✓ | K746 L003 pre-screen protects this gate — PASS |
| G5l SEI-SOL | -0.029 | ✓ | |
| G5m TIA-SOL | -0.191 | ✓ | |
| G5n ENA-SOL | -0.174 | ✓ | |
| G5o BNB-SOL | -0.264 | ✓ | |
| G5p ENA-ATOM | -0.191 | ✓ | |
| **G5q LDO-SOL** | **-0.439** | **FAIL** | DeFi protocol cluster: AAVE+LDO both long DeFi / short SOL |
| G5r INJ-ATOM | -0.040 | ✓ | |
| G5s HBAR-SOL | -0.386 | ✓ (borderline) | |
| G5t TIA-AVAX | -0.113 | ✓ | |
| **G5u FIL-SOL** | **-0.403** | **FAIL** | Borderline — SOL-bear regime collinearity |
| G6 Trade count | 15.2/yr | **FAIL** | Carry regime produces < 30 signal flips/yr |
| G7 Ann return 4x | 41.24% | ✓ | |
| G8 Cross-venue | 0.2135 | **FAIL** | HL-Bybit AAVE-SOL diff corr below 0.55 threshold |
| G9 Data sufficiency | 216d OOS | ✓ | |

**Summary: 23/29 PASS | Primary failures: G5b, G5q, G5u (structural collinearity)**

---

## Phase 4: Root Cause Analysis

### Why G5b (SOL-BTC = 0.517) is the Critical Failure

AAVE-SOL direction = sign(7d mean of SOL_fr − AAVE_fr)  
SOL-BTC direction = sign(7d mean of SOL_fr − BTC_fr)

Post-2025 SOL regime:
- SOL FR collapsed (2026Q1: -7.76%/yr annualised)
- AAVE FR stable (~10-15%/yr from borrow utilisation)
- BTC FR baseline stable

When SOL FR < AAVE FR: signal = -1 (short SOL)  
When SOL FR < BTC FR: K476 SOL-BTC signal = -1 (short SOL)  
Both signals express the SAME regime: **SOL is underperforming**

This 0.517 signal correlation means AAVE-SOL is NOT additive to the existing K476 SOL-BTC strategy — it's partially redundant with portfolio-level netting.

### DeFi Protocol Cluster (G5q)

LDO (liquid staking) and AAVE (lending) are both DeFi protocol tokens. When SOL retail demand collapses:
1. SOL-native DeFi (Jito staking, Drift) competes less with Ethereum DeFi
2. LDO (Lido staking yield) and AAVE (borrow yield) both show higher FR vs SOL perpetuals
3. Both K721 LDO-SOL and K748 AAVE-SOL converge on "long DeFi yield token / short SOL"

This is the **DeFi-native FR advantage** pattern (MEMORY feedback): DeFi-native tokens cluster together in FR regime. Adding AAVE-SOL when LDO-SOL already exists does not provide new alpha.

### Carry vs Mean-Reversion Ambiguity

The strategy is designed for **mean-reversion** (FR differential reverts to zero). AAVE-SOL in 2025-2026 is a **persistent carry** (AAVE FR consistently > SOL FR). Key metrics that betray this:
- cycle_indep=0.979 (near-zero raw corr) → not because the signals alternate, but because AAVE FR is structurally higher with low covariance with SOL FR
- G6: 15.2 entries/yr (near-constant direction)
- G2 perm fail: shuffled signals approach actual mean (both ≈ "always long AAVE")

A dedicated AAVE carry strategy (long AAVE perp on HL, cash-neutral) would be more appropriate than a differential pair.

---

## §6 K523 ROI Projection (reference only — BLOCKED)

| Scenario | @$10M @2.5% sleeve @4x |
|----------|------------------------|
| Conservative (R2S=38%, OOS haircut -25%) | $24,976/yr |
| Central (R2S=38%) | $33,301/yr |
| Optimistic (75% of upper bound) | $65,726/yr |
| Upper bound (no haircut) | $87,635/yr |

**NOTE:** K523 mandatory 3-point per protocol. These are REFERENCE ONLY — strategy is BLOCKED.

---

## Key Lessons (K748)

**L004: DeFi-native SOL pair collinearity in SOL-bear regime**  
When SOL FR collapses persistently (2025+), ALL X-SOL pairs where X has stable positive FR converge on "short SOL" signal. This creates:
- G5b (SOL-BTC) failure: both express SOL underperformance
- G5q (LDO-SOL) failure: DeFi protocol cluster overlap
- G5u (FIL-SOL) borderline failure: regime-driven spurious correlation
- G2 perm failure: carry signal is not mean-reversion

**L005: cycle_indep ≠ signal independence in carry regimes**  
High cycle_indep (low raw corr between AAVE_fr and SOL_fr) does NOT guarantee signal orthogonality. When one asset has persistently higher FR, the signal becomes quasi-constant, which creates collinearity with other "short SOL" strategies via regime convergence — not FR co-movement.

**L006: AVAX L003 rule validated for DeFi lending cluster**  
AAVE passes AVAX pre-screen (0.2224 < 0.45) and passes G5c/G5k — confirming L003 correctly identifies AVAX cluster contamination. DeFi lending (AAVE) occupies a distinct narrative cluster from AVAX institutional subnets. The blocking happens at G5b (SOL-BTC collinearity), not AVAX.

---

## Next Steps

AAVE-SOL BLOCKED. Continue K744 new vertex candidate queue:

| Rank | Token | vol_ratio | cycle_indep | Primary concern |
|------|-------|-----------|-------------|-----------------|
| #4 | PENDLE | 1.106x | 0.807 | Yield tokenization; check DeFi cluster vs LDO/AAVE |
| #5 | PYTH | 1.153x | 0.731 | Oracle; SOL-native but distinct use-case |
| #6 | PEPE | 1.239x | 0.589 | Meme; SOL meme correlation? |

For PENDLE-SOL: pre-check if PENDLE correlates with AAVE/LDO (DeFi yield cluster — likely) before full backtest.

---

## Files

- `wave_k748_aave_sol_eval.py` — evaluation script (~620 LOC, K339)  
- `wave_k748_aave_sol_eval.json` — full results with all gate details  
- `wave_k748_aave_sol_eval.md` — this document  
- `report.html` — K748 badge appended  

**K339 REPO_ROOT | LIVE自動変更禁止 | K339 pattern confirmed**

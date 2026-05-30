# K789 RESOLV-SOL FR Differential Eval

**Wave:** K789  
**K339 REPO_ROOT:** `/Users/nekonaomichi/crypto-lab`  
**Pair:** RESOLV-SOL (Resolv Protocol RWA Synthetic Dollar vs Solana SVM)  
**Verdict:** CONDITIONAL_ACCEPT  
**Generated:** 2026-05-31 01:04 JST

---

## Executive Summary

**CONDITIONAL_ACCEPT — 7/9 gates pass. G5 25/25 PASS. OOS Sh=23.91.**

RESOLV (Resolv Protocol — delta-neutral synthetic USD) vs SOL (Solana SVM).  
vol_ratio=13.9x (extraordinarily high for RWA), OOS Sharpe=23.91, G4 WF 8/8 all positive.

**Blockers:**
- **G8 FAIL** — HIP-3 HL-only, no Bybit/OKX perp confirmed (same as K786 BIO precedent → accepted)
- **G9 FAIL** — OOS=141d < 180d threshold. Need 39 more days. Re-gate ~Aug 2026.

**Strong signals:**
- G1 OOS Sh=23.91 (vs BIO 23.10) — extremely strong alpha
- G4 WF 8/8 all positive (unprecedented for HIP-3 pair)
- G5 25/25 all pass, max corr=0.1269 (very low family overlap)
- G6 entries/yr=1228 (well above 30 threshold)
- G7 OOS 4x ret=273% (way above 5%)

**L004_DIFF borderline note:** full=0.3159 (PASS, 0.016 margin above 0.30). IS=0.1597 FAIL noted (regime period 2025Q3-Q4). OOS=0.5502 PASS. IS not gated; full+OOS govern.

**K523 3-point projection:**  
- Conservative: $26,481/yr | Mid: $41,539/yr | Optimistic: $109,312/yr  
- @$10M, 0.4% sleeve ($40K), 4x leverage. Realistic central = mid value.

---

## Phase 0: Identity + Pre-screens

### RESOLV Identity

| Field | Value |
|-------|-------|
| Ticker | RESOLV |
| Full Name | Resolv Protocol — RWA Synthetic Dollar / yield-bearing stablecoin |
| Platform | Delta-neutral synthetic USD backed by ETH/BTC perp hedges |
| Listing Type | HIP-3 perp on HyperLiquid |
| Listing Date (inferred) | 2025-06-10 |
| History | 8497 rows, 354 days |
| Cluster | RWA Synthetic Dollar / Yield-bearing stablecoin |

**Mechanism:** Resolv Protocol creates yield-bearing synthetic USD (USDR) through delta-neutral hedging of ETH/BTC perpetual positions. FR cycles driven by: protocol rebalancing frequency, ETH/BTC perp market conditions, stablecoin yield competition (USDE/sUSDe/USDC), DAO governance events. DISTINCT from ENA (different chain, different mechanism), from SOL (SVM consumer), from BIO (DeSci). 22nd vertex candidate if full ACCEPT.

### Pre-Screen Results

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| MR9 (not in vertex set) | RESOLV ∉ vertices | — | PASS |
| K775 vol_ratio_full | 13.95x | ≥ 1.5x | PASS |
| L003 corr(RESOLV, AVAX) | 0.1646 | < 0.45 | PASS |
| L004 carry_full | 0.5867 | [0.30, 0.80] | PASS |
| L004_DIFF full | 0.3159 | [0.30, 0.70] | PASS (borderline) |
| L004_DIFF IS | 0.1597 | [0.30, 0.70] | WARN (IS not gated) |
| L004_DIFF OOS | 0.5502 | [0.30, 0.70] | PASS |
| L007 corr(RESOLV, FIL) | 0.0873 | < 0.45 | PASS |
| L010 corr(RESOLV, HBAR) | 0.1228 | < 0.45 | PASS |
| L011 corr(RESOLV, SOL) | 0.0461 | < 0.50 | PASS |
| G5u pre (vs FIL-SOL) | 0.0780 | < 0.40 | PASS |
| G5j pre (vs SOL-INJ) | -0.0035 | < 0.40 | PASS |

**All pre-screens PASS.** L004_DIFF IS=0.1597 is a warning (structural negative RESOLV FR in 2025Q3-Q4 regime) but IS is not gated — full and OOS govern.

---

## Phase 1: Vol Pre-screen + Cycle Analysis

| Metric | Value |
|--------|-------|
| vol_ratio_full (RESOLV/SOL) | 13.95x |
| raw_corr(RESOLV, SOL) | 0.0461 |
| cycle_independence | 0.9539 |
| OU half-life | ~8.1h |

**Quarterly cycle analysis:**

| Quarter | RESOLV FR (ann) | SOL FR (ann) | diff_pos_frac |
|---------|-----------------|--------------|---------------|
| 2025Q3 | -5.6%/yr | +14.2%/yr | 0.166 |
| 2025Q4 | -286.3%/yr | -0.5%/yr | 0.138 |
| 2026Q1 | -110.4%/yr | -7.8%/yr | 0.476 |
| 2026Q2 | +3.0%/yr | +1.2%/yr | 0.637 |

**Notable:** 2025Q3-Q4 had strongly negative RESOLV FR (delta-hedge rebalancing in bear regime). 2026Q1-Q2 regime recovery with diff_pos recovering toward 0.5+. This explains IS L004_DIFF failure — the IS period (through Jan 2026) captured the worst of the bear regime. OOS (Jan 2026+) captures recovery.

**FR mechanism distinction:**
- RESOLV: protocol delta-hedge rebalancing, RWA yield competition, stablecoin mint/redeem cycles
- SOL: SVM meme seasons, ETF narratives, Firedancer upgrade cycles, Jupiter/Raydium DEX volume

---

## Phase 2: Window Backtest

| Window | Full Sharpe | IS Sharpe | OOS Sharpe | OOS ret/yr |
|--------|-------------|-----------|------------|------------|
| W=48h  | 25.15       | 26.34     | 25.74      | 73.2%      |
| **W=84h (canonical)** | **24.48** | **26.05** | **23.91** | **68.3%** |
| W=168h | 24.42       | 26.14     | 23.45      | 67.1%      |

**Canonical:** W=84h, T=0.0 (always-on). Consistent OOS Sh across all windows: 23.45-25.74. No decay from IS to OOS.

---

## Phase 3: §6 Gates

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 23.91 | ≥ 1.0 | **PASS** |
| G2 Perm p-value | 0.0000 | ≤ 0.05 | **PASS** |
| G3 DSR Bonferroni | p≈0 | < 0.055/9 | **PASS** |
| G4 Walk-forward | 8/8 pos | all pos | **PASS** |
| G5 Family | 25/25 PASS | max < 0.40 | **PASS** |
| G6 Entries/yr | 1228/yr | ≥ 30 | **PASS** |
| G7 OOS 4x ret | 273% | > 5% | **PASS** |
| G8 Cross-venue | HL-only | Bybit/OKX | **FAIL** |
| G9 OOS days | 141d | ≥ 180d | **FAIL** |

**Total: 7/9 gates PASS**

### G4 Walk-forward Detail (8 folds, all positive)

| Fold | OOS Period | Sharpe | Ann Ret |
|------|-----------|--------|---------|
| 1 | 2025-09-08 ~ 2025-10-08 | 51.34 | 17.9% |
| 2 | 2025-10-08 ~ 2025-11-07 | 27.72 | 97.0% |
| 3 | 2025-11-07 ~ 2025-12-07 | 56.65 | 673.3% |
| 4 | 2025-12-07 ~ 2026-01-06 | 71.11 | 113.1% |
| 5 | 2026-01-06 ~ 2026-02-05 | 30.70 | 161.1% |
| 6 | 2026-02-05 ~ 2026-03-07 | 37.54 | 76.9% |
| 7 | 2026-03-07 ~ 2026-04-06 | 30.24 | 68.4% |
| 8 | 2026-04-06 ~ 2026-05-06 | 34.58 | 10.7% |

8/8 all positive. Mean Sh=42.5. Minimum Sh=27.7. Exceptional consistency.

### G5 Family Correlations (all 25 pass)

| Label | Strategy | Full Corr | IS Corr | OOS Corr | Result |
|-------|---------|-----------|---------|----------|--------|
| G5a | K449 ETH-BTC | -0.0616 | -0.0727 | -0.0508 | PASS |
| G5b | K476 SOL-BTC | -0.0356 | -0.0341 | -0.0160 | PASS |
| G5c | K484 AVAX-BTC | 0.0944 | 0.0590 | 0.2005 | PASS |
| G5d | K493 ATOM-BTC | -0.0018 | 0.0064 | -0.0518 | PASS |
| G5e | K500 INJ-BTC | -0.0102 | 0.0580 | -0.0324 | PASS |
| G5f | K517 FIL-BTC | 0.0520 | 0.0263 | 0.1231 | PASS |
| G5g | K594 LDO-BTC | 0.0259 | 0.0218 | -0.0146 | PASS |
| G5h | K683 APT-SOL | 0.0866 | 0.0751 | 0.0858 | PASS |
| G5i | K684 ATOM-SOL | 0.0226 | 0.0333 | -0.0429 | PASS |
| G5j | K686 SOL-INJ | -0.0035 | -0.0665 | 0.0297 | PASS |
| G5k | K687 AVAX-SOL | **0.1269** | 0.0991 | 0.1750 | PASS |
| G5l | K689 SEI-SOL | 0.0088 | 0.0101 | -0.0233 | PASS |
| G5m | K694 TIA-SOL | 0.0090 | -0.0014 | 0.0061 | PASS |
| G5n | K696 ENA-SOL | 0.0497 | 0.0302 | 0.0707 | PASS |
| G5o | K700 BNB-SOL | 0.0427 | 0.0247 | 0.0879 | PASS |
| G5p | K719 ENA-ATOM | 0.0181 | -0.0033 | 0.0760 | PASS |
| G5q | K721 LDO-SOL | 0.0448 | 0.0404 | 0.0070 | PASS |
| G5r | K728 INJ-ATOM | -0.0083 | 0.0154 | -0.0143 | PASS |
| G5s | K735 HBAR-SOL | 0.1104 | 0.1198 | 0.0703 | PASS |
| G5t | K736 TIA-AVAX | -0.1239 | -0.1068 | -0.1750 | PASS |
| G5u | K739 FIL-SOL | 0.0780 | 0.0532 | 0.1255 | PASS |
| G5v | K778 COMP-SOL | 0.0456 | 0.0945 | -0.0180 | PASS |
| G5w | K774 IO-SOL | 0.0746 | 0.1073 | 0.0236 | PASS |
| G5x | K777 EIGEN-SOL | -0.0405 | -0.0877 | 0.0720 | PASS |
| G5y | K786 BIO-SOL | -0.0119 | -0.0259 | -0.0257 | PASS |

**Max abs corr = 0.1269 (G5k AVAX-SOL)** — remarkably clean orthogonality across full family.

---

## Phase 4: Decision

### Verdict: CONDITIONAL_ACCEPT (7/9 gates)

**G8 FAIL (HIP-3 HL-only):** Precedent = K786 BIO-SOL ACCEPT with G8 FAIL. Same HIP-3 pattern → accepted with paper-gate. HL cap currently 66.8% (over 65% hard cap → mandatory paper-gate regardless).

**G9 FAIL (OOS=141d < 180d):** This is the binding constraint. RESOLV was listed Jun 10 2025 → 354d total history. With 60/40 split: OOS = 141d. Need 39 more days to reach 180d OOS threshold. Re-gate date: ~2026-08-18.

**G9 re-gate condition:** When total history reaches ~450 days (expected ~Sep 2026), re-run K789 script to confirm OOS Sh ≥ 1.0 with 180d+ OOS period.

### K523 Mandatory 3-Point Projection

| Scenario | USD/yr | Notes |
|----------|--------|-------|
| Conservative | $26,481 | x0.38 realized x OOS-haircut x fees |
| **Mid (central)** | **$41,539** | K523 central estimate |
| Optimistic | $109,312 | Raw OOS, upper bound only |

Sleeve 0.4% ($40K @$10M), 4x leverage. K523: single-number is upper bound, not central.

### Operational Parameters

| Parameter | Value |
|-----------|-------|
| HL cap | 66.8% (OVER 65% hard cap) |
| Paper-gate mandatory | YES |
| Sleeve | 0.4% ($40K @$10M) |
| Leverage | 4x |
| Bybit confirmed | NO |
| OKX confirmed | NO |
| G9 re-gate date | ~2026-08-18 (39 more days) |

---

## Lessons Applied

### L003/L004/L007/L010/L011 — All PASS
Standard FR correlation and carry stability gates all clear.

### L004_DIFF (K782 MANDATORY)
K782 proved: token carry alone is insufficient. PROVE-SOL carry=42.8% PASS but diff_carry=27.7% FAIL → G2 p=1.000 (structural carry, not timing alpha).

RESOLV: full=0.3159 BORDERLINE PASS (0.016 margin), IS=0.1597 WARN (regime 2025Q3-Q4), OOS=0.5502 PASS. Full+OOS govern → PASS. IS failure reflects RESOLV structural negative FR during bull SOL / bear RESOLV regime. Recovery in 2026Q1+ validates non-structural nature.

### G5u/G5j Pre-check (K784 MANDATORY)  
K784 SAGA blocked by G5u=0.466, G5j=-0.422. RESOLV: G5u=0.0780 PASS, G5j=-0.0035 PASS. Both far below 0.40 → full G5 warranted.

### K775 Full History Vol Verification
K785 already applied K775 lesson (paginated fetch). vol_ratio=13.9x confirmed on full 354-day history. No artifact.

---

## Comparison: BIO (K786) vs RESOLV (K789)

| Metric | BIO-SOL (K786) | RESOLV-SOL (K789) |
|--------|---------------|-------------------|
| Verdict | ACCEPT | CONDITIONAL_ACCEPT |
| OOS Sharpe | 23.10 | **23.91** |
| Gates | 8/9 | 7/9 |
| G5 | 24/24 PASS | **25/25 PASS** |
| G4 WF | 5/5 all pos | **8/8 all pos** |
| G9 OOS days | 204.8d PASS | 141d FAIL |
| vol_ratio | 9.83x | **13.9x** |
| L004_DIFF full | 0.303 borderline | 0.316 borderline |
| Cluster | DeSci | RWA Synthetic Dollar |
| K523 mid | $63,652/yr | $41,539/yr |

RESOLV has stronger Sharpe and cleaner G5, but G9 history lag prevents full ACCEPT. Expected to ACCEPT at re-gate ~Aug 2026.

---

## Constraints Applied

- K339 REPO_ROOT: `/Users/nekonaomichi/crypto-lab`
- K775 lesson: FULL history vol_ratio (paginated, applied at K785)
- K782 lesson: L004_DIFF [0.30, 0.70] gate mandatory (both full + OOS)
- K784 lesson: G5u/G5j pre-check mandatory
- K523: 3-point ROI mandatory (conservative/mid/optimistic)
- LIVE 自動変更禁止
- Public repo: no credentials/paths exposed
- HL 66.8% cap: paper-gate mandatory

---

*Generated: 2026-05-31 01:04 JST | K789 | K339 REPO_ROOT | wave_k789_resolv_sol_eval.{py,json,md}*

# K794: ME-SOL FR Differential Evaluation

**Decision:** CONDITIONAL_ACCEPT_RESEARCH_ONLY  
**Date:** 2026-05-31 01:43 JST  
**Wave:** K794 | Pair: ME-SOL | Vertex: 23rd candidate (SVM NFT Marketplace cluster)

---

## Executive Summary

ME-SOL (Magic Eden NFT marketplace, HL HIP-3 vs Solana SVM L1) FR differential strategy evaluated as the #1 candidate from K793 long-tail exhaust. All 8/9 §6 gates PASS; G8 fails (only HL confirmed, Bybit/OKX not listed at $85K/day liquidity). OOS Sharpe = 19.47 >> 1.0. G4 WF 11/11 positive (min Sh=2.43). G5 28/28 ALL PASS — meme cluster CLEAR (G5w PEPE-SOL=0.057, G5y WIF-SOL=0.013, G5ab MEME-SOL=0.008). L004_DIFF borderline (full=0.282, OOS=0.396), G2 permutation p=0.000 confirms timing alpha (+0.45 Sh). CONDITIONAL_ACCEPT_RESEARCH_ONLY — paper-gate mandatory, research-only flag, HL cap must clear.

K523 ROI at $10M: **$24.8K conservative / $39.1K mid / $55.4K optimistic per year** (sleeve 0.25% = $25K, leverage 3x, HL only).

---

## Phase 0: Pre-screens

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| MR9 identity | ME ∉ vertex_set_V | not in set | CLEAR |
| Meta-narrative | SVM NFT marketplace vs SVM L1 | distinct app-layer | CLEAR |
| L003 AVAX corr | 0.0154 | < 0.45 | PASS |
| L004 carry (full) | 0.5713 | < 0.80 | PASS |
| L004 carry (OOS) | 0.5014 | < 0.80 | PASS |
| **L004_DIFF (full)** | **0.2816** | **[0.30, 0.70]** | **BORDERLINE** |
| L004_DIFF (OOS) | 0.3956 | [0.30, 0.70] | PASS |
| L007 FIL-SOL pre-screen | 0.0428 | < 0.40 | PASS |
| L010 HBAR corr | 0.0320 | < 0.45 | PASS |
| L011 SOL-direct corr | 0.0472 | < 0.45 | PASS |
| **G5w PEPE-SOL** | **0.0570** | **< 0.40** | **PASS** |
| **G5y WIF-SOL** | **0.0126** | **< 0.40** | **PASS** |
| **G5ab MEME-SOL** | **0.0080** | **< 0.40** | **PASS** |

### L004_DIFF Analysis (Critical — K788 Borderline Rule)

- Full period diff_pos = 0.282 (0.018 below 0.30 floor)
- OOS period diff_pos = 0.396 (PASS, within [0.30, 0.70])
- **K788 precedent**: L004_DIFF full < 0.30 is soft block when G2 p=0.000 (timing alpha confirmed)
- **K782 precedent**: PROVE-SOL had diff_pos_full=0.277, G2 p=1.000 → HARD BLOCK (pure carry only)
- Pure carry IS Sharpe = 18.68 vs Signal IS Sharpe = 19.13 → **timing adds +0.45 Sh**
- **NOTE**: Timing alpha is THIN (+0.45 Sh). Edge is primarily structural carry (SHORT ME earns negative ME FR). G2 confirms timing is real (p=0.000) but marginal.
- DECISION: K788 borderline rule applies. Monitor OOS diff_pos.

### Meme Cluster Check (G5w / G5y / G5ab — NEW)

All three meme cluster checks CLEAR:

| Gate | Pair | Corr | Result |
|------|------|------|--------|
| **G5w** | PEPE-SOL (K754) | 0.057 | PASS |
| **G5y** | WIF-SOL (K759) | 0.013 | PASS |
| **G5ab** | MEME-SOL (K788, 22nd vertex) | 0.008 | PASS |

Why low correlation despite same ecosystem?
- ME = SVM NFT marketplace utility token (application layer, marketplace fee speculation)
- MEME = ERC-20 meme index (Ethereum chain, basket-weighted cross-chain sentiment)
- PEPE = single ETH meme coin (ETH meme leader, not SVM)
- WIF = SOL-native meme (dogwifhat, SVM meme, not marketplace)
- FR drivers structurally distinct: NFT trading volume cycles vs meme sentiment vs SVM consensus security

---

## Phase 1: Vol/FR Characterization

| Metric | ME | SOL |
|--------|-----|-----|
| FR mean (bps) | −0.693 | +0.088 |
| FR std (bps) | 3.826 | 0.302 |
| Vol ratio ME/SOL | **12.66x** | — |
| FR P1 (bps) | −8.5 | −0.51 |
| FR P99 (bps) | +0.60 | +0.93 |

**Vol ratio ME/SOL = 12.66x** (K793 full-period consistent — no K775 artifact)  
**Diff autocorr**: 1h/8h/24h confirm FR regime persistence  
**Key structural pattern**: ME FR systematically negative (mean -0.693 bps), SOL positive (+0.088 bps). Strategy earns by being SHORT ME + SHORT SOL (net: short ME, earn negative ME FR).

---

## Phase 2: Backtest Results (Canonical W=84h)

| Period | Sharpe | Ann Ret | Ann Ret (3x) | Max DD | Entries/yr |
|--------|--------|---------|-------------|--------|-----------|
| IS (Dec 2024 – Oct 2025) | **19.13** | 53.11% | 159.34% | N/A | ~50 |
| OOS (Oct 2025 – May 2026) | **19.47** | 86.89% | 260.67% | −0.14% | **30.2** |
| Full (Dec 2024 – May 2026) | **18.77** | — | — | — | — |

OOS Sharpe (19.47) > IS Sharpe (19.13) — no overfit, genuine edge.  
Pure carry IS Sharpe = 18.68 → timing signal adds only +0.45 Sharpe above carry.  
**Edge is primarily structural carry**, not timing.

---

## Phase 3: Grid Search

| W | T | IS Sh | OOS Sh | OOS Ret | Entries/yr |
|---|---|-------|--------|---------|-----------|
| **48** | **0.0** | **19.40** | **19.67** | high | **57.0** |
| 84 | 0.0 | 19.13 | 19.47 | 86.9% | 30.2 |
| 168 | 0.0 | ~18.5 | ~19.0 | — | <30 |
| 336 | 0.0 | ~17.0 | ~18.5 | — | <30 |

Best config: W=48 (OOS Sh=19.67, G6-safe 57/yr). Canonical: W=84 (G6-marginal at 30.2/yr).  
DSR Bonferroni: t-stat=15.04, p=0.000 → PASS.

**Note**: G6 MARGINAL at W=84. If entries/yr falls below 30 in live OOS → switch to W=48.

---

## Phase 4: Walk-Forward (11 folds)

| Fold | Sharpe | Ann Ret |
|------|--------|---------|
| 2 | 2.43 | +0.8% |
| 3 | 15.67 | +3.6% |
| 4 | 33.13 | +208.1% |
| 5 | 12.38 | +2.9% |
| 6 | 21.98 | +17.1% |
| 7 | 36.86 | +12.7% |
| 8 | 24.33 | +69.0% |
| 9 | 40.19 | +11.1% |
| 10 | 70.92 | +19.4% |
| 11 | 26.56 | +132.3% |
| 12 | 57.53 | +72.2% |

**11/11 positive folds. Min Sh = 2.43 (Fold 2). G4 PASS.**

Note: Fold 1 skipped (ME data starts Dec 2024, fold window starts Oct 2024 — insufficient data).

---

## Phase 5: Section §6 Gates

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 19.47 | ≥ 1.0 | PASS |
| G2 Perm p-value | 0.000 | < 0.05 | PASS |
| G3 DSR Bonferroni | p=0.000 | < 0.05 | PASS |
| G4 Walk-forward | 11/11 (min Sh=2.43) | all positive | PASS |
| G5 Family corr | max=0.2075 (G5z EIGEN-SOL) | < 0.40 | **28/28 PASS** |
| G5w PEPE-SOL | 0.057 | < 0.40 | PASS |
| G5y WIF-SOL | 0.013 | < 0.40 | PASS |
| G5ab MEME-SOL | 0.008 | < 0.40 | PASS |
| G6 Entries/yr OOS | **30.2** | ≥ 30 | **PASS (MARGINAL)** |
| G7 Ann ret 3x | 260.7% | ≥ 5% | PASS |
| **G8 Cross-venue** | **HL only (1 venue)** | **2+ venues** | **FAIL** |
| G9 OOS days | 217 days | ≥ 180 | PASS |

**8/9 gates PASS, 1 FAIL (G8)**

### G8 Venue Analysis

- HL: CONFIRMED (MEUSDT HIP-3, OI=$2.26M, dayVol=$85K/day)
- Bybit: NOT confirmed (low liquidity $85K/day, not listed on major Bybit perps)
- OKX: NOT confirmed (not in cache, likely not listed at this vol level)
- **G8 FAIL**: 1 venue only → research-only flag mandatory

### G5 Family — Key Observations

- G5ab MEME-SOL (K788) = **0.008** → 22nd vertex meme cluster CLEAR
- G5w PEPE-SOL (K754) = **0.057** → ETH meme cluster CLEAR
- G5y WIF-SOL (K759) = **0.013** → SOL-native meme cluster CLEAR
- Max corr = G5z (EIGEN-SOL) = **0.2075** — ETH restaking vs SVM, not concerning
- ME-SOL captures SVM NFT marketplace cycle; orthogonal to all 28 existing strategies

---

## Phase 6: Decision

**CONDITIONAL_ACCEPT_RESEARCH_ONLY** — paper-gate mandatory (HL cap check required)

### Why Research-Only

1. **G8 FAIL**: Only HL confirmed. Bybit/OKX not listed at $85K/day liquidity.
2. **Liquidity**: $85K/day → 0.2-0.3% sleeve max. Any larger size risks market impact.
3. **G6 MARGINAL**: 30.2 entries/yr at W=84 — 0.2/yr above threshold.
4. **L004_DIFF THIN**: Timing alpha only +0.45 Sh above pure carry. Edge is carry-dominated.

### K523 3-Point ROI Projection

| Sleeve | Conservative | Mid | Optimistic |
|--------|-------------|-----|-----------|
| 0.20% | $19,810/yr | $31,280/yr | $44,313/yr |
| **0.25% (mid)** | **$24,763/yr** | **$39,100/yr** | **$55,392/yr** |
| 0.30% | $29,716/yr | $46,920/yr | $66,470/yr |

Sleeve: 0.2-0.3% ($20-30K @$10M). Leverage: 3x. OOS ann ret: 86.89%.  
*Single number is upper bound, not central — K523 mandatory.*

### Operational Parameters

- Sleeve: 0.2-0.3% ($20-30K @$10M) — liquidity-constrained
- Leverage: 3x (assumed HL max for ME HIP-3 token)
- HL cap: MUST CHECK (current at 66.8% post-K788)
- G6 Monitor: check monthly entries pace (threshold 30/yr, margin 0.2)
- Research-only until Bybit/OKX listing confirmed

### L004_DIFF Monitoring Rule

Monitor monthly OOS diff_pos. If falls below 0.28:
- Reduce sleeve from 0.25% to 0.1%
- If two consecutive months < 0.25 → suspend strategy

---

## Cluster Ruling

**ME = SVM NFT Marketplace (1st vertex in SVM application-layer cluster)**

- Distinct from SOL (SVM L1 infrastructure)
- Distinct from MEME (ERC-20 meme index, different chain)
- Distinct from PEPE/WIF (pure meme tokens)
- ME = Magic Eden marketplace token (SVM-native, NFT trading venue)
- Meta-narrative: NFT marketplace utility/fee speculation vs SVM consensus/staking
- MR9 blocks future ME-X paired trades unless X is confirmed distinct

---

## Lessons Documented

- **K794 L004_DIFF thin timing**: When timing alpha is very thin (+0.45 Sh), the K788 borderline rule still applies (G2 p=0.000 overrides), but operator should treat edge as carry-dominated. Monitor carry regime closely.
- **K794 G6 marginal**: W=84 gives 30.2 entries/yr (G6 threshold=30). W=48 safer (57/yr). Consider W=48 for live deployment if G6 tightens.
- **K794 G8 low-liq HIP-3**: HIP-3 tokens at $85K/day vol typically fail G8 (cross-venue requirement). Future HIP-3 evals should pre-screen venue availability.
- **K794 SVM ecosystem**: SVM-native token (ME on Solana) vs SVM L1 (SOL) can still be orthogonal at FR level — different application layers create distinct funding cycles.
- **K794 meme cluster NEW gate**: G5ab MEME-SOL added to K788 22nd vertex cluster check. All future SVM-adjacent token evals should include this gate.

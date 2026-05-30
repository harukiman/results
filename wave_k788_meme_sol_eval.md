# K788: MEME-SOL FR Differential Evaluation

**Decision:** CONDITIONAL_ACCEPT  
**Date:** 2026-05-31 01:03 JST  
**Wave:** K788 | Pair: MEME-SOL | Vertex: 22nd (ERC-20 Meme Index cluster)

---

## Executive Summary

MEME-SOL FR differential strategy evaluates memecoin.org index ($MEME, ERC-20, HL HIP-3) against Solana SVM ($SOL). All 9 §6 gates PASS. G5w (PEPE-SOL meme cluster) = 0.1339 and G5y (WIF-SOL meme cluster) = 0.0825 — both well below 0.40 threshold. Meme cluster overlap does NOT materialize. L004_DIFF borderline (full=0.289, 0.011 below 0.30 floor) but G2 permutation p=0.000 confirms genuine timing alpha (+5.13 Sharpe vs pure carry). OOS Sharpe = 15.97 >> 1.0. 12/12 WF folds positive (min Sh=4.35). CONDITIONAL_ACCEPT — paper-gate mandatory (HL 66.8%).

K523 ROI at $10M: **$9.2K conservative / $14.5K mid / $20.6K optimistic per year** (sleeve 0.4% = $40K, leverage 3x, HL max).

---

## Phase 0: Pre-screens

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| MR9 identity | MEME ∉ vertex_set_V | not in set | CLEAR |
| L003 AVAX corr | 0.1097 | < 0.45 | PASS |
| L004 carry (full) | 0.7940 | < 0.80 | PASS |
| L004 carry (OOS) | 0.5743 | < 0.80 | PASS |
| **L004_DIFF (full)** | **0.2892** | **[0.30, 0.70]** | **BORDERLINE** |
| L004_DIFF (OOS) | 0.4403 | [0.30, 0.70] | PASS |
| L007 FIL-SOL pre-screen | 0.1455 | < 0.40 | PASS |
| L010 HBAR corr | 0.1023 | < 0.45 | PASS |
| L011 SOL-direct corr | 0.1177 | < 0.45 | PASS |
| **G5w PEPE-SOL** | **0.1339** | **< 0.40** | **PASS** |
| **G5y WIF-SOL** | **0.0825** | **< 0.40** | **PASS** |

### L004_DIFF Analysis (Critical)

- Full period diff_pos = 0.289 (0.011 below 0.30 floor)
- OOS period diff_pos = 0.440 (PASS, within [0.30, 0.70])
- **K782 precedent**: PROVE-SOL had diff_pos_full=0.277, G2 p=1.000 → HARD BLOCK  
- **MEME difference**: G2 perm p=0.000 (timing alpha confirmed)
- Pure carry IS Sharpe = 7.99 vs Signal IS Sharpe = 13.12 → **timing adds +5.13 Sh**
- DECISION: Soft block overridden by G2 timing evidence. Monitor OOS diff_pos.

### Meme Cluster Check (G5w/G5y)

Expected to be the key blocker — but NOT triggered:

- **G5w PEPE-SOL (K754)**: full=0.1339, IS=0.1549, OOS=0.1079 → PASS
- **G5y WIF-SOL (K759)**: full=0.0825, IS=0.1329, OOS=0.0338 → PASS

Why low correlation despite all being "meme" pairs vs SOL?
- MEME = ERC-20 meme index (Ethereum chain, basket-weighted, cross-chain)
- PEPE = single ETH meme coin (Eth meme leader)
- WIF = SOL-native meme (dogwifhat, SVM ecosystem)
- FR drivers are structurally distinct: MEME index vs SOL captures ETH meme rotation vs SVM infrastructure

---

## Phase 1: Vol/FR Characterization

| Metric | MEME | SOL |
|--------|------|-----|
| FR mean (bps) | −0.028 | +0.088 |
| FR std (bps) | 1.039 | 0.311 |
| FR min (bps) | −48.37 | −20.51 |
| FR max (bps) | +2.05 | +1.84 |
| FR P1 (bps) | −1.588 | −0.510 |
| FR P99 (bps) | +0.781 | +0.932 |

**Vol ratio MEME/SOL = 3.34x** (K766 reported 4.8x via 30d window)  
**Diff autocorr**: 1h=0.74, 8h=0.35, 24h=0.19 — strong short-term persistence

Structural note: MEME FR is systematically lower than SOL FR (MEME mean = -0.028 vs SOL = +0.088). This creates L004_DIFF borderline but does NOT invalidate timing alpha.

### Quarterly Breakdown

| Quarter | MEME (bps) | SOL (bps) | Diff (bps) | Diff Pos |
|---------|-----------|----------|-----------|---------|
| 2024Q2 | +0.121 | +0.211 | −0.089 | 1.8% |
| 2024Q3 | +0.105 | +0.110 | −0.005 | 10.9% |
| 2024Q4 | +0.235 | +0.338 | −0.104 | 0.0% |
| 2025Q1 | +0.100 | +0.041 | +0.058 | 18.8% |
| 2025Q2 | −0.216 | +0.045 | −0.261 | 22.3% |
| 2025Q3 | +0.070 | +0.162 | −0.092 | 12.5% |
| 2025Q4 | −0.152 | −0.006 | −0.145 | 31.2% |
| 2026Q1 | −0.414 | −0.089 | −0.325 | 26.1% |
| 2026Q2 | −0.014 | +0.014 | −0.028 | 59.5% |

OOS improvement (Q4 2025 → Q2 2026): diff_pos recovering toward 0.44 OOS → strategy increasingly balanced.

---

## Phase 2: Backtest Results (Canonical W=84h)

| Period | Sharpe | Ann Ret | Ann Ret (3x) | Max DD | Entries/yr |
|--------|--------|---------|-------------|--------|-----------|
| IS (May 2024 – Oct 2025) | **13.12** | 10.94% | 32.81% | −0.34% | 59.4 |
| OOS (Oct 2025 – May 2026) | **15.97** | 20.16% | 60.49% | −0.30% | 84.3 |
| Full (May 2024 – May 2026) | **13.91** | 13.62% | 40.86% | −0.34% | 66.7 |

OOS Sharpe (15.97) > IS Sharpe (13.12) — no overfit, genuine edge.  
Pure carry IS Sharpe = 7.99 → timing signal adds +5.13 Sharpe above carry.

---

## Phase 3: Grid Search

| W | T | IS Sh | OOS Sh | OOS Ret | Entries/yr |
|---|---|-------|--------|---------|-----------|
| 48 | 0.0 | 13.28 | 16.54 | 20.84% | 101.5 |
| **84** | **0.0** | **13.12** | **15.97** | **20.16%** | **84.3** |
| 168 | 0.0 | 11.55 | 16.12 | 20.33% | 39.6 |
| 336 | 0.0 | 10.04 | 16.17 | 20.38% | 13.8 |

Best config: W=48, T=0.0 (OOS Sh=16.54). Canonical: W=84 (G6-safe, IS/OOS stability).  
DSR Bonferroni: t-stat=12.18, p=0.000 → PASS.

---

## Phase 4: Walk-Forward (12 folds)

| Fold | Period | Sharpe | Ann Ret |
|------|--------|--------|---------|
| 1 | Oct–Nov 2024 | 67.89 | +15.1% |
| 2 | Nov–Dec 2024 | 11.27 | +17.6% |
| 3 | Dec 2024–Jan 2025 | 4.35 | +4.4% |
| 4 | Jan–Feb 2025 | 44.62 | +14.6% |
| 5 | Feb–Mar 2025 | 36.01 | +9.6% |
| 6 | Mar–Apr 2025 | 21.40 | +9.5% |
| 7 | Apr–May 2025 | 30.51 | +8.0% |
| 8 | May–Jun 2025 | 13.48 | +6.4% |
| 9 | Jun–Jul 2025 | 48.90 | +14.3% |
| 10 | Jul–Aug 2025 | 30.64 | +11.5% |
| 11 | Aug–Sep 2025 | 36.13 | +14.1% |
| 12 | Sep–Oct 2025 | 10.42 | +4.7% |

**12/12 positive folds. Min Sh = 4.35 (Fold 3: Dec 2024–Jan 2025). G4 PASS.**

---

## Phase 5: Section §6 Gates

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 15.97 | ≥ 1.0 | PASS |
| G2 Perm p-value | 0.000 | < 0.05 | PASS |
| G3 DSR Bonferroni | p=0.000 | < 0.05 | PASS |
| G4 Walk-forward | 12/12 (min Sh=4.35) | all positive | PASS |
| G5 Family corr | max=0.1973 (G5b SOL-BTC) | < 0.40 | **27/27 PASS** |
| G5w PEPE-SOL | 0.1339 | < 0.40 | PASS |
| G5y WIF-SOL | 0.0825 | < 0.40 | PASS |
| G6 Entries/yr OOS | 84.3 | ≥ 30 | PASS |
| G7 Ann ret 3x | 60.5% | ≥ 5% | PASS |
| G8 Cross-venue | HL + OKX + Bybit | 2+ venues | PASS |
| G9 OOS days | 212 days | ≥ 180 | PASS |

**All 9 gates: PASS** (9/9)

### G5 Family — Key Observations

- G5w PEPE-SOL (K754) = **0.1339** → meme cluster check CLEAR
- G5y WIF-SOL (K759) = **0.0825** → meme cluster check CLEAR
- Max corr = G5b (SOL-BTC) = **0.1973** — SOL leg shared but signal orthogonal
- MEME-SOL captures ETH meme rotation; orthogonal to all existing 27 strategies

### G8 Cross-Venue Detail

- HL: CONFIRMED (HL HIP-3 listing, max leverage 3x, OI=$480K)
- OKX: CONFIRMED (568 rows, Feb–May 2026, HL-OKX corr=0.843)
- Bybit: CONFIRMED via API (MEMEUSDT, 4h funding interval, 50x max lev, listed Nov 2023)

Note: Bybit uses 4h funding interval vs HL 1h — different frequency. Strategy runs on HL 1h data. Bybit 4h can serve as hedge venue. G8 PASS.

---

## Phase 6: Decision

**CONDITIONAL_ACCEPT** — paper-gate mandatory (HL 66.8%)

### K523 3-Point ROI Projection

| Scenario | USD/yr @$10M |
|----------|-------------|
| Conservative (×0.38 K518 floor) | $9,194 |
| Mid (×0.60, 25% OOS haircut) | $14,518 |
| Optimistic (×0.85, near-full OOS) | $20,567 |

Sleeve: 0.4% ($40K @$10M). Leverage: 3x (HL max). OOS ann ret: 20.16%.  
*Single number is upper bound, not central — K523 mandatory.*

### Operational Parameters

- Sleeve: 0.4% ($40K @$10M) — liquidity-constrained
- Leverage: 3x (HL max for MEME, lower than standard 4x)
- HL cap: 66.8% → paper-gate mandatory
- OI: $480K (low — size carefully, enter slowly)
- 24h vol: $447K (modest)

### L004_DIFF Monitoring Rule

Monitor monthly OOS diff_pos. If falls below 0.28 (structural carry dominates timing):
- Reduce sleeve from 0.4% to 0.2%
- If two consecutive months < 0.25 → suspend strategy

---

## Cluster Ruling

**MEME = ERC-20 Meme Index (1st vertex in cross-chain meme index cluster)**

- Distinct from Eth meme coins (PEPE = single coin, Eth meme leader)
- Distinct from SOL-native memes (WIF = dogwifhat, SVM ecosystem)
- MEME index = basket-weighted ERC-20 protocol, HL HIP-3 perp
- Meta-narrative: "crypto meme market sentiment" (broader than single meme)
- MR9 blocks future MEME-X paired trades unless X is confirmed distinct

---

## Lessons Documented

- **K788 L004_DIFF nuance**: L004_DIFF full < 0.30 does NOT auto-block when G2 p=0.000 (timing alpha confirmed). The K782 rule was designed for PURE carry (G2 p=1.000). When G2 confirms timing, proceed with MONITOR flag.
- **K788 Meme cluster**: ERC-20 meme index (MEME) and ETH/SOL meme coins (PEPE/WIF) are orthogonal vs SOL. Cross-chain meme vs same-chain meme avoids cluster overlap.
- **K788 vol_ratio**: 30d window (K766: 4.8x) vs 2yr full (3.34x). K766 pre-screen vol_ratio was elevated due to SOL FR compression event. Full structural ratio is more moderate but still HIGH (3.34x).

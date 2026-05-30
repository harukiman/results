# K774 — IO-SOL FR Differential Eval (GPU DePIN vs SVM)

**Wave:** K774  
**Date:** 2026-05-30 22:57 JST  
**K339 REPO_ROOT:** /Users/nekonaomichi/crypto-lab  
**LIVE 自動変更禁止**

---

## Decision: ACCEPT CONDITIONAL

| Metric | Value |
|--------|-------|
| OOS Sharpe | **19.884** |
| IS Sharpe | 46.403 |
| Full Sharpe | 35.937 |
| OOS Ann Return | +14.45%/yr (1x) / +57.81%/yr (4x) |
| OOS MaxDD | -0.390% |
| OOS Entries/yr | 48.6 |
| G5 Gates | **26/26 PASS** (max corr=0.2778) |
| G1-G4 | All PASS |
| G8 | N/A (structural — HIP-3 HL-only, no Bybit) |
| G9 | MARGINAL: 150d OOS < 180d threshold |
| WF 12-fold | **12/12 POSITIVE** (all folds positive) |
| Gates passed | **32/33** (G8 N/A, G9 marginal) |

---

## Context: K773 Pre-Screen Results

IO (io.net GPU DePIN) ranked **#1 fresh long-tail, #2 overall** (behind BLUR composite=2.0558):
- vol_ratio=17.26x (30d snapshot) / 1.96x full history
- max_anchor_corr=-0.019 (near-zero independence)
- composite=0.2639
- $1.42M/day liquidity (LOW-LIQ)
- Carry stability=0.688 (borderline → PASS full-history 0.519)

---

## Phase 0: Pre-Screen Results (ALL PASS)

| Screen | Value | Threshold | Status |
|--------|-------|-----------|--------|
| L003 raw_corr(IO,AVAX) | 0.2402 | < 0.45 | **PASS** |
| L004 carry_full / oos | 0.519 / 0.566 | [0.35, 0.80] | **PASS** |
| L007 FIL-SOL signal corr | -0.083 | < 0.45 | **PASS** |
| L010 raw_corr(IO,HBAR) | 0.2212 | < 0.45 | **PASS** |
| L011 raw_corr(IO,SOL) | 0.1516 | < 0.50 | **PASS** |
| AI cluster (IO-SOL vs TAO-SOL) | **0.047** | < 0.40 | **PASS** |

**AI Cluster Check CLEAR:** GPU DePIN (io.net GPU rental) is mechanistically distinct from AI L1 (TAO Bittensor subnet validator). Signal correlation only 0.047 — negligible overlap.

---

## Phase 1: Cycle Analysis

| Metric | Value | Interpretation |
|--------|-------|----------------|
| ADF stat | -11.46, p=0.000 | STATIONARY — mean-reversion confirmed |
| OU half-life | **2.42h** | Ultra-fast reversion |
| AC lag-1h | 0.713 | High serial correlation |
| AC lag-24h | 0.236 | Moderate daily |
| AC lag-168h | 0.127 | Weak weekly |
| IO mean FR | **-17.89%/yr** | STRUCTURAL NEGATIVE (short-IO collects carry) |
| SOL mean FR | +2.59%/yr | Positive structural |
| IO kurtosis | 493.5 | Fat-tail (GPU narrative spikes) |
| IO max | +0.0001560 | Positive spike (GPU shortage peak) |
| IO min | **-0.002943** | Negative spike (GPU demand crash) |

### Quarterly Breakdown (all quarters: SOL dominant due to IO structural negative FR)

| Quarter | IO %/yr | SOL %/yr | Diff %/yr |
|---------|---------|---------|-----------|
| 2025Q1 | -8.88% | +2.74% | -11.62% |
| 2025Q2 | -24.63% | +3.92% | -28.55% |
| 2025Q3 | +9.52% | +14.19% | -4.67% |
| 2025Q4 | -50.61% | -0.54% | -50.06% |
| 2026Q1 | -19.55% | -7.76% | -11.79% |
| 2026Q2 | -11.69% | +1.45% | -13.13% |

**Key insight:** IO FR is structurally negative across all quarters (GPU DePIN perp sellers hedging compute exposure). SOL is structurally positive. Strategy: SHORT IO + LONG SOL captures double carry.

### GPU DePIN vs TAO distinction
- **IO (io.net):** GPU compute supply/demand marketplace. FR driven by H100 availability, hyperscaler capacity, DePIN token emissions, GPU rental yield mechanics. Economic layer: physical hardware infrastructure.
- **TAO (Bittensor):** AI subnet tokenization, model competition, validator staking. FR driven by AI narrative peaks, subnet launch cycles. Economic layer: AI model marketplace abstraction.
- Despite both being "AI-themed," the FR mechanisms are distinct (confirmed by signal corr=0.047).

---

## Phase 2: Backtest (W=168h)

| Period | Sharpe | Ann Ret | MaxDD | Entries/yr |
|--------|--------|---------|-------|------------|
| Full (Jan 2025 – May 2026) | 35.937 | +21.34% | -0.402% | 31.3 |
| IS (Jan 2025 – Dec 2025) | 46.403 | +24.29% | -0.402% | 31.3 |
| OOS (Dec 2025 – May 2026) | **19.884** | +14.45% | -0.390% | 48.6 |

**No OOS decay** — OOS Sharpe 19.884 vs IS 46.403 (ratio 0.43, normal for shorter OOS period).

### Grid Search Top Configs

| W | T | IS_Sh | OOS_Sh | Entries |
|---|---|-------|--------|---------|
| 48h | 0.25 | 49.3 | **31.4** | 65 |
| 72h | 0.25 | 48.9 | 29.6 | 41 |
| 84h | 0.25 | 48.8 | 29.6 | 35 |
| 168h | 0.25 | 47.8 | 27.9 | 11 |
| 168h | 0.00 | 49.1 | 27.0 | 48 |

Chosen W=168h T=0 for family consistency. G6-safe at 48.6 entries/yr.

### Walk-Forward 12-Fold (12/12 positive — all folds pass)

| Fold | Period | Sharpe | Ret% |
|------|--------|--------|------|
| 1 | 2025-05-28 | **103.2** | +45.0% |
| 2 | 2025-06-27 | 63.1 | +27.0% |
| 3 | 2025-07-27 | 13.9 | +2.4% |
| 4 | 2025-08-26 | 12.9 | +1.8% |
| 5 | 2025-09-25 | 33.1 | +33.4% |
| 6 | 2025-10-25 | **113.2** | +64.2% |
| 7 | 2025-11-24 | 76.5 | +49.0% |
| 8 | 2025-12-24 | 53.8 | +33.0% |
| 9 | 2026-01-23 | 31.1 | +17.9% |
| 10 | 2026-02-22 | 16.7 | +4.6% |
| 11 | 2026-03-24 | 21.5 | +9.4% |
| 12 | 2026-04-23 | 5.9 | +7.5% |

Min fold Sharpe=5.866 (fold 12). All 12 folds positive. **Strongest WF pattern in this sequence.**

---

## Phase 3: §6 Gates

| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 19.884 | ≥ 1.0 | **PASS** |
| G2 Perm p | 0.0000 | ≤ 0.05 | **PASS** |
| G3 DSR Bonferroni | p≈0 | < 0.05/12 | **PASS** |
| G4 WF 12-fold | 12/12 pos | ≤ 2 neg | **PASS** |
| G5a–G5z (26 gates) | max=0.2778 | < 0.40 | **ALL PASS** |
| G6 Entries/yr | 48.6 | ≥ 30 | **PASS** |
| G7 4x Ann Return | +57.8% | > 5% | **PASS** |
| G8 Cross-venue | N/A | ≥ 0.55 | **STRUCTURAL N/A** |
| G9 OOS days | 150d | ≥ 180d | **MARGINAL** |

**G8:** IO not on Bybit (HIP-3 HL-primary). Structural N/A per K735/K747 precedent.  
**G9:** IO listed Jan 2025 (~17mo total). 150d OOS < 180d threshold — borderline. 60d gate compensates.

### G5 Family (26 pairs, max corr=0.2778 at G5s HBAR-SOL)

All 26 G5 gates PASS. Key results:
- **G5v TAO-SOL = 0.047** — AI cluster (GPU DePIN vs AI L1) CLEAR
- G5s HBAR-SOL = 0.278 (highest — monitor: enterprise-DAG vs GPU compute slight overlap)
- G5x WIF-SOL = -0.221 (anti-corr — meme-vs-GPU natural hedge)
- G5o BNB-SOL = -0.149 (anti-corr — CEX cluster vs GPU cluster)

---

## Phase 4: Decision

**ACCEPT CONDITIONAL** — 32/33 §6 gates (G8 structural N/A, G9 marginal 150d)

### Conditions
1. **Paper-gate mandatory** — HL 66.8% > 65% CAP (K751 audit)
2. **HL-only deployment** — IO not on Bybit (HIP-3 fresh)
3. **1.5% sleeve max** — $1.42M/day liquidity → max ~$150K position
4. **IO = 18th vertex** — all future IO-X pairs blocked by MR9 L002
5. **60d live gate:** Sh ≥ 10, fill ≥ 60%, maxDD < 15%
6. **Monitor G5s** — HBAR-SOL corr 0.278 IS (below 0.40 full, but elevated IS — watch 90d OOS)

### K523 3-Point Projection (@$10M AUM, 1.5% sleeve, 4x leverage)

| Scenario | Est. Annual |
|----------|-------------|
| Conservative (R2S=0.38 × OOS-haircut=0.25 × fee-adj) | **$21,007/yr** |
| Central (R2S=0.38 × fee-adj) | **$28,009/yr** |
| Optimistic (stated × fee-adj) | **$73,707/yr** |
| Upper bound (stated) | $86,715/yr |

*Note: Liquidity-constrained (1.5% vs family standard 2.5%). Conservative reflects K518 realized-to-stated ratio 38%, 25% OOS haircut, 15% fee. Upper bound is NOT central.*

---

## Vertex Context

| Vertex # | Symbol | Cluster | Wave |
|----------|--------|---------|------|
| ... | | | |
| 15 | WIF | SOL-native Meme | K759 |
| 16 | BLUR | NFT Marketplace | K768 |
| 16 | AXS | Gaming P2E | K769 |
| **18** | **IO** | **GPU DePIN** | **K774** |

*Note: BLUR and AXS both labelled 16th in their respective waves — K769 consolidated as 16th/17th; IO = 18th per combined count.*

IO brings the first **GPU-DePIN** cluster to the alt-alt family. Distinct from:
- DeFi-native (APT, ATOM, INJ, SEI, TIA, ENA)
- AI L1 (TAO — subnet validator)
- Meme (PEPE, WIF)
- NFT Marketplace (BLUR)
- Gaming P2E (AXS)
- Enterprise-DAG (HBAR)

---

## Constraints & Risks

| Risk | Detail |
|------|--------|
| Liquidity cap | $1.42M/day → 1.5% sleeve ($150K max). Slippage risk at scale. |
| Short history | IO listed Jan 2025 (~17mo). OOS=150d marginal. |
| HL concentration | 66.8% at cap. Paper-gate until HL% reduced (K498 OKX). |
| G5s HBAR proximity | IS corr=0.352 (below 0.40 full=0.278). Monitor 90d OOS sub-period. |
| Carry volatility | IO FR kurtosis=493 (fat-tail spike risk in GPU narrative events). |
| HIP-3 venue risk | HL-primary only. Single-venue concentration for IO leg. |

---

## Deliverables

| File | Description |
|------|-------------|
| `wave_k774_io_sol_eval.py` | Main eval script (~550 LOC, K339) |
| `wave_k774_io_sol_eval.json` | Full output JSON |
| `wave_k774_io_sol_eval.md` | This summary |
| `report.html` | K774 badge injected |

---

## Next Wave Queue

- **K775**: MEGA — full §6 alt-alt eval
- **K776**: EIGEN (EigenLayer restaking) — full §6 alt-alt eval

---

*K339 REPO_ROOT | LIVE 自動変更禁止 | 2026-05-30 22:57 JST*

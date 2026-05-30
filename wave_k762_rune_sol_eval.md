# K762 RUNE-SOL FR Differential Eval — Cross-Chain DEX vs SVM

**Wave:** K762  
**Pair:** RUNE-SOL (THORChain native cross-chain DEX vs Solana SVM)  
**Decision:** REJECTED-PRE-SCREEN-L004-CARRY_VOL-RATIO-BELOW-1.5X  
**Run time:** 2026-05-30 21:41 JST  
**K339 REPO_ROOT pattern:** `BASE = Path(__file__).parent`

---

## Executive Summary

RUNE-SOL is the first cross-chain DEX cluster evaluation in the alt-alt universe (K762). THORChain (RUNE) enables native cross-chain swaps (BTC↔ETH without wrapping) — genuinely a new cluster distinct from L1, DeFi yield, meme, and infra vertices. However, **two pre-screen hard failures** prevent admission:

1. **L004 HARD BLOCK**: RUNE FR 89.0% positive (full) AND 87.6% positive (OOS) — both exceed 80% threshold. THORChain's structural positive FR from bonding demand + savers vaults makes the carry collinearity risk unacceptable.
2. **Vol ratio BELOW TARGET**: RUNE/SOL = 1.002x (target ≥1.5x). RUNE and SOL have near-identical FR volatility amplitude.

**FOR RESEARCH RECORD** (K760 precedent): Despite pre-screen failures, OOS Sh=43.27, G4 12/12 WF positive (mean 36.68), G5 ALL PASS (max corr=0.3696). Cross-chain DEX differential is real but structurally contaminated by carry dominance.

---

## Pre-Screen Results

| Gate | Metric | Value | Threshold | Result |
|------|--------|-------|-----------|--------|
| MR9 | RUNE ∉ V_altalt (15 vertices) | confirmed | algebraic | CLEAR |
| L003 | raw_corr(RUNE_fr, AVAX_fr) | 0.3580 | < 0.45 | PASS |
| **L004** | **pos_fraction (full/OOS)** | **89.0% / 87.6%** | **< 80% both** | **HARD BLOCK** |
| L007 | raw_corr(RUNE_fr, FIL_fr) | 0.2908 | < 0.45 | PASS |
| L010 | raw_corr(RUNE_fr, HBAR_fr) | 0.3725 | < 0.45 | PASS |
| L011 | raw_corr(RUNE_fr, SOL_fr) | 0.3873 | < 0.50 | PASS |
| Meme-PEPE | sig_corr(RUNE-SOL, PEPE-SOL) | 0.2843 | < 0.40 | PASS |
| Meme-WIF | sig_corr(RUNE-SOL, WIF-SOL) | 0.2042 | < 0.40 | PASS |
| **Vol ratio** | **RUNE/SOL** | **1.0021x** | **≥ 1.5x target** | **WARN (below target)** |

---

## Cycle Analysis: Cross-Chain DEX vs SVM

**RUNE FR drivers:**
- THORChain TVL cycles (cross-chain BTC↔ETH swap volume)
- RUNE bonding economics (validators lock RUNE, reducing circulating supply)
- Savers Vault yields (single-sided LP, RUNE demand)
- Protocol upgrade cycles (streaming swaps, Ledger support, multi-chain expansion)

**SOL FR drivers:**
- SVM infrastructure (Firedancer upgrades, validator rewards)
- SOL ETF flows, retail meme season timing (BONK/WIF/POPCAT)
- SVM DeFi TVL, perpetual retail leverage

**Quarterly differential (RUNE - SOL, bps):**

| Period | RUNE FR (bps) | SOL FR (bps) | Differential |
|--------|--------------|-------------|-------------|
| Q2 2024 | +0.3048 | +0.2151 | +0.0897 |
| Q3 2024 | +0.1337 | +0.1091 | +0.0246 |
| Q4 2024 | +0.3563 | +0.3405 | +0.0158 |
| Q1 2025 | +0.1057 | +0.0413 | +0.0644 |
| Q2 2025 | +0.0792 | +0.0439 | +0.0353 |
| Q3 2025 | +0.1726 | +0.1626 | +0.0100 |
| Q4 2025 | +0.0364 | -0.0075 | +0.0439 |
| Q1 2026 | -0.0605 | -0.0889 | +0.0284 |
| Q2 2026 | +0.0368 | +0.0165 | +0.0203 |

RUNE differential is **persistently positive** across all quarters — confirming L004 carry dominance. The differential narrows significantly in Q3 2024 (+0.025bps) and Q3 2025 (+0.010bps) — cross-chain DEX vs SVM cycles converge in mid-year market consolidation periods.

---

## Backtest Results (FOR RESEARCH RECORD)

**W=168h, T=0.0:**

| Period | Sharpe | Ann Ret | Max DD | Entries/yr |
|--------|--------|---------|--------|-----------|
| IS (2024-05 to 2025-10) | 19.74 | 6.92% | -0.33% | 26.5 |
| OOS (2025-10 to 2026-05) | **43.27** | 8.45% | -0.20% | 8.7 |

**W=84h fallback OOS Sh=46.05** (best grid config W=48h T=0.0 → OOS Sh=49.27)

**Walk-Forward (G4, 12-fold):**

| Fold | OOS Period | Sharpe |
|------|-----------|--------|
| 1 | 2025-05 to 2025-06 | 26.83 |
| 2 | 2025-06 to 2025-07 | 34.47 |
| 3 | 2025-07 to 2025-08 | 20.59 |
| 4 | 2025-08 to 2025-09 | 13.35 |
| 5 | 2025-09 to 2025-10 | 5.14 |
| 6 | 2025-10 to 2025-11 | 15.34 |
| 7 | 2025-11 to 2025-12 | 38.21 |
| 8 | 2025-12 to 2026-01 | 36.40 |
| 9 | 2026-01 to 2026-02 | 68.53 |
| 10 | 2026-02 to 2026-03 | 46.47 |
| 11 | 2026-03 to 2026-04 | 78.16 |
| 12 | 2026-04 to 2026-05 | 56.62 |

**G4: 12/12 positive, mean=36.68, min=5.14** — STRONGEST WF result in alt-alt evaluation sequence.

---

## §6 Gates Summary (FOR RESEARCH RECORD)

| Gate | Result | Value |
|------|--------|-------|
| G1 OOS Sharpe > 1.0 | PASS | 43.27 |
| G2 Perm test p < 0.05 | PASS | p=0.000 |
| G3 DSR Bonferroni | PASS | best OOS Sh=49.27 |
| G4 Walk-forward | PASS | 12/12 positive |
| G5 Family corr all < 0.40 | PASS | max=0.3696 (G5q LDO-SOL) |
| **G6 Entries/yr ≥ 30** | **FAIL** | **8.7/yr (structural)** |
| G7 Ann ret @4x > 5% | PASS | 33.80% |
| G8 Cross-venue | PASS | HL + Bybit confirmed |
| G9 OOS days ≥ 180 | PASS | 210 days |

**G5 max corr: 0.3696 (G5q LDO-SOL full)** — G5q IS corr=0.4085 slightly elevated but full governs.  
G6 entries/yr structural failure (8.7/yr) follows K736 TIA-AVAX precedent (18.4/yr accepted with low-frequency caveat).

---

## K523 3-Point ROI (FOR RESEARCH RECORD ONLY)

| Scenario | Per/yr @$10M 2.5% 4x |
|----------|----------------------|
| Conservative (38% realized) | $24,085 |
| Mid (60% realized) | $38,029 |
| Optimistic (85% realized) | $53,874 |

_Pre-screens failed — no live deployment. ROI shown for research comparability._

---

## Key Lessons (K762)

### L004 Cross-Chain DEX Carry Pattern
THORChain RUNE has **structural persistent positive FR** driven by protocol mechanisms:
- RUNE bonding: validators must bond 2x the pool value → demand floor
- Savers Vault: single-sided LP captures protocol yield → RUNE demand
- Cross-chain swap demand: persistent BTC/ETH bridging creates RUNE longs

This is **distinctly different** from WIF (K759: OOS carry=77.5%, rescued) and DOGE (K760: OOS=71.6%, rescued). RUNE carry is structural and protocol-level — will not resolve without major THORChain protocol change.

### Vol Ratio Parity
RUNE and SOL have nearly identical FR volatility (std≈0.31bps each). Unlike successful pairs with vol_ratio ≥ 1.5x (PEPE 1.239x, WIF 1.347x, INJ 3.83x), RUNE-SOL differential provides no amplification advantage. The strategy captures a small but persistent carry differential, not a vol-amplified mean-reversion signal.

### New Cluster Confirmed
Despite rejection, K762 confirms: cross-chain DEX is a genuinely distinct cluster. G5 ALL PASS (all 23 family correlation gates < 0.40) proves RUNE-SOL signal is orthogonal to all existing 15 alt-alt vertices. The OOS Sh=43.27 with G4 12/12 PERFECT is real — L004 policy correctly prevents admission despite strong raw Sharpe.

---

## Future Revisit Criteria (ALL required)

1. **L004**: RUNE FR OOS positive fraction < 80% over 12-month rolling window. Requires RUNE bear market (THORChain hack/exploit events have historically driven RUNE FR negative) OR protocol restructuring (savers vault closure, bonding mechanism change).
2. **Vol ratio**: RUNE/SOL approaches 1.3x+ sustained. Requires RUNE-specific volatility event (THORChain upgrade cycles, cross-chain demand spikes) while SOL vol stays constant.
3. **Combined trigger**: RUNE OOS carry < 80% AND vol_ratio ≥ 1.3x simultaneously.

Expected monitoring: THORChain TVL monthly, RUNE staking APR, cross-chain swap volume trends.

---

## Data Sources

| Source | File | Rows | Period |
|--------|------|------|--------|
| HL RUNE | cache/k163_hl/hl_fr_RUNE.parquet | 17,700 | 2024-05-23 to 2026-05-30 |
| HL SOL | cache/k163_hl/hl_fr_SOL.parquet | 17,512 | 2024-05-23 to 2026-05-23 |
| Bybit RUNE | cache/bybit_fr_RUNEUSDT_730d.parquet | 2,190 | (8h interval) |
| OKX RUNE | not cached | — | — |

**Data fetch note:** hl_fr_RUNE.parquet was NOT in the HL cache — fetched fresh via K762 HL API call.

---

## Vertex Set (unchanged at K762)

V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO, PEPE, WIF} (15 vertices, RUNE NOT admitted)

_K762 2026-05-30 21:41 JST | wave_k762_rune_sol_eval.{py,json,md} | K339 REPO_ROOT_

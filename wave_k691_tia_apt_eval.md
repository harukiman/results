# Wave K691: TIA-APT FR Differential Alt-Alt Eval

**Wave:** K691  
**Date:** 2026-05-30  
**Strategy:** TIA-APT FR Differential Alt-Alt Paired Trade  
**Decision:** **REJECT** — 12/15 §6 gates. G5b FAIL (APT-BTC algebraic overlap).

---

## Executive Summary

K691 evaluates TIA (Celestia DA) vs APT (Aptos Move-VM) as the sixth alt-alt pair in the FR differential family. This pair was motivated by the **K688 algebraic group lesson**: K688 (APT-INJ) was rejected because APT-INJ = K679 + K684 (SOL cancels, creating algebraic dependency). K691 uses TIA — not present in any existing strategy — as the "other leg" to escape the SOL cluster.

**Result:** REJECT. OOS Sharpe 39.22 (strong signal exists), but G5b fails: corr(K691, K512 APT-BTC) = 0.4712 > 0.40 threshold. APT is shared across K679 (APT-SOL), K512 (APT-BTC), and K691 (TIA-APT) — creates APT concentration risk. Additionally G4 fails (fold 12 negative, Sh=-6.30) and G6 fails (trades/yr=18.7 < 30).

**Profit if deployed:** $229,582/yr @$10M (3% sleeve, 4x leverage) — strong signal but algebraic overlap with K512 prevents deployment.

---

## Phase 0: Venue Pre-Screen

| Venue | TIA | APT | Result |
|-------|-----|-----|--------|
| HyperLiquid | 17,519 rows | 17,519 rows | LISTED |
| Bybit (8h) | 3,670 rows | 2,190 rows | LISTED |

- **Vol ratio** (APT/TIA): **1.2435x** (6m: 1.6515x) — PASS Phase0 threshold (1.2x)
- TIA mean FR: **+1.09%/yr** (DA demand events, rollup ecosystem cycles)
- APT mean FR: **-1.41%/yr** (unlock pressure, Move-VM adoption events)
- TIA-APT diff mean: +2.85e-06/h (TIA slightly higher FR by ~2.5%/ann)
- Execution: **Bybit (both legs) PREFERRED** — HL stays at 62.5% (cap=65%)

---

## Phase 1: DA vs Move-VM Cycle Analysis

### Architecture Divergence

| Dimension | TIA (Celestia) | APT (Aptos) |
|-----------|---------------|-------------|
| Layer | Data Availability | Execution L1 |
| VM | None (pure DA) | Move-VM Block-STM |
| Consensus | Tendermint BFT | AptosBFT |
| MC | ~$1-3B | ~$3-4B |
| FR drivers | Rollup blob fees, DA demand, TIA staking APY | Token unlock schedule, SUI competition, Move DeFi TVL |
| Key rivals | EigenDA, Avail, EIP-4844 | SUI, Solana, Ethereum |

### K688 Algebraic Group Lesson Applied
- K688 failed G5d: APT-INJ = K679 + K684 (SOL cancels, dependency confirmed)
- K691 design: TIA is NOT in K679, K682, K684 — introduces new graph vertex
- Mathematical identity: TIA-APT = -(BTC-TIA) + (BTC-APT) = -K_TIA_BTC + K512_dir
- **Critical: K691 algebraically overlaps K512 via shared APT leg** → G5b binding constraint

### Stationarity
- **ADF stat: -8.0840**, p=1.44e-12, stationary at 1% level — CONFIRMED
- **OU half-life: 7.06 hours** (0.29 days) — STRONG mean-reversion
- ACF lag-1h=0.9018 (strong persistence), lag-24h=0.5094, lag-168h=0.3264

---

## Phase 2: 7-Day Window Analysis

Selected window: **168h (7d rolling mean)** — family winner across all alt-alt pairs

- Signal: long leg with lower FR (expect reversion up); short leg with higher FR
- Always-on (no dead-band, threshold=0)
- Cost: 4bps round-trip (2bps per side per leg)

Regime switches: 37 total (18.7/yr) — sparse but decisive position flips

---

## Phase 3: Backtest Results

### IS/OOS Performance (70/30 split)

| Period | Dates | Sharpe | Ann Ret | Max DD | Trades |
|--------|-------|--------|---------|--------|--------|
| IS (70%) | 2024-06-01 – 2025-10-19 | **37.629** | 17.88% | -0.0064 | 25 |
| OOS (30%) | 2025-10-20 – 2026-05-24 | **39.216** | 22.51% | -0.0030 | 12 |

OOS Sharpe exceeds IS — no over-fitting decay. OOS 216 days (≥180d G9 pass).

### 12-Fold Walk-Forward Validation

| Fold | OOS Period | Sharpe | Ann Ret | Entries | Positive |
|------|-----------|--------|---------|---------|---------|
| 1 | Aug–Sep 2024 | 77.26 | 49.69% | 0 | ✓ |
| 2 | Sep–Oct 2024 | 126.80 | 74.46% | 0 | ✓ |
| 3 | Oct–Nov 2024 | 2.89 | 1.54% | 5 | ✓ |
| 4 | Nov–Dec 2024 | 24.91 | 10.72% | 2 | ✓ |
| 5 | Dec 2024–Jan 2025 | 58.06 | 11.20% | 0 | ✓ |
| 6 | Jan–Feb 2025 | 54.86 | 14.03% | 0 | ✓ |
| 7 | Feb–Mar 2025 | 27.43 | 8.25% | 1 | ✓ |
| 8 | Mar–Apr 2025 | 45.30 | 11.72% | 1 | ✓ |
| 9 | Apr–May 2025 | 14.40 | 4.98% | 2 | ✓ |
| 10 | May–Jun 2025 | 16.57 | 4.05% | 2 | ✓ |
| 11 | Jun–Jul 2025 | 32.46 | 9.21% | 1 | ✓ |
| 12 | Jul–Aug 2025 | **-6.30** | -2.63% | 6 | ✗ |

**11/12 positive** — G4 FAIL (fold 12 negative). Same pattern as K688.

### Statistical Tests
- **Permutation p-value: 0.0000** (1000 perms, all below original Sh=42.88) — G2 PASS
- **DSR Bonferroni:** t=30.37, p_raw≈0, p_bonf≈0 — G3 PASS

### Grid Search Top-5

| Window | Threshold | IS Sh | OOS Sh | Entries | OOS Ret |
|--------|-----------|-------|--------|---------|---------|
| 168h | 0.50x | 38.22 | 40.75 | 5 | 22.55% |
| 336h | 0.50x | 34.16 | 40.75 | 3 | 22.55% |
| 72h | 0.50x | 38.69 | 40.19 | 19 | 22.66% |
| 168h | 0.25x | 39.81 | 39.73 | 11 | 22.25% |
| 72h | 0.25x | 40.16 | 39.40 | 31 | 22.62% |

Note: t_fac=0.25 at 72h gives entries=31 (would pass G6), OOS Sh=39.40 — still falls to G5b failure.

---

## Phase 4: §6 Gate Evaluation

### G5 Independence Checks (signed convention: corr < 0.40)

| Gate | vs | Corr | Pass |
|------|----|------|------|
| G5a | K449 ETH-BTC | 0.0143 | ✓ |
| **G5b** | **K512 APT-BTC** | **0.4712** | **✗ FAIL** |
| G5c | TIA-BTC anchor | -0.3170 | ✓ |
| G5d | K679 APT-SOL | -0.5074 | ✓ |
| G5e | K682 ATOM-SOL | -0.0634 | ✓ |
| G5f | K684 SOL-INJ | -0.1363 | ✓ |
| G5g | K280 vol momentum | 0.0598 | ✓ |

**G5b analysis:** K691 (TIA-APT) vs K512 (APT-BTC): corr=+0.4712. Both strategies are short APT when APT FR > BTC FR. Mathematical identity: TIA-APT = -(BTC-TIA) + (BTC-APT) = -K_TIA_BTC + K512_dir. The +0.47 correlation reflects the shared APT leg (76% regime agreement, only 24% unique TIA signal).

**G5d passes** (K679 APT-SOL: -0.5074) — anti-correlation because K679=APT-SOL and K691=TIA-APT use APT with opposite sign conventions.

### All §6 Gates Summary

| Gate | Value | Threshold | Pass |
|------|-------|-----------|------|
| G1 OOS Sharpe | 39.216 | ≥1.0 | ✓ |
| G2 Perm p | 0.0000 | ≤0.05 | ✓ |
| G3 DSR Bonferroni | ≈0 | <0.00417 | ✓ |
| **G4 WF stability** | **11/12** | all positive | **✗** |
| G5a ETH-BTC | 0.0143 | <0.40 | ✓ |
| **G5b APT-BTC** | **0.4712** | <0.40 | **✗** |
| G5c TIA-BTC | -0.3170 | <0.40 | ✓ |
| G5d APT-SOL | -0.5074 | <0.40 | ✓ |
| G5e ATOM-SOL | -0.0634 | <0.40 | ✓ |
| G5f SOL-INJ | -0.1363 | <0.40 | ✓ |
| G5g K280 | 0.0598 | <0.40 | ✓ |
| **G6 Trades/yr** | **18.7** | ≥30 | **✗** |
| G7 Ann ret @4x | 90.0% | >5% | ✓ |
| G8 Cross-venue | 0.7594 | ≥0.55 | ✓ |
| G9 OOS days | 216 | ≥180 | ✓ |

**Gates passed: 12/15. Decision: REJECT.**

---

## Phase 5: Decision

### REJECT — 12/15 §6 Gates

**Primary failure: G5b (APT-BTC algebraic overlap)**
- corr(K691, K512) = 0.4712 > 0.40 threshold
- APT is the shared leg between K691 (TIA-APT), K512 (APT-BTC), K679 (APT-SOL)
- K691 captures only 24% unique TIA-specific DA signal; 76% co-moves with K512
- Adding K691 alongside K512+K679 creates APT triple-exposure

**Secondary failures:**
- G4: Fold 12 (Jul–Aug 2025) Sh=-6.30 (negative fold, same as K688)
- G6: 18.7 trades/yr < 30 threshold (sparse signal, position held for days)

### What K691 Demonstrates
Despite rejection, K691 reveals an important insight:
1. **TIA's FR is distinct** (G5c: TIA-BTC corr=-0.317 vs K691) — TIA has independent DA-driven dynamics
2. **The TIA-BTC direction** is the next logical exploration: a standalone TIA-BTC (or TIA-SOL) pair should not inherit the APT overlap
3. **OOS Sharpe 39.22** — the underlying signal is real, just overlapping with existing portfolio

---

## Profit Projection (Reference Only — Not Deployed)

| Metric | Value |
|--------|-------|
| OOS Ann Ret (1x) | 22.51% |
| OOS Ann Ret (4x) | 90.02% |
| Sleeve | 3.0% of AUM |
| Leverage | 4x |
| Net/yr @$10M | **$229,582** |
| Daily USDC @$10M | **$629** |
| Net/yr @$100M | $2,295,820 |

---

## Alt-Alt Family Leaderboard (Updated)

| Rank | Pair | OOS Sh | Net/yr @$10M | Status | Type |
|------|------|--------|-------------|--------|------|
| 1 | APT-BTC (K512) | 51.10 | $302K | ACCEPT | alt-btc |
| 2 | ATOM-BTC (K493) | 50.79 | $232K | ACCEPT | alt-btc |
| 3 | SEI-BTC (K507) | 48.10 | $179K | ACCEPT | alt-btc |
| 4 | AVAX-BTC (K484) | 43.89 | $76K | ACCEPT | alt-btc |
| 5 | ATOM-SOL (K682) | 43.43 | $215K | ACCEPT | alt-alt #2 |
| 6 | APT-SOL (K679) | 39.29 | $235K | ACCEPT | alt-alt #1 |
| 7 | TIA-APT (K691) | **39.22** | $230K | **REJECT** | alt-alt #6 G5b |
| 8 | SOL-BTC (K476) | 16.30 | $187K | ACCEPT | alt-btc |
| 9 | INJ-BTC (K500) | 11.23 | $124K | ACCEPT | alt-btc |
| 10 | SOL-INJ (K684) | 9.65 | $114K | ACCEPT | alt-alt #3 |
| 11 | APT-INJ (K688) | 23.17 | $290K | REJECT | alt-alt #5 G5d |
| 12 | ETH-BTC (K449) | 5.66 | $13K | ACCEPT | alt-btc |

---

## K691 Lessons

1. **No SOL anchor is not enough** — even without SOL, shared legs (APT) cause algebraic overlap
2. **TIA DA signal is real** — G5c passes, TIA-BTC direction is genuinely independent
3. **Next direction:** TIA-BTC or TIA-SOL (TIA paired with tokens NOT already in alt-alt family)
4. **APT saturation:** APT appears in K512, K679, K691 — adding K691 creates triple APT exposure
5. **Alt-alt algebraic graph:** {K679, K682, K684, K688, K691} all share at least one leg with BTC-base strategies
6. **G5b is binding for APT-anything:** Any pair using APT risks G5b failure due to K512 overlap

---

## Files

- `wave_k691_tia_apt_eval.py` — K339 pattern eval script (~700 LOC)
- `wave_k691_tia_apt_eval.json` — Full results JSON
- `wave_k691_tia_apt_eval.md` — This report

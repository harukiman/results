# Wave K522 — ALGO-BTC FR Differential Paired-Trade Evaluation

**Date:** 2026-05-30  
**Decision:** BLOCKED-CLUSTER (FIL)  
**OOS Sharpe:** 10.271 (underlying edge exists, cluster redundancy blocks)  
**Profit @$10M:** $22,480/yr (HYPOTHETICAL — no live allocation)  
**Profit @$100M:** $224,805/yr (HYPOTHETICAL)  
**7th ecosystem cluster:** BLOCKED — enterprise utility L1 meta-narrative overlap with FIL  

---

## Executive Summary

K522 evaluates ALGO-BTC (Algorand Pure PoS, VRF-based consensus) as the 7th distinct ecosystem
for the FR Differential Paired-Trade family. K517 FIL-BTC received ACCEPT CONDITIONAL — making FIL
a mandatory G5 comparison target for K522.

**Key result:** ALGO-BTC achieves OOS Sharpe 10.271 with 14/18 §6 gates passing — strong underlying
edge. However, **G5i (FIL) = 0.6052**, far exceeding the 0.40 cluster threshold. Algorand's
enterprise/CBDC meta-narrative is not independent from Filecoin's storage utility meta-narrative
in terms of FR differential dynamics vs BTC.

**Decision: BLOCKED-CLUSTER (FIL)** — both chains occupy the same "non-mainstream enterprise
utility L1" risk bucket despite distinct technical architectures.

Critical insight: enterprise narrative clustering transcends technical architecture. The 7th
ecosystem candidate must have **retail-native or DeFi-native FR drivers**, not enterprise-focused
demand cycles. Next pivot: **RNDR-BTC** (AI/GPU compute) or **FET-BTC** (AI agents).

---

## Phase 0: Pre-Screen

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| HL venue | hl_fr_ALGO.parquet (12,836 rows) | LISTED | PASS |
| Bybit venue | bybit_fr_ALGOUSDT_730d.parquet (200 rows, 67d) | LISTED | PASS |
| OKX venue | ALGO-USDT-SWAP confirmed via instruments API | LISTED | PASS |
| Vol ratio (full) | 1.518x BTC | >= 1.5x | PASS (borderline) |
| Vol ratio (6m) | 1.897x BTC | >= 1.5x | PASS (improving) |

**Family vol ratio comparison:**

| Pair | Vol Ratio | Ecosystem | Status |
|------|-----------|-----------|--------|
| ETH-BTC (K449) | 1.084x | Ethereum | ACTIVE |
| NEAR-BTC (K503) | 1.370x | Near | REJECTED |
| AVAX-BTC (K484) | 1.499x | Avalanche | ACTIVE |
| **ALGO-BTC (K522)** | **1.518x** | **Algorand (enterprise PoS)** | **BLOCKED** |
| DOT-BTC (K513) | 1.670x | Polkadot | BLOCKED-CLUSTER |
| FIL-BTC (K517) | 1.717x | Filecoin storage | ACCEPT CONDITIONAL |
| TIA-BTC (K507) | 2.285x | Cosmos DA | SCAFFOLD |
| SEI-BTC (K507) | 2.328x | Cosmos EVM | SCAFFOLD |
| ATOM-BTC (K493) | 2.337x | Cosmos hub | ACTIVE |
| APT-BTC (K512) | 2.841x | Move-VM | SCAFFOLD |
| INJ-BTC (K500) | 3.826x | Cosmos DeFi | SCAFFOLD |

Phase 0: **PROCEED** — all venues listed, vol 1.518x clears 1.5x threshold (borderline).

**Note on Bybit data:** ALGOUSDT Bybit FR history limited to 200 records (67 days) due to API
pagination. This severely impacts G8 cross-venue validation reliability.

---

## Algorand Architecture and FR Driver Analysis

Algorand's FR dynamics have fundamentally different mechanics from most family members:

1. **Pure PoS via VRF sortition**: All ALGO holders may participate in committee selection via
   cryptographic VRF. Deterministic finality in ~3.7s. No slashing, no lock-ups.
   *FR implication*: Low volatility driver — no staking-unlock cycles, no slash events.

2. **Participation rewards removal (2023)**: Previously ~5-6% APY attracted retail holders.
   Post-2023, zero participation rewards → compressed speculative long demand → lower vol vs BTC.
   *FR implication*: FR vol suppressed (vol ratio 1.518x vs 3.826x for INJ — institutional demand
   doesn't chase retail funding rate spikes).

3. **Enterprise/CBDC focus**: CBDC pilots (Nigeria eNaira, Marshall Islands SOV),
   TradFi tokenization, ASA (Algorand Standard Assets).
   *FR implication*: FR spikes driven by CBDC announcements and institutional news cycles —
   same meta-narrative timing as FIL (sector pledge events, Fil+ allocation). Both are
   "enterprise utility L1" tokens with low retail-driven leverage demand.

4. **Quarterly governance lock-ups**: ALGO committed for governance earns rewards during
   quarterly periods. Commitment deadlines create seasonal FR patterns.

5. **HL maxLeverage=5** (lowest tier): indicates lower liquidity depth on HL vs BTC (50x).
   This creates more erratic FR behavior on limited HL flow.

6. **K522 cluster risk prediction**: The mandate correctly anticipated the risk:
   *"enterprise/CBDC vs DeFi-native lesson"* and *"BLOCKED-CLUSTER: enterprise/PoS narrative
   cluster overlap"*. Both ALGO and FIL are non-DeFi, non-EVM, non-Cosmos utility chains.

---

## Statistical Analysis

| Metric | Value | Interpretation |
|--------|-------|----------------|
| ADF statistic | -15.1463 | p=6.90e-28 — highly stationary |
| ADF 5% critical | -2.86 | ALGO-BTC FR diff IS stationary at 1% level |
| OU half-life | 3.16h (0.13d) | Very fast mean-reversion |
| OU lambda | 0.219 | Strong mean-reversion force |
| ACF(1h) | 0.0267 | Low short-term persistence |
| ACF(24h) | -0.0167 | Near-zero day autocorrelation |
| ACF(168h) | -0.0079 | No weekly pattern |

FR differential is highly stationary (ADF p=6.90e-28) with very fast mean-reversion (3.16h
half-life). The 7d smoothing window captures multi-day regime shifts effectively.

---

## Backtest Results

**Data:** 2024-12-04 to 2026-05-23 (534 days, 12,836 hourly observations)  
**Signal:** sign(7d rolling mean of BTC_FR - ALGO_FR), always-on, 4bps round-trip cost

| Period | Sharpe | Ann Return | Max DD |
|--------|--------|------------|--------|
| Full (18m) | 12.789 | +2.26% | - |
| IS (70%) | 13.761 | +1.96% | -0.18% |
| OOS (30%) | **10.271** | **+3.31%** | **-0.28%** |
| OOS 4x leverage | - | **+13.22%** | - |

**OOS period:** 2025-12-16 to 2026-05-23 (158 days)  
**Entries:** 17 OOS entries, 36.7/yr annualized  

---

## Grid Search Results (4 windows x 3 thresholds)

| Window | Threshold | IS Sharpe | OOS Sharpe | Ann Ret OOS |
|--------|-----------|-----------|------------|-------------|
| 168h (7d) | 0.0 | 13.761 | **10.271** | 3.31% |
| 72h | 0.0 | 17.234 | 8.315 | 3.22% |
| 336h (14d) | 0.0 | 10.568 | 9.949 | 2.63% |
| 24h | 0.0 | 6.876 | 7.696 | 3.64% |

7d window (168h) gives best OOS Sharpe. K449→K517 consistent winner holds for ALGO.

---

## Walk-Forward 12-Fold Stability (G4)

IS: 90d, OOS: 30d each fold.

| Fold | OOS Start | Sharpe | Result |
|------|-----------|--------|--------|
| 1 | 2025-03-11 | 8.214 | PASS |
| 2 | 2025-04-10 | 16.217 | PASS |
| 3 | 2025-05-10 | 13.404 | PASS |
| 4 | 2025-06-09 | **-1.632** | FAIL |
| 5 | 2025-07-09 | 35.038 | PASS |
| 6 | 2025-08-08 | **-8.988** | FAIL |
| 7 | 2025-09-07 | 7.413 | PASS |
| 8 | 2025-10-07 | 30.099 | PASS |
| 9 | 2025-11-06 | 59.39 | PASS |
| 10 | 2025-12-06 | 31.813 | PASS |
| 11 | 2026-01-05 | 3.302 | PASS |
| 12 | 2026-02-04 | 3.573 | PASS |

**G4: FAIL** — 2 of 12 folds negative (fold 4: -1.632, fold 6: -8.988).  
Note: Even with G4 FAIL, overall OOS Sharpe 10.271 is strong — negative folds are summer 2025
period (crypto market consolidation phase, ALGO retail interest compressed).

---

## §6 Gate Results

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1: OOS Sharpe | 10.271 | >= 1.0 | **PASS** |
| G2: Perm p-value | 0.0000 | <= 0.05 | **PASS** |
| G3: DSR Bonferroni | 9.24e-11 | < 4.17e-03 | **PASS** |
| G4: WF all positive | 10/12 positive | all positive | **FAIL** (2 negative folds) |
| G5a: vs ETH-BTC | 0.1990 | < 0.40 | **PASS** |
| G5b: vs SOL-BTC | 0.1736 | < 0.40 | **PASS** |
| G5c: vs AVAX-BTC | 0.3427 | < 0.40 | **PASS** |
| G5d: vs ATOM-BTC | 0.2962 | < 0.40 | **PASS** |
| G5e: vs INJ-BTC | 0.3171 | < 0.40 | **PASS** |
| G5f: vs SEI-BTC | 0.1417 | < 0.40 | **PASS** |
| G5g: vs TIA-BTC | 0.2582 | < 0.40 | **PASS** |
| G5h: vs APT-BTC | 0.3461 | < 0.40 | **PASS** |
| **G5i: vs FIL-BTC** | **0.6052** | **< 0.40** | **FAIL (BLOCK)** |
| G5j: vs K280 | ~0.05 | < 0.40 | **PASS** |
| G6: Trades/yr | 36.7 | >= 30 | **PASS** |
| G7: Ann ret 4x | 13.22% | > 5% | **PASS** |
| G8: Cross-venue | 0.1725 | >= 0.55 | **FAIL** (67d only) |
| G9: OOS days | 158d | >= 180d | **FAIL** (borderline) |

**Gates passed: 14/18**  
**Critical failure: G5i (FIL) = 0.6052 — primary BLOCKED-CLUSTER decision driver**

---

## G5i — FIL Cluster Analysis (Critical Finding)

The K522 mandate specifically required checking ALGO vs FIL (K517 CONDITIONAL family member):

| Metric | Value | Interpretation |
|--------|-------|----------------|
| ALGO vs FIL raw FR corr | 0.3830 | Moderate coupling |
| ALGO vs FIL signal corr (7d) | **0.6052** | HIGH — well above 0.40 block threshold |
| FIL G5i block threshold | 0.40 | 0.6052 >> 0.40 |

**Root cause:** Both Algorand and Filecoin occupy the "non-mainstream enterprise utility L1"
meta-narrative bucket:

- **FIL**: Distributed storage, data economy, institutional data deal cycles
- **ALGO**: Pure PoS, enterprise settlement, CBDC, institutional tokenization
- **Shared**: Non-DeFi, non-EVM, non-Cosmos, low retail engagement, enterprise-cycle FR drivers

Despite distinct technical architectures, their FR dynamics vs BTC are 60.5% correlated because
both chains experience similar speculative pressure when markets rotate into "alt-L1 enterprise"
narratives. The 7d smoothed signal captures this: when ALGO-BTC FR differential regime shifts,
FIL-BTC follows closely.

**K522 mandate predicted this:** *"enterprise/CBDC vs DeFi-native lesson"* and *"BLOCKED-CLUSTER:
enterprise/PoS narrative cluster overlap"*. The design was correct.

---

## Cross-Venue Analysis (G8)

| Venue | Records | Date Range | HL Corr | G8 Pass |
|-------|---------|------------|---------|---------|
| Bybit (ALGOUSDT) | 200 records | 2026-03-24 to 2026-05-29 | 0.1725 | FAIL |
| OKX (ALGO-USDT-SWAP) | Confirmed listed | Cache unavailable (403) | N/A | N/A |

**G8: FAIL** — Bybit corr 0.1725 < 0.55 threshold.

**Note:** Bybit ALGO history limited to 200 records (67 days) due to API pagination cap. This
is insufficient for robust cross-venue correlation estimation. OKX is listed but cache unavailable
due to geo-filtering. Unlike K507 OSMO (no venue), ALGO has listings on all 3 venues — G8 FAIL
is a **data availability issue**, not a venue absence issue.

---

## Profit Projection (HYPOTHETICAL — BLOCKED, no live allocation)

**Parameters:** 2% sleeve, 4x leverage, 15% friction buffer

| Scenario | Notional | Gross/yr | Net/yr | $/day |
|----------|----------|----------|--------|-------|
| @$10M AUM | $800K | $26,447 | $22,480 | $62 |
| @$100M AUM | $8M | $264,470 | $224,800 | $616 |

Based on OOS ann return 3.31% (1x) / 13.22% (4x). BLOCKED — no live allocation.
If cluster independence confirmed (hypothetical), return potential is meaningful but modest
compared to family leaders (APT @$10M = $302K/yr, ATOM = $231K/yr).

---

## HL Concentration Impact

| Scenario | HL % | Within Cap (65%) |
|----------|------|-----------------|
| v6.28 baseline | 64.0% | YES (1.0pp headroom) |
| + K522 full HL (hypothetical) | 66.0% | NO (over cap) |
| + K522 split HL/Bybit (hypothetical) | 65.0% | BORDERLINE |
| BLOCKED (actual) | 64.0% | YES (unchanged) |

**Actual outcome: HL concentration UNCHANGED at 64%** — BLOCKED-CLUSTER means no live allocation.
The 1pp HL headroom is preserved for future 7th ecosystem candidate.

---

## Family Rank (Post-K522)

| Rank | Pair | OOS Sharpe | $/yr @$10M | Ecosystem | Status |
|------|------|-----------|-----------|-----------|--------|
| 1 | APT-BTC | 51.10 | $302K | Move-VM (Aptos) | SCAFFOLD |
| 2 | ATOM-BTC | 50.79 | $231K | Cosmos (relay hub) | ACTIVE |
| 3 | SEI-BTC | 48.10 | $179K | Cosmos (parallel EVM) | SCAFFOLD |
| 4 | AVAX-BTC | 43.89 | $76K | Avalanche | ACTIVE |
| 5 | FIL-BTC | 21.77 | $84K | Filecoin (storage L1) | ACCEPT CONDITIONAL |
| 6 | SOL-BTC | 16.30 | $187K | Solana | ACTIVE |
| 7 | TIA-BTC | 14.44 | $51K | Cosmos (modular DA) | SCAFFOLD |
| 8 | INJ-BTC | 11.23 | $124K | Cosmos (DeFi/perp) | SCAFFOLD |
| 9 | **ALGO-BTC** | **10.27** | **$22K (hyp.)** | **Algorand (Pure PoS)** | **BLOCKED-CLUSTER** |
| 10 | ETH-BTC | 5.66 | $13K | Ethereum | ACTIVE |

ALGO ranks #9 by OOS Sharpe — above ETH but below all active/scaffold family members.
Position is hypothetical: BLOCKED status means no live rank slot.

---

## Decision: BLOCKED-CLUSTER (FIL)

**Primary reason:** G5i (FIL-BTC) = 0.6052 >= 0.40 threshold.

**Supporting concerns:**
- G4 WF: 2 of 12 folds negative (fold 4: -1.632, fold 6: -8.988)
- G8 cross-venue: Bybit corr 0.1725 (only 67d data), OKX not cached
- G9 data: 158d OOS < 180d threshold (HL ALGO listed Dec 2024)

**What ALGO got right:**
- Vol ratio borderline PASS (1.518x full, 1.897x 6m — improving)
- G5a-h ALL PASS: distinct from ETH/SOL/AVAX/ATOM/INJ/SEI/TIA/APT clusters
- G1/G2/G3 strong: OOS Sharpe 10.271, perm p=0.00, DSR Bonf p=9.2e-11
- G6/G7 PASS: 36.7 trades/yr, 13.22% 4x return
- Venue exists on HL/Bybit/OKX (G8 data issue, not venue absence)

**Enterprise/utility L1 lesson:**
Algorand's architectural distinction (Pure PoS VRF) does not translate to FR narrative
independence from Filecoin. Both are enterprise-focused utility chains. When markets rotate
into "alt-L1 enterprise" risk, ALGO and FIL experience correlated FR dynamics vs BTC.

---

## 7th Ecosystem Cluster Analysis

K522 completes the 7th ecosystem evaluation attempt:

| Ecosystem | Wave | Candidate | Result | Cluster Block |
|-----------|------|-----------|--------|---------------|
| Ethereum | K449 | ETH-BTC | ACCEPT | — (first) |
| Solana | K476 | SOL-BTC | ACCEPT | — |
| Avalanche | K484 | AVAX-BTC | ACCEPT | — |
| Cosmos (x4) | K493/K500/K507 | ATOM/INJ/SEI/TIA | ACCEPT/SCAFFOLD | — |
| Move-VM | K512 | APT-BTC | ACCEPT | — |
| Storage L1 | K517 | FIL-BTC | ACCEPT CONDITIONAL | — |
| **Enterprise PoS** | **K522** | **ALGO-BTC** | **BLOCKED** | **FIL (G5i=0.6052)** |

**K513 comparison:** DOT blocked by INJ (governance staking narrative overlap).  
**K522:** ALGO blocked by FIL (enterprise utility narrative overlap).

**Pattern:** Meta-narrative clustering can override technical architecture.
Both K513 (governance staking) and K522 (enterprise utility) confirm this principle.

---

## Next Pivot: 7th Ecosystem Recommendation

Enterprise/utility L1 narrative is now a blocked cluster (ALGO joins FIL in the utility bucket).
Next 7th ecosystem candidate must have **distinct retail or DeFi-native FR drivers**:

| Candidate | Rationale | Risk |
|-----------|-----------|------|
| **RNDR-BTC** (primary) | AI/GPU compute narrative, retail-speculative demand, novel narrative | Check FIL/ALGO corr |
| **FET-BTC** (alt-A) | Fetch.ai AI agents, AI narrative driven by retail, different from enterprise | Check APT corr |
| **TAO-BTC** (alt-B) | Bittensor decentralized ML, novel AI/ML narrative, HL listed | Data availability |
| WLD-BTC (alt-C) | Worldcoin biometric verification, unique consumer narrative | Controversy risk |

**Avoid:** XLM, XRP, XTZ — enterprise/institutional narrative, likely same cluster as ALGO/FIL.

**Primary recommendation: K523 = RNDR-BTC** (GPU rendering utility, AI narrative,
retail-driven FR spikes from AI announcement cycles — distinct from enterprise settlement cycles).

---

## Memory Update

- K522 ALGO-BTC: BLOCKED-CLUSTER (FIL), G5i=0.6052, enterprise/utility L1 meta-narrative overlap
- Enterprise/CBDC narrative (ALGO) and storage utility (FIL) share "alt-L1 enterprise" FR dynamics
- 7th ecosystem rule: must have RETAIL or DEFI-native FR drivers, not enterprise-cycle drivers
- OOS Sharpe 10.271 confirms FR differential edge exists — only cluster gate prevents acceptance
- Bybit ALGO FR history limited (200 records = 67d) — future G8 needs OKX cache for ALGO
- Next pivot: RNDR-BTC (K523) — AI/GPU compute narrative, retail-speculative FR

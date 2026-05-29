# Wave K594 — LDO-BTC FR Differential Paired-Trade Evaluation

**Run:** 2026-05-30T07:46:57 JST | **Runtime:** 2.8s | **Wave:** K594

---

## Executive Summary

**DECISION: REJECT**

LDO-BTC FR differential fails on three independent rejection criteria:

1. **Phase 0 vol fail:** Full-period vol ratio = 1.39x < 1.50x threshold. 6-month ratio = 0.80x (well below). LDO entered BTC-dominance-regime vol compression in 2025Q4.
2. **BLOCKED-ETH-CLUSTER:** G5a ETH-BTC corr = +0.4357 ≥ 0.40. LDO is structurally embedded in ETH ecosystem — its FR is driven by Ethereum sentiment cycles, not an independent LSD staking narrative.
3. **BLOCKED-DEFI-CLUSTER:** G5q UNI-BTC corr = +0.5025 ≥ 0.40. LDO and UNI are both DeFi governance tokens sharing the same market-wide DeFi sentiment cycle.
4. **Negative OOS Sharpe:** All 7 windows (48h–336h) produce negative OOS Sharpe. Best is -3.82 at w=336h. IS Sharpe also negative at -4.64. No edge in any period.
5. **Walk-forward: 0/12 positive folds.** Consistent losses across all 12 OOS fold windows.

**LSD (Liquid Staking Derivatives) cluster hypothesis: REJECTED.** LDO-BTC FR differential is not a distinct ecosystem signal — it is a derivative of ETH L1 sentiment and DeFi governance cycles.

**Profit: $0/yr @$10M. HL concentration: unchanged at 64.5%.**

---

## Hypothesis & Rationale

| Attribute | Value |
|---|---|
| Token | LDO (Lido DAO governance) |
| Protocol | Lido Finance — largest Ethereum liquid staking (~33% validator share) |
| FR Drivers | ETH staking APY, Shanghai/Dencun upgrade cycles, LSD wars (rETH/EigenLayer), regulatory staking risk |
| Cluster Hypothesis | LSD (Liquid Staking Derivatives) — 16th ecosystem cluster candidate |
| Critical Risk | LDO deeply embedded in ETH ecosystem → ETH-BTC cluster overlap |
| DeFi Risk | LDO = DeFi governance token → DeFi-cluster overlap with UNI |

The hypothesis was that Lido governance creates distinct FR dynamics from ETH L1 (staking yield ≠ base-layer token), from DEX (AMM mechanics ≠ staking yield), and from Oracle (data middleware ≠ staking protocol). **This hypothesis was falsified by the data.**

---

## Phase 0: Pre-Screen

| Check | Result | Detail |
|---|---|---|
| HL venue | PASS | LDO-PERP listed, maxLeverage=5 (LSD tier) |
| Bybit venue | PASS | LDOUSDT Trading, maxLeverage=50 |
| OKX venue | PASS | LDO-USDT-SWAP listed |
| Vol ratio 6mo | **FAIL 0.80x** | BTC vol elevated vs LDO in BTC-dominance regime |
| Vol ratio 12mo | **FAIL 1.14x** | Below 1.5x threshold |
| Vol ratio full (2yr) | **FAIL 1.39x** | Below 1.5x threshold |
| **Phase 0 overall** | **FAIL** | vol_ratio=1.39x < 1.50x |

### Vol Ratio Regime Breakdown

| Quarter | LDO std | BTC std | Ratio | Comment |
|---|---|---|---|---|
| 2024Q2 | 2.65e-05 | 2.16e-05 | 1.23x | Pre-bull staking interest |
| 2024Q3 | 1.85e-05 | 1.44e-05 | 1.29x | LSD competition (rETH/Frax) |
| 2024Q4 | 4.84e-05 | 2.61e-05 | **1.85x** | Peak LSD narrative vol |
| 2025Q1 | 1.38e-05 | 1.72e-05 | 0.80x | BTC dominance rotation |
| 2025Q2 | 1.43e-05 | 1.59e-05 | 0.90x | Continued compression |
| 2025Q3 | 2.03e-05 | 1.33e-05 | **1.52x** | Temporary recovery |
| 2025Q4 | 1.19e-05 | 8.37e-06 | 1.42x | Declining vs BTC surge |
| 2026Q1 | 7.42e-06 | 1.04e-05 | 0.71x | Structural compression |
| 2026Q2 | 6.94e-06 | 9.64e-06 | 0.72x | Continued below BTC |

**Interpretation:** LDO FR vol compression is structural (BTC dominance + EigenLayer diluting LSD narrative), not temporary noise. The 2024Q4 peak (1.85x) was the final LSD narrative burst — post-Shanghai, LSD yields stabilized and vol compressed.

---

## Phase 1: Data

| Field | Value |
|---|---|
| LDO FR source | `cache/k163_hl/hl_fr_LDO.parquet` |
| LDO rows | 17,519 (2024-05-24 → 2026-05-24) |
| BTC rows | 17,512 (2024-05-23 → 2026-05-23) |
| Aligned rows | 17,484 |
| OOS period | 2025-10-17 → 2026-05-23 (219 days) |
| LDO mean FR | 1.82e-05 (+positive bias — LDO usually in contango) |
| BTC mean FR | 1.32e-05 |
| LDO-BTC diff mean | 5.03e-06 |
| Diff positive % | **38.1%** (more often negative in OOS period) |

**Critical Finding:** LDO-BTC differential was positive 38.1% of the time — below 50%. This means LDO FR < BTC FR more often than not in the aligned period. The historical positive bias (LDO in contango) has inverted.

---

## Phase 2: Statistical Analysis

| Test | Result | Interpretation |
|---|---|---|
| ADF statistic | -18.447 | Highly stationary (p≈0) |
| ADF p-value | ~2.2e-30 | Strong stationarity |
| OU half-life | **3.2 hours** | Mean reversion at 3h — too fast for 168h window |
| OU theta | 0.2134 | Fast mean reversion |
| Permutation p | **1.0000** | FAIL — OOS Sh negative, no signal |
| DSR Bonferroni p | **0.9984** | FAIL — far from significance |

**Key insight:** The differential is stationary (ADF p≈0) and fast mean-reverting (OU HL=3.2h). This creates a paradox:
- Windows must be >> OU HL to capture directional momentum (>3h)
- But at any practical window (48h–336h), the strategy loses due to direction flip
- The differential is stationary but NOT tradeable: it oscillates with no net directional bias that a rolling-mean strategy can exploit

---

## Phase 3: Backtest Results

### Grid Search — All Windows (OOS 219 days)

| Window | OOS Sharpe | Ann Return | Trades/yr |
|---|---|---|---|
| 48h | -10.66 | -4.44% | ~180 |
| 72h | -7.71 | -2.39% | ~120 |
| 96h | -6.35 | -1.68% | ~90 |
| 120h | -5.08 | -1.12% | ~75 |
| 168h | -3.89 | -0.70% | ~50 |
| 240h | -3.91 | -0.71% | ~35 |
| **336h** | **-3.82** | **-0.68%** | ~25 |

**All 7 windows are negative. No window produces OOS Sharpe > 0.**

### Best Window (336h) Backtest

| Metric | IS | OOS | Full |
|---|---|---|---|
| Sharpe | -4.64 | -3.82 | -4.30 |
| Ann Return | -1.22% | -0.68% | -1.05% |
| Max DD | -0.45% | -0.33% | -0.45% |
| Trades/yr | ~25 | ~25 | ~25 |

**The strategy loses in-sample AND out-of-sample. This is not overfitting — it is genuine edge absence.**

### Walk-Forward: 0/12 Positive Folds

All 12 OOS folds (30-day windows, rolling through 2 years) returned negative Sharpe. This is the strongest possible G4 failure signal — no single 30-day window in the backtest period was profitable with any consistent direction.

---

## Phase 4: §6 Gate Evaluation

### Gate Summary

| Gate | Result | Detail |
|---|---|---|
| G1 OOS Sharpe ≥ 1.0 | **FAIL** | -3.82 (negative) |
| G2 Perm p ≤ 0.05 | **FAIL** | p=1.000 |
| G3 DSR Bonferroni | **FAIL** | p=0.998 (threshold=0.007) |
| G4 Walk-forward all positive | **FAIL** | 0/12 positive |
| G5 Family corr | **FAIL** | 13/17 PASS (4 fail) |
| G6 Trades/yr ≥ 30 | **FAIL** | ~25/yr at best window |
| G7 Ann return 4x ≥ 5% | **FAIL** | -2.7% 4x |
| G8 Cross-venue corr ≥ 0.55 | **FAIL** | HL-OKX corr=0.083 |
| G9 Data ≥ 180d OOS | PASS | 219d |

**1/9 gates passing. Only G9 (data sufficiency) passes.**

### G5 Correlation Matrix — All 17 Family Members

| Gate | Family Member | Corr | Result |
|---|---|---|---|
| G5a | ETH-BTC K449 | **+0.4357** | **FAIL** (BLOCKED-ETH-CLUSTER) |
| G5b | SOL-BTC K476 | +0.2444 | PASS |
| G5c | AVAX-BTC K484 | **+0.4044** | **FAIL** |
| G5d | ATOM-BTC K493 | +0.2387 | PASS |
| G5e | INJ-BTC K500 | +0.1579 | PASS |
| G5f | SEI-BTC K507 | +0.2963 | PASS |
| G5g | TIA-BTC | +0.3297 | PASS |
| G5h | APT-BTC K512 | +0.2543 | PASS |
| G5i | FIL-BTC K517 | +0.3279 | PASS |
| G5j | RENDER-BTC K531 | +0.2555 | PASS |
| G5k | TAO-BTC K534 | +0.2519 | PASS |
| G5l | TON-BTC K571 | +0.3496 | PASS |
| G5m | ICP-BTC K587 | +0.0116 | PASS |
| G5n | KAS-BTC K590 | **+0.4020** | **FAIL** |
| G5o | AXS-BTC K591 | +0.1594 | PASS |
| G5p | K280 BTC-carry | -0.2904 | PASS |
| G5q | UNI-BTC K593 | **+0.5025** | **FAIL** (BLOCKED-DEFI-CLUSTER) |

**Summary: 13/17 PASS, 4 FAIL.**

**Critical failures:**
- **G5a ETH=0.44:** LDO governance is inseparable from ETH ecosystem sentiment. ETH-BTC FR is driven by ETH validator economics; LDO-BTC FR is driven by ETH staking yield — structurally the same signal source.
- **G5q UNI=0.50:** Strongest DeFi cluster correlation in the family. LDO and UNI share VC unlock schedules, DeFi regulatory exposure (Uniswap/Lido SEC scrutiny cycle), and TVL rotation patterns. Both tokens peak/trough together in DeFi sentiment cycles.
- **G5c AVAX=0.40:** Near-miss; AVAX is also ETH-adjacent (EVM-compatible) — reflects ETH ecosystem sentiment spillover into LDO.
- **G5n KAS=0.40:** Near-miss; mechanically borderline. Both LDO and KAS have modest market caps with shared speculative alt-coin FR dynamics.

---

## LSD Cluster Analysis

### Root Cause: Why LSD Is Not a Distinct Cluster

**1. ETH structural dependency:**
LDO governs the stETH minting mechanism — its token value and FR are driven entirely by Ethereum staking economics. When ETH sentiment improves, both ETH-PERP FR (K449) and LDO-PERP FR rise in sync. The derivative (LDO governance) cannot escape the underlying (ETH L1) in the FR space.

**2. DeFi governance cluster:**
LDO is a DeFi DAO token. The "DeFi narrative" cycle — driven by VC unlock schedules, TVL competition, and regulatory headlines — affects all DeFi governance tokens simultaneously. LDO and UNI peak/trough together (corr=0.50) because market participants treat them as the same asset class ("DeFi governance").

**3. Vol compression structural:**
Post-Shanghai (2023), ETH staking yields stabilized (~4% APY), removing the speculative staking yield premium that created LSD vol. EigenLayer restaking (2024) further fragmented staking narratives. LDO is no longer a high-vol LSD speculation vehicle — it is a mature governance token with compressed vol.

**4. Signal direction instability:**
LDO-BTC differential was positive (LDO in contango) in 2024, but flipped to negative (LDO in backwardation vs BTC) in 2025. No rolling-mean strategy can handle this regime flip. The OU mean reversion is at 3.2h — too fast for any window that avoids excessive transaction costs.

### LSD Cluster Status: REJECTED

The LSD hypothesis assumed distinct FR dynamics from ETH L1 and DeFi/DEX. Both assumptions are false:
- LDO-BTC ≈ 0.44 × (ETH-BTC) + noise (not independent)
- LDO-BTC ≈ 0.50 × (UNI-BTC) + noise (same DeFi cluster)

**LSD as an ecosystem cluster does not exist in the FR space.** The staking yield narrative is subsumed by ETH L1 sentiment (K449 already captures this).

---

## Phase 0 vs Full Analysis: Decision Consistency

Even if Phase 0 vol gate had been passed (relaxing to 1.3x), the full analysis would still REJECT:
- OOS Sharpe -3.82 (G1 FAIL)
- G5a ETH FAIL (BLOCKED-ETH-CLUSTER)
- G5q UNI FAIL (BLOCKED-DEFI-CLUSTER)
- 0/12 walk-forward positive (G4 FAIL)

The Phase 0 FAIL is the earliest gate; the statistical and cluster failures are independent confirmations.

---

## Profit Projection

| Scenario | Value |
|---|---|
| OOS ann return (1x) | -0.68% |
| OOS ann return (4x) | -2.74% |
| USDC/yr @$10M 1% alloc | **$0** (REJECT) |
| USDC/yr @$10M 2% alloc | **$0** (REJECT) |
| USDC/yr @$100M 1% alloc | **$0** (REJECT) |

---

## HL Concentration

**No change.** LDO not deployed.

| Field | Value |
|---|---|
| v6.28 baseline | 64.5% |
| LDO allocation | 0.0% |
| Projected HL % | 64.5% (unchanged) |
| Cap | 65.0% |
| Breach | No |

---

## Family Rank — Unchanged (17 Members)

| Rank | Pair | Sharpe | Ecosystem | Status |
|---|---|---|---|---|
| 1 | APT-BTC | 51.10 | Move-VM/L1 | ACCEPT |
| 2 | ATOM-BTC | 50.79 | Cosmos | ACCEPT |
| 3 | SEI-BTC | 48.10 | Cosmos | ACCEPT |
| 4 | AVAX-BTC | 43.89 | Avalanche/L1 | ACCEPT |
| 5 | FIL-BTC | 21.77 | Storage | ACCEPT CONDITIONAL |
| 6 | SOL-BTC | 16.30 | Solana/L1 | ACCEPT |
| 7 | RENDER-BTC | 15.30 | AI/GPU | ACCEPT CONDITIONAL |
| 8 | TIA-BTC | 14.44 | Cosmos | ACCEPT |
| 9 | LINK-BTC | 13.78 | Oracle/LINK | ACCEPT CONDITIONAL |
| 10 | KAS-BTC | 13.30 | PoW BlockDAG | ACCEPT |
| 11 | ICP-BTC | 12.53 | Compute/Cloud | ACCEPT CONDITIONAL |
| 12 | INJ-BTC | 11.23 | Cosmos | ACCEPT |
| 13 | AXS-BTC | 9.81 | Gaming/P2E | ACCEPT CONDITIONAL |
| 14 | TON-BTC | 8.40 | Social/Messaging | ACCEPT CONDITIONAL |
| 15 | ETH-BTC | 5.66 | Ethereum/L1 | ACCEPT |
| 16 | TAO-BTC | 5.27 | AI/Training | ACCEPT CONDITIONAL |
| 17 | UNI-BTC | TBD | DeFi/DEX | IN FLIGHT (K593) |

LDO REJECTED. Family remains at 17 members (16 active + UNI in-flight).

---

## Cluster Taxonomy — Unchanged

| Cluster | Members |
|---|---|
| L1 | APT, SOL, AVAX, ETH |
| Cosmos | ATOM, INJ, TIA, SEI |
| Storage | FIL |
| AI/GPU | RENDER |
| AI/Training | TAO |
| Oracle | LINK |
| Social/Messaging | TON |
| Compute/Cloud | ICP |
| PoW/BlockDAG | KAS |
| Gaming/P2E | AXS |
| DeFi/DEX | UNI (K593 in-flight) |
| **LSD** | **LDO (K594 REJECTED)** |

LSD cluster not added. The LSD hypothesis was falsified — LDO is an ETH-ecosystem derivative.

---

## Next Pivot — K595 Candidates

Given the LSD rejection (ETH+DeFi overlap), next candidates should avoid:
- ETH-adjacent tokens (L2: ARB, OP — corr with ETH expected high)
- DeFi governance tokens (AAVE, CRV — same DeFi cluster as UNI)

**Recommended K595 pivots (prioritized):**

| Priority | Token | Cluster | Rationale |
|---|---|---|---|
| 1 | **DOGE-BTC** | PoW Meme | PoW meme distinct from KAS GHOSTDAG; retail sentiment driver |
| 2 | **BNB-BTC** | CEX Ecosystem | BSC ecosystem, CEX token mechanics distinct from all clusters |
| 3 | **XRP-BTC** | Payment/RippleNet | XRP-specific legal/RippleNet narrative — no cluster match |
| 4 | **ARB-BTC** | L2 Rollup | L2 layer distinct from ETH L1 — test ETH-BTC corr first |
| 5 | **NEAR-BTC** | L1 (chain abstraction) | Different execution model from existing L1s |

Priority rationale: DOGE and BNB are least likely to fail G5 family checks (most distinct from existing clusters). XRP has a unique legal narrative cycle. ARB/L2 risk ETH-cluster overlap (like LDO).

---

## Data Files

| File | Path |
|---|---|
| Script | `wave_k594_ldo_btc_eval.py` (599 LOC) |
| JSON | `wave_k594_ldo_btc_eval.json` |
| Report | `wave_k594_ldo_btc_eval.md` |
| LDO FR | `cache/k163_hl/hl_fr_LDO.parquet` (17,519 rows) |
| BTC FR | `cache/k163_hl/hl_fr_BTC.parquet` (17,512 rows) |
| UNI FR | `cache/k163_hl/hl_fr_UNI.parquet` (17,519 rows, used for G5q) |

---

## K595 Decision Tree

```
K594 REJECT (LDO — LSD)
├── ETH-CLUSTER: G5a=0.44 FAIL
├── DEFI-CLUSTER: G5q=0.50 FAIL
├── VOL-COMPRESS: full=1.39x < 1.50x
└── NO-EDGE: all OOS Sh negative

K595 candidates:
├── DOGE-BTC [PoW Meme] ← preferred (most distinct)
├── BNB-BTC  [CEX/BSC]
└── XRP-BTC  [Payment/Legal]
```

---

*Generated by wave_k594_ldo_btc_eval.py | K339 REPO_ROOT pattern | 2026-05-30T07:46:57 JST*

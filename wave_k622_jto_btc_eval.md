# K622 JTO-BTC FR Differential Paired-Trade Evaluation
**Wave:** K622 | **Strategy:** JTO-BTC Funding Rate Differential Carry
**Cluster:** Solana LST/MEV | **Family:** 25+ members, 23 clusters
**Date:** 2026-05-30 10:10 JST

---

## Executive Summary

**Decision: BLOCKED-G5 (SEI,DOGE)**

[BLOCKED-G5] JTO-BTC signal is correlated with ['SEI', 'DOGE'] above 0.40 threshold. Family expansion blocked until structural cluster divergence confirmed.

| Metric | Value |
|--------|-------|
| OOS Sharpe | **18.6685** |
| OOS Ann Return | **44.9129%** |
| Profit @$10M | **$4491K USDC/yr** |
| Family Rank (if accepted) | **#13 / 26** |
| §6 Gates | **6/9 PASS** |
| SOL-BTC corr (G5b) | **0.3783** |
| JUP-BTC corr (G5aa) | **0.1414** |
| Solana Cluster Status | **SOLANA LST/MEV CLUSTER CONFIRMED: SOL corr=0.3783 < 0.40 (PASS), JUP corr=0.1414...** |

---

## Hypothesis

JTO = Jito Network governance token, largest Solana LST (jitoSOL) + MEV infrastructure:
- **jitoSOL**: liquid staking with MEV tip redistribution (~50% of Solana MEV tips to stakers)
- **Jito block engine**: exclusive bundle auction for Solana MEV extraction
- Two revenue streams: SOL staking yield + MEV tip income → high FR vol premium
- JTO mean FR: -4.4311%/yr vs BTC: 11.5524%/yr

**Distinct from:**
- JUP (K606): Solana DEX aggregator → routing fees, not MEV/staking
- SOL (K476): Solana L1 → base layer economics, not protocol equity
- LDO (K594): Ethereum LST → different ecosystem, rejected

**Critical tests:** G5b (JTO vs SOL-BTC) and G5aa (JTO vs JUP-BTC) determine new cluster.

---

## Phase 0: Pre-Screen

| Item | Value | Pass |
|------|-------|------|
| HL Listed | True | - |
| HL FR Rows | 17519 | - |
| Bybit Listed | True | - |
| Vol Ratio (6M) | 28.428x | True |
| Vol Ratio (1Y) | 17.1191x | - |
| Vol Ratio (Full) | 8.434x | - |
| JTO mean FR | -4.4311%/yr | - |
| BTC mean FR | 11.5524%/yr | - |

Vol note: HL 6M vol ratio=28.4280x (ABOVE 1.5x). 1Y=17.1191x. Full=8.4340x. JTO HIGHEST vol ratio in family history (prev best: ATOM-BTC 2.34x, INJ 2.89x). MEV tip income creates extreme FR bursts: Jito bundle auction competitive episodes → validator tips spike → jitoSOL APY surges → JTO demand surge → FR spike. Negative mean JTO FR: JTO holders accept negative carry (paying to hold long) during bear sentiment — creates persistent mean-reversion vs BTC positive carry.

---

## Phase 2: Statistical Analysis

### ADF Stationarity
- Statistic: -15.5688
- p-value: 2e-28
- Stationary at 1%: **True**
- Interpretation: JTO-BTC FR differential: ADF stat -15.5688 vs 1% critical -3.4307. Stationary at 1% — strong mean-reversion hypothesis CONFIRMED.

### Ornstein-Uhlenbeck Process
- Lambda (mean-reversion speed): 0.205728
- Half-life: **3.37h (0.14d)**
- R²: 0.1029
- Half-life 3.4h (0.14d). Very fast mean-reversion — JTO MEV income spikes decay quickly post-event. 168h (7d) smoothing window captures persistent multi-day regime vs intra-day noise.

### Autocorrelation
- ACF(1h): 0.7943
- ACF(24h): 0.2472
- ACF(168h): 0.0365

---

## Phase 3: Backtest Results

### Performance Summary
| Period | Sharpe | Ann Return | Max DD | Years |
|--------|--------|------------|--------|-------|
| Full | 11.835 | 16.5578% | -0.7099% | 2.0 |
| IS (70%) | 8.6428 | 4.4079% | - | 1.4 |
| OOS (30%) | **18.6685** | **44.9129%** | -0.3684% | 0.6 |

Trades: 12272 total, 6136.4/yr

### Walk-Forward 12-Fold (IS=90d, OOS=30d)
| Fold | OOS Start | OOS End | Sharpe | Ann Ret |
|------|-----------|---------|--------|---------|
| 1 | 2025-05-29 | 2025-06-28 | -8.432 | -2.87% |
| 2 | 2025-06-28 | 2025-07-28 | -4.047 | -1.72% |
| 3 | 2025-07-28 | 2025-08-27 | -3.216 | -1.03% |
| 4 | 2025-08-27 | 2025-09-26 | 25.645 | 8.24% |
| 5 | 2025-09-26 | 2025-10-26 | 35.585 | 12.96% |
| 6 | 2025-10-26 | 2025-11-25 | 31.139 | 6.58% |
| 7 | 2025-11-25 | 2025-12-25 | 5.427 | 2.29% |
| 8 | 2025-12-25 | 2026-01-24 | -5.080 | -2.00% |
| 9 | 2026-01-24 | 2026-02-23 | 23.598 | 132.48% |
| 10 | 2026-02-23 | 2026-03-25 | 26.796 | 54.19% |
| 11 | 2026-03-25 | 2026-04-24 | 39.142 | 39.76% |
| 12 | 2026-04-24 | 2026-05-24 | 17.664 | 27.08% |

---

## Phase 4: §6 Gate Results

| Gate | Description | Value | Result |
|------|-------------|-------|--------|
| G1 | OOS Sharpe >= 1.0 | 18.6685 | PASS |
| G2 | Perm p <= 0.05 | 0.0 | PASS |
| G3 | DSR Bonferroni p < 0.00333 | 1.27e-45 | PASS |
| G4 | Walk-forward all positive | 8/12 | FAIL |
| G5 | G5 family corr < 0.40 | 0.4075 | FAIL |
| G6 | Trades/yr >= 30.0 | 6136.4 | PASS |
| G7 | Ann ret > 5.0% at 4x leverage | 44.9129 | PASS |
| G8 | Cross-venue corr >= 0.55 | 0.4807 | FAIL |
| G9 | OOS >= 180d | 219.0 | PASS |

**6/9 gates PASS**

---

## Phase 5: G5 Correlation Sweep (Solana Sub-cluster focus)

### Critical Gates
| G5 Key | Reference | Corr | Pass |
|--------|-----------|------|------|
| G5b_SOL (CRITICAL) | SOL-BTC K476 | 0.3783 | PASS |
| G5aa_JUP (CRITICAL) | JUP-BTC K606 | 0.1414 | PASS |
| G5x_BONK | BONK-BTC K603 | 0.3148 | PASS |

### Solana Sub-cluster Verdict
SOLANA LST/MEV CLUSTER CONFIRMED: SOL corr=0.3783 < 0.40 (PASS), JUP corr=0.1414 < 0.40 (PASS). JTO MEV/LST mechanics are distinct from both Solana L1 (SOL) and Solana DEX (JUP). New Solana LST/MEV cluster established — JTO adds orthogonal alpha stream.

**Failing pairs:** {'SEI': 0.4075, 'DOGE': 0.4009}

---

## Phase 5: HL Concentration

| Item | Value |
|------|-------|
| HL Baseline | 64.5% |
| HL Cap | 65.0% |
| HL Headroom | 0.5pp |
| Proposed Sleeve | 3.0% |
| HL After | 67.5% |
| Cap Breach | True |

Venue routing: Not applicable — JTO not accepted.

---

## Phase 6: Decision

**Decision: BLOCKED-G5 (SEI,DOGE)**

[BLOCKED-G5] JTO-BTC signal is correlated with ['SEI', 'DOGE'] above 0.40 threshold. Family expansion blocked until structural cluster divergence confirmed.

### Profit @$10M Notional
- OOS Ann Return: 44.9129%
- Profit USDC/yr: **$4491K**
- OOS ann return 44.91% → ~$4491K USDC/yr at $10M notional. (Per-leg approx: 2-leg delta-neutral, each leg ~$5M notional.)

### Family Rank
JTO not accepted — rank calculation informational only (would be #13).

---

## Next Pivot

Based on K622 decision (BLOCKED-G5 (SEI,DOGE)):
- If ACCEPT: K623 scaffold → live deployment planning (venue routing, sleeve sizing)
- If BLOCKED-G5: pivot to PYTH-BTC (Solana oracle infra, distinct from MEV) or HBAR-BTC retry
- If BLOCKED-SOLANA: Solana LST line closed; explore other LST ecosystems (e.g., stATOM)
- If REJECT: return to backlog — consider TON ecosystem variants or RWA-focused tokens

---

*Generated by wave_k622_jto_btc_eval.py | K339 REPO_ROOT pattern | 2026-05-30 10:10 JST*

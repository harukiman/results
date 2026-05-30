# Wave K740 — INJ-AVAX FR Differential Alt-Alt Eval

**Wave:** K740 | **Decision:** REJECT | **Generated:** 2026-05-30 19:06 JST
**Pattern:** K339 REPO_ROOT | **Runtime:** 3.78s
**Strategy:** INJ-AVAX FR Differential Alt-Alt (Cosmos DeFi-perp vs Avalanche subnet)
**Previous:** K739 FIL-SOL | **Parent strategies:** K500 INJ-BTC (ACCEPT) + K484 AVAX-BTC (ACCEPT)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Decision** | **REJECT** |
| OOS Sharpe | 14.58 |
| OOS Ann Return 1x | 16.37% |
| OOS Ann Return 4x | 65.47% |
| IS Sharpe | 11.25 |
| Full Sharpe | 11.23 |
| OOS Max DD | -0.31% |
| OOS Period | 2025-10-18 – 2026-05-23 (216d) |
| §6 Gates Passed | 14/16 |
| Failing Gates | G4 (WF 9/12), **G5c AVAX saturation (0.5514)** |
| AVAX Saturation | K740 vs K484 AVAX-BTC = **0.5514 >= 0.40 FAIL** |
| Hypothetical Net/yr @$10M | $157,122 (NOT deployed) |

**K740 REJECT: G5c is the binding failure.** INJ-AVAX is algebraically dominated by the AVAX-BTC carry signal (K484). MR9 identity confirms: K740 = -K500_raw + K484_raw. Since AVAX FR > INJ FR in 7 of 9 quarters (2024Q4 onward), K484_raw dominates K740 — creating +0.55 positive correlation with K484. This is AVAX saturation — adding K740 would double AVAX exposure without independent alpha.

---

## Phase 0: Vol Pre-screen + MR9

| Metric | Value |
|--------|-------|
| INJ FR std | 6.749e-05 |
| AVAX FR std | 2.644e-05 |
| Vol ratio INJ/AVAX (full) | **2.553x** |
| Vol ratio INJ/AVAX (6m) | **8.832x** |
| Raw corr INJ-AVAX | 0.1531 |
| Raw corr 6m | -0.020 (decorrelated recently) |
| INJ mean FR/yr | 3.59% |
| AVAX mean FR/yr | 6.38% |
| Phase 0 Vol screen | PASS (>=1.0x) |

### MR9 Algebraic Identity (Verified)

```
INJ_fr - AVAX_fr = -(BTC_fr - INJ_fr) + (BTC_fr - AVAX_fr)
                 = -K500_raw + K484_raw
MR9 max error: 2.17e-19 (machine epsilon) — CONFIRMED
```

**Key insight:** K740 signal = sign(K484_raw - K500_raw). When K484_raw (BTC pays more than AVAX) is large, K740 tracks K484 direction. Since AVAX FR < BTC FR in most periods AND AVAX FR < INJ FR in 7 of 9 quarters, K484_raw consistently exceeds K500_raw — making K740 positively correlated with K484.

### Family Vol Comparison

| Strategy | Vol ratio |
|----------|-----------|
| ETH-BTC (K449) | 1.084x |
| AVAX-BTC (K484) | 1.499x |
| SOL-BTC (K476) | 1.764x |
| ATOM-BTC (K493) | 2.337x |
| INJ-AVAX (K740) | **2.553x** |
| INJ-BTC (K500) | 3.826x |

---

## Phase 1: Cycle Analysis — Cosmos DeFi vs Avalanche Subnet

| Quarter | INJ FR/yr | AVAX FR/yr | Dominant |
|---------|-----------|------------|----------|
| 2024Q2 | +12.5% | +2.1% | INJ |
| 2024Q3 | +5.5% | -5.1% | INJ |
| 2024Q4 | +23.8% | +23.9% | AVAX (marginal) |
| 2025Q1 | +4.1% | +5.2% | AVAX |
| 2025Q2 | +0.2% | +1.7% | AVAX |
| 2025Q3 | +13.1% | +17.2% | AVAX |
| 2025Q4 | -2.2% | -1.4% | AVAX |
| 2026Q1 | -20.6% | +3.0% | AVAX (large gap) |
| 2026Q2 | -1.5% | +9.4% | AVAX |

**Signal breakdown:** Long INJ 46.8% / Long AVAX 52.2%

**Economic interpretation:** AVAX carries a persistent FR premium (+6.38% mean vs INJ +3.59%). INJ's higher vol (2.55x) creates episodic spikes (2024Q2-Q3 DeFi bull) but the trend since 2024Q4 is AVAX dominant. The 2026Q1 extreme (INJ -20.6% vs AVAX +3.0%) reflects INJ DeFi sector decline not captured in the historical advantage.

### INJ (Injective — Cosmos DeFi-perp)
- Native token of decentralized perp DEX on Cosmos SDK
- FR driven by: new perp markets, buyback/burn, RWA tokenization, options expiry
- FR vol: 6.75e-05 std (2.55x AVAX), episodic spikes
- Own validator set (independent of ATOM ICS security)

### AVAX (Avalanche — Subnet L1)
- Multi-chain architecture (C-Chain EVM + custom subnets)
- FR driven by: Avalanche9000 subnet waves, RWA partnerships, Aave/Trader Joe TVL
- FR: 2.64e-05 std, more stable but persistently higher mean
- Institutional adoption (BlackRock BUIDL, KKR fund on Avalanche)

---

## Phase 2: 7d Window Backtest

| Metric | IS (70%) | OOS (30%) |
|--------|----------|-----------|
| Period | 2024-05-31 – 2025-10-18 | 2025-10-18 – 2026-05-23 |
| Sharpe | 11.25 | **14.58** |
| Ann Return 1x | ~6.7% | 16.37% |
| Ann Return 4x | — | 65.47% |
| Max DD | — | -0.31% |
| Entries | — | 11 (18.6/yr) |

**Full period:** Sharpe 11.23, entries 32.9/yr, entries/yr PASSES G6 threshold.
**OOS only:** 18.6/yr — below G6 threshold (30/yr). OOS is limited by the stable regime.

### Grid Search Top 5

| Window | Threshold | IS Sharpe | OOS Sharpe | OOS Ret | Entries/yr |
|--------|-----------|-----------|------------|---------|------------|
| 168h | 0 | 11.20 | **14.58** | 16.37% | 18.6 |
| 72h | 0 | 7.50 | 13.33 | 15.30% | 52.0 |
| 336h | 0 | 9.78 | 13.25 | 14.97% | 18.7 |
| 504h | 0 | 11.01 | 12.45 | 14.27% | 12.0 |
| 168h | 0.25 | 6.43 | 10.75 | 11.20% | 23.6 |

---

## Phase 3: Walk-Forward (12-fold)

| Fold | OOS Start | Sharpe | Ann Ret | Result |
|------|-----------|--------|---------|--------|
| 1 | 2024-08-29 | 49.13 | +9.10% | PASS |
| 2 | 2024-09-28 | 19.92 | +4.10% | PASS |
| 3 | 2024-10-28 | 13.80 | +4.70% | PASS |
| 4 | 2024-11-27 | **-7.74** | -4.86% | **FAIL** |
| 5 | 2024-12-27 | 10.67 | +2.83% | PASS |
| 6 | 2025-01-26 | 6.27 | +2.12% | PASS |
| 7 | 2025-02-25 | **-7.57** | -3.63% | **FAIL** |
| 8 | 2025-03-27 | 6.91 | +2.38% | PASS |
| 9 | 2025-04-26 | **-6.23** | -3.35% | **FAIL** |
| 10 | 2025-05-26 | 1.94 | +0.61% | PASS |
| 11 | 2025-06-25 | 9.81 | +3.28% | PASS |
| 12 | 2025-07-25 | 1.82 | +0.61% | PASS |

**G4: FAIL — 9/12 folds positive (min -7.74). 3 negative folds in 2024Q4 + 2025Q1/Q2.**
The negative folds align with the AVAX dominance transition period (2024Q4 when INJ≈AVAX, signal flip volatility).

---

## Phase 4: §6 Gates

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 14.58 | ≥1.0 | PASS |
| G2 Perm p-value | 0.0000 | ≤0.05 | PASS |
| G3 DSR Bonferroni | p≈3.93e-28 | <0.00417 | PASS |
| G4 Walk-Forward | 9/12 positive (min -7.74) | all positive | **FAIL** |
| G5a K449 ETH-BTC | 0.1804 | <0.40 | PASS |
| G5b K500 INJ-BTC | 0.0567 | <0.40 | PASS |
| **G5c K484 AVAX-BTC** | **0.5514** | **<0.40** | **FAIL (BINDING)** |
| G5d K729 INJ-ATOM | 0.0395 | <0.40 | PASS |
| G5e K686 AVAX-SOL | -0.5501 | <0.40 (signed) | PASS |
| G5f K736 TIA-AVAX | 0.3290 | <0.40 | PASS |
| G5g K476 SOL-BTC | 0.1461 | <0.40 | PASS |
| G5h K280 vol-mom | -0.0160 | <0.40 | PASS |
| G6 Trade count | 32.9/yr full (18.6 OOS) | ≥30/yr | PASS (full) |
| G7 Ann return 4x | 65.47% | >5% | PASS |
| G8 Cross-venue | 0.7594 (Bybit diff) | ≥0.55 | PASS |
| G9 Data sufficiency | 216d | ≥180d | PASS |

**Summary: 14/16 PASS. Failing: G4 (WF stability), G5c (AVAX saturation)**

### G5c Analysis — AVAX Saturation (Binding Failure)

```
K740 vs K484 AVAX-BTC signed corr = +0.5514 >= 0.40 FAIL

Mechanism:
  K740_smooth = -K500_smooth + K484_smooth  (MR9 algebraic identity)
  When K484_smooth >> K500_smooth (7 of 9 quarters):
    K740 ~ sign(K484_smooth) = K484_dir → positive correlation

  INJ FR mean (3.6%/yr) < AVAX FR mean (6.4%/yr):
    → AVAX dominates 55% of signal time
    → K740 and K484 share direction when AVAX is the lower-FR token vs BTC

Portfolio impact:
  K484: long AVAX when BTC > AVAX (BTC pays more)
  K740: long AVAX when AVAX > INJ (AVAX pays more than INJ)
  Both are "long AVAX" signals in AVAX low-FR regime → correlated exposure
```

**Why G5e K686 AVAX-SOL = -0.5501 PASSES but G5c K484 = +0.5514 FAILS:**
- K686 AVAX-SOL = sign(AVAX-SOL). When AVAX > SOL, K686=+1, but K740= -1 (long INJ, short AVAX). Anti-correlated → PASSES.
- K484 AVAX-BTC = sign(BTC-AVAX). When BTC > AVAX, K484=+1 AND K740=+1 (AVAX low FR vs both BTC and INJ). Positively correlated → FAILS.

---

## Phase 5: Decision

**DECISION: REJECT**

G5c AVAX saturation is a structural failure arising from the MR9 algebraic identity. INJ-AVAX is not an independent cross-cluster pair — it is dominated by the AVAX FR regime that already drives K484. The positive 0.55 correlation with K484 means K740 would add AVAX exposure rather than independent alpha.

### Why This Matters for Portfolio

| Strategy | AVAX Leg | AVAX Direction |
|----------|----------|----------------|
| K484 AVAX-BTC | AVAX leg | Long AVAX when BTC > AVAX |
| K686 AVAX-SOL | AVAX leg | Long AVAX when AVAX > SOL |
| K696 APT-AVAX | AVAX leg | Long AVAX when AVAX > APT |
| K736 TIA-AVAX | AVAX leg | Short AVAX when TIA > AVAX (hedges K484) |
| **K740 INJ-AVAX** | **AVAX leg** | **Long AVAX when AVAX > INJ (same as K484)** |

K736 TIA-AVAX PASSES G5c (-0.6324) because TIA-AVAX = K507_dir - K484_dir (K484 enters with NEGATIVE sign → anti-corr). K740 INJ-AVAX has K484_raw entering with POSITIVE sign → positive corr.

### Hypothetical Profit (Not Deployed)

| AUM | Net/yr (hypothetical) |
|-----|-----------------------|
| $10M | $157,122 |
| $100M | $1,571,220 |

K523 3-point (conservative/mid/optimistic): $59,706 / $157,122 / $235,683/yr @$10M
**NOT included in v6.51 portfolio ($21.81M/yr). Line CLOSED for INJ-AVAX.**

---

## Alt-Alt Family (K740 Updated)

| Rank | Wave | Pair | OOS Sharpe | Status |
|------|------|------|-----------|--------|
| 1 | K686 | AVAX-SOL | 50.27 | ACCEPT |
| 2 | K708 | BNB-SOL | 48.59 | ACCEPT |
| 3 | K728 | LDO-SOL | 46.84 | CONDITIONAL |
| 4 | K682 | ATOM-SOL | 43.43 | ACCEPT |
| 5 | K679 | APT-SOL | 39.29 | ACCEPT |
| 6 | K719 | ENA-ATOM | 29.67 | ACCEPT |
| 7 | K696 | ENA-SOL | 26.93 | ACCEPT |
| 8 | K690 | SEI-SOL | 25.11 | ACCEPT |
| 9 | K729 | INJ-ATOM | 18.75 | ACCEPT |
| 10 | K694 | TIA-SOL | 19.09 | CONDITIONAL |
| 11 | K684 | SOL-INJ | 9.65 | ACCEPT |
| 12 | K736 | TIA-AVAX | 12.97 | CONDITIONAL |
| 13 | **K740** | **INJ-AVAX** | **14.58** | **REJECT (G5c AVAX saturation)** |

---

## Statistical Summary

| Stat | Value |
|------|-------|
| ADF statistic | -13.6116 |
| ADF p-value | 1.87e-25 |
| Stationary at 1% | YES |
| OU lambda | 0.1061 |
| OU half-life | 6.53h (0.27d) |
| Mean reversion quality | FAST |
| ACF 1h | 0.8939 |
| ACF 24h | 0.2334 |
| ACF 168h | 0.0329 |

---

## Next Generalization Candidates

1. **ENA-AVAX** — ENA (Ethena LSD) vs AVAX subnet. New cross-cluster axis. Check G5c vs K484 critical.
2. **TIA-INJ** — DA-layer vs Cosmos DeFi. Both Cosmos cluster. G5d vs K729 INJ-ATOM required.
3. **INJ family exhausted** — K684 SOL-INJ (ACCEPT), K729 INJ-ATOM (ACCEPT), K740 INJ-AVAX (REJECT). No more INJ-based alt-alts viable without new ecosystem expansion.

---

## Closed Line Note

**Line CLOSED: INJ-AVAX alt-alt.** The G5c failure is structural (MR9 algebraic). Cannot be resolved by parameter tuning. Reopen condition: AVAX FR structurally decorrelates from BTC-AVAX carry OR INJ FR persistently dominates (structural ecosystem reversal).

---

*K339 REPO_ROOT | wave_k740_inj_avax_eval.{py,json,md} | 2026-05-30 19:06 JST*

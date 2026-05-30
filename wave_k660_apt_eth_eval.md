# K660 APT-ETH FR Differential Paired-Trade Evaluation

**Wave:** K660  
**Date:** 2026-05-30 JST  
**Decision:** BTC-BASE WINS — KEEP K512  
**K339 Pattern:** REPO_ROOT `/Users/nekonaomichi/crypto-lab`

---

## Executive Summary

K660 tests the ETH-base mechanism (established in K629 WLD-ETH) on K512 APT-BTC (family #1, OOS Sh=51.10, $302K/yr @$10M). The evaluation finds that APT-ETH is **BLOCKED-G5b** with a critical correlation of **0.966** between APT-ETH and APT-BTC OOS PnL — essentially the same trade. The root cause is structural: APT FR is deeply negative (-1.4%/yr) relative to both ETH (+10.6%/yr) and BTC (+11.6%/yr), making both strategies predominantly **long APT with different short legs**. ETH-base does not provide orthogonal alpha for APT family #1.

**Decision: Keep K512 APT-BTC ($302,195/yr @$10M).**

---

## 1. Motivation & Context

| Wave | Strategy | Decision | Sharpe (OOS) | Lesson |
|------|----------|----------|-------------|--------|
| K629 | WLD-ETH | ACCEPT | 19.90 | ETH-base unlocks WLD (was BLOCKED-G5 on JUP=0.46) |
| K632 | HYPE-ETH | CONDITIONAL | 12.99 | ETH-base worse than HYPE-BTC (Sh=24.49) → keep BTC |
| K658 | SOL-ETH | ACCEPT (ETH-base wins) | 29.66 | ETH-base better than SOL-BTC Sh=16.30 |
| **K660** | **APT-ETH** | **BLOCKED-G5b** | **54.27** | **ETH-base redundant (corr=0.966 with K512)** |

K512 APT-BTC: OOS Sh=51.10, ann=29.63%/yr, $302,195/yr @$10M, 12/16 gates PASS.

---

## 2. Data

- **APT FR:** `cache/k163_hl/hl_fr_APT.parquet` — 17,484 rows (2024-05-24 to 2026-05-23)
- **ETH FR:** `cache/k163_hl/hl_fr_ETH.parquet` — 17,512 rows
- **BTC FR:** `cache/k163_hl/hl_fr_BTC.parquet` — 17,512 rows (reference)

### FR Statistics

| Asset | Mean Ann FR | Std (hourly) |
|-------|------------|--------------|
| APT | -1.40%/yr | 5.01e-05 |
| ETH | +10.52%/yr | 1.91e-05 |
| BTC | +11.55%/yr | 1.76e-05 |
| APT-ETH diff | **-11.92%/yr** | 4.71e-05 |

**APT/ETH vol ratio: 2.64x** (>= 1.5 threshold: PASS)

---

## 3. Structural Analysis — Why ETH-Base Fails for APT

### The Core Problem

```
K512 (BTC-base): fr_diff = btc_fr - apt_fr
  → When diff > 0: BTC > APT → SHORT BTC, LONG APT
  → 93.6% of time: signal = +1 (long APT)

K660 (ETH-base): fr_diff = apt_fr - eth_fr  
  → When diff < 0: ETH > APT → SHORT ETH, LONG APT
  → 94.4% of time: signal = -1 (long APT via inverse)
```

**Both strategies are overwhelmingly LONG APT.** The short leg (BTC vs ETH) is a minor variation. With APT FR at -1.4%/yr sitting 12pp below ETH and 13pp below BTC, there is no directional ambiguity — the signal is always "collect the alt-token discount."

### OOS PnL Correlation: 0.9660

This is the decisive metric. The G5b threshold is 0.40. A correlation of 0.966 means the two strategies are near-identical. Holding both would not diversify — it would merely double APT delta exposure.

### Contrast with K658 SOL-ETH (PASS)

SOL FR mean (~7.7%/yr) sits between ETH (~10.6%/yr) and BTC (~11.6%/yr):
- SOL-ETH diff = -2.8%/yr (small negative) → allows directional switching
- SOL-BTC diff = +3.7%/yr (positive) → opposite sign
- Result: K658 OOS PnL corr vs K476 = **0.213** (well below 0.40)

APT FR (-1.4%/yr) sits far below BOTH → no switching → corr=0.966.

---

## 4. Signal Performance

### K660 APT-ETH (W=168h, always-on)

| Period | Sharpe | Ann Return | Max DD | Entries/yr |
|--------|--------|-----------|--------|------------|
| Full (2yr) | 31.58 | 15.33% | -0.74% | 28.4 |
| IS (70%) | 19.96 | 8.32% | -0.74% | 39.3 |
| OOS (30%) | **54.27** | **31.55%** | -0.24% | **3.4** |

### Grid Search Top 5 (12 configs)

| Window | Thresh | IS Sh | OOS Sh | OOS Ann | Entries/yr |
|--------|--------|-------|--------|---------|------------|
| 84h | 0.0 | 20.05 | **54.46** | 31.86% | 6.7 |
| 168h | 0.0 | 19.96 | 54.27 | 31.55% | 3.4 |
| 336h | 0.0 | 21.37 | 53.23 | 31.11% | 3.4 |
| 504h | 0.0 | 23.18 | 52.79 | 30.90% | 3.4 |
| 336h | 0.25 | 11.50 | 50.70 | 29.98% | 6.7 |

Canonical W=168h selected (consistent with family).

---

## 5. §6 Gate Results (8 Gates)

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1: OOS Sharpe | 54.27 | >= 1.0 | **PASS** |
| G2: Perm p-value | 0.000 | <= 0.05 | **PASS** |
| G3: DSR Bonferroni | 0.00e+00 | < 0.00417 | **PASS** |
| G4: WF 4-fold | [5.41, 27.33, 41.31, 70.90] | all > 0 | **PASS** |
| G5a: vs ETH-BTC K449 | 0.0099 | < 0.40 | **PASS** |
| **G5b: vs APT-BTC K512** | **0.9660** | **< 0.40** | **FAIL (BLOCKED)** |
| G5c: vs SOL-ETH K658 | 0.0496 | < 0.40 | **PASS** |
| G5d: vs WLD-ETH K629 | 0.0292 | < 0.40 | **PASS** |
| G6: Trades/yr | 3.4 | >= 30 | **FAIL (structural)** |
| G7: Ann ret 4x | 126.2% | > 5% | **PASS** |

**Gates passed: 5/7 (excl. G5b sub-checks counted separately)**

**CRITICAL FAIL: G5b — APT-ETH vs APT-BTC K512 OOS PnL corr = 0.9660**

---

## 6. Statistical Validation

| Test | Result | Interpretation |
|------|--------|---------------|
| ADF stat | -11.68, p=1.75e-21 | APT-ETH FR diff stationary at 1% level |
| OU half-life | 6.3h | Strong mean reversion — supports carry strategy |
| APT/ETH vol ratio | 2.64x | >> 1.5 threshold (sufficient vol differential) |
| Perm p-value | 0.000 | Signal not explained by chance |
| DSR Bonferroni | 0.00e+00 | Survives 12-trial correction |
| WF 4-fold | all positive | Time-stable signal |

---

## 7. APT-BTC vs APT-ETH Full Comparison

| Metric | K512 APT-BTC | K660 APT-ETH | Winner |
|--------|-------------|-------------|--------|
| OOS Sharpe | 51.10 | **54.27** | K660 (marginally) |
| OOS Ann Return | 29.63% | 31.55% | K660 |
| OOS Max DD | -0.14% | -0.24% | K512 |
| OOS Entries/yr | 3.4 | 3.4 | Tie |
| Net/yr @$10M | $302,195 | $321,855 | K660 |
| **OOS PnL Corr** | — | **0.9660** | **BLOCKED** |
| Gates | 12/16 | 5/7 | K512 |
| Status | **ACCEPT** | **BLOCKED-G5b** | **K512** |

**K660 paradox:** Higher Sharpe on OOS but structurally identical to K512. The marginal Sharpe improvement reflects ETH FR's lower residual volatility as base (1.91e-05 vs BTC 1.76e-05 std — actually similar), but the alpha source is the same: APT's persistent FR discount.

---

## 8. Profit Projection

| Scenario | Value |
|----------|-------|
| Strategy | APT-ETH FR differential (3% sleeve, 4x leverage) |
| OOS Ann Return (1x) | 31.55% |
| OOS Ann Return (4x) | 126.20% |
| Notional @$10M AUM | $1,200,000 |
| Gross USDC/yr | $378,654 |
| Net USDC/yr (15% friction) | **$321,855** |
| Daily USDC | $881 |

Note: **NOT actionable** — blocked by G5b. K512 ($302,195/yr) is the live strategy.

---

## 9. ETH-Base Mechanism: Pattern Recognition

The ETH-base mechanism works differently across the family:

| Alt Token | Alt FR Mean | ETH-base Outcome | Why |
|-----------|------------|-----------------|-----|
| WLD | ~2.7%/yr | ACCEPT (K629, unlocked) | WLD FR near ETH level → directional balance |
| HYPE | ~22.8%/yr | CONDITIONAL worse (K632) | HYPE >> ETH → mostly short HYPE both ways |
| SOL | ~7.7%/yr | ACCEPT better (K658) | SOL FR between BTC and ETH → reversal possible |
| **APT** | **-1.4%/yr** | **BLOCKED (K660)** | **APT << ETH << BTC → always long APT** |

**Rule:** ETH-base helps when alt FR is near or above ETH level (enables directional flip). ETH-base fails when alt FR is far below both BTC and ETH (no flip, same direction always).

---

## 10. Decision

**DECISION: BTC-BASE WINS — KEEP K512**

- K512 APT-BTC: OOS Sh=51.10, $302,195/yr @$10M — **retained**
- K660 APT-ETH: BLOCKED-G5b (corr=0.966) — **not actionable**
- No dual-sleeve: strategies are near-identical, not orthogonal
- Next: ETH-base mechanism has now been tested on 4 family members (WLD, HYPE, SOL, APT)

---

## Deliverables

- `wave_k660_apt_eth_eval.py` — evaluation script (K339 pattern)
- `wave_k660_apt_eth_eval.json` — structured results
- `wave_k660_apt_eth_eval.md` — this report
- `report.html` — badge added

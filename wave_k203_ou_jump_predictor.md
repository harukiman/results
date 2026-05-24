# Wave K203 — OU+Jump FR Predictor: Full Report

**Date:** 2026-05-25  
**Runtime:** 189.6 seconds  
**Parent waves:** K175 (XRP+SUI maker FR strategy), K190 (DAR(2,1) direction filter)  
**Objective:** Implement OU+Jump FR predictor as upgrade candidate for K190's DAR model; test direction accuracy and downstream K175 impact.

---

## Executive Summary

K203 implemented a full Ornstein-Uhlenbeck + Jump process model for 8h Bybit funding rate prediction on XRP and SUI, with Hawkes self-excitation, walk-forward (90d train / 30d test) evaluation, and jump detection at k=2.5σ. The model is internally coherent and passes §6 standalone gates (6/7), but **fails all three K190 replacement acceptance gates**:

| Gate | Required | K203 Result | Pass? |
|------|----------|-------------|-------|
| Direction accuracy +3pp over K190 (≥69%) | ≥0.693 | 0.649 (mean) | FAIL |
| K175 OOS Sh lift >+0.05 over K190 | ≥2.173 (gross) | 1.747 (gross) | FAIL |
| Half-life in 2–6h range | median 2–6h | 8.4h (XRP) / 10.1h (SUI) | FAIL |

**Verdict: K203 REJECTED as K190 replacement.** K204 path: ensemble integration or regime-conditional OU.

---

## 1. Data

| Symbol | Events | FR mean | FR std |
|--------|--------|---------|--------|
| XRPUSDT | 2,190 | 0.000050 | 0.000158 |
| SUIUSDT | 2,190 | 0.000060 | 0.000156 |

Source: `cache/bybit_fr_{XRP,SUI}USDT_730d.parquet` — 730 days at 8h cadence.

---

## 2. OU Parameter Estimation and Half-Life

Both OLS and MLE were run on the full history. OLS and MLE agree exactly (same theta/mu, sigma differs due to conditional vs. unconditional variance).

### Full-history estimates

| Symbol | θ (theta) | μ (long-run mean) | σ_OU (OLS) | Half-life |
|--------|-----------|-------------------|------------|-----------|
| XRP | 1.3215 | 0.0000495 | 0.000152 | **4.20h** |
| SUI | 1.0023 | 0.0000603 | 0.000145 | **5.53h** |

### Walk-forward rolling estimates (90d windows, 20 segments)

| Symbol | HL mean | HL median | HL std | In 2–6h range? |
|--------|---------|-----------|--------|----------------|
| XRP | 9.57h | **8.35h** | 6.88h | **No** |
| SUI | 12.17h | **10.11h** | 9.34h | **No** |

**Critical finding:** Full-history OU estimation confirms the academic 2–6h half-life (XRP: 4.2h, SUI: 5.5h), consistent with arxiv 2605.06405. However, **rolling 90d window estimates yield longer half-lives** (8–12h median). This divergence indicates non-stationarity in the mean-reversion rate: faster reversion in some regimes, slower in others. The walk-forward median reflects recent regime behavior rather than the long-run average.

---

## 3. Jump Detection Log

Jump threshold: k=2.5σ_OU from long-run mean μ.

### Full-history jumps (k=2.5)

| Symbol | Count | Rate | Mean magnitude | Max magnitude | P95 magnitude |
|--------|-------|------|----------------|---------------|---------------|
| XRP | 27 | 1.23% | 4.75σ | 38.4σ | 6.9σ |
| SUI | 49 | 2.24% | 4.21σ | 35.9σ | 5.4σ |

### OOS jump counts (walk-forward, 1800 OOS events)

| Symbol | Jump count OOS | Jump rate OOS |
|--------|---------------|---------------|
| XRP | 100 | 5.56% |
| SUI | 138 | 7.67% |

**Observations:**
- Jumps are rare (1–2% by full-history σ) but extreme (mean 4–5σ, max >35σ). These are genuine funding rate spikes during market stress or listing events.
- OOS jump rate is higher (5–8%) because rolling σ estimates from shorter windows are smaller, making the k=2.5σ threshold easier to breach.
- SUI has 2x more jumps than XRP, consistent with its higher volatility regime.
- Jump magnitude distribution is heavy-tailed: max jump is 38.4σ (XRP) and 35.9σ (SUI).

### Jump K sweep

| k | XRP jumps (OOS) | SUI jumps (OOS) |
|---|-----------------|-----------------|
| 2.0 | 160 | 195 |
| 2.5 | 100 | 138 |
| 3.0 | 73 | 106 |

---

## 4. Direction Accuracy: K190 DAR vs K203 OU+Jump

| Model | XRP dir_acc | SUI dir_acc | Mean |
|-------|------------|------------|------|
| K190 DAR(2,1) | **65.93%** | **66.67%** | **66.30%** |
| K203 OU+Jump (k=2.5, Hawkes) | 64.58% | 65.16% | 64.87% |
| K203 OU+Jump (k=2.5, no Hawkes) | ~64.5% | ~65.2% | ~64.9% |
| K203 sweep k=2.0 | 64.65% | 65.40% | 65.03% |
| K203 sweep k=3.0 | 63.97% | 65.32% | 64.65% |

**Finding:** K203 direction accuracy (64.9%) is **1.4pp BELOW K190** (66.3%), not above. The OU+Jump combined model actually hurts prediction relative to the simpler DAR(2,1) for this data. The jump indicators add noise to the regression rather than signal. The OOS R² values are weakly positive (XRP: 0.031, SUI: 0.101) confirming some predictive content, but it is weaker than K190.

---

## 5. K175 Strategy Backtest: Full Comparison

### Three-way comparison (full sample)

| Strategy | Sh_net | Sh_gross | OOS Sh_net | OOS Sh_gross | n_trades/yr |
|----------|--------|----------|-----------|-------------|------------|
| K175 baseline | 1.333 | 1.423 | 1.930 | **2.036** | — |
| K190 DAR(2,1) | 1.419 | 1.505 | 2.024 | **2.123** | 73 |
| K203 OU+Jump (primary) | 1.030 | 1.131 | 1.613 | **1.747** | 64 |
| K203 no Hawkes | 1.078 | 1.179 | 1.725 | **1.856** | 64 |

### OOS Sharpe delta vs K190

| vs K190 OOS gross Sh (2.123) | Delta |
|------------------------------|-------|
| K203 OU+Jump primary | **-0.376** |
| K203 no Hawkes | **-0.267** |

K203 underperforms K190 by -0.27 to -0.38 in OOS gross Sharpe. The filter is too restrictive (fewer trades: 64/yr vs 73/yr) and filters out some true positives along with noise.

### K203 Primary — §6 Gates

| Gate | Result |
|------|--------|
| G1: Sh_net ≥ 1.0 | PASS (1.030) |
| G2: OOS Sh_net ≥ 0.5 | PASS (1.613) |
| G3: OOS/IS ratio ≥ 0.5 | PASS (2.02x) |
| G4: All WF folds positive | PASS ([1.077, 0.985, 1.044]) |
| G5: Perm p ≤ 0.05 | PASS (0.000) |
| G6: DSR ≥ 0.95 | FAIL (0.000) |
| G7: Trades/yr ≥ 20 | PASS (64) |

**§6 verdict: PASS (6/7)** — K203 has real statistical edge as a standalone signal, but underperforms K190.

### K175 WF fold detail (K203 primary)

| Fold | Sh_net | Sh_gross |
|------|--------|----------|
| Fold 1 | 1.077 | 1.141 |
| Fold 2 | 0.985 | 1.104 |
| Fold 3 | 1.044 | 1.172 |

All folds positive — consistency is good, overall level is lower than K190.

---

## 6. Per-Symbol Performance

### K203 Primary

| Symbol | Sh_net | Sh_gross |
|--------|--------|----------|
| XRP | 1.235 | 1.320 |
| SUI | 0.462 | 0.528 |

SUI remains weak across all K203 variants (0.46–0.59 net). K190 also showed this (SUI 0.64 net). The OU+Jump filter does not help SUI specifically.

---

## 7. Hawkes Excitation Effect

Adding Hawkes self-excitation (`g=0.3, decay=0.5`) worsens performance vs. pure OU+Jump:
- K203 Hawkes: OOS Sh_net 1.613, OOS Sh_gross 1.747
- K203 no Hawkes: OOS Sh_net **1.725**, OOS Sh_gross **1.856**

The Hawkes intensity creates spurious "high-excitation" periods that filter out some valid entries. **No Hawkes is better for this dataset.**

---

## 8. Root Cause Analysis

### Why K203 underperforms K190?

1. **Estimation window mismatch:** Rolling 90d OU parameters yield θ estimates that reflect non-stationary regimes (sometimes high reversion, sometimes low). OLS AR(1) of the simple DAR model implicitly handles this via shorter rolling windows without claiming a specific mean-reversion structure.

2. **Jump indicator overfitting:** In 8h FR data, genuine jumps (>2.5σ) are rare (1–2% by full-history σ). In rolling windows, they inflate to 5–8% because local σ is smaller. These "jumps" often precede continued extreme FR (not reversion), so Jump_t = 1 is a noisy predictor.

3. **Half-life stationarity:** Full-history OU gives XRP HL=4.2h (academic range), but rolling HL=8.4h. The model conditions on the wrong HL in real-time, degrading prediction quality.

4. **DAR advantage:** DAR(2,1) is an autoregressive model that automatically adapts to any AR structure including mild OU patterns, without requiring an explicit structural assumption. When the structural assumption is wrong (rolling HL ≠ true HL), DAR wins by flexibility.

---

## 9. Acceptance Evaluation

| Acceptance Gate | Required | Achieved | Pass? |
|-----------------|----------|----------|-------|
| Dir acc > K190 by +3pp (≥69%) | ≥0.693 | 0.649 | **FAIL** |
| K175 OOS Sh lift > +0.05 vs K190 | ≥2.173 gross | 1.747 gross | **FAIL** |
| Half-life in 2–6h (rolling window) | median 2–6h | 8.4h/10.1h | **FAIL** |
| **Overall** | All 3 pass | 0/3 pass | **REJECTED** |

---

## 10. Verdict and K204 / K198 Ensemble Integration Plan

### Verdict: K203 REJECTED as K190 replacement

K203 implements the arxiv 2605.06405 + SSRN 5290137 OU+Jump model faithfully. The full-history half-life estimates (XRP: 4.2h, SUI: 5.5h) confirm the academic 2–6h finding. However, the **walk-forward rolling estimates yield 8–12h** due to non-stationarity, which degrades real-time prediction. Direction accuracy (64.9%) falls below K190's DAR(2,1) (66.3%), and the K175 OOS Sharpe is lower by -0.38.

### K204 Recommended Paths

**Path A: Regime-conditional OU (highest probability of fix)**
- Segment history into "normal" and "stress" regimes via volatility threshold
- Estimate separate OU parameters per regime; use regime-state classifier at prediction time
- Expected: rolling HL converges to full-history HL within regime, recovering 4–5h range

**Path B: Multi-scale OU (directly from arxiv 2605.06405)**
- Fit two OU components: fast (HL ~2–4h) + slow (HL ~24–48h)
- dFR = θ_fast(μ_fast - FR) + θ_slow(μ_slow - FR) + Jump + dW
- Combined prediction leverages both short-term and medium-term mean reversion

**Path C: K198 Ensemble Integration (safe path, no replacement needed)**
- Add OU residual as a new feature to K198 Ridge regression allocator
- Feature: `ou_resid_t = FR_t - (alpha + beta*FR_{t-1})` — deviations from OU fit
- K198 learns the optimal weight for ou_resid alongside existing K175_DAR (K190) signal
- This sidesteps the direction filter issue entirely; let Ridge regression determine which predictor to trust

**Path D: Extended training window**
- Current: 90d train / 30d test. Try 180d train / 30d test
- Longer training reduces parameter variance in OU estimation
- Trade-off: slower adaptation to regime change

### K204 Recommendation

Implement **Path C (K198 ensemble integration)** as lowest-risk K204, and **Path A (regime-conditional)** as K205 exploratory. Path C requires minimal new backtest infrastructure and directly extends K198's already-deployed Ridge allocator.

---

## Appendix: Key Configuration

```
OU_WINDOW = 300 events (100 days)
OU_REFIT = 50 events
JUMP_K = 2.5 (primary), sweep [2.0, 2.5, 3.0]
HAWKES_DECAY = 0.5, HAWKES_G = 0.3
WF_TRAIN = 270 events (90 days)
WF_TEST = 90 events (30 days)
DT = 1 event = 8 hours
COST = 2bp/side slippage, 0 maker fee
```

---

*Generated by wave_k203_ou_jump_predictor.py — Runtime 189.6s*

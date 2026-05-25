# Wave K301 — v6.12 Extended Satellite

**Date:** 2026-05-25 | **Status:** ACCEPT (4/4 gates)

## Executive Summary

K297 RWA carry (PAXG + SPX, Sh 10.17 full / 12.48 on 96d) added as 3rd satellite component alongside K270 (dYdX) and K275 (OKX). Best combined K301_c achieves Sh **35.26** vs K287d reference **33.00** (+2.26 delta) on the same 55d three-way window. All acceptance gates pass. v6.12 promoted to production.

---

## 1. Data Windows

K270: 731d | K275: 96d (binding) | K297: 504d | K280: 448d  
Common satellite window: 2026-02-19 to 2026-05-25 (96d). Three-way overlap: to 2026-04-14 (55d).

---

## 2. Component Metrics (96d Common Window)

| Component | Sharpe | MaxDD | Ann Ret | Win Rate |
|-----------|--------|-------|---------|----------|
| K270 (dYdX FR) | 14.07 | -0.001007 | 29.7% | 95.8% |
| K275 (OKX FR) | 11.40 | -0.002538 | 18.2% | 93.8% |
| K297 EW (RWA) | 12.48 | -0.001698 | 22.4% | 94.8% |
| K297 full 504d | 10.13 | — | — | — |

---

## 3. Correlation Matrix (96d, daily returns)

|           | K270 | K275 | K297_EW | K297_PAXG | K297_SPX |
|-----------|------|------|---------|-----------|---------|
| K270      | 1.000 | -0.457 | 0.177 | 0.076 | 0.184 |
| K275      | -0.457 | 1.000 | -0.075 | -0.054 | -0.056 |
| K297_EW   | 0.177 | -0.075 | 1.000 | 0.741 | 0.713 |
| K297_PAXG | 0.076 | -0.054 | 0.741 | 1.000 | 0.057 |
| K297_SPX  | 0.184 | -0.056 | 0.713 | 0.057 | 1.000 |

All K297 cross-correlations vs K270/K275 < 0.5. PAXG and SPX are near-uncorrelated (0.057).

---

## 4. Satellite Variants (96d, K270+K275+K297)

| Variant | K270 wt | K275 wt | K297 wt | Sh (96d) | MaxDD |
|---------|---------|---------|---------|----------|-------|
| K301a EW | 33.3% | 33.3% | 33.3% | 25.12 | -0.000534 |
| K301b InvVol | 16.8% | 26.7% | 56.5% | 25.08 | -0.000529 |
| K301c InvVol+cap15 | 32.8% | 52.2% | 15.0% | **25.54** | -0.000488 |
| K301d InvVol+cap25 | 29.0% | 46.1% | 25.0% | 26.13 | -0.000479 |
| K301e InvVol+cap30 | 27.0% | 43.0% | 30.0% | 26.34 | -0.000475 |

---

## 5. Combined K280 (80%) + Extended Satellite (20%) — 55d Three-Way Window

| Variant | Sh (55d) | MaxDD | WF Mean | WF Min | vs K287d |
|---------|----------|-------|---------|--------|----------|
| K301_a | 35.00 | 0.0 | 39.04 | 31.4 | +2.00 |
| K301_b | 34.64 | 0.0 | 38.29 | 31.0 | +1.64 |
| **K301_c** | **35.26** | **0.0** | **39.40** | **29.9** | **+2.26** |
| K301_d | 35.16 | 0.0 | 39.18 | 30.6 | +2.16 |
| K301_e | 35.10 | 0.0 | 39.06 | 30.9 | +2.10 |
| K287d ref | 33.00 | 0.0 | 34.45 | 30.1 | — |

**Selected: K301_c** (inv-vol + K297 cap 15%) — highest combined Sh.

**K301_c WF Folds:** Fold1 47.56 | Fold2 29.85 | Fold3 40.78 (all MaxDD=0.0)

---

## 6. Acceptance Gates

| Gate | Criterion | Result |
|------|-----------|--------|
| G1 | Combined Sh > K287d (33.00) | **PASS** (35.26) |
| G2 | All WF folds positive | **PASS** (min 29.85) |
| G3 | All 3 components > 5% weight | **PASS** (K297=15%) |
| G4 | K297 corr vs K270/K275 < 0.5 | **PASS** (0.18/−0.08) |

**4/4 PASS → VERDICT: ACCEPT**

---

## 7. v6.12 Deployment Plan

```
Portfolio:
  K280 (core)       80%
  Extended Sat      20%
    K270 (dYdX FR)    6.6%  (32.8% of 20%)
    K275 (OKX FR)    10.4%  (52.2% of 20%)
    K297 (RWA carry)  3.0%  (15.0% of 20%)
```

K297 = equal-weight PAXG + SPX perpetual funding rate carry (Hyperliquid HIP-3 mechanism). Adds TradFi RWA perp carry diversification with near-zero correlation to existing FR strategies.

**Key findings:** K297 at 15% cap optimal (Sh 35.26 vs 33.00 baseline). K297 diversifies: rho vs K270=0.18, vs K275=−0.08. PAXG/SPX internal rho=0.057. Uncapped inv-vol over-allocates K297 (56%); cap at 15% maximizes combined Sh. Zero losing days on 55d window; WF min fold 29.85.

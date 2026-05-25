# Wave K299 — K208 + HL predictedFundings vs DAR(2,1)

**Date:** 2026-05-25 | **Status:** COMPLETE — **REJECT**

## Objective
Replace DAR(2,1) in K208 with HL predictedFundings (realized-FR proxy, K298 ρ=0.9989).
K299 gate: `realized_spread > 0` (current Bybit FR > HL FR).
K208 gate: `DAR_predicted_bybit_fr > hl_fr` (multi-step AR).

---

## K208 Baseline (Reproduced Exactly)
OOS Sh=17.53 | WF mean=13.94 | WF min=7.39 | Folds=[7.39, 18.46, 12.82, 17.10]

## K299 Results

| Metric | K208 DAR(2,1) | K299 Realized FR | Δ |
|---|---|---|---|
| OOS Sharpe | **17.53** | 16.52 | **-1.01** |
| WF mean | 13.94 | **17.10** | +3.16 |
| WF min | 7.39 | **14.28** | +6.89 |
| WF folds | [7.39, 18.46, 12.82, 17.10] | [15.69, 20.95, 14.28, 17.48] | all pos |
| MaxDD OOS | -0.000275 | -0.000341 | worse |

ΔOOS K299 vs K208: **-1.01** (threshold: +1.0). **Fails acceptance.**

## Per-Symbol Highlights

| Symbol | K208 Sh | K299 Sh | Δ | Note |
|---|---|---|---|---|
| AXS | 0.80 | 15.46 | +14.67 | DAR over-filtered (1.1% vs 59% in-mkt) |
| SUI/XRP/IMX | avg 7.1 | avg 8.7 | +1.6 | K299 better |
| SOL | 4.29 | 3.56 | -0.73 | DAR correctly filters |
| SAND | 12.75 | 12.17 | -0.58 | DAR correctly filters |

## §6 Gates: K299 — 5/7 PASS
PASS: OOS>15, WF_min>0, all folds positive, perm p≤0.10, MaxDD OK  
FAIL: OOS < K208 baseline, DSR < 0.5

## K280 Integration
K280-with-K208 sim OOS Sh=26.33 → K280-with-K299: 24.47 (Δ=-1.85). K299 degrades ensemble.

## Acceptance Verdict

| Criterion | Result |
|---|---|
| Standalone OOS lift ≥ +1.0 | FAIL (Δ=-1.01) |
| All 4 WF folds positive | PASS |
| K280 integration lift ≥ 0 | FAIL (Δ=-1.85) |

**REJECT — 1/3 criteria met.**

---

## Verdict on DAR Replacement

**DAR(2,1) was ADDING value beyond the simple spread-sign gate.**

The DAR model predicts when the spread will *persist* positive, filtering whipsaw entries.
The naive `spread > 0` gate enters transient positives that don't persist (SOL, SAND).
DAR's cost: it severely over-filters AXS (1.1% in-market vs 59% optimal).

**Actions:**
1. Keep K208 DAR(2,1) as primary — not replaced
2. Use predictedFundings as live intra-period monitor (poll 5min, confirm sign)
3. Investigate AXS-specific DAR config (nearly always excluded; simple gate superior)
4. K280 v6.10.2 unchanged — no integration candidate from K299

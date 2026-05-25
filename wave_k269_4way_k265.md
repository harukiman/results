# Wave K269 — K246a + K265 4-Way Meta-Ensemble Report
*As of 2026-05-25 | K269 → v6.10 candidate*

---

## PRIMARY: Gate 0 — K265 Validation on K246a ML Window (448 days: 2025-01-22 → 2026-04-14)

| Metric | K265 (own window) | K265 (K246a window) | Delta |
|---|---|---|---|
| OOS Sharpe | 13.10 | 8.45 (full-window) | -4.65 (K225 pattern confirmed) |
| WF min Sharpe | 10.10 | **6.07** (Fold 1) | Below K265 own-window |
| All folds positive | Yes | **Yes** | Gate 0 PASS |
| MaxDD | -0.00208 | -0.01224 | Fold 1 stress |

**Gate 0 verdict: PASS (all folds positive). K265 shifts down significantly on K246a window as feared (K225 pattern), but all 4 folds remain positive.**

WF folds on K246a window:
- Fold 1 [2025-01-22 → 2025-05-13]: Sh=6.07  MaxDD=-0.0122
- Fold 2 [2025-05-14 → 2025-09-02]: Sh=12.51  MaxDD=-0.0010
- Fold 3 [2025-09-03 → 2025-12-23]: Sh=18.06  MaxDD=-0.0001
- Fold 4 [2025-12-24 → 2026-04-14]: Sh=9.95   MaxDD=-0.0021

---

## 4x4 Correlation Matrix (K246a window)

|       | K198   | K208   | K226   | K265   |
|-------|--------|--------|--------|--------|
| K198  | 1.0000 | +0.063 | +0.044 | +0.004 |
| K208  | +0.063 | 1.0000 | -0.002 | +0.086 |
| K226  | +0.044 | -0.002 | 1.0000 | +0.038 |
| K265  | +0.004 | +0.086 | +0.038 | 1.0000 |

K265 ρ vs K208 rose from 0.057 (own window) to **0.086** on K246a window — mild K251 pattern, still very low. Diversification remains strong.

---

## Walk-Forward 4-Fold Results (per variant)

Reference K246a: OOS_Sh=12.69 | WF_min=8.93 | MaxDD=-0.001145 | Threshold OOS_Sh > 12.89

| Variant | OOS_Sh | WF_min | WF_mean | OOS_MaxDD | K265 w | All-pos | NZ | Verdict |
|---|---|---|---|---|---|---|---|---|
| K269a (inv-vol K226≤20% K265≤20%) | **15.745** | 9.054 | — | -0.000191 | 9.7% | Y | Y | **PASS** |
| K269b (inv-vol uncapped)           | 15.745 | 9.054 | — | -0.000191 | 9.7% | Y | Y | **PASS** |
| K269c (K226≤20% K265≤25%)         | 15.745 | 9.054 | — | -0.000191 | 9.7% | Y | Y | **PASS** |
| K269d (K226≤20% K265≤30%)         | 15.745 | 9.054 | — | -0.000191 | 9.7% | Y | Y | **PASS** |
| K269e (Equal 25/25/25/25)          | 3.020  | 1.023 | — | -0.039438 | 25%  | Y | Y | FAIL |
| K269f (MVP)                        | 10.969 | 7.848 | — | -0.000087 | neg  | Y | N | FAIL |

Note: K269a–K269d produce identical OOS weights because inv-vol assigns K265 ~9.7% (below all caps 20–30%). Caps not binding. K208 dominates (87%) given its ultra-low vol on this window.

---

## Acceptance Gate Summary (K269a as best)

| Gate | Threshold | K269a | Status |
|---|---|---|---|
| G1: OOS_Sh > K246a+0.20 | > 12.89 | 15.745 | PASS (+3.05) |
| G2: WF_min ≥ K246a | ≥ 8.93 | 9.054 | PASS (+0.12) |
| G3: MaxDD ≤ K246a | ≤ -0.001145 | -0.000191 | PASS (better) |
| G4: All non-zero weights | all > 0 | K198=3% K208=87% K226=0.3% K265=9.7% | PASS |
| G5: All WF folds positive | all > 0 | min=9.054 | PASS |

---

## Risk Notes

1. **K265 downshift confirmed**: Own-window OOS 13.10 → K246a-window full Sh 8.45. Fold 1 Sharpe 6.07 is weakest. This is the K225 pattern. K265 participates at ~10% weight, so portfolio impact is bounded.
2. **K208 dominance (87%)**: inv-vol naturally concentrates in K208 which has ultra-low vol on this window. This is the same structural outcome as K246a. Not a new risk.
3. **K226 near-zero (0.3%)**: Low weight but non-zero; satisfies G4.
4. **Equal-weight (K269e) fails badly**: Confirms K265 alone cannot carry 25% weight on this window.

---

## Verdict: K269 → v6.10 PROMOTED

**Best variant: K269a** (inv-vol + K226 cap 20% + K265 cap 20%)

- OOS Sharpe: **15.745** (+3.05 vs K246a 12.69)
- WF min: **9.054** (+0.12 vs K246a 8.93)
- OOS MaxDD: **-0.000191** (4x improvement vs K246a -0.001145)
- Weights: K198=3.0% / K208=87.0% / K226=0.3% / K265=9.7%
- All 5 acceptance gates: **PASS**

K265 adds marginal diversification (~10% weight) but is not a dominant contributor at this window. The +3.05 Sharpe lift relative to K246a comes primarily from K208 performance on the OOS tail, not K265 alpha injection. The ensemble is robust (all WF folds positive, MaxDD improved).

**Production recommendation: Deploy K269a as v6.10.**

# K483 v6.22 Kelly Criterion Re-optimization

**Date:** 2026-05-30 02:50 JST  
**Wave:** K483  
**Version:** v6.22a candidate  
**Decision:** RECOMMEND 1/4 Kelly MV weights — +$150,300/yr @ $10M vs K479 heuristic

---

## Executive Summary

K483 implements Kelly criterion / mean-variance re-optimization for the v6.22 9-sleeve portfolio.
Key findings:

- **1/4 Kelly MV** (primary): +$150,300/yr lift @ $10M | +$1,503,000/yr @ $100M vs K479 heuristic
- **HL cap (65%) is binding**: Kelly wants more K376 exposure; HL ceiling is the active constraint
- **K476 cap (5%) binding**: confirms conservative paper-trade gate is appropriate
- **Fractional Kelly interp**: +$39,725/yr @ $10M (more balanced, retains all 9 sleeves)
- **K427 lesson confirmed**: Kelly corners to highest-mu sleeve (K376 8%); floor constraint essential

---

## Phase 1: Sleeve (mu, sigma) Parameters

| Sleeve | Source | mu annual | sigma annual | Sharpe | HL_frac |
|---|---|---|---|---|---|
| K280 | K427 task spec (1x deployed) | 5.00% | 4.00% | 1.25 | 0.50 |
| K297' | K427 realized; task spec 4.5%/1.5% | 4.50% | 1.50% | 3.00 | 1.00 |
| sUSDe | K477: 7d APY 3.88% | 3.72% | 0.50% | 7.44 | 0.00 |
| Spark sUSDS | K477: spot 3.34%, 30d 3.67% | 3.34% | 0.60% | 5.57 | 0.00 |
| K376 | Task spec momentum 8%/6%/1.33 | 8.00% | 6.00% | 1.33 | 1.00 |
| K449 | K476 JSON OOS: 1.37%/Sh=5.66 | 1.30% | 2.50% | 0.52 | 1.00 |
| K476 | K476 JSON OOS 4x: 19.55% net 18.7% | 18.70% | 9.00% | 2.08 | 1.00 |
| K457 | Task spec basket 5%/4%/1.25 | 5.00% | 4.00% | 1.25 | 0.50 |
| Cash | Risk-free buffer | 0.00% | 0.00% | 0.00 | 0.00 |

**Note on mu calibration:** K280 task spec = 5% (conservative 1x deployed return); K427 empirical
was 10.94% but includes leverage. K476 sleeve return 18.7% represents 4x leveraged paired-trade
at 3% AUM sleeve weight (from K476/K479 net annual calculation). These are sleeve-level effective
returns, not underlying strategy returns.

---

## Phase 2: Correlation Matrix

| | K280 | K297' | sUSDe | Spark | K376 | K449 | K476 | K457 | Cash |
|---|---|---|---|---|---|---|---|---|---|
| K280 | 1.00 | 0.10 | 0.00 | 0.00 | 0.20 | 0.15 | 0.15 | 0.30 | 0.00 |
| K297' | 0.10 | 1.00 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | 0.00 |
| sUSDe | 0.00 | 0.10 | 1.00 | 0.50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Spark | 0.00 | 0.10 | 0.50 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| K376 | 0.20 | 0.10 | 0.00 | 0.00 | 1.00 | 0.10 | 0.20 | 0.10 | 0.00 |
| K449 | 0.15 | 0.10 | 0.00 | 0.00 | 0.10 | 1.00 | 0.15 | 0.10 | 0.00 |
| K476 | 0.15 | 0.10 | 0.00 | 0.00 | 0.20 | 0.15 | 1.00 | 0.25 | 0.00 |
| K457 | 0.30 | 0.10 | 0.00 | 0.00 | 0.10 | 0.10 | 0.25 | 1.00 | 0.00 |
| Cash | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |

Sources: K480 G5 (K280-K457=0.30 BTC overlap), K476 G5b (K449-K476=0.15 confirmed K478),
K476 G5c (K476-K457=0.25), K476 G5d (K376-K476=0.20), task brief defaults.

---

## Phase 3: Kelly Criterion Optimization

### Methodology

MV utility objective: **U = w'mu - (lambda/2) * w'Sigma*w**

- lambda=1: Full Kelly (maximize expected log-wealth growth rate)
- lambda=2: Half Kelly
- lambda=4: Quarter Kelly (primary)

Constraints:
- HL exposure <= 65%
- K280 weight: 50% floor (production anchor, K427 lesson) to 70% cap
- K476 weight <= 5% (paper-trade gate, conservative)
- K297' weight <= 20% (R12-16 compliance from K427)
- sUSDe + Spark <= 15% (stablecoin diversification cap)
- sum(w) = 1, w >= 0 (long-only)

**K427 lesson:** Unconstrained Kelly in crypto corners to highest-Sharpe or highest-mu sleeve.
For 3-sleeve K427: cornered to sUSDe (highest Sharpe). For 9-sleeve K483: corners to K376
(mu=8%, highest absolute return). K280 >= 50% floor prevents this, enforcing the proven
production anchor.

---

## Phase 4: Comparison Table

| Sleeve | K479 heuristic | 1/4 Kelly MV | 1/2 Kelly MV | Full Kelly MV | 1/4 Kelly interp |
|---|---|---|---|---|---|
| K280 | 65% | **50%** | 50% | 50% | 58.0% |
| K297' | 5% | **0%** | 0% | 0% | 3.8% |
| sUSDe | 5% | **10%** | 10% | 10% | 7.5% |
| Spark sUSDS | 5% | **0%** | 0% | 0% | 3.8% |
| K376 | 5% | **35%** | 35% | 35% | 13.8% |
| K449 | 5% | **0%** | 0% | 0% | 3.8% |
| K476 | 3% | **5%** | 5% | 5% | 3.5% |
| K457 | 5% | **0%** | 0% | 0% | 4.5% |
| Cash | 2% | **0%** | 0% | 0% | 1.5% |

### Portfolio Metrics Comparison

| Metric | K479 heuristic | 1/4 Kelly MV | 1/4 Kelly interp | MaxSharpe (K280>=50%) | Full Kelly interp |
|---|---|---|---|---|---|
| mu annual | 5.10% | **6.61%** | 5.50% | 5.66% | 6.69% |
| vol annual | 2.84% | **3.31%** | 2.78% | 2.37% | 3.23% |
| Sharpe | 1.80 | **2.00** | 1.98 | 2.39 | 2.07 |
| HL exposure | 53.0% | **65.0%** | 56.0% | 59.4% | 65.0% |
| $10M profit/yr | $510,400 | **$660,700** | $550,125 | $565,963 | $669,300 |
| Lift vs K479 | -- | **+$150,300** | +$39,725 | +$55,563 | +$158,900 |

---

## Phase 5: Expected Profit Lift

### 1/4 Kelly MV (Primary Recommendation)

| Scale | K479 heuristic | 1/4 Kelly MV | Lift | Lift % |
|---|---|---|---|---|
| $10M AUM | $510,400/yr | **$660,700/yr** | **+$150,300/yr** | +29.4% |
| $100M AUM | $5,104,000/yr | **$6,607,000/yr** | **+$1,503,000/yr** | +29.4% |

### 1/4 Kelly Interpolation (Conservative Alternative)

| Scale | K479 heuristic | 1/4 Kelly interp | Lift | Lift % |
|---|---|---|---|---|
| $10M AUM | $510,400/yr | $550,125/yr | +$39,725/yr | +7.8% |
| $100M AUM | $5,104,000/yr | $5,501,250/yr | +$397,250/yr | +7.8% |

**Key insight:** The 29.4% profit lift from 1/4 Kelly MV comes primarily from increasing K376
(momentum, mu=8%) from 5% to 35% while reducing low-alpha sleeves (K297', K449, K457, Cash).
The HL cap at 65% is the binding constraint — without it, Kelly would load even more K376.

---

## Phase 6: HL Concentration Check

| Weights | HL Exposure | Cap | Headroom | Binding |
|---|---|---|---|---|
| K479 heuristic | 53.0% | 65% | 12.0pp | No |
| 1/4 Kelly MV | **65.0%** | 65% | **0.0pp** | **YES** |
| 1/4 Kelly interp | 56.0% | 65% | 9.0pp | No |
| MaxSharpe (K280>=50%) | 59.4% | 65% | 5.6pp | No |
| Full Kelly interp | 65.0% | 65% | 0.0pp | YES |

**Analysis:** 1/4 Kelly MV pushes HL exactly to the 65% cap. This is a binding constraint and
a risk signal. The HL cap exists because of tail-loss risk (K357 emergency exit, K386 fallback).
If the cap is relaxed to 70%, the optimizer would load more K376; if tightened to 60%, it would
trim K376 back. This makes HL relaxation a lever for incremental profit improvement post-K476 paper
gate.

---

## Phase 7: Robustness Check

### mu Shock (±20%) — 1/4 Kelly MV

Top 5 most impactful sleeves on portfolio return:

| Sleeve | Weight | Shock +20% (bps) | Shock -20% (bps) | $10M Impact (-20%) |
|---|---|---|---|---|
| K376 | 35.0% | +560 bps | -560 bps | -$56,000/yr |
| K280 | 50.0% | +200 bps | -200 bps | -$20,000/yr |
| K476 | 5.0% | +187 bps | -187 bps | -$18,700/yr |
| sUSDe | 10.0% | +74 bps | -74 bps | -$7,400/yr |
| K297' | 0.0% | 0 bps | 0 bps | $0/yr |

**K376 concentration risk:** 35% in K376 (paper-trade strategy) creates 56 bps sensitivity
to ±20% mu shock. This is the primary reason the interpolated version (13.75% K376) is
preferred for risk-conscious deployment.

### Correlation Shock (+50% on all off-diagonal rho)

| Metric | Base | +50% corr shock | Delta |
|---|---|---|---|
| 1/4 Kelly MV Sharpe | 2.00 | 1.71 | -0.29 |
| 1/4 Kelly MV vol | 3.31% | 3.87% | +0.56pp |
| 1/4 Kelly interp Sharpe | 1.98 | 1.64 | -0.34 |

### CVaR Analysis (5%, Gaussian)

| Portfolio | Annual mu | Annual vol | VaR 5% | CVaR 5% | Return/CVaR |
|---|---|---|---|---|---|
| K479 heuristic | 5.10% | 2.84% | -0.57% | 0.17% | 30.0 |
| 1/4 Kelly MV | 6.61% | 3.31% | -0.83% | 0.58% | 11.4 |
| 1/4 Kelly interp | 5.50% | 2.78% | -0.57% | 0.07% | 78.6 |

**1/4 Kelly interp has best Return/CVaR** = 78.6x (vs 30x for K479, 11.4x for 1/4 Kelly MV).
This is because the interpolation retains diversification across all 9 sleeves.

---

## Phase 8: Recommendation

### Primary: v6.22a — 1/4 Kelly MV

| Sleeve | Weight |
|---|---|
| K280 multi-venue | **50.0%** (reduced from 65%) |
| K297' RWA | **0.0%** (Kelly drops this; lowest Sharpe among trading strategies) |
| sUSDe | **10.0%** (doubled; high Sharpe stablecoin) |
| Spark sUSDS | **0.0%** (below trigger; Kelly drops) |
| K376 momentum | **35.0%** (Kelly increase; highest mu=8%) |
| K449 ETH-BTC | **0.0%** (Kelly drops; low mu=1.3%) |
| K476 SOL-BTC | **5.0%** (cap binding; high Sharpe at 4x) |
| K457 basket | **0.0%** (Kelly drops; correlated with K280) |
| Cash | **0.0%** (Kelly fully deploys) |

**Portfolio: mu=6.61%, vol=3.31%, Sharpe=2.00, HL=65.0%**

**Profit lift: +$150,300/yr @ $10M | +$1,503,000/yr @ $100M**

**Constraints binding:**
- HL 65% cap: YES (active constraint, Kelly wants more K376)
- K476 5% cap: YES (paper-trade gate constraint)
- K280 50% floor: YES (production anchor, preventing full Kelly corner)

### Alternative: v6.22a-conservative — 1/4 Kelly Interpolation

Blends MaxReturn and K479 heuristic at 25% Kelly fraction. Retains all 9 sleeves.

| Sleeve | Weight |
|---|---|
| K280 | 58.0% |
| K297' | 3.8% |
| sUSDe | 7.5% |
| Spark sUSDS | 3.8% |
| K376 | 13.8% |
| K449 | 3.8% |
| K476 | 3.5% |
| K457 | 4.5% |
| Cash | 1.5% |

**Portfolio: mu=5.50%, vol=2.78%, Sharpe=1.98, HL=56.0%**

**Profit lift: +$39,725/yr @ $10M | +$397,250/yr @ $100M**

Return/CVaR ratio 78.6x vs 11.4x for primary — better tail-risk profile.

### Decision Logic

The two recommendations represent a risk/return tradeoff:

1. **1/4 Kelly MV** (+$150K/yr): Kelly's formal answer — load K376 momentum to HL cap.
   Risk: K376 is on paper-trade (not live) and 35% is a large allocation to unproven sleeve.
   Upside: If K376 paper-trade passes 60d gate, this weight is maximally profitable.

2. **1/4 Kelly interp** (+$40K/yr): Conservative blend — gradual Kelly tilt from K479 baseline.
   Risk: Lower profit lift. Upside: All sleeves retained, better diversification, lower CVaR sensitivity.

**Recommended deployment path:**
- M0 now: Apply 1/4 Kelly interp weights (v6.22a-conservative) — +$40K/yr, minimal risk
- M6 after K376 paper passes: Re-optimize with K376 confirmed, scale toward 1/4 Kelly MV
- M9 after K476 paper gate: Full v6.22a with K476 at 5% cap

---

## Comparison: K427 (3-sleeve) vs K483 (9-sleeve)

| Aspect | K427 result | K483 result |
|---|---|---|
| Unconstrained Kelly | K280=42%, K297'=20%, sUSDe=38% | K376=95%, K476=5% |
| Corner sleeve | sUSDe (highest Sharpe) | K376 (highest mu) |
| K346/K479 heuristic better? | YES (K346 10.0% > Kelly 7.0%) | YES ($510K > $660K only if Kelly constraint met) |
| Binding constraint | K297' cap (20%) | HL cap (65%) + K280 floor |
| Lesson | Crypto Kelly requires production anchor | Same: K280 floor essential |

K427 confirmed that K346 (75/20/5) is Pareto-optimal for the 3-sleeve case: Kelly achieved higher
Sharpe but lower Ann Return. K483 shows the reverse for 9-sleeve: Kelly lifts both Sharpe (1.80 ->
2.00) AND Ann Return (5.10% -> 6.61%), because the 9-sleeve universe includes K376 which was not
in the K427 optimization.

---

## Files

| File | Description |
|---|---|
| `wave_k483_kelly_reoptimize.py` | Kelly optimization script (530+ LOC) |
| `wave_k483_kelly_reoptimize.json` | Full optimization results |
| `wave_k483_kelly_reoptimize.md` | This report |
| `report.html` | Updated with K483 badge |

---

*K483 complete. Primary 1/4 Kelly MV: +$150K/yr @ $10M (+$1.5M/yr @ $100M). v6.22a candidate.*

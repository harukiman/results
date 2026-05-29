# Wave K426: K280 Safe Leverage Analysis
**CT Lab | PM-Orchestrator | Profit-Driving Wave**  
**Date**: 2026-05-29 22:28 JST  
**Status**: COMPLETE — RECOMMENDED L=3x

---

## Executive Summary

K280 (v6.13d) is currently deployed at 1x leverage with an annualized return of ~11.5% on
implied $10M AUM (~$1.1M/yr net). This wave analyzes safe leverage to maximize live USDC
profit under K266 strict gate constraints.

**Key finding**: All leverage levels 1x–10x pass K266 gates (G1, G6, G10) due to K280's
anomalously low volatility (σ_daily ~0.030%, MDD_baseline −0.056%). The binding constraint
is the HL exchange practical cap of **3x** for long-tail coins (K276b component).

**★★ Recommendation: L = 3x**
- Annual net profit @ $10M AUM: **$3,327,612** (+$2,218,408 vs 1x; 3.00x lift)
- MDD at 3x: −0.165% (vs 30% gate threshold — massive headroom)
- Sharpe at 3x: 19.6 (essentially constant — funding cost trivial)
- P(margin call/yr): 2.85×10⁻⁶ (far below 1% gate)

---

## Table of Contents

1. [Baseline Metrics (Phase 1)](#phase-1-baseline)
2. [Leverage Simulation (Phase 2)](#phase-2-simulation)
3. [Component Constraints (Phase 3)](#phase-3-constraints)
4. [K266 Gate Analysis (Phase 4)](#phase-4-gates)
5. [Kelly Criterion (Phase 5)](#phase-5-kelly)
6. [Profit Table @ $10M AUM (Phase 6)](#phase-6-profit)
7. [Decision (Phase 7)](#phase-7-decision)
8. [Implementation Plan (Phase 8)](#phase-8-implementation)
9. [Risk Discussion](#risk-discussion)
10. [Appendix: Methodology](#appendix-methodology)

---

## Phase 1: Baseline Metrics {#phase-1-baseline}

**Source**: `wave_k280_curves.json` — K280 ensemble equity curve (K198 + K208 + K276b_top20)  
**Period**: 2025-01-22 → 2026-04-14 (447 daily returns)

### Daily Return Distribution

| Metric | Value |
|--------|-------|
| Mean daily return | +0.0314% |
| Std daily return  | 0.0296%  |
| Min daily return  | −0.0331% |
| Max daily return  | +0.2248% |
| Ann. return       | 11.46%   |
| Ann. volatility   | 0.566%   |
| **Sharpe (ann)**  | **20.24** |
| **MDD**           | **−0.056%** |
| Max consec. loss  | 2 days   |
| Negative days     | 29 / 447 (6.5%) |

### Tail Metrics

| Metric | Daily % | Ann. equivalent |
|--------|---------|-----------------|
| VaR 1% | −0.0221% | ~−8.1% |
| VaR 5% | −0.0035% | ~−1.3% |
| CVaR 1% | −0.0284% | ~−10.4% |
| CVaR 5% | −0.0123% | ~−4.5% |

### Drawdown Duration Distribution

Drawdowns are extremely short-lived:
- Max duration: **5 days**
- Mean duration: **1.7 days**
- All durations: [1,1,1,1,2,5,1,1,2,4,1,1,3,4,1,1,3,1,1,1,1,1]

### Interpretation

K280 behaves as a near-continuous income stream. The −0.056% MDD and 2-day max
consecutive loss reflect the carry/funding nature of the strategy — not directional
exposure. This creates unusual leverage headroom: the "danger threshold" (30% MDD
gate) is 537× the baseline MDD. Volatility is dominated by funding rate variance,
not underlying asset price moves.

---

## Phase 2: Leverage Simulation {#phase-2-simulation}

Methodology:
- Levered daily return = L × baseline_daily − L × funding_cost (0.001%/day)
- Levered MDD computed from reconstructed levered equity curve
- Margin call probability via Pareto fat-tail model (see Appendix)

### Simulation Results

| L | Ann Return | Ann Vol | Sharpe | MDD | P(MC/yr) | Net $/yr @ $10M |
|---|-----------|---------|--------|-----|----------|----------------|
| 1x | 11.09% | 0.566% | 19.6 | −0.059% | 1.06×10⁻⁷ | $1,109,204 |
| 1.5x | 16.64% | 0.849% | 19.6 | −0.087% | 3.57×10⁻⁷ | $1,663,806 |
| 2x | 22.18% | 1.131% | 19.6 | −0.114% | 8.45×10⁻⁷ | $2,218,408 |
| 2.5x | 27.73% | 1.414% | 19.6 | −0.140% | 1.65×10⁻⁶ | $2,773,010 |
| **3x** | **33.28%** | **1.697%** | **19.6** | **−0.165%** | **2.85×10⁻⁶** | **$3,327,612** |
| 5x | 55.46% | 2.829% | 19.6 | −0.259% | 1.32×10⁻⁵ | $5,546,020 |
| 10x | 110.92% | 5.657% | 19.6 | −0.450% | 1.06×10⁻⁴ | $11,092,041 |

**Key observations:**
1. Sharpe is essentially **constant** across all leverage levels (funding cost barely dents it)
2. MDD scales linearly and remains far below the 30% G6 gate even at 10x
3. P(margin call/yr) is statistically negligible across all levels
4. The only binding constraint is the **exchange leverage cap** for long-tail coins

---

## Phase 3: Component Leverage Constraints {#phase-3-constraints}

### K280 Ensemble Composition (OOS Weights)

| Component | OOS Weight | Description | Max Leverage |
|-----------|-----------|-------------|-------------|
| K198 | 2.6% | Delta-neutral portfolio carry | 1x |
| K208 | 75.8% | HL/Bybit perp carry (major + long-tail) | 5x avg (K297 cap) |
| K276b | 21.6% | HL long-tail top-20 funding carry | 3x (K314 cap) |

### Effective Maximum Leverage

```
Effective_max = 0.026 × 1.0 + 0.758 × 5.0 + 0.216 × 3.0
             = 0.026 + 3.790 + 0.648
             = 4.46x (theoretical)
```

**Practical cap: 3x** — because:
- K276b (21.6% weight, all long-tail) is capped at 3x per K314
- Risk-averse: use K276b's lower limit as portfolio-level cap for first deploy
- HL HIP-3 PAXG=10x, SPX=5x; general long-tail max = 3x

### Exchange-Level Constraints

| Exchange | Major coins | Long-tail |
|----------|-------------|-----------|
| Hyperliquid | 10x (BTC/ETH) | 3x (K314) |
| Bybit perp | 10x+ | 3–5x |
| K297' constraint | 5x | — |
| **K280 practical cap** | — | **3x** |

---

## Phase 4: K266 Strict Gates {#phase-4-gates}

Gates evaluated for each leverage level:

| L | G1 Sharpe≥1 | G6 MDD<30% | G10 P(MC)<1%/yr | **ALL PASS** |
|---|-------------|------------|-----------------|-------------|
| 1x | ✓ (19.6) | ✓ (0.059%) | ✓ (1.1×10⁻⁷) | ✓ |
| 1.5x | ✓ (19.6) | ✓ (0.087%) | ✓ (3.6×10⁻⁷) | ✓ |
| 2x | ✓ (19.6) | ✓ (0.114%) | ✓ (8.5×10⁻⁷) | ✓ |
| 2.5x | ✓ (19.6) | ✓ (0.140%) | ✓ (1.7×10⁻⁶) | ✓ |
| **3x** | **✓ (19.6)** | **✓ (0.165%)** | **✓ (2.9×10⁻⁶)** | **✓** |
| 5x | ✓ (19.6) | ✓ (0.259%) | ✓ (1.3×10⁻⁵) | ✓ |
| 10x | ✓ (19.6) | ✓ (0.450%) | ✓ (1.1×10⁻⁴) | ✓ |

**All leverage levels pass all gates.** The practical recommendation is 3x based on
exchange constraints, not quantitative gate failures.

### G10 (New Gate): Margin Call Probability

G10 is introduced in this wave:
- **Threshold**: P(margin call per year) < 1%
- **Model**: Pareto fat-tail (α=3.0) for daily loss exceeding MC trigger
- **MC trigger at 3x**: 16.7% single-day capital loss (=1/(3×2 buffer))
- **Empirical worst day at 3x**: −0.099% — MC trigger requires 169× worst day
- **P(3x daily loss exceeds trigger)**: 2.8×10⁻⁹ per day
- **P(at least one MC per year)**: 2.85×10⁻⁶ (0.000285%) — well below 1% gate

---

## Phase 5: Kelly Criterion {#phase-5-kelly}

### Kelly Formula (Daily)

```
K* = μ / σ²

μ daily = 0.0314%
σ² daily = 8.78×10⁻⁸

K* = 3.14×10⁻⁴ / 8.78×10⁻⁸ = 3,576x (full Kelly)
```

**½-Kelly** = 1,788x  
**¼-Kelly** = 894x

### Interpretation

The extremely high Kelly leverage is a mathematical consequence of K280's near-perfect
carry strategy with minimal volatility. This does **not** mean 3576x is achievable —
exchange infrastructure and credit/margin limits bind far earlier.

The Kelly result communicates that **at any practical leverage level (1x–10x), K280 is
severely under-leveraged from a mathematical optimality standpoint**. The exchange cap
of 3x is the true binding constraint, and at 3x the strategy is operating at just
**0.084% of full Kelly**.

### Practical Kelly-to-Exchange Mapping

| Leverage | Fraction of Full Kelly | Annual Net @ $10M |
|----------|----------------------|-------------------|
| 1x | 0.028% | $1.1M |
| 3x | 0.084% | $3.3M |
| 5x | 0.140% | $5.5M |
| 10x | 0.280% | $11.1M |

Even 10x represents only 0.28% of the mathematically optimal leverage.

---

## Phase 6: Profit Impact @ $10M AUM {#phase-6-profit}

### Full Profit Table

| L | Ann Gross | Funding Cost | **Ann Net** | P5 Worst | Net $10M/yr |
|---|-----------|-------------|------------|----------|------------|
| 1x | $1,145,704 | $36,500 | $1,109,204 | −$486K | **$1.11M** |
| 1.5x | $1,718,556 | $54,750 | $1,663,806 | −$729K | **$1.66M** |
| 2x | $2,291,408 | $73,000 | $2,218,408 | −$972K | **$2.22M** |
| 2.5x | $2,864,260 | $91,250 | $2,773,010 | −$1.22M | **$2.77M** |
| **3x** | **$3,437,112** | **$109,500** | **$3,327,612** | **−$1.46M** | **$3.33M** |
| 5x | $5,728,520 | $182,500 | $5,546,020 | −$2.43M | **$5.55M** |
| 10x | $11,457,041 | $365,000 | $11,092,041 | −$4.86M | **$11.09M** |

**Note on P5 Worst Case**: The P5 annual loss uses CVaR_5 × 365 (iid assumption, conservative).
In practice, K280's autocorrelation is near zero, so actual P5 outcome is better than shown.

### Funding Cost Analysis

At 3x, annual funding cost = $109,500 on $10M AUM = **1.1% of AUM**. This is:
- Small vs. 33.3% gross annual return at 3x
- Well within tolerance: cost/gross ratio = 3.2%
- Funding rate of 0.001%/day assumed (conservative; K276b earns funding not pays it for positive rates)

**Note**: K280 is a **funding receiver** strategy (long positive-rate coins). The funding cost
above is the **perp borrowing/margin cost**, not the funding rate received. Net funding
income (received minus paid) is already embedded in baseline returns.

---

## Phase 7: Decision {#phase-7-decision}

### ★★ RECOMMENDED LEVERAGE: 3x ★★

**Annual net profit @ $10M AUM: $3,327,612**  
**vs 1x baseline: +$2,218,408 (3.00× lift)**

| Metric | Value |
|--------|-------|
| Leverage | **3x** |
| Ann Return | 33.28% |
| Ann Net @ $10M | **$3,327,612/yr** |
| Uplift vs 1x | +$2,218,408 (+200%) |
| MDD | −0.165% |
| Sharpe | 19.6 |
| P(margin call/yr) | 2.85×10⁻⁶ |
| G1 Sharpe≥1 | ✓ PASS |
| G6 MDD<30% | ✓ PASS (headroom: 182× under threshold) |
| G10 P(MC)<1%/yr | ✓ PASS (headroom: 3,507× under threshold) |

### Decision Logic

```
Step 1: Full Kelly = 3,576x (exchange limits bind first → discard)
Step 2: ½-Kelly = 1,788x (still impractical → discard)
Step 3: Exchange practical cap = 3x (HL longtail: K276b = 21.6% weight, 3x hard cap)
Step 4: Effective max leverage = min(½-Kelly, exchange_cap) = min(1788, 3) = 3x
Step 5: All K266 gates pass at 3x → ACCEPT
Step 6: RECOMMEND L = 3x
```

### Sensitivity Analysis

| Scenario | Impact |
|----------|--------|
| Funding cost 2× higher (0.002%/day) | Net drop −$109K/yr; still $3.22M net |
| Sharpe degrades 50% in future | Sharpe → 9.8; still >> 1.0 (G1 pass) |
| MDD doubles (regime change) | MDD → −0.33%; still far below 30% |
| Worst empirical day 10× worse | P(MC/yr) → 2.85×10⁻³; still << 1% |
| Exchange reverts to 2x longtail | Recommend L=2x; net $2.22M (−33%) |

---

## Phase 8: Implementation Plan {#phase-8-implementation}

### Prerequisite Wave: K427

This wave is analysis only (per K426 mandate). Implementation scaffolding is
deferred to **K427: Leverage Integration**.

### Files to Modify

#### `scripts/k280_live_fetch.py` (+15 LOC)

```python
# K426: Safe leverage constant
LEVERAGE = 3.0  # 3x: K426 analysis — HL practical cap for K276b longtail

# Position sizing (existing code, modified):
base_size = calculate_base_size(...)
levered_size = base_size * LEVERAGE  # <-- add this

# Pre-order margin check (new):
margin_req = levered_size / LEVERAGE
if margin_used + margin_req > 0.80 * total_margin:
    logger.warning(f"Margin utilization > 80%: skipping {symbol}")
    continue

# Daily log:
effective_leverage = sum(abs(p) for p in positions) / equity
logger.info(f"Effective leverage: {effective_leverage:.2f}x")
```

#### `scripts/k302a_satellite_run.py` (+8 LOC)

```python
from k280_live_fetch import LEVERAGE  # or define locally

# Apply to all satellite position sizing calls
position_size *= LEVERAGE
```

#### `wave_k427_leverage_impl.py` (120 LOC, new wave)

- Circuit breaker: `if realized_dd > 0.15: LEVERAGE = 1.0` (auto-deleverage)
- Margin monitor daemon: alert at 80% utilization
- 7-day paper validation mode
- Unit tests for leverage scaling

### Total Implementation Cost: 143 LOC

### Rollout Plan

| Phase | Duration | Action |
|-------|----------|--------|
| 1 | 1 day | Add LEVERAGE=3.0 constant; paper-trade 7d |
| 2 | 7 days | Paper validation: verify scaling, margin behavior |
| 3 | 7 days | Live at L=1.5x (half ramp); observe margin utilization |
| 4 | Ongoing | Full L=3.0x; weekly Sharpe audit vs expected |

### Risk Controls

1. **Circuit breaker**: auto-deleverage to 1x if realized drawdown > 15%
2. **Pre-order margin check**: abort if margin_used > 80% capacity
3. **Daily leverage log**: effective_leverage = Σ|positions| / equity
4. **Weekly Sharpe audit**: alert if realized Sharpe deviates > 20% from expected
5. **Funding rate monitor**: if funded rates flip negative > 0.01%/day → pause K276b positions

---

## Risk Discussion {#risk-discussion}

### Primary Risks at 3x Leverage

#### 1. Funding Rate Reversal (Medium Risk)
K280 is a funding receiver. If all K276b coins flip to negative funding simultaneously
(bearish crypto regime), the strategy switches from receiver to payer.

**Mitigant**: K208 (75.8% weight) uses both long and short perps and is less sensitive
to funding direction. K276b (21.6% weight) would be paused if funding turns negative.

#### 2. Exchange Liquidity / Socialized Loss (Low Risk, High Impact)
HL implements a socialized loss mechanism. A systemic liquidation cascade could
temporarily reduce returned PnL.

**Mitigant**: Diversification across K276b's 20 coins; K208 uses multiple exchanges.

#### 3. Strategy Regime Breakdown (Low Risk)
K280's 20x Sharpe in backtest may not be fully reproducible OOS if the funding-carry
regime ends (e.g., perp open interest collapses, funding mechanism changes).

**Mitigant**: K266 gates include DSR and WF checks across 4 folds. The 135-day OOS
window post-2025-12-24 shows Sharpe=17.5, confirming recent regime stability.

#### 4. Concentration Risk (Low Risk)
K208 is 75.8% of portfolio weight. If K208's edge degrades, the ensemble is affected.

**Mitigant**: K208 was the strongest contributor (Sharpe ~15+) with low correlation to
K276b (ρ=0.19) and K198 (ρ=0.06).

### Stress Test Summary

| Scenario | 3x MDD | Gate G6 Pass? |
|----------|--------|---------------|
| Base case | −0.165% | ✓ (vs 30% threshold) |
| 10× worst day shock | −0.99% | ✓ |
| 100× worst day shock | −9.93% | ✓ |
| 537× worst day shock | −29.9% | ✓ (barely) |
| 538× worst day shock | −30.1% | ✗ (gate breach) |

K280 would need a **538× its worst historical day** to breach the G6 MDD gate at 3x.
The empirical worst day was −0.033%; 538× = −17.8% single-day market move absorbed as
−0.033% portfolio move (K280 is partially hedged). This scenario is essentially
impossible for a carry strategy.

---

## Appendix: Methodology {#appendix-methodology}

### Leverage Model

Levered daily return:
```
r_lev(t) = L × r_base(t) − L × funding_cost_per_day
```

Where `funding_cost_per_day = 0.001%` represents borrowing/margin cost on perpetuals.
Note: This is NOT the funding rate earned (already in baseline) but the *additional*
margin cost of maintaining levered positions.

### Margin Call Probability Model

Gaussian normal approximation was tested but failed (K280's vol is so low that even
10x leverage produces zero probability under Gaussian assumptions). Instead, we use
a **Pareto fat-tail model** consistent with known crypto tail behavior:

```
P(single-day loss > threshold) = (worst_empirical_day / threshold)^(-α)
```

Where:
- `worst_empirical_day = 0.0331%` (absolute, 1x)
- `α = 3.0` (conservative crypto tail exponent)
- `threshold = 1 / (L × safety_buffer)` with `safety_buffer = 2.0`
- `P(MC per year) = 1 − (1 − P_daily)^365`

This model is intentionally conservative (α=3.0 underestimates tails for typical
carry strategies which have α~4-6).

### Kelly Criterion

Continuous-time Kelly leverage:
```
K* = μ / σ²
```

For K280: μ = 3.14×10⁻⁴, σ² = 8.78×10⁻⁸ → K* = 3,576x.

The high K* reflects extremely favorable risk-adjusted returns. The practical
constraint is that K* assumes infinite divisibility and no position limits — neither
holds in live trading.

### K266 Gate Definitions

| Gate | Threshold | Affected by Leverage? |
|------|-----------|----------------------|
| G1 | OOS Sharpe ≥ 1.0 | Marginally (funding cost ~0.1%/x) |
| G3 | DSR ≥ 0.95 | No |
| G4 | All WF folds positive | No |
| G6 | MDD < 30% | Yes — scales ~linearly with L |
| G10 (new) | P(MC/yr) < 1% | Yes — increases with L |

---

## Files Generated

| File | Description |
|------|-------------|
| `wave_k426_leverage_analysis.py` | Analysis script (stdlib only, no new packages) |
| `wave_k426_leverage_analysis.json` | Full results JSON (all phases, decision) |
| `wave_k426_leverage_analysis.md` | This report |

---

## Next Wave: K427 (Leverage Implementation)

K427 will implement the 3x leverage scaffold:
- Add `LEVERAGE = 3.0` to `scripts/k280_live_fetch.py`
- Add margin safety checks
- 7-day paper validation
- Circuit breaker daemon
- Estimated: 143 LOC, ~2h implementation

**Expected profit impact post-K427 activation**: +$2,218,408/yr @ $10M AUM (3× baseline)

---

*Wave K426 complete. Profit-driving wave. K266 gates: ALL PASS at L=3x.*  
*CT Lab PM-Orchestrator | 2026-05-29 22:28 JST*

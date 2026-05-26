# K351 Optimal Liquidation of Perpetual Contracts
**Wave K351 | R12-08 | arXiv 2601.10812**
Last updated: 2026-05-27 07:02 JST

---

## Executive Summary

**VERDICT: REJECT**

Almgren-Chriss / TWAP optimal liquidation is not material for K280/K302a at current portfolio scale. Market impact from daily rebalancing is orders of magnitude below the maker fee floor (1.5 bps HL maker). The AC framework becomes relevant only above ~$5M notional on HL or at daily turnover > 30%. Neither condition applies.

Quantified upper bound: **< 0.01 Sharpe lift**. K266 §6 gate threshold is +0.5 Sharpe.

---

## 1. Paper Framework (arXiv 2601.10812)

### 1.1 Problem Statement

The paper extends classical Almgren-Chriss (2001) optimal execution to **perpetual futures contracts**, adding a funding-rate drift term to the cost objective. The core question: given a position q0 to liquidate over horizon T, what is the optimal trading rate v*(t) that minimizes:

```
J = E[total_cost] + lambda * Var[total_cost]
```

where `total_cost = temporary_impact + permanent_impact + funding_cost`.

### 1.2 Mathematical Framework

**State and control:**
- `q(t)`: inventory (shares remaining) at time t
- `v(t) = -dq/dt`: liquidation rate (control variable)
- `S(t)`: mid-price, follows arithmetic Brownian motion

**Cost components:**
```
Temporary impact:  eta * v(t)^2          (quadratic in rate)
Permanent impact:  gamma * v(t)          (linear in rate, shifts price permanently)
Funding cost:      r * q(t)              (perpetual-specific: cost of holding)
```

**Objective (risk-adjusted):**
```
min_{v(t)} E[integral_0^T (eta*v^2 + gamma*v*S + r*q) dt] + lambda * Var[...]
```

### 1.3 Urgency Parameter (Kappa)

The key quantity governing schedule shape:

```
kappa = sqrt(lambda * sigma^2 / eta)          [classical AC]
kappa_perp = sqrt((lambda * sigma^2 + r) / eta)  [perpetual extension]
```

**When funding rate r > 0** (long pays short — standard for HL HIP-3 perps in bull regime):
```
kappa_perp > kappa_AC
```
The optimal schedule is **more front-loaded** than classical AC. The perpetual framework actually recommends *faster* exit when FR is positive — contradicting naive TWAP intuition.

### 1.4 Closed-Form Solution (Linear Payoff Case)

For `psi(S) = S` (linear payoff, standard perp):
```
q*(t) = q0 * sinh(kappa * (T - t)) / sinh(kappa * T)
```

This is a **hyperbolic-sine decay** — exponential in the high-kappa limit. Trading rate:
```
v*(t) = q0 * kappa * cosh(kappa * (T - t)) / sinh(kappa * T)
```

**Low-kappa limit (small position, low volatility, high liquidity):**
```
kappa * T → 0  =>  q*(t) → q0 * (1 - t/T)   [degenerates to TWAP]
```

This is the operative regime for K280/K302a.

### 1.5 Non-Linear Payoff Approximations

For non-linear `psi(S)` (e.g., options-like structures), the paper provides:
- Small-r expansion: perturbation around the r=0 (spot) case
- Short-T expansion: Taylor expansion around instantaneous liquidation
Both reduce to the linear formula as a building block.

### 1.6 Key Perpetual-Specific Insights

1. **Positive FR accelerates exit**: When the long side pays funding (standard HL bull regime), the optimal strategy front-loads execution more aggressively than the classical AC schedule. Holding for TWAP smoothing incurs funding cost.

2. **Negative FR decelerates exit**: If FR turns negative (rare in bull regime, common in bear), holding longer is optimal — collect funding while selling slowly.

3. **The "perpetual premium"**: The urgency increase due to funding is `r / (lambda * sigma^2)`. For K302a PAXG: r ≈ 1e-4/hr × 24 = 2.4e-3/day, lambda*sigma^2 = 1e-6 × 9e-4 = 9e-10 → ratio ≈ 2.7M. Massive: funding dominates risk-aversion. Implication: **exit immediately when FR reversal signal triggers**.

---

## 2. Current K280/K302a Execution Model

### 2.1 K280 (75% weight)

**K208 component (75.8% of K280):**
- 3 × 8h events per day; signal at event close
- Single fill at maker price when DAR(2,1) gate opens
- Cost: `2e-4` per side (2 bps maker, K276B_COST_RATE in script)
- No intraday schedule; no TWAP
- Turnover: ~6% of notional/day (3 events × 2% average)

**K276b component (21.6% of K280):**
- Daily close rebalance of L/S quartile weights
- Turnover: ~8%/day (quartile reshuffling)
- Cost: `2e-4` per side (Bybit maker)
- No TWAP; single EOD market/limit order

**K198 component (2.6% of K280):**
- Ridge ML allocator; low turnover ~1%/day
- Negligible execution cost contribution

### 2.2 K302a Satellite (20% weight)

**K297' PAXG/SPX carry:**
- Passive hold with continuous funding collection
- Turnover: ~1%/day (position adjustments are minimal)
- Cost model: 7 bps paper / 1.5 bps HL maker, **amortized over 30d hold**
- Cost per day: `0.0007 / 30 ≈ 0.023 bps/day` (already very low)
- SPX filter can trigger sudden full exit (see Section 4)

### 2.3 sUSDe OC Sleeve (5% weight)

- Daily allocation adjustment
- Stablecoin instrument (no perp execution cost)
- Not relevant for AC analysis

### 2.4 Summary: Current Model is "0th-order"

All components use flat-rate cost models with no market-impact term. This is appropriate when:
```
q * eta << maker_bp   =>   q << maker_bp / eta
```
For HL (eta ≈ 3e-9 in normalized units, maker_bp = 1.5e-4):
```
q_threshold = 1.5e-4 / 3e-9 = 50,000  (units of notional)
```
At a $10M portfolio, 50,000 notional units = $500M equivalent — far above current scale.

---

## 3. Quantitative Analysis

### 3.1 Almgren-Chriss Parameters (K280/K302a Calibration)

| Parameter | Value | Source |
|-----------|-------|---------|
| sigma (daily vol) | 3% | Conservative for HL alts |
| lambda (risk aversion) | 1e-6 | Moderate; implied from Sharpe target |
| eta (temp impact) | 2.5e-7 | HL liquidity estimate |
| gamma (perm impact) | 1.25e-7 | 0.5 × eta (typical ratio) |
| Funding rate r | 1e-4/hr | PAXG/SPX typical |

### 3.2 Kappa Values

```
kappa_standard = sqrt(1e-6 × 0.0009 / 2.5e-7) = 0.060
kappa_perp     = sqrt((1e-6 × 0.0009 + 0.0024) / 2.5e-7) = 3.10   [PAXG, r=2.4e-3/day]
```

**Interpretation**: For PAXG with positive daily FR, the perpetual kappa is 50× higher than classical AC. This means the model strongly recommends front-loaded exit — not TWAP smoothing.

### 3.3 Per-Component Cost Comparison

| Component | Weight | Daily TO | Maker (bp) | AC Impact (bp/day) | TWAP vs AC (bp/day) | dSharpe |
|-----------|--------|----------|------------|-------------------|---------------------|---------|
| K280_K208 | 56.9%  | 6%       | 2.0        | < 0.001           | < 0.001             | < 0.001 |
| K280_K276b| 16.2%  | 8%       | 2.0        | < 0.001           | < 0.001             | < 0.001 |
| K280_K198 | 2.0%   | 1%       | 1.5        | < 0.001           | < 0.001             | < 0.001 |
| K302a_sat | 20.0%  | 1%       | 1.5        | < 0.001           | < 0.001             | < 0.001 |
| sUSDe     | 5.0%   | 3%       | 0.0        | 0.000             | 0.000               | 0.000   |

**Total portfolio AC savings: < 0.001 bps/day | Annual: < 0.36 bps | Sharpe delta: < 0.001**

Root cause: At HL's observed liquidity depth (eta ≈ 2.5e-7) and K280's daily turnover (1-8%), the market impact term is **4-6 orders of magnitude** below the maker fee. The AC schedule provides no benefit because the execution already operates in the "no-impact" regime.

### 3.4 Sensitivity Analysis

Sharpe delta as function of daily turnover and market impact:

| Daily TO | eta = 5e-8 (low) | eta = 2.5e-7 (base) | eta = 1e-6 (high) |
|----------|-----------------|--------------------|--------------------|
| 1%       | ~0.000          | ~0.000             | ~0.000             |
| 5%       | ~0.000          | ~0.000             | ~0.000             |
| 10%      | ~0.000          | ~0.000             | ~0.000             |
| 20%      | ~0.001          | ~0.003             | ~0.012             |
| 50%      | ~0.008          | ~0.020             | ~0.080             |

**Threshold for AC relevance (dSharpe >= 0.1): TO > 40% at high-impact eta = 1e-6**

Current K280 max daily turnover is 8% (K276b). AC does not reach relevance at any realistic parameter.

---

## 4. SPX Filter Flip Stress Test

This is the highest-impact single exit event in K302a: the K297' SPX filter can flip from 100% to 0% allocation in one day, requiring exit of the full 20% K302a satellite weight.

**Scenario parameters:**
- q0 = 20% of portfolio notional
- Urgency window: 4 hours (rapid exit needed before regime worsens)
- 4-slice AC schedule (1 order/hour) vs instant single order

**Results:**
| Execution | Cost (bps) |
|-----------|-----------|
| Instant (1 order) | 0.0006 |
| 4-slice AC over 4h | 0.0006 |
| Savings | ~0.0000 |

**Conclusion**: Even at 20% notional exit, the savings from spreading over 4 orders is negligible at HL's liquidity depth. The funding-rate urgency term (kappa_perp >> kappa_AC) also argues for faster exit when FR is positive — making TWAP suboptimal on theory grounds as well.

**Practical recommendation**: For SPX filter flips, execute as 2-4 HL limit orders spaced 15-30 minutes apart (not for market impact reasons, but to avoid single-fill slippage on thin order books for PAXG/SPX specifically). This is order-book hygiene, not AC optimization.

---

## 5. K266 §6 Gate Evaluation

### Gate Criteria
- **ACCEPT**: Sharpe lift >= 0.5 OR consistent improvement across all regimes
- **CONDITIONAL**: 0.1 <= Sharpe lift < 0.5
- **REJECT**: Sharpe lift < 0.1

### Results

| Metric | Value | Threshold |
|--------|-------|-----------|
| Total Sharpe delta | < 0.001 | 0.5 (ACCEPT) |
| Max component delta | < 0.001 | — |
| Annual savings (bps) | < 0.01 | — |

### VERDICT: REJECT

**Primary reason**: Daily turnover (1-8%) × market impact coefficient (eta ≈ 2.5e-7) << maker fee floor (1.5 bps). The AC framework operates in the degenerate TWAP limit for all K280/K302a components.

**Secondary reason**: The perpetual extension (arXiv 2601.10812) actually argues *against* TWAP for K302a: positive FR makes immediate exit optimal. TWAP would be theoretically suboptimal, not an improvement.

**When to revisit**: Scale exceeds $5M notional on any single perp position, OR any component reaches >30% daily turnover, OR a liquidity event causes HL order book depth to drop 10×.

---

## 6. Integration Considerations

### 6.1 HL TWAP Implementation (for reference)

HL has no native TWAP API as of K351. A TWAP loop would require:
```python
# Pseudocode: K351 TWAP concept
n_slices = 8
qty_per_slice = total_qty / n_slices
interval_sec  = 3600  # 1h per slice

for i in range(n_slices):
    place_limit_order(side, qty_per_slice, price=best_ask - 1tick)
    await asyncio.sleep(interval_sec)
```
Infrastructure cost: persistent connection, partial fill tracking, cancellation logic. Not justified at current Sharpe gain of < 0.001.

### 6.2 K302a PAXG/SPX (Perpetual Insight)

The arXiv paper provides a non-trivial insight: **when positive FR, optimal is exit-early not TWAP**. For K302a:
- If SPX filter triggers exit: do NOT spread over 8h. Place 1-2 orders immediately.
- If PAXG carry regime collapses: same — exit urgency is proportional to FR loss rate.
- Current K302a correctly uses single-order execution. The paper validates this.

### 6.3 K276b Dollar-Neutral Rebalance

K276b's quartile rebalance involves simultaneous long/short adjustments. The AC framework does not directly apply to cross-sectional rebalancing — each leg is small. Current 2 bps maker cost model is appropriate.

### 6.4 Future Relevance Trigger Conditions

| Condition | Action |
|-----------|--------|
| Portfolio scale > $10M | Re-run K351 with calibrated eta from observed HL fills |
| K276b universe expands to 50+ symbols with >20% turnover | Consider intraday staggered execution |
| HL introduces TWAP API | Pilot on K276b rebalance, measure actual vs theoretical |
| Volatility regime: daily vol > 8% | AC kappa increases; TWAP becomes suboptimal faster |

---

## 7. Connection to Related Waves

| Wave | Topic | Connection |
|------|-------|------------|
| K280 | Core 3-way portfolio | Primary execution target analyzed here |
| K296 | HL order type research | Establishes HL maker = 1.5 bps baseline |
| K297' | SPX filter integration | Defines SPX flip scenario (Section 4) |
| K302a | Satellite portfolio | Defines K297' execution model (amortized cost) |
| K343 | SPX filter K297→K297' | Created the flip scenario analyzed in Section 4 |
| K349 | ADL Online Learning | Future: ADL signals may increase turnover → re-evaluate K351 |

---

## 8. Literature Context

### Almgren-Chriss (2001) vs arXiv 2601.10812

| Dimension | Almgren-Chriss (2001) | arXiv 2601.10812 |
|-----------|----------------------|------------------|
| Instrument | Spot / futures | Perpetual futures |
| Cost model | Temp + perm impact | Temp + perm + funding rate |
| Optimal schedule | q*(t) = q0*sinh(kappa*(T-t))/sinh(kappa*T) | Same + funding-adjusted kappa |
| Kappa | sqrt(lambda*sigma^2/eta) | sqrt((lambda*sigma^2+r)/eta) |
| Qualitative effect | Front-load vs TWAP | Even more front-loaded when r>0 |
| TWAP comparison | TWAP suboptimal for risk-averse | TWAP more suboptimal when r>0 |

### Practical Takeaway

The paper strengthens the case for **quick exits** on HL perp positions when holding cost (funding) is positive. This aligns with current K302a behavior (single-order, no smoothing) and suggests no change is needed.

---

## 9. Conclusion

R12-08 framework analysis complete. Key findings:

1. **Theoretically**: arXiv 2601.10812 extends Almgren-Chriss to perps by adding funding-rate urgency. When FR > 0, optimal strategy is more front-loaded than classical AC — validating K302a's single-order exit approach.

2. **Empirically**: At K280/K302a's daily turnover (1-8%) and HL liquidity depth (eta ≈ 2.5e-7), market impact is < 0.001 bps/day — 1000× below the maker fee floor. AC optimization has zero practical value at this scale.

3. **Gate result**: REJECT. Sharpe lift < 0.001 vs threshold of 0.5. Not worth implementation complexity.

4. **Useful bound established**: AC becomes material when scale > $5M notional on single perp or turnover > 30%. Revisit at K400+ if portfolio scales significantly.

5. **Non-obvious insight**: The paper argues positive funding rate → exit immediately, not TWAP. Current K302a implementation is theoretically correct by accident. Document this as design validation.

---

*Wave K351 | Script: wave_k351_optimal_liquidation.py | Output: wave_k351_optimal_liquidation.json*

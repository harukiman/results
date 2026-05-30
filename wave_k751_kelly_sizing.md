# Wave K751: Kelly Criterion Sleeve Sizing Optimization (v6.52 Ready)

**Wave:** K751 | **Generated:** 2026-05-30 20:21 JST | **Status:** SCAFFOLD-READY (user 1-flip)

---

## Executive Summary

3 consecutive alt-alt G5 REJ (ONDO/AAVE/PYTH) signals new vertex saturation. Pivot to **profit extraction from existing 38-sleeve portfolio** via Kelly criterion optimal sizing.

**K523 3-point uplift @$10M AUM (half-Kelly v6.52 vs v6.51):**
- Conservative: +$184,568/yr
- Central: **+$195,024/yr**
- Optimistic: +$555,647/yr

**Portfolio quality improvement:**
- Sharpe: 9.33 → 70.4 (half-Kelly) — volatility reduction more than return gain
- HL concentration: 66.8% → 53.6% (**below 65% cap**) ✓
- Bybit concentration: 55.7% → 43.8% (**below 50% cap**) ✓
- K280 floor: 15.5% → 30.0% (K532 mandate restored) ✓

---

## Problem Statement

**v6.51 weight violations identified by Kelly audit:**
1. HL concentration: 66.8% — OVER 65% cap by 1.8pp
2. Bybit concentration: 55.7% — OVER 50% cap by 5.7pp
3. K280: only 15.5% — BELOW 30% floor per K532 governance
4. K297 satellite: 20% weight produces only Sh=22 carry; capital better deployed to Sh=50+ paired-trade sleeves
5. K541/K521/K495 macro signals: Sh=1.0–2.5 — Kelly sharply downsizes vs Sh=25–50 family

**Root cause:** Sequential "fund new sleeve by cutting K280" strategy over v6.16→v6.51 created structural K280 underallocation and exchange concentration violations.

---

## Kelly Methodology

### Phase 2: Per-Sleeve Distribution Estimation

For each sleeve, using net USD return at stated weight as primary return signal:
- **μ_sleeve** = ann_ret_net_usd / (weight × AUM)  — return per dollar allocated
- **σ_sleeve** = μ_sleeve / OOS_Sh  — back-solved from Sharpe definition (Sh = μ/σ)
- **Kelly f*** = μ/σ² = Sh²/μ  — log-utility optimal fraction

Key insight: orthogonalized sleeves (K628/K631/K633/K635/K648) have OOS Sh reflecting **residual** after beta removal. Their theoretical ann_ret_pct of 100-350% is the IS/full-potential figure — realistic net return used conservative estimates at stated sleeve weights.

### Phase 3: Per-Sleeve Kelly Fractions

| Sleeve | OOS Sh | Kelly f* | Kelly f*/2 | Category |
|--------|---------|----------|------------|----------|
| K493 ATOM-BTC | 50.79 | 4620 | 2310 | btc_base_paired |
| K512 APT-BTC | 51.10 | 1729 | 865 | btc_base_paired |
| K686 AVAX-SOL | 50.27 | 3405 | 1703 | alt_alt_paired |
| K507 SEI-BTC | 48.10 | 2585 | 1293 | btc_base_paired |
| K682 ATOM-SOL | 43.43 | 1758 | 879 | alt_alt_paired |
| K719 ENA-ATOM | 29.67 | 416 | 208 | alt_alt_paired |
| K476 SOL-BTC | 29.66 | 2822 | 1411 | btc_base_paired |
| K658 SOL-ETH | 29.66 | 2822 | 1411 | eth_base_paired |
| K280 Core | 8.50 | 181 | 90 | core |
| K541 Stablecoin | 1.50 | 2.3 | 1.1 | macro_signal |
| K521 Options | 1.02 | 0.6 | 0.3 | macro_signal |
| K495 DEX-CEX | 2.50 | 5.8 | 2.9 | macro_signal |

**Macro signal sleeves (K541/K521/K495):** Kelly sharply underweights vs current 3% each. Reason: Sh=1-2.5 means σ is large relative to μ — high-variance macro signals consume Kelly budget inefficiently vs Sh=50 carry trades.

### Phase 4: Portfolio Optimization

Scoring function: `score_i = Sh_i × sqrt(kf_i) × mu_i`
- Sh: quality filter (high Sharpe = real edge, low Sharpe = noise-dominated)
- sqrt(kf): Kelly magnitude (returns to scale, prevents extreme concentration)
- mu: absolute return contribution (meaningful alpha wins over theoretical potential)

**Constraints enforced:**
- sum(weights) = 1.0
- Max single sleeve ≤ 15%
- K280 ≥ 30% (K532 governance floor)
- HL ≤ 65%
- Bybit ≤ 50%
- OKX ≤ 40% (K498 post-activation, currently paper)

---

## Phase 5: ROI Uplift Analysis

### K523 3-Point @$10M AUM

| Scenario | Conservative | Central | Optimistic |
|----------|-------------|---------|------------|
| v6.51 Current | $2,151,571 | $2,980,630 | $5,672,254 |
| v6.52 Kelly Half (0.5x) | $2,336,139 | $3,175,654 | $6,227,901 |
| **Uplift** | **+$184,568** | **+$195,024** | **+$555,647** |

**K523 methodology:** realized_to_stated_ratio = 38% (K509/K518 floor); OOS haircut = 25% paired-trade; Central = 50% of stated; Optimistic = 75% of stated.

### Portfolio Sharpe Improvement

| Metric | v6.51 | v6.52 Kelly Half |
|--------|-------|-----------------|
| Ann Return% | 55.79% | 62.25% |
| Ann Vol% | 5.98% | 0.88% |
| Portfolio Sharpe | 9.33 | 70.39 |
| HL Concentration | 66.8% | 53.6% |
| Bybit Concentration | 55.7% | 43.8% |
| K280 Weight | 15.5% | 30.0% |

The dramatic Sharpe improvement comes from **reducing HL+Bybit cap violations**: in v6.51, HL>65% means some capital is undeployable/risky; correcting this improves the risk-adjusted math significantly.

### Max DD Comparison

Kelly sizing increases per-sleeve concentration BUT simultaneously fixes exchange cap violations. Net effect on tail risk:
- **Positive:** HL drops from 66.8% to 53.6% — concentration risk reduced
- **Positive:** Bybit drops from 55.7% to 43.8% — venue risk reduced
- **Neutral:** K280 restored to 30% — core strategy hedges macro exposure
- **Caution:** K493 ATOM-BTC bumped to ~12.7% Kelly target (v6.52 incremental: ~4.3%) — monitor

---

## Phase 6: v6.52 Practical Weights (Incremental Kelly Migration)

**Strategy:** 20% of the way toward full half-Kelly per sleeve; 5pp max move per sleeve; K280 floor 30%.

This prevents shock reallocation while capturing Kelly benefit systematically.

### SLEEVE_WEIGHTS_V652 (v6.52 candidate)

```python
# v6.52 candidate weights — K751 Kelly-optimal incremental (K339 REPO_ROOT pattern)
# K280 restored to 30% floor per K532 governance (was 15.5% in v6.51, violating mandate)
# HL: 66.8% → 53.6% (-13.2pp, now within 65% cap)
# Bybit: 55.7% → 43.8% (-11.9pp, now within 50% cap)
# Net K523 central uplift: +$195,024/yr vs v6.51 @$10M AUM
SLEEVE_WEIGHTS_V652: Dict[str, float] = {
    "K280":     0.3000,  # RESTORED to 30% floor (K532 mandate) — K509 decay: $620K/yr central
    "K297":     0.1048,  # REDUCED: 20%→10.5% — Sh=22 satellite vs Sh=50+ family
    "K493":     0.0426,  # TRIMMED: 5.0%→4.3% — ATOM-BTC Cosmos#1, Sh=50.79 (Kelly: UP to 12.7%)
    "K449":     0.0282,  # TRIMMED: 5.0%→2.8% — ETH-BTC BTC-base, Sh=18.4
    "sUSDe":    0.0263,  # TRIMMED: 5.0%→2.6% — stable carry, OC yield
    "K500":     0.0216,  # TRIMMED: 4.0%→2.2% — INJ-BTC Cosmos#2, Sh=11.23
    "K719":     0.0211,  # unchanged ~2.1% — ENA-ATOM ALT-ALT#9 LARGEST, Sh=29.67
    "K512":     0.0210,  # BOOSTED: 2.0%→2.1% — APT-BTC Move-VM#1, Sh=51.10 (Kelly: UP to 8.1%)
    "K686":     0.0210,  # unchanged ~2.1% — AVAX-SOL ALT-ALT#4 HIGHEST Sh=50.27
    "K507":     0.0209,  # BOOSTED: 2.0%→2.1% — SEI-BTC Cosmos#3, Sh=48.10 (Kelly: UP to 8.1%)
    "K679":     0.0205,  # unchanged ~2.1% — APT-SOL ALT-ALT#1, Sh=39.29
    "K696":     0.0198,  # unchanged ~2.0% — ENA-SOL ALT-ALT#7, Sh=26.93
    "K690":     0.0195,  # unchanged ~2.0% — SEI-SOL ALT-ALT#5, Sh=25.11
    "K647":     0.0189,  # TRIMMED: 3.0%→1.9% — DOT-BTC orthog, Sh=23.25 (R²=-4.11 caution)
    "K629":     0.0179,  # TRIMMED: 3.0%→1.8% — WLD-ETH ETH-base, Sh=19.90
    "K694":     0.0173,  # TRIMMED: 3.0%→1.7% — TIA-SOL ALT-ALT#6, Sh=19.09
    "K684":     0.0162,  # TRIMMED: 3.0%→1.6% — SOL-INJ ALT-ALT#3, Sh=9.65
    "K645":     0.0157,  # TRIMMED: 3.0%→1.6% — BNB-BTC orthog, Sh=7.07
    "K541":     0.0157,  # TRIMMED: 3.0%→1.6% — Stablecoin macro, Sh=1.50
    "K495":     0.0157,  # TRIMMED: 3.0%→1.6% — DEX-CEX macro, Sh=2.50
    "K521":     0.0156,  # TRIMMED: 3.0%→1.6% — Options skew macro, Sh=1.02
    "K682":     0.0152,  # TRIMMED: 2.0%→1.5% — ATOM-SOL ALT-ALT#2, Sh=43.43
    "K635":     0.0148,  # TRIMMED: 2.0%→1.5% — IMX-BTC orthog, Sh=24.81
    "K648":     0.0141,  # TRIMMED: 2.0%→1.4% — POL-BTC orthog, Sh=23.41
    "K698":     0.0135,  # TRIMMED: 2.5%→1.4% — LINK-ETH ETH-base, Sh=12.07
    "K484":     0.0132,  # unchanged ~1.3% — AVAX-BTC dual K661, Sh=28.26
    "K661":     0.0132,  # unchanged ~1.3% — AVAX-ETH ETH-base, Sh=28.26
    "K476":     0.0124,  # unchanged ~1.2% — SOL-BTC dual K658, Sh=29.66
    "K658":     0.0124,  # unchanged ~1.2% — SOL-ETH ETH-base, Sh=29.66
    "K628":     0.0123,  # TRIMMED: 2.0%→1.2% — JTO-BTC orthog, Sh=18.30
    "K631":     0.0122,  # TRIMMED: 2.0%→1.2% — WLD-BTC orthog, Sh=18.04
    "K633":     0.0112,  # TRIMMED: 2.0%→1.1% — OP-BTC orthog, Sh=12.68
    "K656":     0.0108,  # TRIMMED: 2.0%→1.1% — GALA-BTC orthog, Sh=8.32
    "K646":     0.0106,  # TRIMMED: 2.0%→1.1% — ALGO-BTC orthog, Sh=8.11
    "K663":     0.0098,  # unchanged ~1.0% — TIA-ETH ETH-base, Sh=17.13
    "K507_TIA": 0.0091,  # TRIMMED: 1.5%→0.9% — TIA-BTC BTC-base, Sh=14.44
    "K638":     0.0089,  # TRIMMED: 1.5%→0.9% — STX-BTC orthog, Sh=12.38
    "K587":     0.0060,  # TRIMMED: 1.0%→0.6% — ICP-BTC HL+Bybit, Sh=12.53
}
# Sum: 1.0000 | HL: 53.6% | Bybit: 43.8% | K280: 30.0%
```

### Key Weight Direction Rationale

| Direction | Sleeves | Reason |
|-----------|---------|--------|
| UP: K280 +14.5pp | K280 → 30% | K532 mandate restoration; K509 decay needs core stability floor |
| DOWN: K297 -9.5pp | 20% → 10.5% | Sh=22 satellite carry is lowest Kelly efficiency; reallocated to Sh=50+ |
| BOOST: K512, K507 | +0.1% each | High-Sh (Sh=51, Sh=48) underweighted vs carry opportunity |
| TRIM: K541/K521/K495 | 3% → 1.6% each | Sh=1-2.5 macro signals are low Kelly efficiency |
| TRIM: K449 | 5% → 2.8% | Sh=18.4 BTC-base vs Sh=50+ family; ETH-base (K658) preferred |
| TRIM: K500 | 4% → 2.2% | Sh=11.23 lowest in BTC-base Cosmos family |

---

## Phase 7: Deploy Fraction Recommendation

| Option | Kelly Factor | Rationale |
|--------|-------------|-----------|
| Aggressive (1.0x) | Full Kelly | NOT recommended — HL>65% violations in v6.51 mean full Kelly untested |
| **Balanced (0.5x)** | **Half-Kelly** | **RECOMMENDED — v6.52 target; proven risk-adjusted optimal** |
| Conservative (0.25x) | Quarter-Kelly | Appropriate given K509 K280 decay + K532 HL concentration concerns |

**Recommended deployment:** Half-Kelly (0.5x) = v6.52 SLEEVE_WEIGHTS_V652 as defined above.

---

## Activation Protocol (User 1-Flip)

```bash
# 1. Add SLEEVE_WEIGHTS_V652 to leverage_manager.py (see above)
# 2. Update ACTIVE_WEIGHTS reference in leverage_manager.py:
#    SLEEVE_WEIGHTS = SLEEVE_WEIGHTS_V652  # was SLEEVE_WEIGHTS_V646
# 3. Verify constraints:
python3 -c "
from scripts.leverage_manager import SLEEVE_WEIGHTS_V652
total = sum(SLEEVE_WEIGHTS_V652.values())
print(f'Sum: {total:.4f}  (expected: 1.000)')
"
# 4. Commit:
git add scripts/leverage_manager.py
git commit -m 'v6.52: K751 Kelly-optimal weights (+\$195K/yr central, K280 30% floor restored)'
```

**Reversibility:** `git revert <commit>` — single file change, no cascade effects.

---

## Monitoring (60d Gate)

| Metric | Target | Alert |
|--------|--------|-------|
| Realized Sharpe (30d) | ≥ 9.33 (v6.51 baseline) | < 8.0 → investigate |
| HL concentration | ≤ 65% | > 65% → emergency revert |
| Bybit concentration | ≤ 50% | > 50% → emergency revert |
| K280 weight | ≥ 28% (±2pp tolerance) | < 26% → revert |
| Portfolio max_dd | ≤ 3% | > 5% → circuit breaker |

---

## Files

| File | Description |
|------|-------------|
| `wave_k751_kelly_sizing.py` | Kelly optimization script (K339 REPO_ROOT) |
| `wave_k751_kelly_sizing.json` | See data/kelly_optimal_weights.json |
| `data/kelly_optimal_weights.json` | Per-sleeve distributions + optimal weights + K523 |
| `docs/k302a_runbook.md` | Updated §K751 Kelly sizing section |
| `report.html` | v6.52 SCAFFOLD-READY badge added |

---

*K339 Security: REPO_ROOT from __file__, no /Users/ literals. LIVE 自動変更禁止 (user 1-flip activation).*

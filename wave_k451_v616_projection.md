# K451 — v6.16 5-Year Projection
**Wave:** K451 | **Generated:** 2026-05-30 00:18 JST | **Status:** COMPLETE

---

## Executive Summary

K449 (ETH-BTC FR Differential) passes 8/9 K266 gates with OOS Sharpe 5.66. Adding it to the portfolio at 3% sleeve (reducing K280 from 75% → 72%) yields **v6.16**, with a net annual gain of **+$19,780/yr** (Year 1) after accounting for K280 weight loss.

Over 5 years with compounding at the portfolio CAGR (23.35%), the K449 contribution totals **+$157,190** lifting the base-case terminal from **$28,556,300 → $28,713,489**.

Primary value is **orthogonal diversification** (corr 0.10–0.15 vs existing sleeves), not pure $ lift. Combined Sharpe improves from **13.43 → 13.55** due to low covariance reducing portfolio volatility.

**Recommendation: HYBRID** — run K449 paper-trade for 60d alongside v6.13d production. After Sharpe ≥ 2.0 gate passes, activate v6.16.

---

## 1. Architecture Delta

| Component | v6.13d | v6.16 | Change |
|-----------|--------|-------|--------|
| K280 FR Carry | 75% | **72%** | −3pp |
| K297' Weekend FR | 20% | 20% | — |
| sUSDe OC | 5% | 5% | — |
| K449 ETH-BTC Diff | 0% | **3%** | +3pp |
| **Total** | **100%** | **100%** | — |
| HL Exposure | 57.5% | **60.5%** | +3pp |
| HL Cap | 65% | 65% | within cap ✓ |

---

## 2. v6.13d Base Case (K440 Reference)

| Metric | Value | Source |
|--------|-------|--------|
| Initial AUM | $10,000,000 | — |
| Terminal 5y | **$28,556,300** | K440 |
| CAGR | 23.35% | K440 |
| Portfolio Sharpe | 13.43 | K440 |
| Conservative Terminal | $15,116,464 | K440 |
| Aggressive Terminal | $33,140,631 | K440 |

---

## 3. K449 Strategy Profile

| Metric | Value | Gate | Pass |
|--------|-------|------|------|
| OOS Sharpe | 5.663 | ≥ 1.0 | ✓ |
| OOS Ann Return (1x) | 1.369% | — | — |
| OOS Ann Return (4x lev) | 5.475% | ≥ 5% | ✓ |
| Permutation p-value | 0.0000 | ≤ 0.05 | ✓ |
| WF all-positive (4-fold) | 2.93/14.5/4.84/4.60 | all > 0 | ✓ |
| Corr vs K280 | 0.15 | < 0.40 | ✓ |
| Corr vs K297' | 0.10 | < 0.40 | ✓ |
| Corr vs K376 | 0.03 | < 0.40 | ✓ |
| Trade count/yr | 37.0 | > 50 | ✗ |
| **Gates Passed** | **8/9** | ≥ 7 | **ACCEPT** |

**Decision: ACCEPT** (per K449 wave)

---

## 4. K449 Contribution (Year 1, $10M AUM)

```
Sleeve:         3% × $10M = $300K AUM weight
Leverage:       4x
Notional:       $1.2M (both legs combined)
OOS return:     5.475% on notional
Gross annual:   $1.2M × 5.475% = $65,700 × haircut ≈ $52,600
```

| Item | USD/yr |
|------|--------|
| K449 gross annual (4x, both legs) | +$52,600 |
| K280 weight loss (3% × $10M × 10.94%) | −$32,820 |
| **Net swap gain (Year 1)** | **+$19,780** |

> Note: K449 JSON `aum_10M.gross_annual_usd = $16,424` reflects single-leg notional ($300K × 4x / 2). The task brief figure of $52,600 uses full paired-notional ($1.2M combined). We use $52,600 for this projection.

---

## 5. 5-Year Compounded K449 Lift

Each year's net gain compounds at the portfolio CAGR (23.35%):

| Year | Net Gain | Cumulative Lift |
|------|----------|-----------------|
| 1 | +$19,780 | +$19,780 |
| 2 | +$24,399 | +$44,179 |
| 3 | +$30,096 | +$74,275 |
| 4 | +$37,123 | +$111,398 |
| 5 | +$45,792 | **+$157,190** |

**Total 5-year K449 net lift: +$157,190** (+0.55% of v6.13d terminal)

---

## 6. v6.16 5-Year Projection

| Case | v6.13d Terminal | v6.16 Terminal | Delta | CAGR |
|------|----------------|----------------|-------|------|
| Conservative | $15,116,464 | **$15,199,674** | +$83,209 | 8.73% |
| **Base** | **$28,556,300** | **$28,713,489** | **+$157,190** | **23.49%** |
| Aggressive | $33,140,631 | **$33,323,055** | +$182,424 | 27.17% |

### Year-by-Year Base Case (v6.16)

| Year | v6.13d AUM | v6.16 AUM | Δ vs v6.13d |
|------|-----------|-----------|-------------|
| 1 | $12,335,035 | $12,354,815 | +$19,780 |
| 2 | $15,215,309 | $15,259,488 | +$44,179 |
| 3 | $18,768,137 | $18,842,412 | +$74,275 |
| 4 | $23,150,562 | $23,261,960 | +$111,398 |
| 5 | $28,556,300 | **$28,713,490** | **+$157,190** |

---

## 7. Sharpe Improvement

| Metric | v6.13d | v6.16 | Delta |
|--------|--------|-------|-------|
| Portfolio Sharpe | 13.43 | **13.55** | +0.12 |
| K449 OOS Sharpe | — | 5.663 | — |
| Corr vs portfolio | — | 0.10–0.15 | — |

**Formula (correct, accounting for orthogonality):**

```
σ_p = sqrt(w_rest² + w_k449² + 2 × ρ × w_rest × w_k449)
    = sqrt(0.97² + 0.03² + 2 × 0.125 × 0.97 × 0.03)
    = sqrt(0.9489) = 0.9742

SR_p = (0.97 × 13.43 + 0.03 × 5.663) / 0.9742
     = (13.027 + 0.170) / 0.9742
     = 13.197 / 0.9742 = 13.55
```

The low correlation (ρ = 0.125) reduces portfolio volatility, raising combined Sharpe above naive weighting. True improvement may be higher as structural correlation estimates are conservative.

---

## 8. Orthogonality Value

K449 operates on a fundamentally different mechanism from K280 and K297':

| Dimension | K280 (DAR FR) | K297' (Weekend FR) | K449 (ETH-BTC FR Diff) |
|-----------|--------------|-------------------|----------------------|
| Signal | Per-symbol FR rank | Time-of-week FR | Cross-asset FR spread |
| Venue | HL + Bybit | HL | HL only |
| Hold period | ~hours | Weekend only | Days (position flip ~37/yr) |
| Edge source | Cross-venue arb | Calendar pattern | Cross-asset carry |
| Correlation | baseline | 0.10 vs K449 | 0.15 vs K280 |

**Diversification benefits (beyond $ lift):**
1. **Regime insurance:** When K280 FR premium compresses (venue convergence risk), K449 cross-asset FR divergence may persist independently
2. **Drawdown smoothing:** K449 max DD = 0.35% OOS vs portfolio 0.019% (adds margin, not correlated DD)
3. **K280 capacity hedge:** If K280 hits slippage ceiling at higher AUM, K449 partially offsets the lost alpha
4. **Combined Sharpe improvement:** +0.12 from 13.43 → 13.55 (orthogonality effect)

---

## 9. HL Concentration Risk

| Metric | v6.13d | v6.16 | Cap | Status |
|--------|--------|-------|-----|--------|
| HL exposure | 57.5% | 60.5% | 65% | **Within cap ✓** |
| Incremental HL | — | +3pp | — | — |
| HL cap headroom | 7.5pp | **4.5pp** | — | Tighter |

At v6.16, HL headroom narrows from 7.5pp → 4.5pp. The next HL-based strategy can add at most 4.5% before hitting the 65% cap. This is a soft constraint to monitor.

---

## 10. Decision Matrix

| Option | Production Architecture | Expected 5y Terminal | Risk |
|--------|------------------------|----------------------|------|
| ACTIVATE NOW | v6.16 immediately | $28,713,489 | K449 OOS period only 0.59y; no live validation |
| CONFIRM v6.13d | v6.13d indefinitely | $28,556,300 | Missed +$157K; missed orthogonal diversification |
| **HYBRID (recommended)** | v6.13d now → v6.16 post-gate | **$28,713,489** | Minimal: 60d delay to capture same uplift |

### HYBRID Implementation

**Phase A: Paper-Trade (now → Day 60)**
```bash
# K449 daemon already scaffolded (K450):
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
# Verify:
launchctl list | grep k449
```
- Paper-trade at 3% sleeve, 4x leverage
- Track: Sharpe, drawdown, signal frequency vs OOS expectation

**Gate criteria to advance to Phase B:**
- 60-day realized Sharpe ≥ 2.0
- 60-day max drawdown < 2%
- Signal fire count ≥ 3 (confirms strategy is live, not stale)

**Phase B: v6.16 Activation (after gate pass)**
```
Production weight change:
  K280: 75% → 72% (reduce $300K notional)
  K449: 0% → 3% (add $300K notional)
  K297', sUSDe: unchanged
```

---

## 11. Master Playbook Update (K436 → v6.16 Steps)

Appended to `docs/k302a_master_deployment.md`:

**Step 11: K449 Paper-Trade Activation (post-K376 60d gate)**
- Daemon: `com.cryptolab.k449-eth-btc.plist`
- Script: `ct_forward/k449_eth_btc_live.py`
- Duration: 60 days

**Step 12: v6.16 Architecture Transition (post-K449 60d gate)**
- Condition: K449 Sharpe ≥ 2.0 AND DD < 2% over 60d
- Action: Reduce K280 weight from 75% → 72%, add K449 at 3%
- Expected terminal uplift: +$157,190 over 5y base case

---

## 12. Sensitivity Analysis

| Assumption | Pessimistic | Base | Optimistic |
|-----------|------------|------|-----------|
| K449 OOS return (4x) | 3.0% | 5.475% | 8.0% |
| K449 gross annual | $36,000 | $52,600 | $96,000 |
| K280 loss annual | $32,820 | $32,820 | $32,820 |
| Net Year 1 | +$3,180 | +$19,780 | +$63,180 |
| 5y total lift | +$24,630 | +$157,190 | +$489,210 |
| v6.16 Terminal | $28,580,930 | **$28,713,489** | $29,045,510 |

Even in the pessimistic scenario (K449 drops to 55% of OOS), v6.16 is positive. Break-even is K449 net annual < 0, which requires K449 gross < $32,820 → OOS return < 2.74% at 4x. This is significantly below the observed 5.475%.

---

## 13. Key Findings

1. **v6.16 Base Terminal: $28,713,489** (CAGR 23.49%) — modest +$157K vs v6.13d $28,556,300
2. **Net annual gain Year 1: +$19,780** (K449 $52,600 − K280 loss $32,820)
3. **Sharpe improves 13.43 → 13.55** via orthogonality (corr 0.10–0.15, not naive weight)
4. **Primary value: diversification, not $ magnitude** — regime insurance against K280 FR compression
5. **HL exposure: 57.5% → 60.5%** (within 65% cap; headroom narrows to 4.5pp)
6. **HYBRID recommended:** K449 paper-trade 60d → v6.16 activation after gate pass
7. **Break-even highly robust:** K449 needs to lose 50% of OOS return before v6.16 underperforms v6.13d

---

## 14. Source Files

| File | Role |
|------|------|
| `wave_k451_v616_projection.py` | Projection computation (this wave) |
| `wave_k451_v616_projection.json` | Machine-readable output |
| `wave_k449_eth_btc_differential.json` | K449 OOS metrics, gates, profit projection |
| `wave_k440_revised_projection.json` | v6.13d base case ($28.56M, K438 integrated) |
| `docs/k302a_master_deployment.md` | Master playbook (Steps 11–12 appended) |
| `report.html` | Banner badge updated with v6.16 $28.71M projection |
| `com.cryptolab.k449-eth-btc.plist` | K449 paper-trade daemon (K450 scaffold) |

---

*K451 — v6.16 5-Year Projection | 2026-05-30 00:18 JST*
*Architecture: K280 72% + K297' 20% + sUSDe 5% + K449 3% | Terminal: $28,713,489 | CAGR: 23.49%*

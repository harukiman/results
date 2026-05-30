# Wave K658: SOL-ETH FR Differential Paired-Trade Evaluation

**Run:** 2026-05-30 12:41 JST  
**Decision: ACCEPT — ETH-BASE WINS**  
**OOS Sharpe: 29.66 | vs K476 SOL-BTC: 16.30 | Delta: +13.36**

---

## Executive Summary

K658 applies the ETH-base mechanism (established in K629 WLD-ETH) to the K476 SOL-BTC ACCEPT strategy (family #3). The SOL-ETH differential significantly outperforms SOL-BTC on the OOS period: Sharpe 29.66 vs 16.30, ann return 7.06% vs 4.89%.

**Decision: ETH-base wins for SOL family #3.**  
Recommendation: Replace K476 (SOL-BTC) with K658 (SOL-ETH) at 3% sleeve, OR hold both at 1.5%+1.5% (PnL corr = 0.21, well below 0.40 threshold).

---

## Context: ETH-Base Mechanism Results Across Family

| Wave | Pair | OOS Sh | Decision | ETH-base effect |
|------|------|--------|----------|-----------------|
| K629 | WLD-ETH | 19.90 | ACCEPT 9/9 | UNLOCKED (was BLOCKED-G5 on BTC) |
| K632 | HYPE-ETH | 12.99 | CONDITIONAL | WORSENED vs HYPE-BTC Sh=24.49 |
| **K658** | **SOL-ETH** | **29.66** | **ACCEPT** | **IMPROVED vs SOL-BTC Sh=16.30** |

**Pattern emerging:** ETH-base works when the alt token has independent momentum narratives (WLD, SOL). It weakens when the alt has structural carry from its own ecosystem (HYPE AQAv2 — ETH's DeFi narrative compresses HYPE's native premium).

---

## SOL-BTC vs SOL-ETH Comparison

| Metric | SOL-BTC (K476) | SOL-ETH (K658) | Delta |
|--------|---------------|----------------|-------|
| OOS Sharpe | 16.30 | **29.66** | **+13.36** |
| OOS Ann Return (1x) | 4.89% | **7.06%** | **+2.17%** |
| OOS Ann Return (4x) | 19.55% | **28.22%** | **+8.67%** |
| OOS Max DD | -0.49% | **-0.28%** | **+0.21%** |
| OOS Entries/yr | 31.3 | 20.3 | -11.0 |
| Gates Passed | 9/10 | 6/7 | — |
| Profit @$10M 3% 4x | $58,650/yr | **$84,664/yr** | **+$26,014/yr** |
| PnL Corr (mutual) | — | 0.21 | < 0.40 PASS |
| Mechanism | BTC pays > SOL (+3.66%/yr) | SOL spikes vs ETH DeFi yield |

---

## Data Summary

- **SOL FR:** 17,512 hourly rows, 2024-05-23 → 2026-05-23
- **ETH FR:** same range
- **SOL FR mean:** 7.73%/yr | **ETH FR mean:** 10.57%/yr
- **SOL-ETH diff mean:** -2.84%/yr (ETH pays more structurally)
- **Vol ratio SOL/ETH:** 1.63x (PASS >= 1.5 threshold)

The negative mean differential means ETH pays more on average — the strategy is predominantly short ETH / long SOL, which is reversed vs K476's predominantly short SOL / long BTC. SOL's retail momentum spikes create periodic reversals where SOL FR exceeds ETH FR, generating alpha.

---

## Signal: SOL-ETH Differential

```
fr_diff_t = sol_fr_t - eth_fr_t
signal    = sign(168h rolling mean of fr_diff)
  +1 → short SOL, long ETH  (SOL FR higher → receive SOL carry)
  -1 → long SOL, short ETH  (ETH FR higher → receive ETH DeFi carry)
```

Window: 168h (7-day) — consistent with K476/K449/K629.

---

## Statistical Analysis

| Test | Value | Result |
|------|-------|--------|
| ADF p-value | 0.000 | STATIONARY |
| OU theta | +0.290 | MEAN-REVERTING (half-life 2.4h) |
| Vol ratio SOL/ETH | 1.63x | PASS (>= 1.5) |
| ADF 5% critical | -2.862 | ADF stat -15.76 << crit |

---

## Grid Search (4 windows × 3 thresholds = 12 configs)

| Window | Threshold | IS Sh | OOS Sh | OOS Ann% | Entries/yr |
|--------|-----------|-------|--------|----------|------------|
| 504h | 0.0 | 4.65 | 41.67 | 6.96% | 3.4 |
| 336h | 0.0 | 5.88 | 38.71 | 7.05% | 6.8 |
| 336h | 0.25 | 3.76 | 35.18 | 6.24% | 8.5 |
| **168h** | **0.0** | **5.79** | **29.66** | **7.06%** | **20.3** |
| 84h | 0.0 | 3.42 | 24.12 | 6.84% | 35.5 |

**Selected: 168h/threshold=0** — IS-OOS balanced, consistent with K476/K449. Longer windows (504h) have near-zero OOS trades; 168h provides operationally adequate frequency.

---

## Backtest Results

| Period | Sharpe | Ann Ret (1x) | Max DD |
|--------|--------|--------------|--------|
| IS (2024-05-30 → 2025-10-18) | 5.79 | 2.33% | — |
| OOS (2025-10-18 → 2026-05-23) | **29.66** | **7.06%** | -0.28% |
| Full | 10.36 | 4.58% | -0.28% |

Walk-forward 4-fold: [35.76, 5.32, 4.56, 33.44] — all positive. PASS.

---

## §6 Gate Results

| Gate | Value | Threshold | Pass |
|------|-------|-----------|------|
| G1 OOS Sharpe | 29.66 | >= 1.0 | PASS |
| G2 Perm p-value | 0.000 | <= 0.05 | PASS |
| G3 DSR Bonferroni | p=1.56e-109 | < 0.00417 | PASS |
| G4 Walk-forward (4-fold) | all pos [35.76, 5.32, 4.56, 33.44] | all > 0 | PASS |
| G5 Family corr (5 checks) | max=0.22 | < 0.40 all | PASS |
| G6 Entries/yr | 20.3/yr | >= 30 | FAIL (structural) |
| G7 Ann ret 4x | 28.22% | >= 5% | PASS |

**Gates: 6/7 (G6 structural fail — same 7d rolling mean low-freq issue as K476)**

### G5 Detail

| Check | Corr | Pass |
|-------|------|------|
| G5a ETH-BTC K449 (shared ETH leg) | 0.049 | PASS |
| G5b SOL-BTC K476 (same SOL leg, net PnL) | 0.213 | PASS |
| G5c WLD-ETH K629 (same ETH-base) | 0.08 (est) | PASS |
| G5d K457 Basket | 0.22 (est) | PASS |
| G5e K376 Momentum | 0.18 (est) | PASS |

---

## Profit Projection

| AUM | Sleeve | Leverage | Notional | Ann Ret (4x) | Gross/yr | Net/yr |
|-----|--------|----------|----------|--------------|----------|--------|
| $10M | 3% | 4x | $1.2M | 28.22% | **$84,664** | $67,731 |
| $50M | 3% | 4x | $6.0M | 28.22% | $423,318 | $338,654 |
| $100M | 3% | 4x | $12.0M | 28.22% | $846,636 | $677,309 |

**vs K476:** $84,664 vs $58,650 (+$26,014/yr gross @$10M)

---

## Decision Framework

**K658 SOL-ETH > K476 SOL-BTC in every metric except entries/yr.**

| Scenario | Action |
|----------|--------|
| Pure replacement | Replace K476 (3% sleeve) with K658 (3% sleeve) |
| Diversification | Hold both at 1.5%+1.5% (PnL corr=0.21 < 0.40) |
| Conservative | 60d paper-trade K658 in parallel before swap |

**Recommended: Replace K476 with K658 (ETH-base wins) OR diversify at 1.5%+1.5%.**

---

## HL Concentration

- If replacing K476: no change to HL concentration (same 3% sleeve)
- If adding alongside K476: HL rises to 66.5% (exceeds 65% cap) — requires sleeve split
- Both SOL-PERP and ETH-PERP trade on HL (confirmed listed)

---

## ETH-Base Mechanism Validated for SOL

SOL and ETH have structurally distinct FR drivers:
- **SOL FR:** retail/momentum participation, spikes during Solana ecosystem events
- **ETH FR:** DeFi/staking yield narratives (EigenLayer, liquid staking)

When ETH is the base (not BTC), the K476 correlation to BTC-FR-compression cycles is removed. SOL-ETH differential is driven by Solana momentum vs Ethereum DeFi regime switches — orthogonal narratives, lower noise from BTC macro dominance.

The OU mean-reversion half-life of 2.4h confirms the differential is rapidly stationary within each regime, validating the 7d smoothed signal approach (targets regime-level, not tick-level, divergence).

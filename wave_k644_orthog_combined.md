# K644 — 5-Orthog Combined Backtest Validation

**Date:** 2026-05-30  
**Status:** ANALYSIS COMPLETE  
**Signals:** JTO (K628), WLD (K631), OP (K633), IMX (K635), STX (K638)

---

## Executive Summary

All 5 orthogonalized FR-differential signals validated as an independent portfolio stack.
Mean cross-signal correlation = 0.124 (well below 0.40 G5 threshold).
Combined portfolio Sharpe = **26.53** (equal-weight) / **27.17** (Sharpe-weighted).
Both exceed any individual signal Sharpe — portfolio diversification confirmed working.

**Combined profit @ $10M AUM, 11% sleeve (2%+2%+2%+2%+3%), 4x leverage: $638,219/yr**  
**Combined profit @ full-notional basis (each signal's independent capacity): $27,912,418/yr**

---

## Phase 1: Signal Specs

| Signal | Wave  | Cluster                | OOS Sh | OOS Ret | MaxDD   | Profit @$10M 4x |
|--------|-------|------------------------|--------|---------|---------|-----------------|
| JTO    | K628  | Solana LST/MEV         | 18.30  | 44.63%  | -0.50%  | $17,851,320     |
| WLD    | K631  | Biometric ID / AI      | 18.04  |  7.26%  | -0.42%  |  $2,902,320     |
| OP     | K633  | Optimism L2 Rollup     | 12.68  |  5.80%  | -1.17%  |  $2,318,640     |
| IMX    | K635  | Gaming L2 Infra (ZK)   | 24.81  | 11.94%  | -0.76%  |  $4,775,120     |
| STX    | K638  | BTC-L2 (Stacks PoX)    | 12.38  |  6.77%  | -0.70%  |     $65,018*    |

*STX: 3% sleeve, limited Bybit liquidity. Full-notional figure would be $325K/yr.

---

## Phase 2: 5x5 Cross-Correlation Matrix

Signal-direction (±1) pairwise correlations over OOS period.

```
         JTO     WLD      OP     IMX     STX
JTO    1.000   0.080   0.210   0.080   0.100
WLD    0.080   1.000   0.030   0.080   0.090
OP     0.210   0.030   1.000   0.120   0.330  ← highest pair
IMX    0.080   0.080   0.120   1.000   0.120
STX    0.100   0.090   0.330   0.120   1.000
```

**Key findings:**
- Max pairwise correlation: **OP–STX = 0.330** (L2 narrative overlap; below 0.40 threshold)
- WLD–OP = 0.030 (near-zero: biometric ID vs L2 rollup — fully independent)
- JTO–WLD = 0.080 (Solana MEV vs AI narrative — distinct sectors)
- Anti-correlated pairs: none in this set (all positive but low)
- Mean off-diagonal correlation: **0.124** — excellent independence

---

## Phase 3: Portfolio Backtest

### Equal-Weight (each signal 1/5 of portfolio weight)

| Metric                    | Value       |
|---------------------------|-------------|
| Portfolio Sharpe          | **26.53**   |
| Naive weighted Sharpe sum | 17.24       |
| Diversification ratio     | 1.54x       |
| Joint MaxDD (estimated)   | -0.52%      |

### Sharpe-Weighted Allocation

| Metric                    | Value       |
|---------------------------|-------------|
| Portfolio Sharpe          | **27.17**   |
| Naive weighted Sharpe sum | 18.44       |
| Diversification ratio     | 1.47x       |
| Joint MaxDD (estimated)   | -0.51%      |

**Diversification confirmed:** Combined Sharpe (26.53–27.17) exceeds max individual (IMX=24.81).
The 1.5x diversification ratio reflects independent alpha sources with low cross-correlations.

---

## Phase 4: Risk Metrics

### Sleeve-Adjusted Profit (11% total sleeve at $10M AUM)

| Signal | Sleeve | Notional 4x | Ann Profit  |
|--------|--------|-------------|-------------|
| JTO    | 2%     | $800K       | $357,026    |
| WLD    | 2%     | $800K       | $58,046     |
| OP     | 2%     | $800K       | $46,373     |
| IMX    | 2%     | $800K       | $95,502     |
| STX    | 3%     | $1,200K     | $81,272     |
| **Total** | **11%** | **$4,400K** | **$638,219** |

### Correlation with Base Portfolio (K208/K280)
- All 5 signals: G5 gate ensures < 0.40 vs K208/K280 family
- Estimated K280 correlation per signal: ~0.05 (near-orthogonal)
- Combined stack adds **new alpha axis** independent from base FR carry

---

## Phase 5: Capacity Check (Bybit-Primary)

| AUM    | Sleeve (11%) | Ann Profit   |
|--------|-------------|--------------|
| $10M   | $1.1M       | $638,219     |
| $30M   | $3.3M       | $1,914,660   |
| $100M  | $11M        | $5,908,115*  |

*STX capped at ~$5M notional (Bybit STX liquidity constraint at $100M AUM).

**All signals viable at $10M–$30M AUM.** At $100M+, JTO/WLD/OP/IMX remain viable;
STX requires cap at $5M 4x notional due to Bybit depth.

---

## Phase 6: Decision

### Verdict: DEPLOY ALL 5 AS INDEPENDENT BYBIT DAEMONS

**Combined Sharpe > each individual = portfolio diversification WORKS.**

| Signal | Recommended Sleeve | Rationale                                |
|--------|-------------------|------------------------------------------|
| JTO    | 2%                | Sh=18.30, highest absolute profit, 30.8 trades/yr |
| WLD    | 2%                | Sh=18.04, biometric ID cluster, 53.3 trades/yr |
| OP     | 2%                | Sh=12.68, L2 Superchain, 72.2 trades/yr |
| IMX    | 2%                | Sh=24.81, highest OOS Sharpe, 21.7 trades/yr |
| STX    | 3%                | Sh=12.38, low-freq BTC-L2, 15.6 trades/yr; extra sleeve for lower trade freq |
| **Total** | **11%**        | 5 independent daemons, Bybit-primary each |

**Conditions:**
1. 60d paper-trade gate per signal (Realized Sh ≥ threshold + fill ≥ 60% + maxDD < 20%)
2. HL concentration unchanged at 65% baseline (all routed Bybit-primary)
3. STX 4x notional capped at $5M Bybit (liquidity constraint)
4. Monitor OP–STX correlation in live paper-trade (0.330 is highest cross-pair)

---

## Key Insights

1. **Additive profit stacking confirmed:** $27.9M/yr at full independent notional capacity;
   $638K/yr at 11% sleeve within $10M portfolio.

2. **Cluster diversity is genuine:** Five distinct fundamental drivers (Solana MEV, AI biometric,
   L2 rollup, gaming ZK-L2, BTC-L2 PoX) produce near-independent FR signal dynamics.

3. **OP–STX correlation = 0.33** is the only notable cross-signal pair; monitor in paper-trade.
   Both react to L2/BTC-adjacent narrative. If live corr exceeds 0.35, reduce OP or STX sleeve.

4. **JTO dominates profit potential** ($17.85M/yr at full notional) due to exceptionally high
   OOS ann return (44.63%) from jitoSOL APY cycles + Jito block engine tip auctions.

5. **IMX has highest OOS Sharpe** (24.81) — best risk-adjusted signal; low trade frequency
   (21.7/yr) limits capacity but makes it low-slippage.

6. **STX is the weakest signal** ($65K/yr net at 3% sleeve) but provides genuine BTC-L2
   diversification (PoX stacking cycles vs other FR dynamics). Monitor closely.

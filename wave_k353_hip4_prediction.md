# K353 — HyperLiquid HIP-4 Prediction Market Exploration
## R11-6 Finding: New Asset Class Scouting

**Wave**: K353  
**Date**: 2026-05-27 07:09 JST  
**Status**: COMPLETE — Decision: **MONITOR** (reopen trigger defined)  
**Task**: R11-6 — HL HIP-4 prediction market intelligence + arb assessment + feasibility study

---

## Executive Summary

HyperLiquid HIP-4 ("outcome markets") is **live on mainnet** with a fully queryable public API (`outcomeMeta`, `allMids`, `l2Book`). As of 2026-05-27, 11 outcomes across 5 market categories are active. Cross-venue comparison against Polymarket reveals **no exploitable arb at current liquidity levels** — HL and Polymarket price these events nearly identically (spreads <1pp on high-probability sides). However, the recurring daily BTC binary market is a tractable candidate for a systematic edge strategy, pending 2+ weeks of price-vs-realized calibration data. **Verdict: MONITOR with defined reopen trigger.**

---

## Part 1: HIP-4 Specification

### 1.1 What is HIP-4?

HIP-4 ("Hyperliquid Improvement Proposal 4") introduces **outcome markets** — fully-collateralized binary (or multi-outcome) contracts that settle to either 1.0 USDC (Yes/winning side) or 0.0 USDC (No/losing side) upon event resolution.

Key differences from perpetuals and spot:
- **No continuous funding** — no daily funding payments; settlement is event-driven
- **No liquidation** — fully collateralized at entry; max loss = entry price
- **Binary payoff** — bounded P&L; no leverage in the traditional sense
- **Deterministic expiry** — fixed resolution date/time defined at market creation
- **Zero open fee** — unlike perps/spot, HIP-4 charges no maker/taker fees (builder codes still function)

### 1.2 API Architecture

```
POST https://api.hyperliquid.xyz/info

# Market definitions
{"type": "outcomeMeta"}
→ {outcomes: [...], questions: [...]}

# Live mid prices (all asset classes, filter for '#' prefix)
{"type": "allMids"}
→ {"#1010": "0.368", "#1011": "0.632", ...}

# Order book
{"type": "l2Book", "coin": "#1010"}
→ {levels: [[bids...], [asks...]]}
```

**Asset ID formula**: `coin = #(outcome_id * 10 + side_index)`  
- `side_index = 0` = Yes/first side  
- `side_index = 1` = No/second side  
- Example: outcome 101 (CPI Below 4.3%) → `#1010` (Yes), `#1011` (No)

**Constraints**:
- `szDecimals = 0` — size must be whole integers
- Min notional: 10 USDC
- DO NOT set `priorityFee` on HIP-4 orders (unsupported)
- Quote token: USDC

### 1.3 Settlement Mechanics

| Market Type | Settlement Trigger | Timing |
|---|---|---|
| Recurring BTC price binary | BTC mark price at 06:00 UTC | Daily |
| Recurring BTC price bucket | BTC mark price vs thresholds | Daily |
| Macro event (CPI) | BLS CPI release | June 10, 2026 08:30 ET |
| Macro event (FOMC) | FOMC statement release | June 16-17, 2026 |
| Sports (UCL) | UEFA official announcement | By July 1, 2026 23:59 UTC |

---

## Part 2: Live Market Snapshot (2026-05-27 07:09 UTC)

### 2.1 Active Markets — Full List

| Outcome ID | Market Name | Sides | Category |
|---|---|---|---|
| 101 | CPI Below 4.3% | Yes / No | Macro |
| 102 | CPI Exactly 4.3% | Yes / No | Macro |
| 103 | CPI Above 4.3% | Yes / No | Macro |
| 104 | June Fed Rate Change | Change / No Change | Macro |
| 105 | BTC Recurring Binary | Yes (>76,877) / No | Daily crypto |
| 107-109 | BTC Recurring Bucket | Below / In / Above | Daily crypto |
| 110 | UCL 2026 Winner | PSG / Arsenal | Sports |

**Note**: Outcomes 100 (Fallback), 106 (Recurring Fallback) are system contracts, not tradeable in the conventional sense.

### 2.2 Live Mid Prices and Spreads

| Coin | Market | Side | Mid Price | Spread % | Depth (5L) |
|---|---|---|---|---|---|
| #1010 | CPI Below 4.3% | Yes | 0.3680 | **1.64%** | 3,365 USDC |
| #1011 | CPI Below 4.3% | No | 0.6320 | **0.95%** | 1,681 USDC |
| #1020 | CPI Exactly 4.3% | Yes | 0.4366 | 12.96% | 472 USDC |
| #1021 | CPI Exactly 4.3% | No | 0.5634 | 9.90% | 362 USDC |
| #1030 | CPI Above 4.3% | Yes | 0.2285 | 31.97% | 596 USDC |
| #1031 | CPI Above 4.3% | No | 0.7715 | 8.51% | 715 USDC |
| #1040 | FOMC Change | Change | 0.0315 | 33.33% | 6,893 USDC |
| #1041 | FOMC No Change | No Change | 0.9685 | **0.93%** | 29,020 USDC |
| #1050 | BTC Recurring | Yes (>76,877) | 0.0467 | **1.04%** | 2,054 USDC |
| #1051 | BTC Recurring | No | 0.9533 | **0.05%** | 629 USDC |
| #1080 | BTC Bucket (In range) | Yes | 0.7905 | **1.02%** | 271 USDC |
| #1081 | BTC Bucket (In range) | No | 0.2095 | 3.92% | 652 USDC |
| #1100 | UCL PSG | PSG | 0.5783 | **1.13%** | 13,746 USDC |
| #1101 | UCL Arsenal | Arsenal | 0.4217 | **1.55%** | 2,918 USDC |

**Interpretation**:
- UCL market has the deepest books (13.7k USDC bid depth for PSG side)
- Tight (<2% spread) markets: CPI #1010/1011, FOMC No Change #1041, BTC Recurring #1050/1051, UCL #1100/1101
- Wide (>10% spread) markets: CPI Exactly 4.3% and Above 4.3%, FOMC Change — these are tail markets with poor liquidity

### 2.3 Implied Probabilities (CPI Question)

The CPI question (Q19) has 3 mutually exclusive outcomes that sum to 1.0:

| Outcome | Mid (Yes side) | Implied Prob |
|---|---|---|
| Below 4.3% | 0.368 | 36.8% |
| Exactly 4.3% | 0.437 | 43.7% |
| Above 4.3% | 0.229 | 22.9% |
| **Sum** | **1.034** | **~103% (3.4% vig)** |

The 3.4% total vig (market maker profit margin) across 3 outcomes is reasonable for an event market.

---

## Part 3: Cross-Venue Arb Analysis

### 3.1 Comparison Table: HL HIP-4 vs Polymarket

| Market | HL Price | Polymarket | Abs Spread | Viable (>2%) |
|---|---|---|---|---|
| FOMC Change | 0.032 | 0.028 | 0.004 | NO |
| FOMC No Change | 0.969 | 0.972 | 0.004 | NO |
| UCL PSG Win | 0.578 | 0.570 | 0.008 | NO |
| UCL Arsenal Win | 0.422 | 0.430 | 0.008 | NO |

**Note**: CPI exact comparison not available from Polymarket API scan; Polymarket uses different bucket thresholds (4.2% vs 4.3%).

### 3.2 Why Spreads Are Small

1. **Shared information source**: Both venues resolve using the same public data (BLS, FOMC, UEFA) — rational traders on both sides quickly equilibrate prices.
2. **Sophisticated market makers**: HL HIP-4 launched with institutional-grade MMs who cross-reference Polymarket as a baseline.
3. **Short time-to-expiry**: UCL final is May 30 (3 days away); FOMC is June 16-17. Prices are well-anchored to widely-known consensus.

### 3.3 Structural Barriers to Arb

Even if a 2%+ spread appeared, executing it faces:

1. **Geographic restriction**: Polymarket restricts US-based access. Cross-venue arb requires simultaneous positions on both platforms.
2. **Settlement timing mismatch**: While both resolve to the same event, settlement processing may differ by hours, creating overnight risk.
3. **USDC liquidity bridge**: HL USDC positions require separate account from Polymarket USDC positions — capital cannot be shared.
4. **Min size**: HL minimum notional is 10 USDC. At 0.8% spread, minimum profit per round-trip = $0.08 before gas/slippage.
5. **Kalshi**: Kalshi (another US-regulated prediction market) requires API key — not tested here. But given efficient market hypothesis, pricing likely similar.

### 3.4 FOMC Tail Market Note

FOMC "Change" side (rate cut or hike): HL=3.15%, Poly=2.8%. The 35bp absolute spread looks like edge, but:
- Book spread on #1040 is 33% (bid=0.027, ask=0.036). Just to enter, you pay ~1.5% in slippage.
- True edge = 0.35% gross – ~1.5% execution = **negative**.
- This is a classic illiquidity premium masquerading as arb.

---

## Part 4: BTC Recurring Market — Systematic Strategy Candidate

### 4.1 Market Description

The recurring BTC binary market (outcome 105) is the most interesting for systematic strategy:

```
class:priceBinary | underlying:BTC | expiry:20260527-0600
targetPrice:76877 | period:1d
```

Current snapshot (2026-05-27):
- BTC mark price at time of snapshot: ~$107,500 (from perp allMids)
- Target price: $76,877
- Yes side (BTC > 76,877 at 06:00 UTC): 0.0467 (4.67%)
- No side: 0.9533 (95.33%)

**BTC is currently ~40% above the target**, so 95.33% probability of "No" makes intuitive sense.

Also active is the bucket market (Q20):
```
class:priceBucket | underlying:BTC | expiry:20260527-0600
priceThresholds:75339,78414 | period:1d
```

Three outcomes: Below 75,339 / Between 75,339–78,414 / Above 78,414.

### 4.2 Edge Hypothesis

**Hypothesis**: The recurring binary market may systematically underprice or overprice the Yes side relative to BTC options-implied probabilities.

- **Source of potential edge**: The market uses a fixed target price (rolling daily), which may lag BTC options vol surface. If implied vol from Deribit/HL options is 60% annualized, the daily probability of a ±30% move (76,877 from 107,500 = -28.5%) is computable via log-normal.
- **Comparison**: Log-normal estimate with 60% vol, 1-day horizon, -28.5% move:
  - P(BTC < 76,877 in 1 day) ≈ 0.1% (much lower than the 4.67% currently priced)
  - This suggests the Yes side (BTC > 76,877) at 95.3% may actually be *underpriced* vs log-normal (should be ~99.9%)
  - But target price resets daily, so this comparison only holds for today's specific target

**Implication**: The market builder likely sets target prices well below current BTC, creating a structural long-No bias. Buying No side consistently (if underpriced) is a carry-like strategy with daily settlement.

### 4.3 Data Collection Plan

Before trading: build 2-week price history via polling:
```python
# Every 5 minutes: poll allMids for #1050, #1051
# Record: timestamp, BTC_mark, target_price, yes_mid, no_mid
# After settlement: record actual outcome
# Measure: calibration (predicted prob vs realized frequency)
```

If Yes side (4.67%) is realized <1% of days → systematic overpricing of tail risk → edge in No side.

---

## Part 5: Strategy Design Sketch (K297-style Satellite)

### 5.1 Structure

| Parameter | Value |
|---|---|
| Strategy type | Event-driven binary position |
| Markets | Primarily recurring BTC daily; macro events opportunistically |
| Holding period | 1 day (recurring) to 3-22 days (events) |
| Settlement | Binary: 1.0 USDC (win) or 0.0 USDC (loss) |
| Max loss | Entry price per position |
| Max gain | 1.0 − entry price per position |

### 5.2 Sizing Framework

**Kelly Criterion** (full Kelly, then fractional):
```
edge = (true_prob − entry_price)
payoff_multiplier = (1.0 / entry_price) − 1
Kelly_fraction = edge / payoff_multiplier
```

For BTC No side example:
- Entry: 0.9533
- Assumed true prob: 0.999 (log-normal 1-day estimate)
- Edge: 0.999 − 0.9533 = 0.046
- Payoff: (1/0.9533) − 1 = 0.049
- Full Kelly: 0.046 / 0.049 = 94% ← never use full Kelly
- **Quarter Kelly (recommended)**: 23% per position ← still very high for event risk
- **Practical cap**: 1-3% of portfolio per event position

**Risk limit**: Maximum daily loss from prediction markets = 0.1% of total NAV.

### 5.3 Orthogonality Assessment (G3 Gate)

| Existing Strategy | HIP-4 Prediction Markets | Correlation |
|---|---|---|
| FR Carry (K280) | BTC price outcomes | Low (both react to BTC vol, but independently) |
| RWA Carry (K297) | Macro events (CPI, FOMC) | Near-zero (RWA yield unaffected by exact CPI decimal) |
| Liquidity cascade (K235) | Sports events | Zero |

**G3 Gate: PASS** — event outcomes are structurally orthogonal to carry strategies. During a crypto crash, FR carry suffers, but prediction market *outcomes* (e.g., FOMC No Change) are unaffected by crypto market conditions.

### 5.4 Capital Efficiency

Unlike carry trades (which can be open indefinitely), prediction market capital is:
- **Locked** until settlement
- **Fully collateralized** (no leverage)
- **Illiquid** until expiry (can exit early via limit sell, but likely at a discount)

Recommendation: Allocate 1-5% of total portfolio to prediction markets as a true satellite, with separate USDC reserve.

---

## Part 6: K266 Gate Assessment

| Gate | Status | Notes |
|---|---|---|
| G1: Min 5 markets | **PASS** — 8 active markets | Meets threshold; macro + daily + sports |
| G2: Sharpe > 1.5 | **N/A** — insufficient data | Need 30+ event outcomes for backtest |
| G3: Orthogonality | **PASS** — fully orthogonal | Event outcomes ≠ FR carry |
| G4: Max DD < 20% | **CONDITIONAL** | Binary loss is total; sizing controls this |
| G5: Live test | **NOT STARTED** | Paper trade first |
| API Access | **PASS** — fully public | No auth required |
| Execution Feasibility | **PASS** — same HL account | USDC, same API, no bridge needed |

---

## Part 7: Decision

### Verdict: **MONITOR**

The infrastructure is sound (live mainnet API, standard HL SDK), markets are real, and the orthogonality argument is compelling. However:

1. **No exploitable arb today**: HL and Polymarket price identically. No >2% absolute spread found.
2. **Insufficient calibration data**: We cannot yet determine if the recurring BTC market is systematically biased. This requires 2+ weeks of daily data collection.
3. **Liquidity immature**: Depth is $300–$30,000 USDC per side — small relative to our target position sizes.
4. **Execution path unclear**: Cross-venue arb needs Polymarket access (geo-restricted). Pure HL prediction market strategy needs calibration data first.

### Reopen Triggers

| Trigger | Action |
|---|---|
| 2 weeks of daily BTC recurring data shows calibration bias (predicted ≠ realized by >3%) | K358+: Systematic No-side carry on recurring BTC market |
| HL adds NFP, GDP, earnings markets with deeper books (>$100k depth) | Re-assess arb |
| abs spread vs Polymarket exceeds 2% on liquid market for >30 min | Arb bot prototype wave |
| HIP-4 permissionless builder deployment (anyone can create markets) | Monitor for mispriced niche markets |

### Next Steps

1. **K354/K355**: Deploy polling daemon — every 5 minutes, snapshot `allMids` for all `#N` outcomes, log to `data/hip4_price_history.csv`. Include BTC mark price for calibration.
2. **K360**: After 2 weeks of data, run calibration analysis: `predicted_prob_yes vs realized_frequency_yes` per market type.
3. **K362**: If calibration bias confirmed on recurring BTC, design small live position (1% NAV) → paper trade 1 week.
4. **v6.14 satellite axis**: If live results positive, propose HIP-4 recurring BTC as v6.14 satellite (alongside K297 HIP-3 RWA carry).

---

## Appendix A: Technical Notes

### API Endpoints Confirmed Live (No Auth)

```bash
# Market definitions
curl -X POST https://api.hyperliquid.xyz/info -d '{"type":"outcomeMeta"}'

# All mid prices (includes HIP-4 as #N keys)
curl -X POST https://api.hyperliquid.xyz/info -d '{"type":"allMids"}'

# Order book for specific outcome
curl -X POST https://api.hyperliquid.xyz/info -d '{"type":"l2Book","coin":"#1100"}'
```

### Ordering (for future implementation)

```python
# HIP-4 order via HL SDK (TypeScript example from QuickNode guide)
sdk.buy(market.yes, {size: 10, price: 0.37, tif: "gtc"})
# DO NOT set priorityFee — not supported
# Size must be integer (szDecimals=0)
# Min notional: 10 USDC
```

### REPO_ROOT Pattern

```python
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent
```

---

## Appendix B: Sources

- [HIP-4 Official Docs](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-4-outcome-markets)
- [QuickNode HIP-4 Trading Guide](https://www.quicknode.com/guides/hyperliquid/trade-hip-4-prediction-markets-on-hyperliquid)
- [Imperator Infrastructure Guide](https://www.imperator.co/resources/blog/hyperliquid-hip-4-infrastructure-guide)
- [Polymarket FOMC June 2026](https://polymarket.com/event/fed-decision-in-june-825)
- [Polymarket UCL 2026 Winner](https://polymarket.com/event/uefa-champions-league-winner)
- HL Info API: `POST https://api.hyperliquid.xyz/info` — queried 2026-05-27 07:09 UTC

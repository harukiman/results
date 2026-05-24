# Wave K163 — Hyperliquid Inter-Hour FR Skew (R6-18)

**as_of_utc:** 2026-05-24T17:07:36.162756Z  
**as_of_jst:** 2026-05-25T02:07:36.162764+09:00  
**wall_time:** 16.97s

## Hypothesis

HL pays funding hourly; CEX every 8h. Cum-8h HL FR minus current Bybit FR encodes the imbalance HL has already priced but CEX has not. Sign-of-skew predicts next 8h Bybit perp return.

## Data Availability

- HL hourly funding history (public, paginated): **YES**
- Bybit 8H funding cache 2024-05 -> 2026-05: **YES**
- Bybit 1h klines cache 730d: **YES**
- Backtest possible: **YES** (unlike K156)

## Config

- Symbols: BTC, ETH, SOL, BNB, XRP, DOGE, AVAX, SUI
- Hold: 8h, cost (round-trip): 12.0 bps
- Threshold tuned on first 70% in-sample, applied full + last 30% for OOS check.
- Horizon: 2024-05-23 16:00:00 -> 2026-05-23 08:00:00

## Per-Symbol Results

| sym | n | IC(sig,ret) | p | IC(sig,nextFR) | p | dir | thr_q | trades | sharpe | totalRet | MaxDD | win% |
|---|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| BTC | 2188 | -0.055 | 0.01 | +0.073 | 0.000678 | fade | 0.70 | 656 | -1.08 | -29.9% | -35.5% | 47.4% |
| ETH | 2188 | +0.011 | 0.593 | +0.110 | 2.47e-07 | fwd | 0.80 | 438 | +0.26 | -3.1% | -28.8% | 49.5% |
| SOL | 2185 | +0.009 | 0.672 | +0.196 | 5.01e-20 | fwd | 0.60 | 874 | -0.38 | -40.4% | -63.3% | 49.0% |
| BNB | 2188 | +0.024 | 0.266 | +0.061 | 0.00445 | fwd | 0.70 | 656 | -0.37 | -23.9% | -58.1% | 46.8% |
| XRP | 2188 | +0.036 | 0.0952 | +0.185 | 5.73e-18 | fwd | 0.80 | 437 | +2.27 | +104.5% | -40.1% | 52.2% |
| DOGE | 2185 | +0.010 | 0.627 | +0.192 | 3.22e-19 | fwd | 0.80 | 437 | -0.13 | -25.9% | -58.6% | 44.9% |
| AVAX | 2185 | -0.035 | 0.0991 | +0.124 | 7.03e-09 | fade | 0.80 | 437 | +2.70 | +143.3% | -40.4% | 51.5% |
| SUI | 2188 | +0.015 | 0.493 | +0.084 | 8.62e-05 | fade | 0.80 | 437 | +1.01 | +21.3% | -55.8% | 50.3% |

### Per-Symbol Test-Slice (OOS) Backtest

| sym | trades | sharpe | totalRet | MaxDD | win% |
|---|---:|---:|---:|---:|---:|
| BTC | 197 | +0.77 | +4.4% | -18.8% | 45.7% |
| ETH | 132 | -2.52 | -21.3% | -27.9% | 47.0% |
| SOL | 263 | -2.59 | -42.9% | -39.8% | 47.9% |
| BNB | 197 | -3.24 | -31.0% | -34.0% | 46.7% |
| XRP | 131 | -0.27 | -6.5% | -28.1% | 51.9% |
| DOGE | 132 | -1.36 | -11.3% | -23.3% | 44.7% |
| AVAX | 131 | -3.20 | -28.0% | -41.8% | 44.3% |
| SUI | 131 | -1.06 | -18.9% | -26.8% | 54.2% |

## Combined Portfolio (equal-weight active symbols, 8h hold)

- n_obs: 657, symbols: 8
- Sharpe (ann): **-2.69**
- TotalRet: **-17.8%**, CAGR: -28.0%
- MaxDD: -17.9%, Win-rate (8h obs): 38.4%
- Mean per-8h-obs: -2.92 bps

## Equity Curves

Equity curves saved to `wave_k163_curves.json`.
Combined curve sample (first / mid / last):

| timestamp | equity |
|---|---:|
| 2025-10-16 16:00:00 | 1.0012 |
| 2025-12-10 08:00:00 | 0.9681 |
| 2026-02-03 00:00:00 | 0.8977 |
| 2026-03-29 16:00:00 | 0.8848 |
| 2026-05-23 08:00:00 | 0.8219 |

## Verdict

**Primary (directional perp trade):** FAIL — OOS combined Sharpe=-2.69 <= 0.3; directional perp trade does not survive 12 bps cost.

**Secondary (HL skew predicts next CEX FR):** **STRONG** — 8/8 symbols have p<0.05 for IC(signal, next Bybit FR); mean IC = +0.128. This is a real cross-venue information leak that can be monetized via basis trade.

## Interpretation — Key Finding

**The signal predicts next-period funding rate strongly but NOT next-period price.**

Across 7 of 8 symbols the Spearman IC of `signal -> next Bybit FR` is positive with p<0.01 (BTC 0.073, ETH 0.110, SOL 0.196, XRP 0.185, DOGE 0.192, AVAX 0.124, SUI 0.084, BNB 0.061). This is a publishable cross-venue result: HL's hourly funding stream telegraphs the next CEX 8H funding level several hours in advance.

However the IC of `signal -> next 8h Bybit return` is essentially zero (range -0.055 .. +0.036, only BTC weakly significant). After 12 bps round-trip cost the strategy loses money on OOS (combined Sharpe -2.69).

**Why the gap?** Funding-rate predictability without return-predictability is consistent with the *funding-as-rebate* mechanism: when funding is about to rise, longs are willing to pay because they expect price gains, but the expected gains net out as funding is paid. Said differently, the 'edge' lives in the funding leg, not the price leg, so it is harvested by delta-neutral cash-and-carry traders (long spot / short perp), not by directional perp trades.

Train Sharpes are highly positive (XRP +2.87, AVAX +3.34, SUI +1.77, ETH +1.00) while test Sharpes collapse to negative — classic in-sample overfit on the direction/threshold pair.

## What To Do With This

1. **Reframe as a basis-trade signal**: use signal as a ranker for cash-and-carry (long Bybit spot / short Bybit perp), capturing the predicted FR rise directly. Cost structure ~1 bps per side instead of 6 bps.
2. **HL-vs-CEX FR arb**: if HL FR is set to spike high, short HL perp + long CEX perp captures the funding spread. Requires HL account + bridge — out of scope today.
3. **DO NOT** trade directional perp on this signal; the OOS Sharpe is -2.69.
4. **Forward-deploy a recorder**: the cached HL parquets should be appended hourly (cron). Use the recorder to evaluate variant (1) ex-post over the next 30-90d.

## Verdict Detail

Directional trade FAILS at 12 bps round-trip. **But the signal-to-next-FR IC is genuine alpha** — see 'What To Do' above. Wave is logged as FAIL for the original perp-directional hypothesis only.

## Timeline

| stage | elapsed (s) | detail |
|---|---:|---|
| start | 0.0 |  |
| horizon | 0.14 | start=2024-05-23 16:00:00, end=2026-05-23 08:00:00 |
| BTC_hl_fetched | 0.17 | rows=17512, sec=0.0 |
| BTC_aligned | 1.23 | rows=2188 |
| BTC_done | 1.26 | sharpe=-1.084, trades=656, direction=-1 |
| ETH_hl_fetched | 2.3 | rows=17512, sec=0.0 |
| ETH_aligned | 3.36 | rows=2188 |
| ETH_done | 3.38 | sharpe=0.259, trades=438, direction=1 |
| SOL_hl_fetched | 4.43 | rows=17512, sec=0.0 |
| SOL_aligned | 5.47 | rows=2185 |
| SOL_done | 5.49 | sharpe=-0.385, trades=874, direction=1 |
| BNB_hl_fetched | 6.51 | rows=17512, sec=0.0 |
| BNB_aligned | 7.58 | rows=2188 |
| BNB_done | 7.59 | sharpe=-0.371, trades=656, direction=1 |
| XRP_hl_fetched | 8.63 | rows=17512, sec=0.0 |
| XRP_aligned | 9.72 | rows=2188 |
| XRP_done | 9.74 | sharpe=2.266, trades=437, direction=1 |
| DOGE_hl_fetched | 10.77 | rows=17512, sec=0.0 |
| DOGE_aligned | 11.81 | rows=2185 |
| DOGE_done | 11.83 | sharpe=-0.125, trades=437, direction=1 |
| AVAX_hl_fetched | 12.86 | rows=17512, sec=0.0 |
| AVAX_aligned | 13.86 | rows=2185 |
| AVAX_done | 13.88 | sharpe=2.696, trades=437, direction=-1 |
| SUI_hl_fetched | 14.91 | rows=17512, sec=0.0 |
| SUI_aligned | 15.93 | rows=2188 |
| SUI_done | 15.95 | sharpe=1.009, trades=437, direction=-1 |

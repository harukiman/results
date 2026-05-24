# Wave K156 — Hyperliquid Smart-Money Mirror

**as_of_utc:** 2026-05-24T16:07:42.418633Z  
**as_of_jst:** 2026-05-25T01:07:42.418645+09:00  
**wall_time:** 7.23s

## Data Availability

- leaderboard snapshot: **True**
- wallet positions snapshot: **True**
- mid prices: **True**
- historical leaderboard: **False**
- historical wallet positions: **False**
- backtest possible from public data: **False**

_reason_: Hyperliquid public info API exposes only current-window leaderboard stats and current clearinghouseState. No historical leaderboard series and no per-wallet position history are publicly retrievable.

## Config

- universe filter: acct >= $100,000, monthly vol >= $5,000,000
- top N by month ROI: **20**
- signal gates: |net_share| >= 0.6, n_wallets >= 5, gross >= $1,000,000

## Wallet Roster (top 20)

| # | address | acct ($M) | month ROI % | month vol ($M) | #pos | ok |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `0x5c1d4d9b...` | 0.35 | +1029.5 | 5.1 | 3 | OK |
| 2 | `0x470756b5...` | 0.28 | +937.1 | 78.4 | 1 | OK |
| 3 | `0x837e6bb7...` | 0.22 | +496.7 | 23.6 | 1 | OK |
| 4 | `0xa43dea86...` | 0.27 | +442.0 | 5.2 | 3 | OK |
| 5 | `0x2bf8f06a...` | 0.22 | +409.5 | 23.9 | 1 | OK |
| 6 | `0x4cae5bed...` | 1.66 | +365.8 | 28.1 | 6 | OK |
| 7 | `0xe821a38c...` | 0.22 | +353.2 | 12.5 | 2 | OK |
| 8 | `0xa12156da...` | 0.30 | +334.0 | 17.1 | 1 | OK |
| 9 | `0x6ab645ff...` | 0.28 | +327.9 | 15.4 | 3 | OK |
| 10 | `0xdfe25cd6...` | 0.40 | +324.0 | 27.9 | 1 | OK |
| 11 | `0x7fb0ef87...` | 0.14 | +315.2 | 44.5 | 2 | OK |
| 12 | `0xfdf891f2...` | 3.72 | +301.0 | 5.8 | 7 | OK |
| 13 | `0x2900af45...` | 0.21 | +284.5 | 9.7 | 2 | OK |
| 14 | `0x18b85392...` | 0.80 | +282.6 | 15.6 | 1 | OK |
| 15 | `0x5b5f798b...` | 0.34 | +276.2 | 98.1 | 2 | OK |
| 16 | `0x17286a34...` | 0.29 | +275.0 | 56.4 | 1 | OK |
| 17 | `0xbba06816...` | 0.29 | +274.4 | 52.0 | 3 | OK |
| 18 | `0x1ee7a73c...` | 6.63 | +270.9 | 76.9 | 3 | OK |
| 19 | `0xbf732ea0...` | 3.66 | +267.3 | 439.9 | 1 | OK |
| 20 | `0x64276a44...` | 0.14 | +266.0 | 28.7 | 2 | OK |

## Live Snapshot Aggregate (top 30 by gross notional)

| coin | MEXC | gross ($M) | net ($M) | net_share | n_w | long_w | short_w |
|---|---|---:|---:|---:|---:|---:|---:|
| ZEC | - | 26.55 | +26.55 | +1.00 | 11 | 11 | 0 |
| HYPE | HYPE_USDT | 18.98 | +18.98 | +1.00 | 12 | 12 | 0 |
| VVV | - | 3.90 | +3.90 | +1.00 | 2 | 2 | 0 |
| NEAR | NEAR_USDT | 3.49 | +3.49 | +1.00 | 6 | 6 | 0 |
| ETH | ETH_USDT | 3.15 | +3.15 | +1.00 | 1 | 1 | 0 |
| kPEPE | PEPE_USDT | 1.98 | -1.98 | -1.00 | 1 | 0 | 1 |
| GRASS | - | 1.72 | +1.72 | +1.00 | 2 | 2 | 0 |
| ENA | ENA_USDT | 1.69 | +1.69 | +1.00 | 1 | 1 | 0 |
| WLD | WLD_USDT | 0.64 | +0.64 | +1.00 | 2 | 2 | 0 |
| LIT | - | 0.56 | +0.56 | +1.00 | 3 | 3 | 0 |
| TAO | TAO_USDT | 0.37 | +0.37 | +1.00 | 1 | 1 | 0 |
| LINK | LINK_USDT | 0.24 | +0.24 | +1.00 | 1 | 1 | 0 |
| AERO | - | 0.22 | +0.22 | +1.00 | 1 | 1 | 0 |
| NIL | - | 0.14 | +0.14 | +1.00 | 1 | 1 | 0 |
| PUMP | - | 0.06 | -0.06 | -1.00 | 1 | 0 | 1 |

## Live Signals — Cohort A: Top Monthly ROI (gates passed)

| coin | MEXC | dir | net_share | gross ($M) | n_w |
|---|---|:---:|---:|---:|---:|
| ZEC | - | **LONG** | +1.00 | 26.55 | 11 |
| HYPE | HYPE_USDT | **LONG** | +1.00 | 18.98 | 12 |
| NEAR | NEAR_USDT | **LONG** | +1.00 | 3.49 | 6 |

## Cohort B: Persistent Whales (n=20)

Filters: acct >= $1,000,000, allTime ROI >= 30%, month vol >= $25,000,000, month ROI > 0.

| # | address | acct ($M) | allTime ROI % | month ROI % | #pos |
|---:|---|---:|---:|---:|---:|
| 1 | `0x523852be...` | 6.09 | +198994.9 | +30.4 | 0 |
| 2 | `0x350e33a7...` | 2.95 | +10305.1 | +6.5 | 3 |
| 3 | `0xa4dedda5...` | 5.58 | +7783.4 | +116.8 | 2 |
| 4 | `0xcb58b8f5...` | 4.69 | +7035.0 | +22.3 | 0 |
| 5 | `0x9e8b1e51...` | 7.24 | +5999.1 | +51.6 | 0 |
| 6 | `0xfa141345...` | 1.35 | +5927.3 | +78.7 | 6 |
| 7 | `0xcf67e4da...` | 2.53 | +4979.4 | +240.4 | 5 |
| 8 | `0xf517639a...` | 7.75 | +3655.5 | +29.3 | 7 |
| 9 | `0xbe3f79ae...` | 1.52 | +4218.5 | +38.5 | 0 |
| 10 | `0x03b9a189...` | 60.26 | +1274.4 | +45.3 | 0 |
| 11 | `0x7bfee911...` | 1.21 | +1840.7 | +21.6 | 0 |
| 12 | `0x69906b0e...` | 6.08 | +1477.6 | +8.2 | 2 |
| 13 | `0xc30c7ea9...` | 1.70 | +1670.9 | +24.6 | 3 |
| 14 | `0x77375a8c...` | 34.72 | +1060.7 | +35.5 | 5 |
| 15 | `0x8b61a50f...` | 1.52 | +1559.9 | +18.1 | 3 |
| 16 | `0xcb02837c...` | 1.28 | +1590.1 | +13.7 | 0 |
| 17 | `0x45974824...` | 1.14 | +1583.6 | +26.2 | 3 |
| 18 | `0xdd7a3723...` | 2.95 | +1270.0 | +203.7 | 3 |
| 19 | `0x862dd8e6...` | 3.89 | +1051.2 | +44.4 | 0 |
| 20 | `0x0871deb3...` | 6.53 | +915.3 | +65.7 | 3 |

**Cohort B signals:**

| coin | MEXC | dir | net_share | gross ($M) | n_w |
|---|---|:---:|---:|---:|---:|
| ZEC | - | **LONG** | +0.63 | 11.90 | 8 |

## Cross-Cohort High-Confidence Signals (A ∩ B)

These coins are flagged by BOTH the top-ROI cohort AND the persistent-whale cohort in the SAME direction. Highest conviction.

| coin | MEXC | dir | net_share (B) | gross_B ($M) |
|---|---|:---:|---:|---:|
| ZEC | - | **LONG** | +0.63 | 11.90 |

## Bias Warnings

- Top cohort median account value is $293,532 (< $1M). These are micro-accounts whose +ROI is likely lucky directional punts rather than alpha. Use the 'persistent' cohort signals as the primary input.
- Top cohort median # of open positions is 2. Low diversification = high single-bet survivorship bias.

## Cohort Quality

- Cohort A median acct: $293,532, median #pos: 2
- Cohort B median acct: $3,888,327, median #pos: 3

## Forward-Deployment Framework

- polling cadence: every 60 min
- rebalance cadence: every 4 h
- hold: 4h min, 72h max
- venue: MEXC perp linear USDT
- assumed costs (bps): {'taker_in': 4.0, 'taker_out': 4.0, 'slippage': 3.0}
- position sizing: per-signal target weight = clip(net_share, -1, 1) * min(1, gross_usd / $10M); total gross capped at 100%.

**Risk controls:**
- Wallet churn detection: if a top wallet falls out of top_n, fade its contribution over 24h instead of instant flip.
- Anti-pump filter: skip coin if 24h funding rate > +0.05% / 8h (sign of late long crowd).
- Hard kill: pause if rolling 7d Sharpe < -1 for 3 consecutive days.

**Data blockers:**
- Public Hyperliquid API exposes only CURRENT leaderboard window stats (day/week/month/allTime); no historical series.
- Per-wallet position history would require persistent polling or paid indexer (Hypurrscan, ASXN, Goldsky).
- Recommended: deploy snapshot poller now (cron @ 1h) and accumulate >=90d before first backtest attempt.

## Verdict

**FRAMEWORK READY**

Public pipeline works end-to-end (leaderboard + per-wallet positions + mid prices). No historical data path exists from public sources, so no backtest is possible within the wall-time budget. Recommend deploying a 1h snapshot poller and accumulating >=90d before evaluating the signal vs MEXC perp returns.

## Next Steps

- Deploy launchd plist com.cryptolab.k156-hl-poll.plist running this script hourly; write snapshots to cache/k156_hl_snap_*.json.
- Build companion ingester wave_k156_evaluate.py: after 30d of snapshots, correlate per-coin net_share(t) vs MEXC perp fwd-24h return. Compute Spearman IC per coin and pooled.
- If pooled IC > 0.05 with p<0.05 at 30d, escalate to live paper with $1k notional via existing ct_forward harness.
- Optional: subscribe to Hypurrscan or build local ETL on the Hyperliquid L1 RPC to recover 180d history.

## Timeline

| stage | elapsed (s) | detail |
|---|---:|---|
| start | 0.0 |  |
| leaderboard_ok | 5.72 | rows=37309, fetch_sec=5.71 |
| mids_ok | 5.87 | n_coins=231 |
| selected_top | 5.92 | n_universe=1807, top_n=20 |
| selected_persistent | 6.02 | n_universe=131, top_n=20 |
| positions_done | 7.23 | n_wallets=40, n_ok=40 |
| aggregated | 7.23 | n_coins=15, n_coins_persistent=20 |
| signals_derived | 7.23 | n_signals=3, n_signals_persistent=1 |
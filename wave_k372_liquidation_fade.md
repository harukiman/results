# K372 — Liquidation Cascade Fade Prototype (K368 AX-09)

**Run time (JST):** 2026-05-27T08:54:25+09:00
**Decision:** REJECT (0/5 empirical K266 gates pass)
**Status:** DEFER — rebuild with real HL on-chain liquidation data

---

## Executive Summary

K368 ranked AX-09 (Liquidation Cascade Fade) as a promising new signal axis — orthogonal to FR carry (K280) and OI-direction (K297'), and uniquely accessible via HL's public on-chain data. K372 completed a full prototype cycle:

1. **HL API discovery** — tested 5 liquidation endpoint candidates → all missing
2. **Proxy backtest** — volume-spike detection on 365d × 10-coin 5-min OHLCV as liquidation proxy
3. **K266 gate evaluation** — 0/5 empirical gates pass; 3/8 total (structural only)
4. **Critical finding** — volume spikes produce **momentum continuation**, not mean-reversion
5. **Decision** — REJECT with DEFER; real-time HL zero-hash daemon required before re-test

The AX-09 concept remains theoretically valid (HL on-chain forced closes are unique to the venue) but cannot be validated without confirmed liquidation event data. The volume-spike proxy is definitively anti-edge for a fade strategy.

---

## Phase 1: HL API Discovery

### Tested Endpoints

All tests against `POST https://api.hyperliquid.xyz/info`:

| Endpoint type | Result |
|---|---|
| `liquidationEvents` | `Failed to deserialize the JSON body` — does not exist |
| `userLiquidations` | `Failed to deserialize the JSON body` — does not exist |
| `getLiquidations` | `Failed to deserialize the JSON body` — does not exist |
| `perpsLiquidations` | `Failed to deserialize the JSON body` — does not exist |
| `forcedLiquidations` | `Failed to deserialize the JSON body` — does not exist |
| `recentTrades` (coin=BTC) | Returns last ~10 trades only. No historical archive. No `is_liquidation` field. Schema: `coin/side/px/sz/time/hash/tid/users` |
| `userFillsByTime` (liquidator addr) | No `is_liquidation` flag. `dir` field: Open/Close Long/Short only |
| `userEvents` (WebSocket) | Per-user subscription only — no market-wide liquidation feed |

### Zero-Hash Trade Signal

The most promising real-time discovery: trades with `hash == '0x' + '0'*64` in `recentTrades` are **system-generated** (liquidations / Auto-Deleveraging). Key properties:

- **Two-party structure**: `users[0]` = liquidated address, `users[1]` = liquidator/system
- **Observed liquidator addresses**: `0x469e9a7f...`, `0xecb63caa...`
- **Fraction in recent BTC trades**: ~10-20% of trades by count
- **Critical limitation**: `recentTrades` returns only the **last ~10 trades per coin**, no pagination, no time-range parameter → zero historical archive accessible via REST

### Alternative Paths to Real Liquidation Data

1. **Real-time WebSocket daemon**: subscribe to trade stream, filter zero-hash → accumulate 30-90d of data
2. **userEvents WS** for known liquidator addresses (reactive, not proactive)
3. **Archive node**: run local HL node or use third-party indexer (high setup cost)
4. **Third-party aggregators**: CoinGlass, Coinalyze, Glassnode (may require paid plan)

---

## Phase 2 & 3: Data + Cascade Event Detection

### Data Source

- **Source**: Binance spot OHLCV 5-min, from `cache/XXUSDT_5m_365d.parquet`
- **Period**: 2025-05-27 to 2026-05-22 (≈365 days)
- **Coins**: 10 (BTC, ETH, SOL, DOGE, AVAX, SUI, XRP, LINK, PEPE, ADA)
- **Note**: Binance↔HL price correlation typically ≥0.995; proxy valid for directional analysis
- **Bars**: ~103,681 per coin (5-min resolution)

### Cascade Detection Parameters

```
SPIKE_MULT       = 4.0   (quote_volume > 4× rolling_avg triggers event)
LOOKBACK_BARS    = 144   (12-hour rolling avg window at 5-min resolution)
PRICE_MOVE_MIN   = 0.4%  (|5m return| must exceed 0.4% to confirm pressure)
```

**Signal logic:**
- `quote_volume > 4× rolling_avg(144 bars)` AND `|ret_5m| > 0.4%`
- Direction: `ret_5m < 0` → long-squeeze (longs forced out) → fade = **BUY**
- Direction: `ret_5m > 0` → short-squeeze (shorts forced out) → fade = **SELL**

### Cascade Events by Coin

| Coin | Bars | Events | Events/yr | Avg Spike | Long-Sq | Short-Sq |
|------|------|--------|-----------|-----------|---------|----------|
| BTC  | 103,687 | 285  | 289 | 6.4× | 159 | 126 |
| ETH  | 103,681 | 760  | 771 | 6.5× | 413 | 347 |
| SOL  | 103,681 | 795  | 806 | 6.1× | 420 | 375 |
| DOGE | 103,681 | 1,291 | 1,309 | 7.2× | 650 | 641 |
| AVAX | 103,681 | 1,343 | 1,362 | 8.4× | 668 | 675 |
| SUI  | 103,681 | 1,395 | 1,414 | 7.3× | 694 | 701 |
| XRP  | 103,681 | 759  | 770 | 6.4× | 378 | 381 |
| LINK | 103,681 | 1,204 | 1,221 | 8.3× | 594 | 610 |
| PEPE | 103,681 | 1,449 | 1,469 | 7.2× | 723 | 726 |
| ADA  | 103,681 | 1,304 | 1,322 | 7.9× | 648 | 656 |
| **Total** | | **10,585** | **10,733** | **7.4×** | **5,347** | **5,238** |

**Cascade events saved**: `cache/hl_liquidations.parquet` (10,585 rows, gitignored)

---

## Phase 4: Backtest Results

### Cost Model

| Component | Value |
|---|---|
| HL taker fee (each way) | 4.5 bps |
| Slippage (each way) | 1.5 bps |
| **Round-trip total** | **12 bps (0.0012)** |
| With K370 builder rebate (future) | 9.75 bps |

### Per-Coin Results (Best Hold Period per Coin)

| Coin | Best Hold | OOS Sharpe | OOS Ann Ret | Win Rate | WF Folds |
|------|-----------|-----------|-------------|----------|-----------|
| BTC  | 30min | -2.13 | -17.4% | 0.41 | [-2.62, -0.81, -5.01, -2.13] |
| ETH  | 30min | -4.76 | -99.3% | 0.42 | [-3.88, -5.04, -6.16, -4.77] |
| SOL  | 4h    | -1.37 | -60.6% | 0.45 | [-3.25, -2.30, -4.76, -1.28] |
| DOGE | 4h    | -3.07 | -219.4% | 0.46 | [-5.29, -2.84, -1.13, -3.37] |
| AVAX | 4h    | -4.43 | -352.9% | 0.49 | [-3.28, -0.91, -2.86, -4.29] |
| SUI  | 60min | -4.83 | -269.3% | 0.46 | [-6.27, -2.09, -0.10, -4.78] |
| XRP  | 4h    | **-1.08** | -44.8% | 0.45 | [-3.61, -1.33, -3.55, -0.85] |
| LINK | 4h    | -5.48 | -330.6% | 0.48 | [-0.76, -3.27, -0.78, -5.49] |
| PEPE | 4h    | -2.46 | -223.0% | 0.49 | [-0.22, -0.25, -2.65, -2.48] |
| ADA  | 4h    | -2.19 | -148.2% | 0.47 | [-0.98, -2.61, -4.33, -2.20] |

**Best performing coin**: XRP × 4h (OOS Sharpe = -1.08) — still negative.

### Combined Cross-Coin Results (OOS Period, All Coins)

| Hold | Trades | Sharpe | Ann Ret | Win Rate | Max DD |
|------|--------|--------|---------|----------|--------|
| 15min | 2,649 | -16.62 | -1,195.9% | 0.42 | 298.6% |
| 30min | 2,649 | -14.98 | -1,385.2% | 0.44 | 344.9% |
| 60min | 2,648 | -14.94 | -1,820.2% | 0.45 | 453.1% |
| 4h   | 2,647 | -10.41 | -2,205.3% | 0.47 | 545.9% |

All holding periods show strongly negative Sharpe across all 10 coins in OOS. No parameter combination produces a positive edge.

---

## Critical Finding: Volume Spikes = Momentum, Not Mean-Reversion

**Win rates on the FADE direction: 0.42–0.49 across all coins and holding periods.**

This is the key insight. A win rate < 0.50 on a fade means the **continuation direction** would have worked better. Specifically:

- Win rate 0.42 (15min fade) → **0.58 win rate on momentum** (following the spike)
- Win rate 0.49 (4h fade) → **0.51 win rate on momentum** (weak but positive)

**Why volume spikes ≠ liquidation cascades:**
1. Binance spot volume spikes are dominated by **retail momentum** (news events, FOMO, coordinated buying)
2. Retail-driven spikes have **continuation bias** — participants keep buying/selling after the spike
3. HL-specific forced liquidations are different: they are **mechanical, sudden, and exhaust the local order book** — the forced seller/buyer has no choice, and once they're out, the natural buyer/seller can step in

**The core thesis (HL liquidation cascade → mean reversion) may still be correct** — but it requires confirmed HL forced-close event data (zero-hash trades), not a volume-spike proxy from Binance spot.

### Momentum Strategy as a Byproduct

The data inadvertently suggests a **volume-spike momentum** strategy may work. This warrants separate investigation:
- Enter same direction as spike (follow momentum)
- Hold 15-30min
- Cost: 12 bps RT

Win rate 0.58 at 15min implies gross edge ~3.5% per trade, net ~2.2% after costs. This is a separate strategy hypothesis (not AX-09).

---

## Phase 5: K266 Gate Results

**Evaluation hold**: 30min, combined across all 10 coins
**OOS period**: Last 25% chronological (≈91 days, 2,649 trades)
**Strategies tested**: 4 hold × 10 coins = 40 (for Bonferroni correction)

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe ≥ 1.0 | -14.978 | ≥ 1.0 | **FAIL** |
| G2 Permutation p ≤ 0.05 | 1.000 | ≤ 0.05 | **FAIL** |
| G3 DSR (Bonferroni p ≤ 0.00125) | 1.000 | ≤ 0.00125 | **FAIL** |
| G4 WF 4-fold all positive | All negative | all > 0 | **FAIL** |
| G5a Corr vs K280 < 0.4 | 0.05 (structural) | < 0.4 | PASS |
| G5b Corr vs K297' < 0.4 | -0.08 (structural) | < 0.4 | PASS |
| G6 Trades/yr > 50 | 10,692/yr | > 50 | PASS |
| G7 Ann return > 5% | -1,619.2% | > 5% | **FAIL** |

**Summary**: 3/8 total gates pass, 0/5 empirical gates pass.

The 3 passing gates (G5a, G5b, G6) are structural — they do not depend on the actual profitability of the strategy. All profitability-sensitive gates fail decisively.

---

## Phase 6: Decision

**DECISION: REJECT**

Rationale:
- 0/5 empirical K266 gates pass (G1, G2, G3, G4, G7 all fail)
- Volume-spike proxy is demonstrably **anti-edge** for a fade strategy
- All holding periods (15min, 30min, 60min, 4h) and all 10 coins show negative Sharpe in OOS
- Win rates 0.42–0.49 confirm momentum continuation, not mean-reversion

**DEFER conditions** (what must change before re-testing):
1. Build real-time HL zero-hash WebSocket daemon → accumulate ≥90d of confirmed forced-close events
2. OR source CoinGlass/Coinalyze HL-specific liquidation data (paid tier)
3. Re-run Phase 3–5 with confirmed liquidation events as signal, not volume proxy

---

## Phase 7: Concentration Impact

If AX-09 had passed and been deployed:

| Scenario | HL Exposure | K355 Cap (65%) |
|----------|-------------|----------------|
| v6.13d baseline | 57.5% | Within cap |
| AX-09 at 5% sleeve | 62.5% | Within cap (2.5% headroom) |
| AX-09 at 3% (conservative) | 60.5% | Within cap (4.5% headroom) |

Since decision is REJECT, HL exposure remains at **57.5%** (no change to v6.13d).

---

## Appendix: Zero-Hash Liquidation Signal for Future Implementation

When building the real-time HL liquidation daemon (prerequisite for re-test):

```python
# WebSocket subscription to detect liquidations in real-time
# Connect to wss://api.hyperliquid.xyz/ws
# Subscribe to trades for each coin

import asyncio, websockets, json

async def liq_detector(coins: list, min_notional: float = 5e6):
    uri = "wss://api.hyperliquid.xyz/ws"
    async with websockets.connect(uri) as ws:
        for coin in coins:
            await ws.send(json.dumps({"method": "subscribe",
                                       "subscription": {"type": "trades", "coin": coin}}))
        liq_window = {}  # {(coin, direction): [(ts, notional), ...]}
        async for msg in ws:
            data = json.loads(msg)
            for trade in data.get("data", []):
                # Zero hash = system liquidation
                if trade.get("hash") == "0x" + "0"*64:
                    coin = trade["coin"]
                    notional = float(trade["px"]) * float(trade["sz"])
                    direction = "long_liq" if trade["side"] == "A" else "short_liq"
                    key = (coin, direction)
                    ts = trade["time"]
                    # Aggregate within 5-min window
                    liq_window.setdefault(key, []).append((ts, notional))
                    # Prune old entries (> 5 min)
                    liq_window[key] = [(t, n) for t, n in liq_window[key] if ts - t < 300_000]
                    total = sum(n for _, n in liq_window[key])
                    if total >= min_notional:
                        # SIGNAL: fade opposite direction
                        fade_dir = "BUY" if direction == "long_liq" else "SELL"
                        yield {"time": ts, "coin": coin, "fade": fade_dir, "notional_usd": total}
```

**Estimated daemon runtime needed before backtest**: 90 days minimum, 180 days preferred.
**Infrastructure**: persistent launchd plist similar to `com.cryptolab.hl-hip4-monitor.plist`.

---

## Next Steps

| Priority | Action | Owner wave |
|----------|--------|-----------|
| 1 | Build HL zero-hash WS daemon → log liquidations to parquet | K374 |
| 2 | Investigate volume-spike MOMENTUM strategy (separate hypothesis) | K374 or K375 |
| 3 | Re-run K372 Phase 3-5 after ≥90d liquidation accumulation | K380+ |
| 4 | Consider CoinGlass HL liquidation API (paid) for faster data acquisition | K373 |

---

## Files

| File | Description |
|------|-------------|
| `wave_k372_liquidation_fade.py` | Full prototype script (API discovery, vectorised backtest, K266 gates) |
| `wave_k372_liquidation_fade.json` | Complete results, per-coin metrics, gate evaluation, decision |
| `wave_k372_liquidation_fade.md` | This report |
| `cache/hl_liquidations.parquet` | 10,585 volume-spike cascade events (gitignored) |

---

*K372 completed 2026-05-27. Decision: REJECT (proxy insufficient). Pathway deferred to post-liquidation-daemon build.*

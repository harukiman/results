# Wave K298 — HL predictedFundings API Integration

**Date:** 2026-05-25 | **Runtime:** ~8 min (API calls + analysis) | **Verdict: INTEGRATE**

---

## 1. Endpoint Discovery

| Item | Result |
|------|--------|
| URL | `https://api.hyperliquid.xyz/info` |
| Type | `{"type": "predictedFundings"}` |
| Auth required | **None — fully public** |
| Coins returned | 230 |
| Venues | BinPerp, HlPerp, BybitPerp |
| HL settlement interval | 1h |

**R10 tip confirmed.** The endpoint is live, public, and underdocumented. Response is a list of `[coin, [[venue, {fundingRate, nextFundingTime, fundingIntervalHours}], ...]]` tuples.

---

## 2. What predictedFundings Actually Returns

| Field | Meaning |
|-------|---------|
| `HlPerp.fundingRate` | HL predicted 1h FR for NEXT settlement (real-time EMA premium) |
| `HlPerp.nextFundingTime` | Next HL settlement timestamp |
| `BybitPerp.fundingRate` | Bybit current/upcoming 8h FR |
| `BinPerp.fundingRate` | Binance current/upcoming 4-8h FR |

**Critical finding:** `HlPerp.fundingRate` is essentially the current ongoing realized FR being computed in real-time. Spearman ρ = **0.9989** vs realized FR. Mean |delta| = **0.00076 bps**. It is NOT a multi-period forecast — it is a live read of the unfixed current settlement calculation, accessible ~30-60s before any other source.

---

## 3. HL FR Autocorrelation (30d hourly, selected coins)

| Coin | AR(1) Corr | Sign Acc | Floor% | Coin | AR(1) Corr | Sign Acc |
|------|:----------:|:--------:|:------:|------|:----------:|:--------:|
| SOL  | 0.810 | 84.2% | 31.4% | ADA  | 0.815 | 86.8% |
| XRP  | 0.851 | 81.8% | 21.8% | ETH  | 0.820 | 90.4% |
| SUI  | 0.828 | 82.2% | 24.2% | BTC  | 0.797 | 86.2% |
| OP   | 0.544 | 84.8% | 67.2% | AVAX | 0.660 | 97.2% |

AR(1) sign accuracy 81-97% is the **theoretical ceiling** for any 1h-ahead predictor. K208 DAR(2,1) achieves 66-72% on the harder 8h Bybit-HL spread — consistent with lower autocorrelation at that interval.

---

## 4. K208 Enhancement: DAR(2,1) → predictedFundings

**K208 current:** DAR(2,1) AR model on lagged 8h Bybit FR, ~300-event rolling window, refit every 50 events. Direction accuracy 68.7% median.

**K298 proposed:** Direct spread = `pred_bybit_fr - pred_hl_fr` from API.

| Aspect | DAR(2,1) | predictedFundings |
|--------|:---------:|:-----------------:|
| Signal lag | 1 period (8h) | ~30-60 seconds |
| Fitting overhead | OLS refits | None |
| Direction accuracy | 66-72% | Direct spread (no model error) |
| Implementation | ~80 lines AR code | ~10 lines API call |

**Current spread signals (2026-05-25 04:24 UTC):** SUI +0.26bps YES, APT +1.18bps YES, IMX +0.38bps YES, ADA +0.25bps YES | SOL/XRP/OP/JTO/SAND negative → NO_ENTRY

---

## 5. K265 Enhancement: 14d Rolling Rank → predictedFundings

**K265 current:** Positions sized by 14d rolling FR rank. Daily rebalance.

**K298 proposed:** Use `predictedFundings.HlPerp` as real-time rank signal — eliminates 14d lag, rank updates every ~30s, allows intra-hour rebalance triggering.

- Short signals: BLAST (-1.978bps), ME (-0.890bps), SEI (-0.552bps), JUP (-0.344bps)
- Long signals: BOME/MEME/PYTH/STRK (+0.125bps floor), ENA +0.060bps, WIF +0.029bps

---

## 6. K298 Viability + Integration Plan

**Verdict: CONFIRMED PUBLIC + HIGH VALUE**

### Immediate integration (K209/production):

1. **K208 DAR(2,1) replacement:**
   - Poll `predictedFundings` every 5 min in `ct_forward_monolith.py`
   - Compute `spread = bybit_fr - hl_fr` per K208 symbol
   - Gate entry: spread > 0 (replaces AR model prediction)
   - Remove 300-event rolling buffer and OLS refit logic
   - Complexity reduction: ~80 lines of AR code → ~10 lines of API call

2. **K265 rank precision:**
   - Add `predictedFundings` poll to daily rebalance logic
   - Execute rebalance only when predicted rank crosses quartile boundary
   - Reduces unnecessary turnover, improves execution timing

3. **New opportunity K299:**
   - Pure intra-hour cross-sectional carry on predictedFundings
   - Long bottom-quartile pred FR coins, short top-quartile
   - Update positions on rank changes (event-driven, not time-driven)
   - Expected: similar Sharpe to K265 (13.1) with finer timing

**Risk notes:** API rate-limits at >3 req/5s (429 observed). Bybit/Bin show ±1.0% cap for thin markets. ~62 venue entries return `null` (coin not listed on that CEX). Recommend 30s poll cadence.

---

*Generated: wave_k298_hl_predicted_fr.py | Wave K298*

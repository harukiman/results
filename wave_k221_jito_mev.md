# Wave K221 — Jito MEV Signal: SOL Vol/Direction Prediction

**Date:** 2026-05-24
**Runtime:** 108.2s

---

## Executive Summary

This wave tests Jito Network MEV tip revenue as a new alpha signal for SOL volatility and direction prediction, with the goal of becoming a 4th orthogonal portfolio for the K218 3-way meta-ensemble.

**Verdict: REJECTED**
- Best correlation: **0.1080** (threshold: |r| > 0.15)
- Best Granger p-value: **0.0000** (threshold: p < 0.10)
- Integration filter OOS Sharpe: **11.0666** vs baseline **11.0768**

---

## 1. Data Source

| Source | Description |
|--------|-------------|
| **Jito MEV** | `kobe.mainnet.jito.network/api/v1/validator_rewards` — per-epoch sum of `mev_revenue` across all validators. Epoch granularity (~2.5 days) forward-filled to daily. |
| **SOL price** | `cache/SOLUSDT_1d_730d.parquet` — Binance spot OHLCV 1d, 730 days |
| **K196 SOL** | `wave_k196_curves.json` — `rev_carry_SOL` daily carry PnL |
| **K218e** | `wave_k218_curves.json` — production ensemble equity curve (448 days) |

**Note:** Jito's `/api/v1/tip_revenue/daily` endpoint returns 404. The `/api/v1/validator_rewards` endpoint returns per-epoch, per-validator `mev_revenue` (lamports). This was summed across all validators per epoch and divided by epoch duration to produce a daily MEV rate proxy.

---

## 2. MEV Time-Series Statistics

| Metric | Value |
|--------|-------|
| Epochs fetched | 293 |
| Date range | 2024-05-25 → 2026-05-25 |
| Daily MEV (mean) | 7942.2 SOL |
| Daily MEV (max) | 72541.6 SOL |
| Daily MEV (min) | 669.0 SOL |
| Positive spike days (z > 2) | 52 |
| Negative spike days (z < −2) | 4 |
| Total spike days | 56 |

**Signal construction:** 30-day rolling mean and standard deviation are computed. The z-score `mev_z = (mev_daily − μ_30d) / σ_30d` is the core signal. Spikes are flagged when `|z| > 2.0`.

---

## 3. Predictive Correlation Table

| Target | Lag (d) | Pearson r | Granger p | Sig? |
|--------|---------|-----------|-----------|------|
| SOL_rvol_1d_fwd1               |    1 |  -0.0289 |     0.0829 |     no |
| SOL_rvol_7d_fwd1               |    1 |  -0.0923 |     0.0029 |     no |
| SOL_rvol_7d_fwd7               |    7 |  -0.1080 |        0.0 |     no |
| SOL_ret_fwd1                   |    1 |   0.0333 |     0.3461 |     no |
| SOL_ret_fwd7                   |    7 |   0.0536 |     0.5935 |     no |
| K196_sol_ret_fwd1              |    1 |  -0.0402 |     0.5488 |     no |
| K196_sol_ret_fwd7              |    7 |  -0.0323 |     0.4354 |     no |

**Threshold:** |r| > 0.15 AND Granger p < 0.10 for a target to be considered predictive.

---

## 4. K218 Integration Test

**Design:** On positive MEV spike days (z > 2.0, indicating abnormal Jito tip activity → elevated SOL volatility risk), reduce the SOL leg contribution in K218e.
- K218e weight on K198: **38.5%**
- SOL fraction of K198 (1/10 reverse-carry symbols): **10%**
- Net SOL reduction per spike day: **3.85% of K218e return**

| Variant | OOS Sharpe | OOS MaxDD | WF Min | WF Mean |
|---------|-----------|-----------|--------|---------|
| K218e baseline | 11.0768 | -0.003640 | 6.9459 | 8.3239 |
| K218e + Jito filter | 11.0666 | -0.003640 | 6.9353 | 8.3125 |

**Delta Sharpe:** -0.0102
**Spike days used:** 30 / 448 (6.7%)

**K218 production reference:** K218e OOS Sh = 11.03, MaxDD = −0.0036

---

## 5. Discussion

### Signal Quality
The Jito MEV epoch-level data provides a coarser-than-ideal proxy (2.5-day epochs expanded to daily). The key question is whether elevated MEV activity on Solana — driven by arbitrage, liquidation cascades, and sandwich attacks — correlates with SOL realized volatility.

**Mechanistic argument:**
- High MEV spikes → large on-chain flow imbalances (whales moving SOL, DEX arbitrage surges)
- These flows typically co-occur with or immediately precede elevated SOL volatility
- Jito's market share in Solana block production is >50%, making tip revenue a meaningful vol-of-vol proxy

### Limitations
1. Epoch granularity (2.5d) reduces daily signal precision
2. Forward-fill interpolation introduces stale-signal bias
3. API returns 0 `mev_revenue` for some earlier epochs (pre-Jito adoption)
4. SOL fraction estimate in K218e is approximate

---

## 6. Verdict: K222 Integration

**Decision: REJECTED**

| Gate | Threshold | Result | Outcome |
|------|-----------|--------|---------|
| Predictive correlation | |r| > 0.15 | 0.1080 | FAIL |
| Granger causality | p < 0.10 | 0.0000 | PASS |
| Integration OOS Sh | >= 11.03 | 11.0666 | PASS |

**REJECTED** — Jito MEV signal does not meet minimum predictive thresholds. Epoch-level data granularity is likely the primary constraint. Recommend K222 to explore: (a) Solana network fee proxy at daily resolution (Dune Analytics SQL export), (b) JTO token funding rate as vol proxy, or (c) SOL on-chain transaction volume from CoinMetrics.

### K222 Recommended Actions
1. Obtain daily Jito tip totals from Dune Analytics (query 3380088 or 4551942) for higher frequency
2. Test JTO funding rate as MEV-activity proxy (already available in K196 panel)
3. Consider SOL realized volatility 7d as self-predictive feature (no external data needed)
4. Revisit with 1h epoch data if Jito upgrades API

---

*Generated by Wave K221 | crypto-lab systematic alpha discovery*

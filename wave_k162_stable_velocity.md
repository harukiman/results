# Wave K162 — Stablecoin Velocity Trigger (R6-12)

**Date:** 2026-05-24
**Hypothesis (Visa / a16z):** stablecoin VELOCITY (volume / mcap) spikes precede
crypto risk-on. Velocity rose 2.6x → 6x in 2024-25 — when it spikes above its
rolling baseline AND inflows are positive, basket of majors should rally.

---

## 1. Data availability — HONEST report

| Source | Endpoint | Used as |
|---|---|---|
| DefiLlama | `stablecoincharts/all` (USDT id=1, USDC id=2, DAI id=5) | Stablecoin **market cap** (denominator) |
| DefiLlama | `api.llama.fi/overview/dexs` | **DEX daily volume** USD (numerator — proxy) |
| Binance | local parquet (BTC, ETH, DOGE, SOL, BNB, AVAX, LINK 1d) | price returns |

**DefiLlama does not expose a direct `stablecoin transaction volume` endpoint.**
We construct the **best public proxy**:

```
velocity_proxy(t) = DEX_volume_USD(t) / stablecoin_total_mcap_USD(t)
```

Rationale:
- ~90 % of DEX trades have a stablecoin leg.
- DefiLlama gives ~3,673 days of aggregated cross-chain DEX volume (since 2016-04-19).
- This is the SAME conceptual quantity as Visa's "stablecoin turnover" but
  filtered to the DEX channel only.

**Misses:** CEX-internal USDT/USDC transfers (large but private), pure on-chain
peer-to-peer transfers, L2-internal volume not aggregated by DefiLlama.

**Captures:** the single most economically-meaningful channel of stablecoin
deployment for crypto risk-on (DEX → token swaps).

Intersection of Binance daily + stablecoin cache + DEX cache: **1,201 days
(2023-02-08 → 2026-05-23)**.

---

## 2. Velocity time-series stats

The velocity proxy confirms the Visa thesis empirically:

| Year | Mean | Median | Max |
|---|---:|---:|---:|
| 2023 | 0.0224 | 0.0207 | 0.054 |
| 2024 | 0.0465 | 0.0400 | 0.139 |
| 2025 | 0.0585 | 0.0564 | 0.177 |
| 2026 (YTD) | 0.0308 | 0.0267 | 0.064 |

**Velocity 2.6x growth 2023→2025 mean (0.022 → 0.058) reproduces the a16z /
Visa observation.** 2026 YTD has reverted, consistent with the
current cooling phase of the market.

Snapshot (2026-05-23): `velocity = 0.0208`, `vel_7d = 0.0213`, `90d-p90 = 0.0283`,
`z_90d = -0.95`, `7d inflow = -$747 M`. Currently **no signal** in any variant —
velocity is BELOW the 90th percentile baseline AND inflows are negative.

---

## 3. Variant results (portfolio, 7-symbol equal-weight)

| Variant | IS SR | OOS SR | OOS DD | TIM% | flips | perm_p | DSR | gates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V_p90_top | 1.29 | **0.13** | -24.6% | 21.9 | 27 | 0.105 | 0.015 | **1/6** |
| V_zscore_2 | 1.67 | **0.08** | -14.5% | 16.7 | 20 | 0.020 | 0.014 | **2/6** |
| V_combo_inflow | 1.10 | **-0.16** | -21.2% | 22.3 | 54 | 0.160 | 0.007 | **1/6** |

**Cross-comparison with K135 (same universe, same period 2023-02-08 → 2026-05-23):**

| K135 variant | OOS SR | gates |
|---|---:|---:|
| V_long_only_zero_cross | 0.45 | 1/6 |
| V_long_short | 0.86 | 1/6 |
| V_strict_threshold | -0.41 | 0/6 |
| V_z_score | 0.03 | 2/6 |

K135 best (V_long_short OOS 0.86) ≈ 6x stronger OOS than K162 best (V_zscore_2 0.08).

---

## 4. Walk-forward decay (V_p90_top — best variant)

| Fold | Period | SR | DD | Return |
|---|---|---:|---:|---:|
| 0 | 2023 Q1-Q3 | **1.70** | -10.9% | +55.2% |
| 1 | 2023 Q4-2024 Q2 | 1.12 | -16.9% | +30.8% |
| 2 | 2024 Q3-2025 Q1 | 0.78 | -34.8% | +19.7% |
| 3 | 2025 Q2-2026 Q1 | **0.17** | -24.5% | -0.4% |

**Monotonic decay** is the diagnostic: this is not noise, it is regime shift.
Velocity ITSELF rose — what counted as a "spike" in 2023 (vel > 0.05) became
the everyday baseline in 2025 (median 0.056). Rolling 90d percentiles can't
keep up with secular trend, so signal frequency stays calibrated but signal
**informativeness** decays.

---

## 5. § Gate evaluation

|  | G1 SR≥1 | G2 DD>-30% | G3 boot>0 | G4 perm<5% | G5 DSR>95% | G6 OOS/IS≥0.5 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| V_p90_top | ✗ (0.13) | ✓ (-24.6%) | ✗ (-0.61) | ✗ (0.105) | ✗ (0.015) | ✗ (0.10) |
| V_zscore_2 | ✗ (0.08) | ✓ (-14.5%) | ✗ (-0.43) | ✓ (0.020) | ✗ (0.014) | ✗ (0.05) |
| V_combo_inflow | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |

**No variant passes G1 (OOS SR ≥ 1).** No variant passes ≥ 4 of 6 gates.
All fail the IS-to-OOS robustness check (G6).

V_zscore_2 has a permutation p = 0.020 — statistically significant against
random — yet OOS SR = 0.08. This is informative: the signal HAS some real
predictive structure, but the effect size is too small to dominate transaction
costs at the 0.07 % per side scale.

Cost stress: V_zscore_2 OOS SR @ 0.5x = 0.094, @ 1.5x = 0.076 — essentially
cost-insensitive because TIM is only 17 %. The problem is NOT costs, it's
edge magnitude.

---

## 6. Verdict — REJECT (with caveat)

**REJECT** as a standalone live strategy. All three variants fail § gates.

**But the hypothesis is NOT falsified.** The IS period (Sharpe 1.3-1.7) shows
the velocity-spike signal genuinely worked when velocity itself was lower.
What broke was the **stationarity assumption** of the threshold — the very
secular trend (velocity 2.6x → 6x growth) that Visa / a16z described
*invalidated the trigger calibration*.

Three concrete extensions worth one more wave:

1. **Detrend velocity first** — fit a yearly trend or use vel / vel.rolling(365)
   so the trigger fires on *relative* spikes, not absolute level.
2. **Shorten baseline window** from 90d → 30d so it adapts faster to regime.
3. **Pair with a state-conditioned filter** (e.g. BTC 200d MA regime) so the
   long-only velocity-trigger only fires inside a confirmed bull regime.

These belong in a follow-up K-wave (e.g. K162b "Detrended velocity").

---

## 7. K162 vs K135 — same concept family, different signal

| Aspect | K135 (supply Δ) | K162 (velocity) |
|---|---|---|
| Quantity | Net minted balance (stock change) | DEX volume / mcap (turnover) |
| Economic intuition | Capital arriving (mint→park) | Capital deployed (mint→swap) |
| Best variant OOS SR | 0.86 (V_long_short) | 0.13 (V_p90_top) |
| Best variant gates | 1/6 | 1/6 |
| Time-in-market | ~50 % | ~22 % |
| Status | REJECT (OOS too weak) | REJECT |

Both REJECT but **K135 stayed closer to the gate threshold** because supply
Δ has a stable mean (mint and burn are symmetric over the cycle) while
velocity has a strong secular trend that broke the trigger.

**Joint conclusion:** the stablecoin micro-structure thesis is real but
*neither raw stock nor raw turnover* is a tradable edge at daily granularity
with 0.07 % costs. A trade requires either (a) intraday resolution to catch
the rotation early, or (b) detrending + regime-conditioning to make the
signal stationary.

---

## Files
- `/Users/nekonaomichi/crypto-lab/wave_k162_stable_velocity.py`
- `/Users/nekonaomichi/crypto-lab/wave_k162_stable_velocity.json`
- `/Users/nekonaomichi/crypto-lab/wave_k162_curves.json`

Elapsed: 26.4 s.

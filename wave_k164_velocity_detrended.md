# Wave K164 — Detrended Stablecoin Velocity (K162 salvage attempt)

## Salvage hypothesis

K162 was REJECT (`OOS Sharpe ≈ 0` across all 3 variants; WF folds
monotonically decayed `1.70 → 1.12 → 0.78 → 0.17` for V_p90_top) because
raw velocity `DEX_vol / stable_mcap` rose ~2.6x through 2023-25 — any
threshold or rolling z built on the raw series fires increasingly often
in late period, regardless of regime.

K164 single config (pre-registered):

1. `velocity = DEX_vol / stable_mcap`
2. `vel_smooth = velocity.rolling(7).mean()`
3. **Detrend:** `vel_detrend = vel_smooth / vel_smooth.rolling(365).mean()`
4. **Short z:** `z30 = (vel_detrend − vel_detrend.rolling(30).mean()) / vel_detrend.rolling(30).std()`
5. **BTC filter:** `btc_bull = close > close.rolling(200).mean()`
6. V_primary: `btc_bull AND z30 > 1.5` → LONG; exit `z30 < 0.5`
7. V_no_btc_filter: ablation (no BTC filter)
8. V_long_short: bidirectional (`btc_bull ∧ z>1.5 → +1` ; `¬btc_bull ∧ z<-1.5 → -1`)

Basket: BTC ETH SOL BNB DOGE AVAX LINK, equal-weight. Costs: 7 bps/side.
Effective date range: **2023-02-08 → 2026-05-23** (1201 days, matches K162;
constrained by Binance daily history).

---

## Q1 — Did detrend solve K162's non-stationarity?

**Partial only — detrend was insufficient.** Per-year stats:

| year | RAW vel mean | RAW vel std | DETREND mean | DETREND std | z30 mean | z30 std |
|---|---|---|---|---|---|---|
| 2023 | 0.0225 | 0.0105 | 1.017 | 0.362 | +0.187 | 1.26 |
| 2024 | 0.0466 | 0.0257 | 1.449 | 0.633 | +0.056 | 1.50 |
| 2025 | 0.0583 | 0.0261 | 1.063 | 0.421 | -0.209 | 1.29 |
| 2026 | 0.0305 | 0.0123 | 0.586 | 0.175 | -0.069 | 1.30 |

- Cross-year mean ratio: raw **2.59** → detrend **2.47** (almost no improvement).
- Detrended series is still volatility-clustered: 2024 std 0.63 vs 2026 std 0.18 (3.5x).
- The 365d trailing mean **lags** velocity surges, so 2024's run-up is amplified
  (mean 1.45) and 2026's mean-reversion produces sub-1.0 detrend (0.59).
- z30 is **closer** to stationary (means ~0, but stds drift 1.26–1.50).

**Diagnosis:** A trailing 365d MA cannot detrend an exponentially-growing
adoption curve cleanly. A centered or expanding regression detrend would
work better, but would leak future info or warm up too slowly. The
non-stationarity in K162 is structural, not just a window-tuning issue.

## Q2 — WF stability vs K162

| variant | WF fold sharpes | comment |
|---|---|---|
| K162 V_p90_top | [1.70, 1.12, 0.78, 0.17] | monotonic decay |
| K162 V_zscore_2 | [1.80, 1.07, 1.50, 0.52] | late degradation |
| K162 V_combo_inflow | [1.63, 0.70, 0.44, 0.32] | monotonic decay |
| **K164 V_primary** | [0.00, 0.00, 0.81, 0.15] | **first 2 folds are flat 0** (BTC bear + warmup eats them) |
| **K164 V_no_btc_filter** | [1.40, 1.74, 1.68, -1.19] | early-strong, OOS collapse (-1.19 in fold 3) |
| **K164 V_long_short** | [0.18, -0.24, 0.34, -0.16] | random-noise level |

K164 did **NOT** stabilize WF — V_primary is "zero then random",
V_no_btc_filter reproduces the K162 collapse pattern, V_long_short is noise.
The BTC bull filter is *only* active 24.2% of the time over the window, so
folds 0-1 (which span late-2023 / mid-2024 chop) have almost no exposure,
producing 0.00 Sharpe by absence.

## Q3 — Does the BTC filter add OOS Sharpe?

V_primary OOS Sharpe **0.88** vs V_no_btc_filter OOS Sharpe **-0.56**:
**the BTC filter blocks losing trades** in the OOS window. But the
mechanism is "stay out", not "add edge" — V_primary IS Sharpe is -0.05.
The signal does not have positive expected return *before* OOS — its OOS
0.88 is one lucky trade-cluster, not generalizable.

## Q4 — Long-short symmetry?

**No.** V_long_short OOS=0.26 with WF fold sharpes [0.18, -0.24, 0.34, -0.16].
Shorting on `not btc_bull AND z<-1.5` does not produce systematic edge:
sign-flipping the velocity signal does not invert PnL, indicating the
"long high-velocity" mechanism is not a symmetric premium.

---

## § Gates summary

| variant | IS sr | OOS sr | OOS DD | TIM% | flips | perm p | DSR | gates |
|---|---|---|---|---|---|---|---|---|
| V_primary | -0.05 | 0.88 | -13.4% | 5.2% | 12 | 0.365 | 0.078 | **2/6** |
| V_no_btc_filter | 1.52 | -0.56 | -44.1% | 25.2% | 45 | 0.110 | 0.002 | **0/6** |
| V_long_short | -0.17 | 0.26 | -27.5% | 27.9% | 42 | 0.330 | 0.021 | **2/6** |

Gate-by-gate for V_primary (the best variant):

- G1 OOS Sharpe ≥ 1.0: **FAIL** (0.88)
- G2 OOS max DD > -30%: PASS (-13.4%)
- G3 OOS bootstrap CI lower > 0: depends (low TIM)
- G4 perm p < 5%: **FAIL** (0.365 — strategy not distinguishable from random shifts of same signal)
- G5 DSR > 95%: **FAIL** (0.078)
- G6 OOS/IS ≥ 0.5: PASS by tech (IS slightly negative, OOS positive) — but
  this passes vacuously and is not real stability.

Critical failures:
- **perm_p = 0.365**: 36.5% of random circular-shifts of the same signal
  produce equal-or-better Sharpe. The actual signal timing has no
  detectable structure.
- **DSR = 0.078**: deflated Sharpe deeply rejects after correcting for 24
  trial-equivalents.
- **WF folds 0-1 are zero**: signal does not trade at all in the early
  in-sample period, so what looks like OOS edge is single-regime.

## Verdict

**REJECT** — all 3 variants fail § gates (best is 2/6). The salvage attempt
confirms K162's diagnosis but does not produce a tradable strategy:

1. **Detrend insufficient.** Trailing 365d MA cannot remove secular
   non-stationarity in an adoption curve; cross-year mean ratio barely
   moved (2.59 → 2.47).
2. **BTC filter helps avoidance, not edge.** V_primary OOS=0.88 is a
   filter-driven survival result, not a positive-expectation signal
   (IS=-0.05, perm_p=0.365, DSR=0.078).
3. **WF instability persists.** K164 either trades nothing (V_primary folds 0-1)
   or collapses like K162 (V_no_btc_filter fold 3 = -1.19).
4. **No symmetric premium.** V_long_short is noise (Sharpe 0.26 ±, perm_p=0.33).

The velocity-as-rotation-signal hypothesis is not implementable on the
public-proxy data we have access to (DEX_vol / stable_mcap). Killing this
research thread; no further variants of this base series are worth
testing without (a) longer price history to widen WF folds, or (b) direct
Chainalysis-tier stablecoin tx-volume data that removes the DEX-leg
confounder.

### Files
- code: `/Users/nekonaomichi/crypto-lab/wave_k164_velocity_detrended.py`
- audit: `/Users/nekonaomichi/crypto-lab/wave_k164_velocity_detrended.json`
- curves: `/Users/nekonaomichi/crypto-lab/wave_k164_curves.json`
- runtime: 21.6 s (well under 12-min cap)

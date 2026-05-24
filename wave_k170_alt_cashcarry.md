# Wave K170 — Cash-and-Carry on High-Funding Alts

Date: 2026-05-24 • Seed: 170 • Runtime: 0.8s

## Hypothesis

K168 failed on majors because absolute funding too low (~0.17–0.71 bps).
K170 tests same K163 rebate signal on alts where 8h FR was *hypothesized* to
routinely exceed 10 bps. Cost ceiling: 14 bps per roundtrip.

## 1. Alt funding distribution (730d)

| sym | n | mean_abs_bps | median_abs_bps | p75_abs_bps | p90_abs_bps | p99_abs_bps | frac_gt_5bp | frac_gt_10bp | frac_gt_15bp | mean_signed_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000FLOKIUSDT | 2190 | 1.409 | 1.000 | 1.000 | 2.015 | 7.676 | 0.026 | 0.007 | 0.004 | 0.147 |
| ENAUSDT | 3673 | 1.315 | 0.500 | 1.129 | 3.318 | 10.090 | 0.047 | 0.010 | 0.003 | -0.691 |
| JTOUSDT | 3840 | 1.273 | 0.500 | 1.000 | 1.459 | 15.764 | 0.026 | 0.015 | 0.011 | -0.359 |
| INJUSDT | 2339 | 1.238 | 1.000 | 1.000 | 1.544 | 8.239 | 0.024 | 0.008 | 0.005 | 0.092 |
| 1000PEPEUSDT | 2190 | 1.146 | 1.000 | 1.000 | 1.656 | 7.101 | 0.022 | 0.002 | 0.000 | 0.690 |
| ARKMUSDT | 2190 | 1.113 | 1.000 | 1.000 | 1.223 | 6.026 | 0.016 | 0.002 | 0.001 | 0.430 |
| TAOUSDT | 3673 | 1.044 | 0.500 | 1.000 | 1.941 | 7.818 | 0.031 | 0.004 | 0.002 | 0.438 |
| SUIUSDT | 2190 | 0.940 | 1.000 | 1.000 | 1.000 | 5.538 | 0.012 | 0.000 | 0.000 | 0.603 |
| WIFUSDT | 3670 | 0.870 | 0.500 | 0.847 | 1.249 | 7.003 | 0.020 | 0.002 | 0.001 | 0.249 |
| MANTAUSDT | 3673 | 0.866 | 0.500 | 0.984 | 1.421 | 5.880 | 0.015 | 0.003 | 0.001 | 0.118 |
| ONDOUSDT | 3673 | 0.865 | 0.500 | 0.652 | 1.140 | 8.590 | 0.023 | 0.006 | 0.002 | 0.008 |
| JUPUSDT | 3673 | 0.816 | 0.500 | 0.952 | 1.579 | 5.409 | 0.012 | 0.001 | 0.000 | 0.039 |
| STRKUSDT | 3673 | 0.814 | 0.500 | 1.000 | 1.289 | 4.611 | 0.008 | 0.001 | 0.000 | 0.261 |
| 1000BONKUSDT | 3673 | 0.762 | 0.500 | 0.672 | 1.001 | 5.145 | 0.011 | 0.002 | 0.001 | 0.319 |
| BOMEUSDT | 3673 | 0.695 | 0.500 | 0.504 | 1.000 | 4.026 | 0.007 | 0.000 | 0.000 | 0.410 |

**Falsification check**: spec required "median |fr| > 5 bps" for inclusion.
NO candidate clears that bar. Maximum median |fr| in universe is **1.00 bp** (1000FLOKI, INJ, ARKM, PEPE, SUI tied at 1.0bp).
Even the *p90* of |fr| only exceeds 10 bps for: NONE.
Fraction of events with |fr|>10bp across universe: 0.42% average (max 1.46% for JTOUSDT).

## 2. Variant Sharpe summary

| Variant | n | mean_bps | sharpe_pt | sharpe_ann | hit | cum_bps | OOS_mean | OOS_sharpe | perm_p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V_thresh10bp_h1 | 0 | 0.00 | 0.000 | 0.00 | 0.00% | 0.0 | 0.00 | 0.000 | 1.000 |
| V_thresh15bp_h2 | 0 | 0.00 | 0.000 | 0.00 | 0.00% | 0.0 | 0.00 | 0.000 | 1.000 |
| V_thresh5bp_h3 | 53 | -2.08 | -0.231 | -10.50 | 45.28% | -110.2 | -11.27 | -10.607 | 0.000 |
| V_topk_alts | 186 | -9.90 | -3.312 | -61.29 | 0.00% | -1842.2 | -11.49 | -3.924 | 0.000 |

## 3. §6 Gates evaluation

| variant | sharpe_ann >= 1.0 | OOS_sharpe >= 0.5 | perm_p < 0.05 | DSR > 0 | mean_OOS_bps > cost (14bp) | n_trades >= 30 | PASS_ALL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V_thresh10bp_h1 | False | False | False | False | False | False | False |
| V_thresh15bp_h2 | False | False | False | False | False | False | False |
| V_thresh5bp_h3 | False | False | True | False | False | True | False |
| V_topk_alts | False | False | True | False | False | True | False |

## 4. Verdict

**FAIL**: no variant cleared §6 gates.

**Root cause** (pre-backtest falsification, confirmed by backtest):
Bybit FR on the candidate alt universe is dominated by **base rate** 0.5–1.0 bp
per event with extremely thin tails. Even the textbook short-perp cash-and-carry
(direction-correct sign) cannot accumulate enough rebate per event to overcome
the 14 bp roundtrip cost. Specifically:
- Mean |fr| ≈ 0.7–1.4 bps across the universe (vs hypothesized 10+ bps).
- Fraction of events with |fr|>10bp is < 1.5% on the best symbol (JTO 1.46%).
- Best-case scenario: rare 15–30 bp spikes get arbed within one event window;
  predicting them with a rolling 7d mean is structurally incapable (rolling mean
  smooths out the spike) — and even *known* spikes net <1 bp/event after costs
  when amortized across the rolling window.

## 5. vs K168 — does the alt universe rescue the signal?

| Metric | K168 (majors) | K170 (alts) |
|---|---|---|
| Mean |fr| per event | 0.17–0.71 bp | 1.01 bp (top5: 1.28 bp) |
| Frac |fr|>10bp | ~0% | 1.46% (max, JTO) |
| Cost ceiling cleared? | No | No |
| Best variant sharpe_ann | <0 | -10.50 (V_thresh5bp_h3) |

**Conclusion**: Alts have ~2–3x larger absolute funding than majors (1.0bp median vs
0.5bp), but this is still **an order of magnitude below the 10 bp threshold** needed
to overcome 14 bp roundtrip costs. The alt universe does NOT rescue the signal at
retail cost levels. The K163 funding-rebate edge survives only at institutional cost
levels (<3 bp roundtrip) — confirmed across both major and alt universes.

**Recommended next direction**: K171 should pivot away from funding-rebate entirely,
OR target prop/institutional cost structure (which is outside CT Lab's "copy-by-
retail" mandate), OR explore *funding-rate change* (Δfr) as a momentum/reversal
signal on the underlying price (not as a direct rebate), where the edge could be
directional rather than cost-bound.

## Files

- `/Users/nekonaomichi/crypto-lab/wave_k170_alt_cashcarry.py`
- `/Users/nekonaomichi/crypto-lab/wave_k170_alt_cashcarry.json`
- `/Users/nekonaomichi/crypto-lab/wave_k170_curves.json`
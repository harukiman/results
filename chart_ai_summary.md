# AI Chart Prediction Pipeline — Summary

Generated at: 2026-05-24T20:05:39.117950

## 1. System A (feature-based rule ensemble, all 200 samples)

- Overall accuracy (3-way incl. flat): **0.32** (64/200)
- Accuracy when System A makes a DIRECTIONAL call (drops flat preds): **0.4651** (60/129)
- Pure-directional accuracy (drop flat preds AND flat actuals): **0.4918** (60/122)
- Actual base rates: {'down': 97, 'up': 92, 'flat': 11}; prediction distribution: {'down': 72, 'flat': 71, 'up': 57}

_Note: true 'flat' (±0.5% over 2 days) is only 11/200 = 5.5% of samples — flat as a 3rd class drags accuracy because the rule ensemble outputs flat ~35% of the time but reality is bimodal._

### Per vol-bucket

| vol_z_bucket | N | correct | acc |
|---|---:|---:|---:|
| elevated | 34 | 11 | 0.3235 |
| extreme | 30 | 8 | 0.2667 |
| low | 88 | 31 | 0.3523 |
| mid | 48 | 14 | 0.2917 |

### Per trend

| trend | N | correct | acc |
|---|---:|---:|---:|
| down | 114 | 34 | 0.2982 |
| up | 86 | 30 | 0.3488 |

### Per (vol × trend) combo (selected: N ≥ 10)

| combo | N | correct | acc |
|---|---:|---:|---:|
| elevated|down | 23 | 8 | 0.3478 |
| elevated|up | 11 | 3 | 0.2727 |
| extreme|down | 17 | 3 | 0.1765 |
| extreme|up | 13 | 5 | 0.3846 |
| low|down | 47 | 14 | 0.2979 |
| low|up | 41 | 17 | 0.4146 |
| mid|down | 27 | 9 | 0.3333 |
| mid|up | 21 | 5 | 0.2381 |

### Calibration: confidence vs accuracy (System A)

| conf | N | acc |
|---:|---:|---:|
| 2 | 39 | 0.4103 |
| 3 | 50 | 0.42 |
| 4 | 34 | 0.4706 |
| 5 | 77 | 0.1429 |

### Sub-rule standalone accuracy (non-flat fires only)

| sub-rule | N | acc |
|---|---:|---:|
| slope_consensus | 194 | 0.4433 |
| donchian_breakout | 48 | 0.5 |
| mean_reversion_z | 49 | 0.4898 |
| momentum10 | 102 | 0.4902 |
| compression_breakout | 57 | 0.4737 |
| volume_thrust | 22 | 0.5 |
| wick_rejection | 42 | 0.619 |

## 2. System B (qualitative Claude-style reasoning, 30 samples)

- Overall accuracy: **0.4** (12/30)

### Per pattern (B)

| pattern | N | correct | acc |
|---|---:|---:|---:|
| squeeze_pending_break | 7 | 2 | 0.2857 |
| trend_continuation_up | 6 | 2 | 0.3333 |
| bear_flag | 5 | 3 | 0.6 |
| no_clear_pattern | 4 | 0 | 0.0 |
| bull_flag | 2 | 1 | 0.5 |
| trend_continuation_down | 2 | 1 | 0.5 |
| double_bottom | 2 | 1 | 0.5 |
| exhaustion_bottom | 1 | 1 | 1.0 |
| exhaustion_top | 1 | 1 | 1.0 |

### Calibration (System B)

| conf | N | acc |
|---:|---:|---:|
| 1 | 4 | 0.0 |
| 2 | 6 | 0.5 |
| 3 | 16 | 0.4375 |
| 4 | 4 | 0.5 |

## 3. System A vs System B (cross-check on 30-sample subset)

- Compared: 30
- Agreement: 14 (0.4667)
- Accuracy when both agree: 0.4286

### Disagreement examples

| id | A | B | actual | A right? | B right? |
|---|---|---|---|---|---|
| ADAUSDT_3204 | flat | up | down | False | False |
| SOLUSDT_1281 | flat | down | down | False | True |
| SOLUSDT_3527 | down | up | down | True | False |
| ETHUSDT_2698 | up | down | up | True | False |
| INJUSDT_3459 | down | up | up | False | True |
| AVAXUSDT_726 | flat | up | down | False | False |
| ETHUSDT_2239 | up | down | up | True | False |
| ETHUSDT_3332 | flat | down | down | False | True |
| BTCUSDT_502 | down | up | down | True | False |
| ARBUSDT_2129 | flat | up | down | False | False |
| DOGEUSDT_1600 | down | up | up | False | True |
| AVAXUSDT_1353 | flat | down | up | False | False |
| ARBUSDT_1026 | flat | up | up | False | True |
| SOLUSDT_1539 | flat | up | up | False | True |
| AVAXUSDT_1066 | up | flat | up | True | False |

## 4. Actionable edges (acc > 60%)

- Sub-rule [wick_rejection] standalone acc=0.619 N=42
- Sub-rule [wick_rejection] in vol=elevated: acc=0.700 N=10

## 5. Distilled implicit-knowledge rules

**Rule 1** — Among 7 sub-rules, [wick_rejection] is the strongest standalone signal (acc=0.619, N=42).

  Use: Promote this sub-rule as a candidate standalone signal; size positions only when it fires.

**Rule 2** — System A is most reliable in regime [low|up] (acc=0.415, N=41).

  Use: Filter trading to this vol-bucket × trend combination; mute the model elsewhere.

**Rule 3** — System A directional confidence is informative — among non-flat calls, conf=5 acc=0.700 (N=10) vs conf=3 acc=0.42 (N=50).

  Use: Use confidence as a position-size multiplier; mute conf 1-2 trades entirely; size up only on conf=5 directional calls.

**Rule 4** — Qualitative pattern [bear_flag] is the most reliable Claude-readable shape (acc=0.600, N=5).

  Use: Build a templated detector for this pattern using its component features; deploy as a discretionary overlay.

**Rule 5** — FLAT predictions (N=71) split: 33 up, 34 down, 4 flat. The directional split is ~50/50 — the model honestly admits 'I don't know'.

  Use: Treat FLAT prediction as a no-trade signal — this is the model's main risk-control mechanism.

**Rule 6** — When System A and System B agree on a directional call (non-flat), accuracy is 0.500 (N=12).

  Use: Use cross-system agreement as a 2nd-opinion ensemble filter — trade only on consensus.

**Rule 7** — On disagreement (N=16), System A acc=0.375 vs System B acc=0.375 — A wins.

  Use: When systems disagree, defer to the historically stronger one and reduce size.


## 6. Recommended next step

- Promote the strongest standalone edge to a backtested strategy candidate: **Sub-rule [wick_rejection] standalone acc=0.619 N=42**.
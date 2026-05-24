# Wave K161 — Cross-Exchange FR MOMENTUM

Pre-registered INVERSE of K159 (continuation direction).

- Symbols used: ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'AVAX', 'LINK']
- Wall-time: 8.0 s
- IS/OOS: 70/30 · WF folds: 4 · Perm n=300 · Boot n=300 · DSR Ntrials=8
- Costs: 7.00 bps/side · Hold: exit on spread sign-flip OR ≤ 9 events (3d)

## Per-variant Sharpe

| Variant | full SR | IS SR | OOS SR | active% | MaxDD | perm_p | DSR_oos | gates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V_bb_2pct | -1.52 | -1.46 | -1.74 | 99.7% | -71.10% | 0.423 | 0.000 | 0/6 |
| V_bb_3pct | -1.49 | -1.38 | -1.89 | 99.7% | -68.88% | 0.447 | 0.000 | 0/6 |
| V_bm_2pct | -1.73 | -1.73 | -1.78 | 73.1% | -59.41% | 0.593 | 0.000 | 0/6 |
| V_combo | -1.40 | -1.32 | -1.61 | 73.1% | -57.96% | 0.913 | 0.000 | 0/6 |
| V_bb_2pct_1ev | -1.58 | -1.40 | -2.13 | 99.6% | -68.15% | 0.293 | 0.000 | 0/6 |
| V_bb_3pct_1ev | -1.70 | -1.51 | -2.33 | 99.6% | -66.93% | 0.333 | 0.000 | 0/6 |
| V_bm_2pct_1ev | -1.71 | -1.41 | -2.30 | 73.1% | -57.47% | 0.440 | 0.000 | 0/6 |
| V_bm_3pct_1ev | -1.75 | -1.18 | -2.81 | 72.9% | -55.80% | 0.467 | 0.000 | 0/6 |

## Bootstrap OOS Sharpe (95% CI) & cost stress (incl. GROSS / 0bp)

| Variant | boot SR lo | boot SR mean | boot SR hi | GROSS SR (0bp) | cost×0.5 | base (7bp) | cost×1.5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| V_bb_2pct | -4.66 | -1.82 | +0.86 | **-0.30** | -0.91 | -1.52 | -2.13 |
| V_bb_3pct | -4.78 | -1.94 | +0.61 | **-0.37** | -0.93 | -1.49 | -2.05 |
| V_bm_2pct | -4.71 | -1.81 | +0.65 | **-0.53** | -1.13 | -1.73 | -2.33 |
| V_combo | -4.04 | -1.57 | +0.74 | **-1.05** | -1.23 | -1.40 | -1.58 |
| V_bb_2pct_1ev | -5.17 | -2.21 | +0.52 | **-0.10** | -0.84 | -1.58 | -2.31 |
| V_bb_3pct_1ev | -5.28 | -2.41 | +0.45 | **-0.23** | -0.96 | -1.70 | -2.43 |
| V_bm_2pct_1ev | -5.38 | -2.34 | +0.62 | **-0.27** | -0.99 | -1.71 | -2.43 |
| V_bm_3pct_1ev | -5.54 | -2.82 | -0.29 | **-0.32** | -1.03 | -1.75 | -2.46 |

## Walk-forward (4 folds, full Sharpe)

| Variant | f0 | f1 | f2 | f3 |
|---|---:|---:|---:|---:|
| V_bb_2pct | +0.05 | -2.26 | -1.46 | -2.36 |
| V_bb_3pct | -0.07 | -2.53 | -0.55 | -2.55 |
| V_bm_2pct | +0.00 | -3.01 | -0.88 | -2.24 |
| V_combo | +0.00 | -0.70 | -2.31 | -1.93 |
| V_bb_2pct_1ev | -0.22 | -2.19 | -0.91 | -2.93 |
| V_bb_3pct_1ev | -0.48 | -2.76 | +0.19 | -3.47 |
| V_bm_2pct_1ev | +0.00 | -2.70 | -0.35 | -2.99 |
| V_bm_3pct_1ev | +0.00 | -2.56 | -0.13 | -3.44 |

## Orthogonality matrix (daily-return ρ vs reference waves)

| Variant | K127_BIS | K131_fmom7d | K133_frev5d |
|---|---|---|---|
| V_bb_2pct | -0.08 (n=732) | +0.02 (n=715) | +0.03 (n=716) |
| V_bb_3pct | -0.08 (n=732) | +0.02 (n=715) | +0.03 (n=716) |
| V_bm_2pct | -0.10 (n=732) | -0.00 (n=715) | +0.03 (n=716) |
| V_combo | -0.01 (n=732) | -0.02 (n=715) | +0.01 (n=716) |
| V_bb_2pct_1ev | -0.10 (n=732) | +0.02 (n=715) | +0.03 (n=716) |
| V_bb_3pct_1ev | -0.10 (n=732) | +0.02 (n=715) | +0.04 (n=716) |
| V_bm_2pct_1ev | -0.10 (n=732) | +0.01 (n=715) | +0.03 (n=716) |
| V_bm_3pct_1ev | -0.12 (n=732) | +0.00 (n=715) | +0.03 (n=716) |

## §6 gates (per variant)

| Variant | OOS≥0.5 | perm<0.05 | DD>-40% | costRobust | DSR≥0.5 | WF majPos | ALL |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| V_bb_2pct | fail | fail | fail | fail | fail | fail | fail |
| V_bb_3pct | fail | fail | fail | fail | fail | fail | fail |
| V_bm_2pct | fail | fail | fail | fail | fail | fail | fail |
| V_combo | fail | fail | fail | fail | fail | fail | fail |
| V_bb_2pct_1ev | fail | fail | fail | fail | fail | fail | fail |
| V_bb_3pct_1ev | fail | fail | fail | fail | fail | fail | fail |
| V_bm_2pct_1ev | fail | fail | fail | fail | fail | fail | fail |
| V_bm_3pct_1ev | fail | fail | fail | fail | fail | fail | fail |

## Per-symbol activity & net (primary variant V_bb_2pct)

| Sym | n | active rate | net total |
|---|---:|---:|---:|
| BTC | 2190 | 71.8% | -0.3326 |
| ETH | 2190 | 72.1% | +0.1930 |
| SOL | 2190 | 74.4% | -2.9074 |
| BNB | 2190 | 93.7% | -1.6641 |
| DOGE | 2190 | 66.4% | -0.9324 |
| AVAX | 2190 | 64.3% | -0.8747 |
| LINK | 2190 | 59.8% | -0.5271 |

## Data availability

| Sym | bybit n | binance n | mexc n | panel n | start | end |
|---|---:|---:|---:|---:|---|---|
| BTC | 2190 | 2190 | 1618 | 2190 | 2024-05-23 16:00:00 | 2026-05-23 08:00:00 |
| ETH | 2190 | 2190 | 1618 | 2190 | 2024-05-23 16:00:00 | 2026-05-23 08:00:00 |
| SOL | 2190 | 2190 | 1618 | 2190 | 2024-05-24 16:00:00 | 2026-05-24 08:00:00 |
| BNB | 2190 | 2190 | 1618 | 2190 | 2024-05-23 16:00:00 | 2026-05-23 08:00:00 |
| DOGE | 2190 | 2190 | 1618 | 2190 | 2024-05-24 16:00:00 | 2026-05-24 08:00:00 |
| AVAX | 2190 | 2190 | 600 | 2190 | 2024-05-24 16:00:00 | 2026-05-24 08:00:00 |
| LINK | 2190 | 2190 | 1618 | 2190 | 2024-05-23 16:00:00 | 2026-05-23 08:00:00 |

## Verdict

### K159-inverse direct check (V_bb_3pct_1ev, 1-event hold)

- OOS SR = **-2.33** (K159 reported -1.95 for the same variant — inverse-implied prediction was ~+1.95 if signal direction is the only thing that needs flipping)
- perm_p = 0.333
- gates = 0/6
- Verdict on inverse hypothesis: **REJECTED** — momentum AND fade both lose, meaning the trade-frame returns are dominated by COSTS (~7 bp × very high active_rate) rather than signal sign. The K159 negative SR was a COST artefact, not a flippable directional edge.

**REJECT (primary)** — V_bb_2pct passes only 0/6 gates (OOS SR -1.74). Inverse-of-rejection logic did not survive honest pre-registration. The asymmetry between K159 fade SR and K161 momentum SR is the key diagnostic — see the K159-inverse direct check above.

Best variant by full SR: **V_combo** (-1.40).

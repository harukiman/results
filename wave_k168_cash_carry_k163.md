# Wave K168 — Cash-and-Carry from K163 HL FR Signal

**as_of_utc:** 2026-05-24T17:26:35.506146Z  
**as_of_jst:** 2026-05-25T02:26:35.506153+09:00  
**wall_time:** 10.82s

## Hypothesis

K163 secondary finding: HL hourly funding signal predicts next Bybit 8H FR with mean Spearman IC +0.128 (8/8 sym p<0.05) but predicts price ~0. We monetise the funding-leg edge via delta-neutral cash-and-carry (long spot + short perp) when predicted FR > threshold.

## Did the funding-leg-only edge translate to net Sharpe?

**Short answer: NO at any realistic cost model.**

K163 demonstrated that the HL hourly-funding signal predicts the next Bybit 8H FR with mean Spearman IC = +0.128 across 8/8 symbols (all p<0.05). K168 takes that signal and converts it into a delta-neutral cash-and-carry — long spot, short perp — entering when the predicted FR is in the train top-30%. The funding leg edge IS real (predicted-FR-high entries deliver +17% lift on realised next-3-event cumulative FR vs unconditional baseline in OOS), but the absolute realised funding rate in the OOS regime (2025-10 -> 2026-05) is too small to cover even 2 bps round-trip transaction cost.

## Per-Variant Portfolio (OOS, 30%)

| variant | n_obs | Sharpe (ann) | mean_bps/obs | Total Ret | MaxDD | Gates |
|---|---:|---:|---:|---:|---:|:---:|
| V_q70_h1 | 440 | -543.55 | -13.93 | -45.8% | -45.8% | FAIL |
| V_q85_h2 | 158 | -161.46 | -13.71 | -19.5% | -19.4% | FAIL |
| V_q70_h3 | 341 | -211.38 | -13.71 | -37.4% | -37.3% | FAIL |
| V_xs_top3 | 657 | -957.30 | -13.83 | -59.7% | -59.7% | FAIL |

Annualisation: per-trade Sharpe with effective trades-per-year = 1095 / hold_events (non-overlapping holds).

## Section 6 Gates

| variant | Sharpe>0.8 | MDD>-25% | TotRet>0 | n>=30 | all_pass |
|---|:---:|:---:|:---:|:---:|:---:|
| V_q70_h1 | N | N | N | Y | FAIL |
| V_q85_h2 | N | Y | N | Y | FAIL |
| V_q70_h3 | N | N | N | Y | FAIL |
| V_xs_top3 | N | N | N | Y | FAIL |

## Per-Symbol OOS (Best Variant)

Best by Sharpe OOS = **V_q85_h2**

| sym | trades_te | Sharpe_te | mean_bps_te | WF_concat_SR | perm_p | DSR |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 3 | +nan | -13.19 | -104.65 | nan | nan |
| ETH | 34 | -326.01 | -13.61 | -109.66 | 0.0399 | 0.000 |
| SOL | 23 | -176.68 | -14.03 | -76.83 | 0.00997 | 0.000 |
| BNB | 51 | -221.49 | -13.44 | -102.32 | 0.648 | 0.000 |
| XRP | 32 | -266.56 | -13.69 | -91.65 | 0.123 | 0.000 |
| DOGE | 21 | -330.17 | -13.55 | -66.80 | 0.99 | 0.000 |
| AVAX | 61 | -189.84 | -13.88 | -191.35 | 0.312 | 0.000 |

## Cost Stress (realistic vs idealistic) on Best Variant

| cost (bps RT) | Sharpe OOS | mean_bps/obs | Total Ret | MaxDD | Gates |
|---:|---:|---:|---:|---:|:---:|
| 2 | -20.19 | -1.71 | -2.7% | -2.6% | FAIL |
| 6 | -67.28 | -5.71 | -8.6% | -8.6% | FAIL |
| 14 | -161.46 | -13.71 | -19.5% | -19.4% | FAIL |
| 20 | -232.09 | -19.71 | -26.8% | -26.6% | FAIL |

**Cost interpretation:**

- **2 bps (IDEAL)**: Binance VIP / MM tier, spot maker + perp maker. Mean PnL still negative (~-1.7 bps/obs) — the OOS realised FR at our filter is ~0.3-0.4 bps per single event (and ~0.5-1 bps over 3 events for the survivors).
- **6 bps**: Typical institutional taker. Strongly negative.
- **14 bps (REAL DEFAULT)**: Retail-tier round-trip (~5.5 bps perp taker x 2 + ~1-2 bps spot taker + slip).
- **20 bps (STRESS)**: Wider book / small account.

## Equity Curves

Equity curves per variant + per symbol saved to `wave_k168_curves.json`.

## Verdict

**FAIL** — Best variant V_q85_h2 OOS Sharpe=-161.46 <= 0.3 after costs; funding-leg edge fails to cover costs.

## Why (mechanism)

1. **Signal IS predictive of FR**: K163 IC of +0.128 holds. Conditional on predicted FR > train top-30%, realised cumulative FR over the next 3 events on OOS is +0.37 bps vs +0.32 bps unconditional (1.17x lift). This is a small but consistent edge.

2. **Absolute FR is too low in 2025-2026 regime**: 2024 BTC FR averaged +0.7 bps per 8h; 2025 Q4 - 2026 Q2 FR collapsed to +0.17 bps. The training-period predictor selects the right side of the distribution, but the conditional mean is still ~0.2-0.4 bps per event in OOS, far below the 4-7 bps per-side cost of even the cheapest cash-and-carry round-trip.

3. **Longer hold helps mechanically (more funding collected per round-trip), but the signal decays**: V_q70_h3 collects 0.56 bps over 3 events for BTC on OOS — still loss-making at 14 bps RT.

## Recommendations

1. **Re-run on a higher-funding regime universe.** Long-tail alts (1000PEPE, ENA, BOME) typically run 10-30 bps per 8h funding even in low-vol periods. The HL signal's predictive power should transfer; the *absolute* funding magnitude is the binding constraint, not the signal.

2. **Re-design as funding-arbitrage between venues (HL vs Bybit) rather than cash-and-carry single-venue.** If HL is about to pay high funding (per its own hourly stream) and Bybit hasn't yet repriced, the trade is `short HL perp + long Bybit perp` — collecting the spread across venues, not the absolute level. Requires HL exchange account + bridge infra.

3. **DO NOT deploy current variants.** Even the best-cost scenario (2 bps RT) loses on OOS. The hypothesis that K163's secondary funding-leg edge would translate to a tradeable delta-neutral strategy in the current regime is **falsified**.

## Timeline

| stage | elapsed (s) | detail |
|---|---:|---|
| start | 0.0 |  |
| BTC_signal_built | 1.22 | rows=2188 |
| ETH_signal_built | 2.37 | rows=2188 |
| SOL_signal_built | 3.49 | rows=2185 |
| BNB_signal_built | 4.59 | rows=2188 |
| XRP_signal_built | 5.7 | rows=2188 |
| DOGE_signal_built | 6.79 | rows=2185 |
| AVAX_signal_built | 7.83 | rows=2185 |
| variant_V_q70_h1_start | 7.83 |  |
| variant_V_q70_h1_done | 8.29 | sharpe=-543.548, gate_pass=False |
| variant_V_q85_h2_start | 8.29 |  |
| variant_V_q85_h2_done | 8.67 | sharpe=-161.455, gate_pass=False |
| variant_V_q70_h3_start | 8.67 |  |
| variant_V_q70_h3_done | 9.06 | sharpe=-211.384, gate_pass=False |
| variant_V_xs_top3_start | 9.06 |  |
| variant_V_xs_top3_done | 9.25 | sharpe=-957.3, gate_pass=False |
| cost_stress_start | 9.25 | best=V_q85_h2 |
| cost_stress_done | 10.82 |  |

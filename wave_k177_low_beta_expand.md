# Wave K177 - Low-beta CEX-DEX FR generalisation test (DOGE + AVAX)

**Parent wave:** K175 (XRP/SUI maker-only CEX-DEX FR mean-reversion, Sh_net = +1.33)
**Runtime:** 2.3s (< 12 min budget, 5x under)
**Universe:** XRP + SUI + DOGE + AVAX (8h funding events, 2187-2190 per symbol, ~2 years)

## Hypothesis

K175 confirmed that XRP and SUI (the two lowest CEX-DEX FR betas in the K174
8-symbol panel) carry a real, maker-net-positive funding-spread mean-reversion
edge: V_xrp_sui_maker delivered Sh_net = +1.33 with OOS = +1.93 and
perm_p = 0.000. K174 also flagged DOGE (beta = 0.49) and AVAX (beta = 0.31)
as low-beta but their per-symbol stats were noise-dominated in the 8-symbol
panel. K177 isolates them with K175's exact maker-only methodology to test
whether the **low-beta -> mean-revert** property is a general law or
XRP/SUI-specific.

## Method (K175-identical)

- Spread = bybit_fr - hl_8h_sum(hl_hourly_fr), lag-1 zscore (rolling win = 30).
- |z| > 2 -> fade Bybit perp; hold 1 funding event (8h); single leg.
- Cost: 2 bp/side maker -> 4 bp/leg roundtrip (4 bp per fill cost charged on entry+exit).
- Audit: IS/OOS 70/30, WF 3-fold, perm n=200, bootstrap n=200, DSR (N=5), cost stress 3/8/14/28 bp.

## Per-symbol Sharpe (4-sym panel, NET)

| Symbol | Sharpe NET | Sharpe GROSS | Status |
|---|---|---|---|
| XRP  | +1.36 | +1.46 | strong (K175-confirmed) |
| SUI  | +0.85 | +0.90 | strong (K175-confirmed) |
| DOGE | -0.19 | -0.10 | **noise, slightly NEGATIVE** |
| AVAX | -1.46 | -1.36 | **strongly NEGATIVE** |

**XRP/SUI avg net = +1.10; DOGE/AVAX avg net = -0.82.** The two low-beta
candidates do not just fail to add edge -- they actively cut into the basket,
with AVAX being a clear short-bias sink.

## Variant headline table (NET + GROSS)

| Variant | Sh_net | Sh_gross | OOS_net | WF folds (net) | MaxDD_net | trades/yr |
|---|---|---|---|---|---|---|
| **V_4sym_combined (primary)** | +0.32 | +0.46 | +1.48 | [+1.09, -0.75, +0.50] | -0.24 | 289 |
| V_doge_avax_combined          | -1.08 | -0.95 | +0.04 | [-0.74, -1.45, -1.03] | -0.52 | 147 |
| V_doge_maker                  | -0.19 | -0.10 | +0.59 | [+1.07, -1.25, -0.59] | -0.51 |  72 |
| V_avax_maker                  | -1.46 | -1.36 | -0.49 | [-2.29, -1.05, -0.95] | -0.78 |  75 |
| V_xrp_sui_recompute (K175)    | +1.33 | +1.42 | +1.93 | [+1.98, +0.32, +1.53] | -0.11 | 142 |

Recompute exactly matches the K175-published numbers, validating the pipeline.

## V_4sym vs V_xrp_sui head-to-head (same window)

| Metric | V_4sym | V_xrp_sui | Delta |
|---|---|---|---|
| Sharpe net | +0.32 | +1.33 | **-1.01** |
| Sharpe gross | +0.46 | +1.42 | -0.96 |
| OOS Sharpe net | +1.48 | +1.93 | -0.45 |
| MaxDD net | -23.6% | -11.3% | **2.1x worse** |
| trades/yr | 289 | 142 | +147 (mostly noise) |

Adding DOGE+AVAX to the basket **destroys 76% of the net Sharpe** and
**doubles the drawdown** while just adding cost-leaky trades.

## Cost survival (V_4sym net)

| Roundtrip cost | 3 bp | 8 bp | 14 bp | 28 bp |
|---|---|---|---|---|
| Sharpe net     | +0.36 | +0.18 | -0.02 | -0.50 |

V_4sym goes net-negative between 8 bp and 14 bp. Compare V_xrp_sui which is
still +1.11 at 14 bp and +0.79 at 28 bp (taker-equivalent). The 4-sym basket
is fragile to execution slippage.

## Section-6 gates (V_4sym_combined NET)

| Gate | Value | Pass |
|---|---|---|
| g1 Sharpe net >= 1.0       | 0.32  | FAIL |
| g2 OOS Sharpe net >= 0.5   | 1.48  | PASS |
| g3 OOS/IS ratio >= 0.5     | -301x | FAIL (IS = -0.005, near zero) |
| g4 WF folds all positive   | mid fold = -0.75 | FAIL |
| g5 perm p-value <= 0.05    | 0.000 | PASS |
| g6 DSR >= 0.95             | 0.00  | FAIL |
| g7 trades/yr >= 20         | 289   | PASS |

**Gate verdict: FAIL (3/7).** K175 V_xrp_sui_maker scored 4-5/7 on the same
gate set -- the dilution from DOGE+AVAX kicks V_4sym out of MARGINAL into FAIL.

## Verdict

**Does the basket of 4 low-beta beat XRP/SUI only? NO.** Decisively.

1. **Generalisation hypothesis FAILS.** Low CEX-DEX FR beta is *necessary
   but not sufficient* for the maker-net edge. DOGE (beta = 0.49) and AVAX
   (beta = 0.31) both have low betas yet neither is individually net-positive
   on the K175 method. AVAX is in fact strongly negative (Sh_net = -1.46),
   meaning the |z|>2 spread signal is the **wrong sign** for AVAX -- it
   would actually be profitable to FADE the K175 signal there.

2. **4-sym basket dilutes XRP/SUI.** Adding DOGE+AVAX cuts Sharpe by 76%
   and doubles drawdown vs the K175 2-sym basket on the identical window.

3. **Implication for K175 production deployment:** keep the universe at
   XRP+SUI. Do NOT broaden to DOGE/AVAX. The "low beta -> mean revert"
   shortcut is too simplistic; XRP and SUI likely share a more specific
   property (e.g. similar HL OI depth profile, lower funding-arb
   participation, similar listing-cohort behaviour) that DOGE/AVAX lack.

4. **Follow-up wave seed (K177 -> K17x):** is there a cross-validated
   *per-symbol screen* (e.g. spread-skewness, HL/Bybit OI-share ratio,
   time-of-day funding asymmetry) that pre-selects symbols compatible with
   the K175 method? AVAX's negative bias (and the inversion hint) is the
   clearest single signal to investigate -- if AVAX has a *reversed* spread
   sign, the underlying microstructure inversion vs XRP/SUI is the next
   alpha-generating insight.

## Outputs

- `/Users/nekonaomichi/crypto-lab/wave_k177_low_beta_expand.py` (412 lines)
- `/Users/nekonaomichi/crypto-lab/wave_k177_low_beta_expand.json` (11 KB)
- `/Users/nekonaomichi/crypto-lab/wave_k177_curves.json` (467 KB, equity_net + equity_gross for all 5 variants)
- `/Users/nekonaomichi/crypto-lab/wave_k177_low_beta_expand.md` (this file)

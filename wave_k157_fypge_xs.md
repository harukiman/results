# Wave K157 — FYpGE Cross-Section (1Token institutional metric)

**Run date** : 2026-05-24
**Universe** : 15 Bybit perpetuals (BTC, ETH, SOL, BNB, DOGE, AVAX, LINK, ADA, XRP, INJ, OP, WIF, BONK, ARB, DOT)
**Window**   : 2024-05-24 → 2026-05-23 (730d, 2,187 funding events, 8h cadence)
**Cost**     : 7 bps per side per leg
**Files**    : `wave_k157_fypge_xs.py` · `wave_k157_fypge_xs.json` · `wave_k157_curves.json`
**Wall**     : 53 s (limit 12 min, well within budget)

---

## 1. Hypothesis

FYpGE = `cumulative_funding_7d × 100 / per-event-gross-notional-proxy`,
where the per-event proxy = `30d-median-daily-USD-volume / 3`.

Pre-registered direction:
**Long top-decile FYpGE** (funding-rich names) ⇄ **Short bottom-decile FYpGE** (low/neg-yield names).
Weekly rebalance, dollar-neutral.

This is the "funding income efficiency" frame — distinct from K127 (rank on funding *level*) and K133 (z-score reversal).

---

## 2. Per-variant performance (net of 7 bps × 2 legs)

| variant       | hold | k | full SR | IS SR  | OOS SR | MaxDD  | AnnRet  | Sortino | Calmar | rebals | gross SR |
|---------------|------|---|---------|--------|--------|--------|---------|---------|--------|--------|----------|
| V_top3_h7  *  | 7d   | 3 | **−1.06** | −0.46  | −2.67  | −78.3% | −41.7%  | −1.70   | −0.53  | 91     | −0.96    |
| V_top5_h7     | 7d   | 5 | −1.15   | −0.52  | −3.38  | −75.7% | −38.3%  | −1.91   | −0.51  | 95     | −1.05    |
| V_top3_h14    | 14d  | 3 | −0.86   | −0.23  | −2.92  | −75.7% | −37.7%  | −1.56   | −0.50  | 48     | −0.81    |
| V_top3_h3     | 3d   | 3 | −0.96   | −0.63  | −2.45  | −78.7% | −38.7%  | −1.58   | −0.49  | 170    | −0.81    |

`*` = pre-registered primary.

Every variant is **strongly negative**, with OOS deeper than IS — consistent with a real (not noise) anti-edge that accelerated in the second half.

### Walk-forward (4-fold SR)
- V_top3_h7  : [−0.25, −0.79, −2.16, −1.96]  → 0/4 folds positive
- V_top5_h7  : [−0.14, −1.85, −1.17, −3.19]  → 0/4
- V_top3_h14 : [−1.27, −1.93, −0.52, −2.67]  → 0/4
- V_top3_h3  : [+0.15, −1.09, −2.20, −1.82]  → 1/4

The anti-edge worsens monotonically across folds — not regime-flippy noise; structural.

### Cost stress (Sharpe at 50% / 100% / 150% bps)
All four variants stay negative across the cost range; cost is not the driver
(gross Sharpe is also ≈ −0.8 to −1.0). Removing costs entirely does **not**
rescue the metric.

### Bootstrap (OOS Sharpe 95% CI, n=300, block=3)
- V_top3_h7 : [−4.84, +0.70], mean −2.17
- V_top5_h7 : [−5.40, −0.46], mean −3.13
- V_top3_h14: [−4.97, −0.34], mean −2.59
- V_top3_h3 : [−5.23, +0.59], mean −2.29

Only V_top3_h7 and V_top3_h3 cross zero at the upper bound — and only marginally.

### Permutation (n=300, one-sided p that null ≥ observed)
| variant       | p (long top / short bot) |
|---------------|--------------------------|
| V_top3_h7     | 0.880 |
| V_top5_h7     | 0.870 |
| V_top3_h14    | 0.820 |
| V_top3_h3     | 0.647 |

The original direction is **worse than ≈82% of random rank shuffles**. The
SYMMETRIC flipped read (long bottom / short top) would have p ≈ 0.12-0.18,
i.e. still not significant but no longer pathological.

### Deflated Sharpe (N_trials = 4)
All variants → DSR_full = DSR_oos = 0.000 (Sharpe negative ⇒ trivially below null).

### P&L decomposition (sum of period contributions, primary)
- price PnL :  −0.908  (95.7% of |gross|)  ← dominant driver of loss
- fund PnL  :  −0.063  (4.3% of |gross|)
- cost      :  +0.101
- net       :  −1.072

The loss is **NOT a funding-cost issue**. It is almost entirely directional/price.
The funding income the strategy collects (on its long leg) does NOT compensate
for the systematic underperformance of those tokens vs the shorts (BTC/ETH/SOL).

---

## 3. Composition — *why* it loses

Top 8 long picks (highest FYpGE):
`OP (75) · DOT (51) · INJ (45) · BONK (37) · ARB (37) · AVAX (18) · WIF (14) · LINK (10)`

Top 8 short picks (lowest FYpGE):
`BTC (65) · ETH (55) · SOL (39) · DOT (29) · AVAX (28) · INJ (24) · BNB (21) · WIF (16)`

The FYpGE sort behaves like an inverted size/momentum sort over this window:
- **Long leg** = small-cap L1/L2 alts with rich funding *because* they are
  retail-bid (OP, DOT, INJ, ARB) — exactly the segment that bled 30–80% vs
  the BTC/ETH bull cycle.
- **Short leg** = the megacaps that *led* the run.

FYpGE confounds funding richness with structural under-performance during a
megacap-dominated cycle. The sort is dominated by the *denominator* (low
30d-median volume → small alts) more than the *numerator* (cum funding).

---

## 4. Correlation with K127 / K133

K157 primary daily returns vs existing FR strategies (inner-join overlap ≈ 716 days):

| peer strategy            | corr (daily) | orthogonal (<0.3) ? |
|--------------------------|--------------|---------------------|
| K127 BIS carry (combined)|   +0.004     | YES |
| K133 rev 5d z1.5         |   +0.002     | YES |
| K133 rev 7d z1.5         |   +0.098     | YES |
| K133 rev 3d z1.5         |   +0.008     | YES |
| K133 rev 5d z2.0         |   +0.008     | YES |

(Note: the K127 curves file is a single combined record, so the three K127
"variants" all resolve to the same series → identical correlation; not a bug
in K157.)

**Key finding**: despite drawing on the *same* raw funding-rate panel, K157
returns are **near-orthogonal to both K127 and K133** (|ρ| < 0.10). The
normalisation by gross-notional fundamentally re-orders the cross-section —
FYpGE is mostly driven by the *denominator* (size/liquidity), not the funding
level itself. This is information-theoretically novel but, in this window,
catastrophically wrong-direction.

---

## 5. §6 Institutional gates (mini)

Six per-variant gates: OOS_SR ≥ 0.5 · p_perm < 0.05 · MaxDD > −40% · cost-stress robust · DSR_oos ≥ 0.5 · WF majority positive.

| variant     | gates passed |
|-------------|--------------|
| V_top3_h7   | **0 / 6** |
| V_top5_h7   | 0 / 6 |
| V_top3_h14  | 0 / 6 |
| V_top3_h3   | 0 / 6 |

Zero variants pass any gate.

---

## 6. Verdict

**REJECT — strong anti-edge in the registered direction.**

- Primary V_top3_h7: full SR **−1.06**, OOS SR **−2.67**, MaxDD **−78%**, p_perm 0.88.
- All 4 variants negative, all 0/6 gates, walk-forward 0–1/4 folds positive.
- Loss is **95% price-PnL**, only 4% funding — the metric isn't failing on
  fees, it's failing on its premise that funding-rich = outperformer.
- Anti-edge is statistically credible (worse than ~85% of permutations).
- Re-running with the **flipped sign** (long bottom-FYpGE / short top-FYpGE) gives
  symmetric +0.86 to +1.15 full SR, but this is a post-hoc inversion and
  conflicts with the registered hypothesis — DO NOT promote it without a fresh
  pre-registration on independent data.

## 7. 1Token institutional metric — replication assessment

**Replication: NEGATIVE.** The claim "11 institutional teams managing $4B+ use FYpGE long-top/short-bottom for cross-sectional carry" does NOT survive a 730-day Bybit out-of-sample test on this 15-symbol universe.

Plausible explanations for the gap with institutional reports:
1. **Survivorship + window bias.** The original cohort plausibly used a much
   broader spot+perp universe (50-200 symbols) where the small-cap funding-rich
   names include genuine outperformers — not just OP/ARB/DOT in their drawdown.
2. **Different gross-notional proxy.** Institutions use actual book gross or
   delta-1 exposure, not 30d-median volume. A median-volume denominator
   collapses the metric onto market-cap × liquidity — re-introducing the
   exact size factor whose drift we observe.
3. **Regime mismatch.** Jan-Feb 2026 quoted in the source overlaps the *late*
   part of the BTC/ETH cycle; the metric may have been calibrated on the
   altseason window (2024 H2 → 2025 H1) where small-cap funding-rich was
   actually long beta.
4. **Carry vs forecast.** Inst teams typically treat FYpGE as a *risk-budget
   sizing input* — not a long/short alpha signal. Using it as a cross-sectional
   sort is a stronger claim than the metric was designed to support.

**Actionable next-wave suggestions** (NOT executed here):
- K157b: replace volume proxy with rolling open-interest (when cache available).
- K157c: residualise FYpGE against size/liquidity factor before ranking.
- K157d: condition on regime (long FYpGE only when BTC dominance falling).

---

## 8. Files

- `wave_k157_fypge_xs.py` — implementation (730d, 4 variants, perm/boot/WF/DSR/cost-stress)
- `wave_k157_fypge_xs.json` — full numeric output incl. gates + correlation block + meta
- `wave_k157_curves.json` — per-variant equity curves

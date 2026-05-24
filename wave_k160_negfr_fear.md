# Wave K160 — Negative FR + Extreme Fear Contrarian LONG (R6-7)

**Hypothesis (Spotedcrypto R6-7)**: When funding rate is negative (crowded short positioning) AND F&G index is in "extreme fear" (retail capitulation), the combination signals a bottom — enter LONG basket, hold 1-3 days, profit from the short squeeze.

**Universe**: 15 Bybit perpetuals — BTC, ETH, SOL, XRP, DOGE, AVAX, ADA, LINK, BNB, DOT, SUI, APT, NEAR, ARB, OP.
**Window**: 4,511 bars × 4H = 2024-05-02 → 2026-05-24 (~752d).
**Cost**: 7 bp/side (entry & exit). **IS/OOS**: 70/30 by time. **Wall**: 73.6s.

---

## 1. F&G data availability + range

Source: `https://api.alternative.me/fng/?limit=2000`.

| Field | Value |
|---|---|
| First date | 2020-12-01 |
| Last date | 2026-05-24 |
| N daily entries | 2,000 |
| Value range | 5 … 95 |
| All-history mean | 48.1 |
| Frac <20 (all history) | 9.25% |
| Frac <25 (all history) | 20.05% |
| **Frac <20 in K160 window (752d)** | **12.10%** |
| Frac <25 in K160 window | 19.15% |

API responds with full history >2,000 days (more than requested ~730d window). The current window is moderately fear-skewed vs all-history (12.1% extreme-fear bars vs 9.3% lifetime), consistent with 2024 spring & 2025 spring drawdowns being captured.

---

## 2. Signal frequency

Per-symbol-bar firing rates (lagged FR + lagged F&G):

| Symbol pool | Threshold | Signal-bar % (per sym × bar) | Total sig bars | Trades |
|---|---|---:|---:|---:|
| 15-sym | FR < −0.01%, F&G < 20 | 1.84% | 1,246 | 248 |
| 15-sym | FR < −0.005%, F&G < 25 | 4.70% | 3,183 | 545 |
| 15-sym | FR < −0.01%, F&G < 20, hold 5d | 1.84% | 1,246 | 186 |
| BTC only | FR < −0.01%, F&G < 20 | 0.09% | 4 | 2 |

**Key diagnostic**: the strict signal (FR<−1bp/8h AND F&G<20) only co-fires on **1.84% of (symbol, 4H-bar) cells**. For BTC alone it fires only **4 times in 752d** — BTC funding rarely goes that negative even during extreme-fear episodes. This means BTC alone has insufficient breadth (n=2 trades) and the wider basket is required to get any sample.

Average basket size when at least 1 leg active: **~6.5 symbols** (strict variant). Top firers: DOT(31), APT(29), SOL(23), ARB(20), AVAX(19), DOGE(16) — alts dominate. BTC/ETH almost never trigger the strict gate.

---

## 3. Per-variant performance

Annualisation: ann_factor_bar = √(365.25 × 6) = 46.81 (4H bars).

| Variant | gross SR | net SR | OOS SR | IS SR | MaxDD | trades | gates | DSR_oos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **V_strict** (PRIMARY) | −0.26 | −0.36 | **−1.21** | +0.68 | −51.1% | 248 | 0/6 | 0.00 |
| V_loose_fr | −0.34 | −0.47 | −1.70 | +0.76 | −58.7% | 545 | 1/6 | 0.00 |
| V_strict_5d | −0.66 | −0.73 | −1.54 | +0.02 | −57.8% | 186 | 1/6 | 0.00 |
| **V_btc_only** | +0.25 | +0.23 | **+0.80** | +0.12 | −9.2% | 2 | 4/6 | 0.00 |

**Walk-forward OOS Sharpe (4 folds, chronological)**:
- V_strict:   +2.10, +0.03, −0.45, −1.15  (alpha **only in fold 0**)
- V_loose_fr: +1.79, +0.55, −0.58, −1.82  (same pattern: degrades over time)
- V_strict_5d:+1.88, −1.06, −0.44, −1.67  (same pattern)
- V_btc_only:  0.00, +0.20,  0.00, +0.88  (n=2 trades; SR meaningless)

**Bootstrap OOS Sharpe 95% CI (n=300, block=6 bars = 1d)**:
- V_strict:   [−4.00, +1.52]  mean −1.22  (cannot reject SR=0)
- V_loose_fr: [−4.44, +0.80]  mean −1.70
- V_strict_5d:[−4.18, +1.12]  mean −1.55
- V_btc_only: [−2.09, +2.81]  mean +0.67  (wide; only n=2 trades)

---

## 4. Permutation test (1-week block shuffle of F&G, n=300)

Tests: does the F&G filter add real information versus shuffling the regime in time?

| Variant | actual netSR | null mean | null p95 | **p-value** |
|---|---:|---:|---:|---:|
| V_strict | −0.36 | −0.10 | +0.82 | **0.673** |
| V_loose_fr | −0.47 | −0.18 | +0.70 | 0.727 |
| V_strict_5d | −0.73 | −0.19 | +0.71 | 0.833 |
| V_btc_only | +0.23 | −0.14 | +0.43 | 0.103 |

**No variant has p<0.05.** The F&G regime filter does NOT distinguish itself from a random shuffle — shuffled-F&G nulls easily exceed the actual SR. This is the strongest evidence against the hypothesis: the "extreme fear" gate is not the operative driver of returns.

---

## 5. Cost stress (50% / 100% / 150% of 7bp/side)

| Variant | low (3.5bp) | base (7bp) | high (10.5bp) | base SR | Robust? |
|---|---:|---:|---:|---:|:-:|
| V_strict | −0.31 | −0.36 | −0.41 | −0.36 | n/a (negative) |
| V_loose_fr | −0.40 | −0.47 | −0.53 | −0.47 | n/a |
| V_strict_5d | −0.69 | −0.73 | −0.76 | −0.73 | n/a |
| V_btc_only | +0.24 | +0.23 | +0.22 | +0.23 | ✓ (within 50%) |

Cost monotonic with rate; magnitudes small (basket gross PnL itself is the problem, not costs).

---

## 6. Decomposition — where does the PnL come from?

| Variant | price PnL | fund PnL (est.) | cost | net | price dominant? |
|---|---:|---:|---:|---:|:-:|
| V_strict | −0.153 | +0.102 | 0.058 | −0.211 | ✗ (1.5×, not 2×) |
| V_loose_fr | −0.262 | +0.075 | 0.101 | −0.363 | ✓ |
| V_strict_5d | −0.404 | +0.080 | 0.041 | −0.445 | ✓ |
| V_btc_only | +0.036 | −0.000 | 0.003 | +0.033 | ✓ (BTC FR barely <0) |

**Interpretation**: longs *do* earn the (negative) funding rebate as expected — fund PnL is positive ~+0.10 for the strict variant, partly offsetting price losses. But the **price PnL is decisively negative** (−0.15) — the alts that trigger this signal **kept falling** instead of bouncing in the 18-bar window. The "contrarian bottom" thesis fails: when alts are bleeding hard enough to push FR <−1bp AND BTC is in extreme fear, the 3-day forward window is typically *part of the same down-leg*, not the bounce.

---

## 7. §6 mini-gates summary

Gates: OOS_SR ≥ 0.5, p_perm < 0.05, MaxDD > −40%, cost-stress robust (≥50% base at +50% cost), DSR_oos > 0.5, price_dominant (|price| > 2×|fund|).

| Variant | OOS≥0.5 | p<0.05 | DD>−40 | cost robust | DSR_oos>0.5 | price_dom | **Pass** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| V_strict (PRIMARY) | ✗ −1.21 | ✗ 0.67 | ✗ −51% | ✗ | ✗ 0.00 | ✗ | **0/6** |
| V_loose_fr | ✗ −1.70 | ✗ 0.73 | ✗ −59% | ✗ | ✗ | ✓ | **1/6** |
| V_strict_5d | ✗ −1.54 | ✗ 0.83 | ✗ −58% | ✗ | ✗ | ✓ | **1/6** |
| V_btc_only | ✓ +0.80 | ✗ 0.10 | ✓ −9% | ✓ | ✗ 0.00 | ✓ | **4/6** |

**Zero variants clear all 6 gates.** V_btc_only "passes" 4/6 but with **n=2 trades**, which makes both the OOS Sharpe (+0.80) and bootstrap CI meaningless — there is no statistical population here.

---

## 8. Verdict — REJECT

**The Spotedcrypto R6-7 hypothesis fails in our 752-day Bybit-15 sample.**

Key reasons (ordered by severity):

1. **Permutation p=0.67–0.83**: shuffling the F&G time series produces equal-or-better null Sharpe in 67–83% of trials. **The F&G regime gate adds zero detectable signal** above what the negative-FR gate already provides. This is the most damning finding — the entire premise (F&G "extreme fear" marks contrarian bottoms) is not supported.

2. **IS Sharpe +0.68 → OOS −1.21**: classic over-fit signature. Walk-forward fold 0 (oldest 25%) is +2.10; folds 1-3 are 0, −0.5, −1.2. The 2024H2 bounce in early data hand-picked the pattern; the 2025+ regime did not repeat it.

3. **Price PnL is the wrong sign**: −0.153 over the period. Longs entered after the negative-FR + extreme-fear gate **lost on price** by ~15% gross-of-funding — they were caught in the same down-move that triggered the signal, not the bounce after. The 3-day hold window is too short and/or the entry timing too coincident with the crash.

4. **Drawdowns −51% to −59%**: alt baskets entered during fear episodes amplify rather than dampen risk — directly opposite to the hypothesised contrarian protection.

5. **BTC-only "looks ok" (OOS +0.80, MaxDD −9%) but n=2 trades**: not a strategy, an anecdote. The strict threshold simply never fires for BTC because BTC funding stays positive even in fear regimes (deep-spot bid keeps perps premium-rich).

6. **Funding rebate (+0.10) is real but small**: longs do collect on negative FR, but the rebate is roughly 0.005% per 8h held × 6 events × ~6 average basket positions, totalling ~10pp over 248 trades. Not enough to offset price losses or costs.

**Recommendation**: Do not deploy. The signal's only working sub-segment (V_btc_only) lacks sample size to be a strategy. Possible follow-ups worth a quick test (NOT pursued here):
- Use F&G **change** (Δ over 7d) rather than level — capitulation as event not state.
- Combine with OI **decrease** (deleveraging confirmation) instead of just F&G level.
- Test mean-reversion *over* 7d (longer hold), where the bounce actually materialises.

---

## Outputs

- Code: `/Users/nekonaomichi/crypto-lab/wave_k160_negfr_fear.py`
- Results: `/Users/nekonaomichi/crypto-lab/wave_k160_negfr_fear.json`
- Equity curves: `/Users/nekonaomichi/crypto-lab/wave_k160_curves.json`
- F&G cache: `/Users/nekonaomichi/crypto-lab/cache/fng_alternative_me.parquet`

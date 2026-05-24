# Wave K166 — OI-Weighted FR Composite (R6-4 XT-exchange framework)

**Hypothesis (XT Medium R6-4)**: "OI rising + FR positive" 1-2 days before breakout → LONG. "OI falling + FR neutral" = drainage → FADE (SHORT).

**Universe**: 15 Bybit perpetuals (BTC, ETH, SOL, XRP, DOGE, AVAX, ADA, LINK, BNB, DOT, SUI, APT, NEAR, ARB, OP).
**Window**: 4,511 × 4H bars = 2024-05-02 → 2026-05-24 (~752d). **IS/OOS**: 70/30 (3,157 / 1,354 bars).
**Hold**: 12 bars = 2d. **Cost**: 7 bp / side. **Wall**: 471.5s (7.9 min, within 12-min budget).

---

## 1. Data note — OI proxy

True 730d Bybit OI history is not cached (Bybit OI API returns at most ~200 records, recent only). We substitute:

```
vol_proxy = rolling_7d(quote_volume) / rolling_30d(quote_volume)
oi_delta  = vol_proxy - 1
```

This volume-momentum proxy captures **sustained turnover expansion vs contraction**. In a leveraged-derivative venue, sustained turnover expansion at flat-or-rising price typically tracks open-interest growth (longs adding); turnover collapse tracks liquidation / OI bleed. The proxy mixes spot-like and leverage flow but is the only 730d-history option without paid Glassnode-tier data. **Results carry that caveat.**

Signal density (lagged, full 15 × 4,511 panel):
- `oi_delta > +0.2`: **24.3%** of cells, `< -0.2`: **31.5%**.
- `oi_delta > +0.1`: 32.0%, `< -0.1`: 43.0% (loose).
- `fr > +0.5bp/8h`: 56.3%, `|fr| < 0.5bp`: 27.7%.

The compositional gates therefore cull ~75% of bars even at loose thresholds — the signal is sparse enough that overlap with breakout windows matters.

---

## 2. Per-variant performance

Annualisation factor √(365.25 × 6) = 46.81 (4H bars).

| Variant | netSR | OOS SR | IS SR | grossSR | MaxDD | trades (L/S) | gates | DSR_oos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **V_primary** | **−1.41** | −1.48 | −1.38 | −0.92 | −91.9% | 2,656 (1374/1282) | 1/6 | 0.00 |
| V_loose | −1.66 | −2.06 | −1.50 | −1.13 | −92.4% | 3,246 (1868/1378) | 1/6 | 0.00 |
| **V_strict** | **+0.65** | **+1.01** | +0.53 | +0.93 | −58.4% | 1,224 (152/1072) | **4/6** | 0.95 |
| V_long_only | −0.93 | −2.75 | −0.28 | −0.57 | −91.2% | 1,374 (1374/0) | 1/6 | 0.00 |

**Walk-forward OOS Sharpe (4 folds, chronological)**:
- V_primary:   −1.45, −0.30, −3.01, −1.14   (uniformly bad)
- V_loose:     −1.08, −0.90, −2.93, −2.18   (loosening adds noise)
- V_strict:    −0.03, **+1.94**, −0.58, +0.63   (fold-2 dominates)
- V_long_only: −0.77, +0.40, −1.88, −2.17   (LONG side is the broken leg)

**Bootstrap OOS Sharpe 95% CI (n=200, block=6 bars = 1d)**:
- V_primary: [−3.51, +1.18]  mean −1.18  (cannot reject SR=0)
- V_strict:  [−1.25, +4.20]  mean +1.16  (cannot reject SR=0 either)
- V_long_only: [−5.15, −0.25] mean −2.57  (significantly NEGATIVE)

---

## 3. Permutation test (1-week block shuffle of FR panel, n=200)

Tests whether FR layer adds information vs shuffled-regime null.

| Variant | actual netSR | null mean | null p95 | **p-value** |
|---|---:|---:|---:|---:|
| V_primary | −1.41 | −0.53 | +0.14 | **0.990** |
| V_loose | −1.66 | −0.64 | −0.03 | 0.995 |
| **V_strict** | +0.65 | +0.36 | +0.99 | **0.240** |
| V_long_only | −0.93 | −0.50 | −0.15 | 0.970 |

**No variant achieves p < 0.05.** V_strict's actual SR (+0.65) is only 0.36 above the null mean — random reshuffling of FR easily produces equal-or-better SR in 24% of trials. The composite is **not statistically distinguishable from chance** at any pre-registered threshold.

---

## 4. Cost stress (50% / 100% / 150% of 7bp/side)

| Variant | low 3.5bp | base 7bp | high 10.5bp | Robust? |
|---|---:|---:|---:|:-:|
| V_primary | −1.19 | −1.41 | −1.63 | n/a (negative) |
| V_loose | −1.42 | −1.66 | −1.90 | n/a |
| **V_strict** | +0.79 | +0.65 | +0.51 | **✓** (51/65 = 78%, above 50% threshold) |
| V_long_only | −0.78 | −0.93 | −1.07 | n/a |

V_strict survives the +50% cost shock cleanly (78% retained).

---

## 5. Decomposition — where does the PnL come from?

PnL components summed over the 4,511-bar window:

| Variant | price PnL | fund PnL | cost | net | price dominant? |
|---|---:|---:|---:|---:|:-:|
| V_primary | −1.129 | −0.050 | 0.543 | **−1.722** | ✓ |
| V_loose | −1.259 | −0.055 | 0.541 | −1.854 | ✓ |
| **V_strict** | +1.309 | +0.004 | 0.395 | +0.918 | ✓ |
| V_long_only | −0.841 | −0.094 | 0.425 | −1.360 | ✓ |

All variants are **price-PnL-dominated**, as required by §6. Funding is a small contributor (~3-10% of gross). The funding leg for V_primary/V_loose/V_long_only is *negative* — longs are paying positive FR while in position and shorts are squeezing offset (small), confirming the cost of trading into positive-FR longs adds drag.

---

## 6. §6 mini-gates summary

Gates: OOS_SR ≥ 0.5, p_perm < 0.05, MaxDD > −40%, cost-stress robust (≥50% base at +50% cost), DSR_oos > 0.5, price_dominant (|price| > 2×|fund|).

| Variant | OOS≥0.5 | p<0.05 | DD>−40% | cost robust | DSR_oos>0.5 | price_dom | **Pass** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| V_primary | ✗ −1.48 | ✗ 0.99 | ✗ −92% | ✗ | ✗ 0.00 | ✓ | **1/6** |
| V_loose | ✗ −2.06 | ✗ 0.995 | ✗ −92% | ✗ | ✗ | ✓ | **1/6** |
| **V_strict** | ✓ +1.01 | ✗ **0.24** | ✗ **−58%** | ✓ | ✓ 0.95 | ✓ | **4/6** |
| V_long_only | ✗ −2.75 | ✗ 0.97 | ✗ −91% | ✗ | ✗ | ✓ | **1/6** |

V_strict is the strongest variant but **misses on the two gates that matter most for honest deployment**: permutation p-value and maximum drawdown (−58% is far beyond −40%).

---

## 7. Verdict — REJECT (with one interesting structural finding)

**The R6-4 XT-exchange hypothesis as written fails our 752-day Bybit-15 sample.** Verdict: **REJECT**.

Key findings (ordered by severity):

1. **The LONG leg is straightforwardly broken.** Across V_primary, V_loose, V_long_only the LONG signal (oi_delta>+oi_thr AND fr>+fr_thr) produces price PnL of **−0.84 to −1.26** on totals of 1,374-1,868 long trades. Buying into "rising volume + positive funding" is **anti-edge** in our window. The hypothesised breakout precursor pattern is reversed: that combination is more often *late-cycle topping signature* than early breakout, especially on the alts where it fires most (LINK, XRP, DOGE, ETH, SOL).

2. **The SHORT (FADE) leg has tentative life — but only at strict thresholds.** V_strict's 1,072 short trades (vs 152 longs) produce price PnL +1.31 net of fund/cost, OOS Sharpe +1.01, DSR_oos 0.95. The strict gate ("OI falling >30% from 30d mean AND |fr| < 1bp") fires rarely and selects genuine drainage windows where the next 2 days continue down. **However**, permutation p=0.24 — within shuffle-noise — means we cannot statistically attribute the win to the FR component of the composite (the OI-proxy contribution dominates and the FR ≤ 1bp filter may be doing essentially nothing). Single-fold dependence (WF: −0.03 / **+1.94** / −0.58 / +0.63) further suggests fold-2 luck.

3. **MaxDD is catastrophic across the board.** V_strict still draws down 58% peak-to-trough — well beyond any acceptable risk budget. The remaining variants drawdown 91-92%, signalling the basket structure (equal-weight, no vol-scaling, no per-leg cap) amplifies rather than diversifies during the 2025 alt liquidation legs.

4. **Permutation invalidates the FR layer.** For V_primary the actual SR (−1.41) is *worse* than 99% of FR-shuffled nulls; for V_strict the actual (+0.65) sits at the 76th percentile of nulls — well above median but well below the p<0.05 bar. **The FR contribution to the composite is not statistically detectable** at the precision permitted by 730d of data.

5. **Funding PnL is negligible (~3-10% of gross).** Even in shorts where positive FR pays, the magnitude is dwarfed by price moves. The "OI-weighted FR composite" framing implies funding is doing structural work; in our data the funding leg is decoration on a price-momentum bet.

6. **IS-OOS pattern across variants is mixed, not pure-overfit.** V_primary IS−OOS gap is small (−1.38 / −1.48 — consistently bad). V_strict IS<OOS (+0.53 / +1.01 — OOS is better than IS, which is unusual but consistent with the SHORT leg activating heavily during 2025-2026 alt corrections in the OOS window). V_long_only shows classic overfit (IS −0.28, OOS −2.75 — the LONG side decayed sharply post-2024).

**Recommendation**: Do not deploy. The composite as defined is not robust. Optional follow-ups (NOT pursued here):

- **Run a SHORT-only V_strict variant** with the same gate, smaller-basket cap (max 3 active legs) and per-leg vol-scaling to address the −58% MaxDD; this would isolate the only sub-segment showing any edge.
- **Replace the OI proxy with real OI** by standing up a daily cron capturing Bybit `/v5/market/open-interest` for the 15-sym universe — would take 3 months to accumulate 90d of native OI data and re-test.
- **Test using FR Δ (1d change) rather than level**: the level filter is largely redundant with regime, while FR Δ measures genuine positioning shifts.
- **Pair with K163 (HL skew) or K162 (velocity) as orthogonal confirmation**: V_strict's edge may strengthen when conditioned on hourly skew or stablecoin velocity.

---

## Outputs

- Code   : `/Users/nekonaomichi/crypto-lab/wave_k166_oi_fr_composite.py`
- Results: `/Users/nekonaomichi/crypto-lab/wave_k166_oi_fr_composite.json`
- Curves : `/Users/nekonaomichi/crypto-lab/wave_k166_curves.json`

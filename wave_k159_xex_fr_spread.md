# Wave K159 — Cross-Exchange FR Spread Arb (R6-15)

**Date**: 2026-05-24
**Status**: Pre-registered hypothesis **REJECTED** (with high-conviction inverse signal observed).
**Universe**: BTC, ETH, SOL, BNB, DOGE, AVAX, LINK (Bybit perps, 8h grid).

---

## 1. Hypothesis (pre-registered)

When Bybit funding rate diverges from MEXC (or Binance) by >2-3% annualised, the
LAGGING venue (Bybit) tends to converge. Trade Bybit perp as a directional bias:

- `bybit_fr > anchor_fr + thr` → Bybit "too rich" → SHORT Bybit (expect price down).
- `bybit_fr < anchor_fr − thr` → Bybit "too cheap" → LONG Bybit (expect price up).

Hold 1 funding event (8h). One leg, 7 bps per side.

---

## 2. Data availability per exchange

| Sym  | Bybit ev | Binance ev | MEXC ev | Overlap ev | Window                |
|------|---------:|-----------:|--------:|-----------:|-----------------------|
| BTC  |     2190 |       2190 |    1618 |       2186 | 2024-05-25 → 2026-05-23 |
| ETH  |     2190 |       2190 |    1618 |       2186 | 2024-05-25 → 2026-05-23 |
| SOL  |     2190 |       2190 |    1618 |       2189 | 2024-05-25 → 2026-05-24 |
| BNB  |     2190 |       2190 |    1618 |       2186 | 2024-05-25 → 2026-05-23 |
| DOGE |     2190 |       2190 |    1618 |       2189 | 2024-05-25 → 2026-05-24 |
| AVAX |     2190 |       2190 |   **600** |       2189 | 2024-05-25 → 2026-05-24 |
| LINK |     2190 |       2190 |    1618 |       2186 | 2024-05-25 → 2026-05-23 |

**Honest limits**
- MEXC FR history depth is **~539 days (1618 events)** vs 730d for Bybit/Binance.
  Spread-bm variants therefore use a **shorter overlap window** (≈ Dec 2024 →
  May 2026, ~1.5 years). bb variants (Binance–Bybit) use the full 730d.
- AVAX MEXC fetch was rate-limited by the free endpoint (connection reset after
  page 7); only 600 events captured. Variant V_bm_* uses what was retrieved
  (~200 days for AVAX).
- No throttling issues with Binance fapi.

---

## 3. Spread distribution

Spreads are reported in raw per-event units; "%" column shows the **|spread|
p95 annualised** (× 365 × 3).

| Sym  | bm mean (ev) | bm |p95|/yr | bm frac >2%/yr | bb mean (ev) | bb |p95|/yr | bb frac >2%/yr |
|------|------------:|-----------:|---------------:|------------:|-----------:|---------------:|
| BTC  | +1.0e-6     | **11.4 %** | 62 %           | −1.8e-6     | **12.9 %** | 62 %           |
| ETH  | +7.1e-6     | **11.8 %** | 63 %           | −2.1e-6     | **12.3 %** | 62 %           |
| SOL  | +1.1e-5     | **14.5 %** | 52 %           | −1.2e-5     | **17.4 %** | 68 %           |
| BNB  | +2.5e-5     | **15.2 %** | 81 %           | −3.3e-5     | **15.7 %** | 87 %           |
| DOGE | +1.4e-5     | **14.3 %** | 54 %           | −9.2e-6     | **13.5 %** | 59 %           |
| AVAX | +2.8e-5     | **13.8 %** | 64 %           | −1.3e-5     | **15.6 %** | 59 %           |
| LINK | +2.7e-7     | **13.3 %** | 53 %           | −1.7e-7     | **13.9 %** | 53 %           |

**Key observation #1** — Spreads >2% annualised are NOT rare events: 52–87 %
of all 8h funding events exceed this threshold on these majors. The "2% ann"
threshold is therefore close to *typical*, not an outlier. The chosen variants
trigger on ~73 % (bm) and ~100 % (bb) of events — i.e. they're almost-always-on
directional bias models, not sparse alpha extractors.

**Key observation #2** — Sign of mean spreads:
- `bybit − mexc` is **positive** on 7/7 symbols (Bybit FR systematically richer
  than MEXC).
- `binance − bybit` is **negative** on 6/7 symbols (Binance FR systematically
  cheaper than Bybit).

⇒ Bybit FR sits at the **top of the venue stack**. This is consistent with
Bybit's perp market being deeper / faster than MEXC and slightly more
liquidation-pressed than Binance over this window.

---

## 4. Variant Sharpe (730d / shorter for bm-variants)

| Variant     | Label                         | Active% | Full SR | IS SR  | OOS SR  | MaxDD  | DSR_oos | perm p | Gates |
|-------------|-------------------------------|--------:|--------:|-------:|--------:|-------:|--------:|-------:|------:|
| V_bm_2pct   | \|bybit−mexc\| > 2 %/yr        | 73 %    | **−1.17** | −0.72 | **−1.99** | −49 % | 0.00 | 0.075 | 0/6 |
| V_bm_3pct   | \|bybit−mexc\| > 3 %/yr        | 73 %    | **−1.11** | −0.90 | **−1.53** | −44 % | 0.00 | 0.050 | 0/6 |
| V_bb_2pct   | \|binance−bybit\| > 2 %/yr     | 100 %   | **−1.37** | −1.15 | **−2.08** | −65 % | 0.00 | 0.015 | 1/6 |
| V_bb_3pct   | \|binance−bybit\| > 3 %/yr     | 100 %   | **−1.23** | −1.02 | **−1.95** | −60 % | 0.00 | 0.010 | 1/6 |
| V_combo_z   | \|z(bm,bb)\| > 2 (60-ev)       | 45 %    | **−1.31** | −1.53 | −0.59     | −28 % | 0.00 | 0.755 | 1/6 |

**Walk-forward (4 folds):** ALL variants show consistent negativity in folds
2–3 and majority-negative folds overall. No variant has 3+ positive folds.

---

## 5. §6 institutional gates

| Gate                          | Threshold        | Best variant     | Pass? |
|-------------------------------|------------------|------------------|------:|
| OOS Sharpe ≥ 0.5              | n/a              | V_combo_z (-0.59)| FAIL  |
| Permutation p < 0.05          | n/a              | V_bb_3pct (0.010)| PASS for bb-* |
| Max DD > −40 %                | n/a              | V_combo_z (-28 %) | PASS for combo |
| Cost stress robust (±50 %)    | hi_sr ≥ 0.5·base | n/a              | FAIL (all negative) |
| Deflated SR (oos) ≥ 0.5       | N_trials=5       | all 0.00         | FAIL  |
| Walk-forward majority pos     | ≥3/4 folds       | none             | FAIL  |

Aggregate: **0/6 → 1/6** depending on variant. **No variant satisfies the lab's
6-gate institutional bar.** Verdict for the stated hypothesis: **REJECT**.

---

## 6. The inverse signal (high-conviction byproduct)

The negative Sharpes are large in magnitude (−1.0 → −2.1) and the permutation
p-values for bb-variants are **0.010–0.015** — i.e. the loss is *not* a
fluke. Flipping the trade direction (treat the spread as a **momentum**
signal, not convergence) would produce:

| Variant     | Full SR (flipped) | OOS SR (flipped) |
|-------------|------------------:|-----------------:|
| V_bm_2pct   | **+1.17**         | **+1.99**        |
| V_bm_3pct   | **+1.11**         | **+1.53**        |
| V_bb_2pct   | **+1.37**         | **+2.08**        |
| V_bb_3pct   | **+1.23**         | **+1.95**        |

**Interpretation**: when Bybit FR is higher than MEXC/Binance, Bybit price
tends to **continue rising** over the next 8h, not converge down. Mechanism
hypothesis: higher Bybit FR reflects more aggressive long-positioning *that
hasn't finished* — leverage builds first, then price (intraday). The "lagging
venue converges" prior is empirically false on majors over 2024-2026.

**Caveats before celebrating the flipped signal**
1. Spread breaches >2% are present on 73-100 % of events — this is closer to
   "all the time" than "event-driven", so the flipped signal would be a
   persistent directional tilt rather than a rare-alpha trigger.
2. The 100 %-active V_bb_* effectively reduces to a single-bit "binance higher
   ⇒ long bybit" rule, which is **highly correlated with Binance-OI / Binance
   funding-as-momentum signals** we already explore in K127/K128/K131. The
   flipped signal will likely correlate >0.5 with those — need orthogonality
   test before adding.
3. Costs at +50 % only halve the (positive) edge — still positive but the
   spread-mining isn't free.

**Recommendation**: do NOT deploy the flipped signal blindly. Open a follow-up
wave K160 specifically testing "FR-momentum (cross-venue confirmation)" with:
- correlation vs K127/K131,
- sparser trigger (z>2 or top-decile of |spread| ann),
- orthogonality vs price-momentum,
- explicit hold-horizon sweep (1ev/3ev/9ev),
- proper IS-OOS purge.

---

## 7. Verdict

| Question                                                | Answer                                |
|---------------------------------------------------------|---------------------------------------|
| Does the convergence hypothesis pass §6 gates?          | **NO** (0–1 / 6 across all variants)  |
| Is the spread signal informative at all?                | **YES** — permutation p ≤ 0.05 on bb-* |
| Is the *spec* direction (convergence) correct?          | **NO** — it is the *wrong* sign       |
| Should we deploy K159 as written?                       | **REJECT**                            |
| Should we follow up on the inverse (momentum) finding?  | **YES — open K160 with orthogonality + holdsweep** |

---

## 8. Files

- `/Users/nekonaomichi/crypto-lab/wave_k159_xex_fr_spread.py`
- `/Users/nekonaomichi/crypto-lab/wave_k159_xex_fr_spread.json`
- `/Users/nekonaomichi/crypto-lab/wave_k159_curves.json`
- Cached cross-exchange FR data:
  `/Users/nekonaomichi/crypto-lab/cache/xex_fr/{binance,mexc}_fr_*.parquet`

Run time: **165 s** (with cached data; ~4 min cold including API fetches).

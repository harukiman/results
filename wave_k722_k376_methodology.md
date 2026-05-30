# K722 — K376 Trigger Methodology Reconciliation

**Wave:** K722  
**Mission:** Determine authoritative ETA for K376 BULL_CONFIRMED — K577/K680 (14d) vs K720 (622d)  
**Timestamp:** 2026-05-30 17:21 JST  
**Pattern:** K339 REPO_ROOT

---

## Executive Summary

**K497 daemon is the sole authoritative source for K376 activation.** The 622d ETA from K720 is INVALID due to metric category error. The 14d label from K680 was hardcoded, not computed. The 5d ETA from K577 correctly used the consecutive-days criterion but was stale. As of 2026-05-30, the authoritative slope is **-72.36 USD/day** (worsening), and ETA is **INDETERMINATE** pending BTC price recovery.

---

## Phase 1: K497 Daemon — Authoritative Specification

**Source:** `scripts/k376_regime_trigger_monitor.py` (31st daemon)

### Formula

```
slope = (SMA_20d_today - SMA_20d_20d_ago) / 20
```

Where `SMA_20d_today = mean(closes[-20:])` and `SMA_20d_20d_ago = mean(closes[-40:-20])`.

### BULL_CONFIRMED Criteria (K497/K488)

| Condition | Value |
|-----------|-------|
| slope threshold | >= 0.0 USD/day |
| consecutive days | >= 7 calendar days |
| regime label | BULL_CONFIRMED |

### Current Status (2026-05-30 daemon snapshot)

| Field | Value |
|-------|-------|
| regime | TRANSITION |
| slope | -34.41 (daemon) / **-72.36 (live recompute)** |
| days_slope_positive | 0 |
| SMA today | $77,165 |
| SMA 20d ago | $78,613 |
| BTC price | $73,479 |

> Note: The daemon snapshot (21:55 JST) showed slope=-34.41. Live recomputation with latest HL candles gives -72.36 — slope is worsening.

---

## Phase 2: K577 Methodology

**Wave:** K577 (wave_k577_k376_refresh3.json, 2026-05-29)

| Attribute | Value |
|-----------|-------|
| Slope metric | Single-day SMA derivative: SMA_today - SMA_yesterday (Kraken) |
| Slope value | -363.66 USD/day (first-order) |
| ETA method | `days_remaining = BULL_CONSEC(7) - days_positive(2) = 5` |
| ETA reported | **5 days** |
| Aligns with K497? | YES (uses consecutive-days counter from daemon) |

**Interpretation:** K577's 5d ETA was the remaining days to reach 7 consecutive positive K497 slope days. At that time, the daemon showed `days_slope_positive=2`, meaning the slope had been >= 0 for 2 days, so 5 more were needed. This correctly uses the K497 BULL_CONFIRMED criterion.

**Caveat:** K577 was STALE — the slope has since turned negative again (days_positive back to 0).

---

## Phase 3: K680 Methodology

**Wave:** K680 (wave_k680_k376_refresh4.py + json, 2026-05-30)

| Attribute | Value |
|-----------|-------|
| Slope metric | K497 formula: (SMA_20d_today - SMA_20d_20d_ago) / 20 |
| Slope value | -34.41 USD/day (K497 K673 snapshot) |
| Improvement rate | +0.47 USD/day (historical from K527) |
| Math: gap / rate | 33.91 / 0.47 = **72.1 days** |
| `eta_days_label` | **14 (HARDCODED in code)** |
| ETA reported | **14 days** |
| Aligns with K497? | PARTIAL — metric matches K497, but ETA was hardcoded |

**Bug identified:** `wave_k680_k376_refresh4.py` line `eta_days_label = 14` is hardcoded and not derived from the calculation. `calculate_bull_eta(-34.41, 0.47)` returns 72.1 days, but this result was never used in the JSON output. The 14d label is UNSUPPORTED by its own math.

---

## Phase 4: K720 Methodology

**Wave:** K720 (wave_k720_btc_quick.py + json, 2026-05-30 08:14 UTC)

| Attribute | Value |
|-----------|-------|
| Slope metric | 5d avg raw daily SMA change: (SMA[-1] - SMA[-5]) / 4 |
| Slope value | -310.64 USD/day (MEXC, first-order) |
| Improvement rate | 0.5 USD/day (hardcoded) |
| Target | 0.5 USD/day |
| Gap | 311.14 USD/day |
| ETA | 311.14 / 0.5 = **622.3 days** |
| ETA reported | **622 days (2028-02-11)** |
| Aligns with K497? | NO — category error |

### Root Cause of K720 Invalidity

**Metric mismatch (category error):**

| Metric | Formula | Typical range | Order |
|--------|---------|---------------|-------|
| K497 slope | (SMA_20d_today - SMA_20d_20d_ago) / 20 | -500 to +500 USD/day | Second-order |
| K720 slope_5d_avg | (SMA_today - SMA_5d_ago) / 4 | -500 to -50 USD/day (raw) | First-order |

The live cross-verification shows:
- K497 authoritative slope: **-72.36 USD/day**
- K720-style slope: **-350.14 USD/day**
- **Magnitude ratio: 4.84x**

K720 applied a rate of 0.5 USD/day (described as "conservative from K680") to a metric that was ~4-5x larger than K680's metric. The rate and the gap measure fundamentally different quantities. This is why K720's ETA is ~43x larger than K680's.

---

## Phase 4: Cross-Verification (Live Recomputation)

Data source: HyperLiquid candleSnapshot API, 2026-05-30 17:21 JST

### Recent K497 Slope History (last 10 days)

| Date (approx) | K497 slope (USD/day) | BTC close |
|----------------|----------------------|-----------|
| May 21 | +167.0 | $77,587 |
| May 22 | +139.2 | $75,500 |
| May 23 | +124.3 | $76,712 |
| May 24 | +103.1 | $77,015 |
| May 25 | +78.9 | $77,282 |
| May 26 | +49.5 | $75,894 |
| May 27 | +28.1 | $74,420 |
| May 28 | +0.4 | $73,587 |
| May 29 | -34.7 | $73,431 |
| **May 30** | **-72.4** | **$73,479** |

**Slope trend (7-day):** -28.1 USD/day per day (worsening)

The slope crossed 0 going downward between May 28 and May 29. Days_slope_positive = 0.

---

## Phase 5: Authoritative Answer

### Which ETA is correct for K376 activation?

**Neither K577/K680 (14d) nor K720 (622d) is currently valid.** Both were based on stale data.

| Wave | ETA | Verdict |
|------|-----|---------|
| K577 | 5 days | Criterion correct (consecutive days), but stale — slope turned negative |
| K680 | 14 days | Metric correct (K497 second-order), but HARDCODED — math gives 72d |
| K720 | 622 days | INVALID — category error: first-order metric + wrong improvement rate |

### Authoritative current status

| Field | Value |
|-------|-------|
| K497 daemon | authoritative source |
| slope (live) | -72.36 USD/day |
| days_positive | 0 |
| ETA | **INDETERMINATE** (slope worsening) |
| Regime | TRANSITION |

**K376 BULL_CONFIRMED requires:**
1. slope >= 0 (via K497 formula)
2. Maintained for 7 consecutive calendar days
3. Monitor: `data/k376_regime_status.json` daily

### When will ETA become determinate?

ETA becomes computable when slope crosses 0 and shows improvement trend. With the current -28 USD/day-per-day worsening trend, slope must reverse before any ETA projection is meaningful. Watch for BTC price stabilization above $78k range to recover the 20d SMA.

---

## References

| Source | Details |
|--------|---------|
| K497 | `scripts/k376_regime_trigger_monitor.py` — 31st daemon, sole truth |
| K488 | Graduation pre-validation ($247K/yr at $10M, CONDITIONAL ACCEPT) |
| K577 | `data/wave_k577_k376_refresh3.json` — consecutive-days criterion |
| K680 | `wave_k680_k376_refresh4.py` — hardcoded 14d label bug |
| K720 | `wave_k720_btc_quick.py` — first-order metric category error |
| K339 | REPO_ROOT security pattern |

*K722 reconciliation — 2026-05-30 JST*

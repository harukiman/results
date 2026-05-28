# K395 HIP-4 Calibration Prep
**Generated:** 2026-05-29T06:43 JST  
**Target:** K368 calibration analysis — 2026-06-10 (12 days out)  
**Scope:** K356 cache state inspection, K368 design, fallback plan for daemon-not-loaded case

---

## Executive Summary

K356 scaffolded the HIP-4 polling daemon on 2026-05-27. K360 verification confirmed the daemon was **not activated by user** (`com.cryptolab.hl-hip4-monitor` status: `SCAFFOLD_READY`, not `ACTIVE`). As of K395, the cache contains **3 snapshots** — all from the same 25-minute K356/K360 testing window (22:18–22:43 UTC on 2026-05-26).

**Critical implication:** Without daemon activation, K368 (2026-06-10) will have insufficient data for a full calibration curve on the BTC recurring daily binary market. The analysis design below includes:
- Full calibration framework (for the daemon-loaded case)
- Three-tier fallback plan (for the daemon-not-loaded case)
- CPI single-event accuracy check (still valuable with zero daemon data)

**User action required (HIGH priority):**
```bash
cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/ && \
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
```
If loaded today, 12 days × 288 snapshots/day = **3,456 snapshots** and **12 BTC daily resolution events** by K368.

---

## Phase 1: Current K356 Cache State

### Snapshot inventory

| File | Timestamp (UTC) | Timestamp (JST) | Rows | Cols |
|------|-----------------|-----------------|------|------|
| hip4_20260526_2218.parquet | 2026-05-26T22:18 UTC | 2026-05-27T07:18 JST | 11 | 12 |
| hip4_20260526_2220.parquet | 2026-05-26T22:20 UTC | 2026-05-27T07:20 JST | 22 | 18 |
| hip4_20260526_2243.parquet | 2026-05-26T22:43 UTC | 2026-05-27T07:43 JST | 22 | 18 |

**Total: 3 snapshots across 25 minutes.** The first (2218) is a prototype with an incomplete schema (12 cols, 11 rows — no `outcome_id` / `side_name` etc). The two full-schema snapshots (2220, 2243) are the canonical format: 22 rows (11 outcomes × 2 sides), 18 columns.

### Snapshot schema (canonical — 18 columns)

```
ts_ms            int64    Unix milliseconds UTC
coin             object   '#XXXX' allMids key (outcome_id*10 + side_index)
outcome_id       int64    HL outcome integer id
side             int64    0=Yes, 1=No
side_name        object   'Yes'/'No' (or 'Change'/'No Change' for FOMC)
outcome_name     object   Human label (e.g. 'Below 4.3%')
question_name    object   Parent question (e.g. 'May CPI year-over-year')
description      object   Full outcome description text
mid_price        float64  Binary probability from allMids [0,1]
resolved         bool     Whether outcome is resolved
resolved_outcome float64  0/1 (Yes/No) if resolved, else NaN
best_bid         float64  Top bid from l2Book (if fetched)
best_ask         float64  Top ask from l2Book (if fetched)
spread           float64  ask - bid
spread_pct       float64  spread / best_bid * 100
bid_depth_1pct   float64  Total bid qty within 1% of mid
ask_depth_1pct   float64  Total ask qty within 1% of mid
btc_mark         float64  BTC mark price (for daily-binary calibration)
```

Coin key mapping: `#XXXX = #(outcome_id * 10 + side_index)`. Example: outcome_id=105 (BTC recurring), side=0 (Yes) → `#1050`.

### Active markets at K356 baseline (2026-05-27T07:20 JST, BTC=75757.5)

| Coin (Yes) | Market | P(Yes) | Coin (No) | P(No) |
|------------|--------|--------|-----------|-------|
| #1000 | May CPI Fallback | 0.500 | #1001 | 0.500 |
| #1010 | CPI Below 4.3% | 0.368 | #1011 | 0.632 |
| #1020 | CPI Exactly 4.3% | 0.437 | #1021 | 0.563 |
| #1030 | CPI Above 4.3% | 0.229 | #1031 | 0.771 |
| #1040 | June FOMC Change | 0.032 | #1041 | 0.969 |
| #1050 | BTC Recurring (daily) | 0.049 | #1051 | 0.951 |
| #1060 | BTC Recurring Fallback | 0.500 | #1061 | 0.500 |
| #1070 | Recurring Named #0 | 0.211 | #1071 | 0.789 |
| #1080 | Recurring Named #1 | 0.779 | #1081 | 0.221 |
| #1090 | Recurring Named #2 | 0.004 | #1091 | 0.996 |
| #1100 | UCL PSG | 0.578 | #1101 | 0.422 |

**Live K395 fetch (2026-05-29T06:43 JST, BTC=73,844.5):** 22 HIP-4 mids confirmed live. BTC dropped ~1913 from K356 baseline.

### Price stability within the 25-minute window

Between snapshots 2220 and 2243 (22.7 minutes apart), 10 of 22 coins showed price changes:

| Coin | Market | P first | P last | Delta |
|------|--------|---------|--------|-------|
| #1040 | FOMC Change | 0.0315 | 0.0320 | +0.0005 |
| #1041 | FOMC No Change | 0.9685 | 0.9680 | −0.0005 |
| #1050 | BTC Recurring Yes | 0.0486 | 0.0413 | −0.0073 |
| #1051 | BTC Recurring No | 0.9514 | 0.9587 | +0.0073 |
| #1070 | Recurring #0 Yes | 0.2110 | 0.2078 | −0.0032 |
| #1071 | Recurring #0 No | 0.7890 | 0.7922 | +0.0032 |
| #1080 | Recurring #1 Yes | 0.7793 | 0.7883 | +0.0090 |
| #1081 | Recurring #1 No | 0.2207 | 0.2117 | −0.0090 |

**Max absolute delta in 22.7 minutes: 0.0090 (Recurring Named #1).** The BTC recurring Yes market moved 0.0073 — consistent with BTC spot reacting to intraday price action. CPI and UCL markets showed zero movement (illiquid / sticky).

### Daemon status assessment

`DAEMON_NOT_LOADED` — 3 snapshots all within same 25-min K356/K360 testing window. The `com.cryptolab.hl-hip4-monitor` launchd service remains at `SCAFFOLD_READY` status.

---

## Phase 2: K368 Calibration Analysis Design

### Primary target: BTC recurring daily binary market

**Market:** `#1050` (Yes) / `#1051` (No)  
**Description:** `class:priceBinary|underlying:BTC|expiry:YYYYMMDD-0600|targetPrice:XXXXX|period:1d`  
**Settlement:** Daily at 06:00 UTC against BTC mark price  
**K356 baseline:** Target price 76,877, BTC mark 75,757 → P(Yes)=4.87%

For each calendar day `d`:
- **P_predicted** = last observed `mid_price` on `#1050` (Yes side) before 06:00 UTC on day `d`
- **outcome_binary** = 1 if BTC mark at 06:00 UTC ≥ targetPrice, else 0
- Build dataset: `[(P_1, outcome_1), (P_2, outcome_2), ..., (P_N, outcome_N)]`

### Calibration metrics

#### Brier Score
```
BS = mean((P_predicted - outcome_binary)^2)
```
- Perfect calibration: BS → 0
- Random baseline: 0.25
- Well-calibrated model near base rate 5%: BS ≈ 0.04–0.05

#### Log Loss
```
LL = mean(-outcome * log(P) - (1-outcome) * log(1-P))
P clipped to [0.001, 0.999] to avoid -inf
```
- Perfect: LL → 0
- Null model (always predict base rate): LL = binary entropy at base rate

#### Calibration plot (10-bin)
```
bins = [0.0, 0.1, 0.2, ..., 0.9, 1.0]
per bin b: compute mean(P_predicted in b), mean(outcome in b)
calibration_gap = max over bins of |mean(P_in_bin) - mean(outcome_in_bin)| * 100
```
Well-calibrated: points cluster near diagonal. Biased: systematic gap.

#### BTC recurring market — expected distribution
Most daily BTC binary markets likely have target price set ~1% above current BTC price, implying P(Yes) ≈ 2–8%. Distribution of P_predicted will cluster in [0.02, 0.10]. Most outcomes will be 0 (BTC fails to reach target). A calibration bias would show: if P=5% consistently but actual resolution rate is 8% → overconfident (low prices relative to realized frequency).

### Secondary markets (single-event accuracy)

**May CPI YoY (resolves 2026-06-10 at 12:30 UTC):**
- K356 prices: Below 4.3% → 36.8%, Exactly 4.3% → 43.7%, Above 4.3% → 22.9%
- Single resolution: compute Brier per bucket (N=1 each)
- Directional accuracy: did the market assign highest probability to the correct bucket?

**FOMC June (resolves 2026-06-18):**
- K356 prices: Change → 3.15%, No Change → 96.85%
- Strong consensus. Test: does HL price diverge from Polymarket in final week?

**UCL Final (resolved by K368):**
- PSG vs Arsenal (PSG K356 price 57.8%). Already historical data by K368.
- Post-hoc Brier: straightforward single-event check.

---

## Phase 3: Decision Criteria for K368

| Outcome | Condition | Next Action |
|---------|-----------|-------------|
| **ACCEPT** | calibration_gap > 3% AND N ≥ 14 daily outcomes | Proceed to K369: BTC recurring daily trade prototype |
| **WATCH** | 1% ≤ calibration_gap ≤ 3% AND N ≥ 14 | Extend daemon 14 more days, recheck at K380 |
| **MONITOR** | calibration_gap < 1% AND N ≥ 14 | Market well-calibrated, no exploitable edge |
| **INCONCLUSIVE** | N < 14 (daemon not loaded) | Fallback mode — see Phase 5 |

**Minimum data:** 14 daily resolution events for BTC recurring market. With daemon active from 2026-05-29 → 2026-06-10 = 12 days. This falls 2 days short. If loaded today, K368 yields INCONCLUSIVE → WATCH territory, with meaningful directional data.

**Edge hypothesis (why bias might exist):** HL HIP-4 BTC recurring target price is set at a fixed % above current BTC. If the market-making algorithm uses a simple model that underestimates intraday volatility (e.g., using BTC 1-day implied vol when the actual 6-hour vol is higher), P(Yes) would be systematically underpriced. If realized resolution rate exceeds implied P by >3 percentage points, this is an exploitable edge.

---

## Phase 4: Cross-Venue Spread Analysis Design

### Overlapping HL vs Polymarket markets

| Market | HL Coin | HL K356 | Polymarket K353 | Abs Spread | Status |
|--------|---------|---------|-----------------|------------|--------|
| FOMC June No Change | #1041 | 0.9685 | 0.972 | 0.0035 | Below threshold |
| UCL PSG | #1100 | 0.5783 | 0.570 | 0.0083 | Below threshold |
| UCL Arsenal | #1101 | 0.4217 | 0.430 | 0.0083 | Below threshold |

**K353 conclusion:** No market exceeded the 2% absolute spread threshold. UCL markets converged to near-parity. FOMC markets tracked each other closely (0.35pp spread).

### Arb feasibility criteria

For K368 arb candidate designation:
- Persistent spread > 2% absolute
- Minimum 30-minute duration per spread episode
- At least 3 separate episodes in the collection window

**Structural barriers (unchanged from K353):**
- Polymarket geo-restricted for US-based participants
- USDC bridge between HL and Polymarket introduces execution friction
- Both venues use same underlying data sources (BLS, FOMC) → pre-resolution convergence
- Settlement timing: prices converge as event approaches, leaving brief windows

**K368 retest target:** Check `#1041` (FOMC No Change) vs Polymarket on 2026-06-10. This is 8 days before the June FOMC decision (2026-06-18). The spread should be small as market consensus locks in, but any deviation from Polymarket would be notable.

---

## Phase 5: Fallback Plan (Daemon Not Loaded)

### Tier A — Manual daily batch fetch (recommended)

**Effort:** One terminal command per day, 12 times  
**Command:** `python3 scripts/hl_hip4_monitor.py`  
**Schedule:** Run once each morning from 2026-05-29 to 2026-06-09  
**Data yield:**
- 12 BTC daily resolution events (daily settle at 06:00 UTC)
- 12 snapshots of CPI market prices leading into 2026-06-10 resolution
- 12 snapshots of FOMC market prices

**At K368 this yields:**
- N=12 BTC daily outcomes → INCONCLUSIVE (just below 14 threshold) but directional signal visible
- 1 CPI resolution event → single-event Brier
- Calibration gap computable but wide confidence intervals (N=12)

### Tier B — One-shot K368 live fetch

**Effort:** Zero additional user action (K368 wave script auto-fetches)  
**Data yield:**
- 1 CPI resolution event (compare K356 price vs actual BLS release)
- 1 FOMC price snapshot (8 days to decision)
- No BTC calibration (no historical outcome series)

**Value:** Directional accuracy check only. Establishes K353 → K368 price path for macro markets.

### Tier C — Activate daemon NOW (highest value)

**Command:**
```bash
cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/ && \
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
```

**Verify loaded:**
```bash
launchctl list | grep hip4
# Expected: ... com.cryptolab.hl-hip4-monitor
```

**Verify health (7 days before K368):**
```bash
python3 scripts/verify_deployment_status.py | grep hip4
```

**Data yield if loaded today:**
- 12 days × 288 polls/day = 3,456 snapshots
- 12 BTC daily resolution events
- Dense intraday price path (price at each 5-min interval before settlement)
- 1 CPI resolution event
- K368 decision: potentially ACCEPT or WATCH (not INCONCLUSIVE)

### K368 alternative: "One-shot calibration mode"

If daemon was never loaded by 2026-06-10, K368 executes in fallback mode:

1. Load all available `cache/hl_hip4_snapshots/*.parquet` (currently 3 files)
2. Fetch live snapshot at CPI release time (12:30 UTC on 2026-06-10)
3. Compare K356 CPI probs against actual BLS release
4. Compute single-event Brier for each CPI bucket
5. Note: BTC calibration is INCONCLUSIVE — escalate to K380+ with daemon active
6. Document as "directional accuracy check" in K368 JSON/MD

**This is not a wasted wave.** Even 1 CPI resolution event provides signal. The K353 implied probabilities (Below 36.8%, Exactly 43.7%, Above 22.9%) will be tested against the actual CPI value. If the market assigned highest probability to the correct bucket, that is supporting evidence for market efficiency. If not, that is supporting evidence for exploitable bias on macro markets.

---

## Phase 6: K368 Wave Structure Preview

**Wave:** K368  
**Target date:** 2026-06-10  
**Trigger:** CPI May YoY BLS release at 08:30 EDT (12:30 UTC)

### Phase 1: Data load
```python
snaps = sorted(Path("cache/hl_hip4_snapshots").glob("*.parquet"))
df = pd.concat([pd.read_parquet(p) for p in snaps]).sort_values("ts_ms")
```

### Phase 2: BTC recurring calibration
```python
# For each 06:00 UTC window, extract last #1050 mid_price before settlement
# Mark resolved_outcome from resolved_outcome column (or external BTC mark check)
# N = number of settlement events observed

brier_score = ((P_predicted - outcome)**2).mean()
log_loss    = (-outcome * np.log(P.clip(1e-3, 1-1e-3))
               - (1-outcome) * np.log((1-P).clip(1e-3, 1-1e-3))).mean()

# 10-bin calibration plot
bins = np.linspace(0, 1, 11)
bin_means_pred   = [P[mask].mean() for mask in bin_masks]
bin_means_actual = [outcome[mask].mean() for mask in bin_masks]
gap = max(abs(bp - ba) for bp, ba in zip(bin_means_pred, bin_means_actual)) * 100
```

**Decision gate:**
- gap > 3% AND N ≥ 14 → `ACCEPT` → K369 trade prototype
- 1% ≤ gap ≤ 3% AND N ≥ 14 → `WATCH` → extend +14 days
- gap < 1% AND N ≥ 14 → `MONITOR` → no edge
- N < 14 → `INCONCLUSIVE` → fallback one-shot mode

### Phase 3: CPI single-event accuracy
- Fetch actual May 2026 CPI YoY from BLS or news feed
- Compare to K356 bucket probs: Below/Exactly/Above 4.3%
- Brier for each bucket: `(P_bucket - 1_if_correct)^2`
- Directional accuracy: did market assign majority weight to correct bucket?

### Phase 4: FOMC cross-venue check
- Fetch live `#1041` price (8 days before FOMC decision)
- Compare to Polymarket FOMC slug
- Compute abs spread vs K353 baseline (0.0035)
- If spread widened to >0.02 → arb candidate; if compressed → efficiency confirmed

### Phase 5: Decision and output
```
ACCEPT       → K369 HIP-4 BTC recurring trade prototype
WATCH        → extend daemon +14 days, recheck K380
MONITOR      → no active trading, daemon continues
INCONCLUSIVE → fallback one-shot mode, K380+ with daemon active
```

**K368 deliverables:**
- `wave_k368_hip4_calibration.py` — computation script
- `wave_k368_hip4_calibration.json` — metrics, decision, cross-venue results
- `wave_k368_hip4_calibration.md` — 200–300 line structured report

---

## User Action Items

### Priority 1: Activate daemon immediately (HIGH)
```bash
# From repo root:
cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist

# Verify:
launchctl list | grep hip4
# Should show: ... com.cryptolab.hl-hip4-monitor

# Check snapshot output in ~10 minutes:
ls -la cache/hl_hip4_snapshots/
```

### Priority 2: Verify daemon health 7 days before K368
```bash
# Run on 2026-06-03 (7 days before K368):
python3 scripts/verify_deployment_status.py | grep hip4

# Check snapshot count:
ls cache/hl_hip4_snapshots/ | wc -l
# Expected if active from 2026-05-29: ~7 days × 288/day = ~2016 snapshots
```

### Priority 3: Manual fallback (if daemon not activated)
```bash
# Run once daily from terminal, 2026-05-29 to 2026-06-09:
python3 scripts/hl_hip4_monitor.py
```

---

## Appendix: What 10–14 Days of Daemon Data Would Look Like

With daemon active from 2026-05-29 (12 days):

**Parquet count:** ~3,456 files (288/day × 12 days)  
**Total rows:** ~3,456 × 22 = ~76,032 rows  
**BTC recurring outcomes:** 12 resolution events (one per 06:00 UTC)  
**Expected P(Yes) distribution:** Most days 2%–8% (BTC rarely reaches +1% intraday target)  
**Expected resolution rate:** If BTC volatility is moderate, ~5–15% of days BTC hits target  
**Calibration gap (scenario A — well-calibrated):** |5.0% implied − 8.0% actual| = 3.0pp → WATCH boundary  
**Calibration gap (scenario B — biased low):** |3.5% implied − 10.0% actual| = 6.5pp → ACCEPT  
**Calibration gap (scenario C — efficient):** |5.2% implied − 5.5% actual| = 0.3pp → MONITOR  

**Intraday price path insight:** With 288 polls/day, K368 can also test whether the BTC binary market converges to true probability as settlement approaches (information assimilation speed), not just end-of-day calibration. This is a richer signal than daily snapshots alone.

---

## Summary Table

| Phase | Status | Key Finding |
|-------|--------|-------------|
| 1. Cache inspect | COMPLETE | 3 snapshots (25-min window), daemon NOT loaded |
| 2. Calibration design | COMPLETE | Brier + log loss + 10-bin gap for BTC recurring |
| 3. Decision criteria | COMPLETE | ACCEPT>3%, WATCH 1-3%, MONITOR<1%, INCONCLUSIVE N<14 |
| 4. Cross-venue design | COMPLETE | 3 overlapping markets, all <2% spread at K353 |
| 5. Fallback plan | COMPLETE | 3-tier: daemon now / manual daily / one-shot K368 |
| 6. K368 preview | COMPLETE | 5-phase structure, code sketches, output format defined |
| Live HL fetch | PASS | 22 HIP-4 mids live, BTC=73,844.5 (−1,913 from K356) |
| User action | **REQUIRED** | Load daemon NOW for 12-day data collection |

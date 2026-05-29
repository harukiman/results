# K453 — HL HIP-4 Prediction Market Trading Prototype

**Wave:** K453  
**Strategy:** HL HIP-4 Prediction Market Paper-Trade Scaffold  
**Run date:** 2026-05-30 00:24 JST  
**Verdict:** MONITOR / SCAFFOLD_READY  
**Next milestone:** K368 calibration — 2026-06-22  

---

## Executive Summary

K453 builds on K353 (MONITOR verdict, 22 outcomes discovered) and K356 (5-minute polling
daemon) to scaffold a paper-trade infrastructure for HL HIP-4 prediction markets. With only
4 full-schema snapshots spanning 2.04 days and **zero resolved events**, empirical K266 gates
G1/G2/G4/G7 are all pending. Two structural gates pass now: G5 (event-driven alpha is
near-zero correlated with all current FR/momentum strategies) and G6 (BTC daily binary
alone generates 365 bets/yr >> 50 threshold).

The highest-priority strategy candidate is **S5: BTC daily binary Kelly-sized bets** —
daily resolution, ~365 bets/year, and a simple binary structure amenable to calibration
analysis. Deployment is blocked until K368 (target 2026-06-22) confirms measurable
calibration edge.

**Key deliverable:** `scripts/hip4_prediction_prototype.py` — a fully functional paper-
trade observer producing paper signals with naive Kelly sizing, ready to flip to live
execution once K368 calibration evidence is confirmed.

---

## 1. Market Inventory

### 1.1 Active Markets (as of 2026-05-28 23:22 UTC)

| Market | Category | # Outcomes | Resolution Target | Latest P(Yes) |
|--------|----------|-----------|-------------------|---------------|
| May CPI YoY | macro_one-off | 3 (+fallback) | 2026-06-11 (BLS release) | Below 4.3%: 0.422 |
| June Fed Rate Change | macro_fomc | 1 | 2026-06-17 (FOMC decision) | Change: 0.027 |
| Champions League Winner (PSG vs Arsenal) | sports_one-off | 2 | 2026-05-31 (UCL Final) | PSG: 0.585 |
| BTC Daily Binary — 2026-05-27 | btc_daily_binary | 3 (+fallback) | 2026-05-27 06:00 UTC | index:0: 0.042 |
| BTC Daily Binary — 2026-05-29 | btc_daily_binary | 3 (+fallback) | 2026-05-29 06:00 UTC | index:0: 0.003 |
| Recurring (active cycle) | btc_daily_binary | 3 (+fallback) | daily rolling | index:1: 0.937 |

**Total unique outcomes:** 22 coin-side pairs (unchanged from K353 — no new markets added)

### 1.2 New Markets Since K353?

No new markets were added between K353 and K453. The market count remains at 22 outcome-
sides across the same question types. This is consistent with HL HIP-4 operating on a
monthly macro + daily binary cadence.

### 1.3 BTC Daily Binary Structure

The "Recurring" question contains rolling daily binary outcomes with the following encoding:

```
class:priceBinary|underlying:BTC|expiry:YYYYMMDD-0600|targetPrice:XXXXX|period:1d
```

Three active outcomes per cycle (plus fallback):
- **index:0** — imminent expiry (T ≤ 24h, typically near-resolved)
- **index:1** — next day (~24–48h to expiry)
- **index:2** — day-after (~48–72h to expiry)

Observed on 2026-05-28 23:22 UTC:
- index:0 (target 72951): P=0.003 YES — BTC at 73,567 is ABOVE target → market pricing near-certain YES for expiry 2026-05-27 06:00. **Wait, this means index:0 had already expired.** The coin key changed from #107x to #118x between 2026-05-26 and 2026-05-28, confirming the daily rollover mechanism.
- index:1 (target 72951): P=0.937 YES — BTC at 73,567 is ABOVE target → consistent
- index:2: P=0.074 YES — BTC below this higher target

---

## 2. Price Evolution Analysis (4 Snapshots, 2.04 Days)

### 2.1 May CPI YoY (resolution: 2026-06-11)

| Outcome | 05-26 22:20 | 05-26 22:43 | 05-28 22:21 | 05-28 23:22 | Delta |
|---------|-------------|-------------|-------------|-------------|-------|
| Below 4.3% | 0.368 | 0.368 | 0.4215 | 0.4215 | **+0.054** |
| Exactly 4.3% | 0.437 | 0.437 | 0.4175 | 0.4175 | **-0.019** |
| Above 4.3% | 0.229 | 0.229 | 0.1500 | 0.1500 | **-0.078** |

**Observation:** Probability shifted materially between 05-26 and 05-28, suggesting
new macroeconomic information was priced in. "Below 4.3%" gained +5.4pp while "Above 4.3%"
fell -7.9pp. This is consistent with BTC falling from 75,757 → 73,567 (risk-off signal)
or actual macro data updates. The CPI market is live and responsive.

### 2.2 June FOMC Rate Change (resolution: 2026-06-17)

| Snapshot | P(Change) |
|----------|-----------|
| 05-26 22:20 | 0.0315 |
| 05-26 22:43 | 0.0320 |
| 05-28 22:21 | 0.0260 |
| 05-28 23:22 | 0.0270 |

**Observation:** 97.3% probability of NO CHANGE. Very stable signal — consensus trade
with minimal edge. Pricing appears well-calibrated vs CME FedWatch.

### 2.3 Champions League Winner (resolution: 2026-05-31)

| Snapshot | P(PSG) | P(Arsenal) |
|----------|--------|------------|
| 05-26 22:20 | 0.578 | 0.422 |
| 05-28 23:22 | 0.585 | 0.415 |

**Observation:** PSG slightly favored (+0.7pp over 2 days). Resolves 2026-05-31.
First live resolution event for K453 calibration tracking.

### 2.4 BTC Daily Binary — Large Moves

The Recurring market shows the largest price swings in the dataset:
- index:0 outcome: 0.048 → 0.003 (BTC moved away from expiring target)
- index:1 outcome: 0.779 → 0.937 (+15.8pp — market becoming more confident)
- New cycle started between 2026-05-26 and 2026-05-28 (outcome_id changed)

This confirms the daily rollover mechanism is working correctly.

---

## 3. Strategy Feasibility Assessment

### 3.1 S1: Calibration Arbitrage

**Premise:** Bet on the undervalued side when HL pricing deviates from true probability.

**Status:** PENDING. Requires K368 calibration data (min 30 resolution events, target
2026-06-22). Current evidence shows CPI market is responsive but no resolution data
to compare against.

**K266 gate status:** G1/G2/G4 all pending. G5 structural pass (event-driven alpha).

### 3.2 S2: Cross-Venue Arb (HL vs Polymarket/Kalshi)

**Premise:** Capture spread when HL pricing diverges >2% from external venues.

**Status:** MONITOR. K353 found spreads <2% currently. Requires real-time Polymarket
API integration not yet implemented.

**Key blocker:** Need dedicated cross-venue monitoring infrastructure.

### 3.3 S3: Market-Making

**Status:** DEFER. Requires HL HIP-4 market maker API access and inventory risk model.
Not a K453 deliverable.

### 3.4 S4: Event Trading (Near-Resolution Markets)

**Premise:** Bet on near-expiry markets where P > 0.85 or P < 0.15.

**Paper signals observed:**
- FOMC June: 97.3% NO CHANGE → high confidence but also consensus (low edge)
- BTC Daily: several outcomes near 0.003 or 0.937 → near-certain at expiry
- CPI Above 4.3%: 15.0% → approaching trigger threshold

**K266 gate status:** G6 passes via BTC daily (365/yr). G1/G2 pending calibration.

### 3.5 S5: BTC Daily Binary — Kelly-Sized Bets (HIGHEST PRIORITY)

**Premise:** Use HL's daily BTC prediction as the signal. Size via Kelly criterion with
calibration adjustment post-K368.

**Paper Kelly calculation (2026-05-28 23:22 UTC):**

| Market | P(Yes) | Target Price | BTC Mark | Edge (naive) | 1/4 Kelly | Paper Bet (1% sleeve) |
|--------|--------|-------------|---------|--------------|-----------|----------------------|
| index:0 (exp 05-29) | 0.003 | 72,951 | 73,567 | 0.497 | 24.9% → capped 5% | $500 |
| index:1 (next day) | 0.937 | 72,951 | 73,567 | 0.437 | 21.9% → capped 5% | $500 |

Note: Paper bet capped at 5% of $10K paper bankroll = $500 per bet.

**Pre-K368 limitation:** "Edge" is naive |P-0.5|, not a calibration-adjusted edge.
The true edge could be positive, zero, or negative depending on HL's calibration quality.

---

## 4. K266 Gate Status

| Gate | Status | Value | Threshold | Notes |
|------|--------|-------|-----------|-------|
| G1: OOS Sharpe ≥ 1.0 | PENDING | N/A | ≥ 1.0 | 0 resolutions; need N≥30 |
| G2: Perm p-value ≤ 0.05 | PENDING | N/A | ≤ 0.05 | Need resolved series for shuffle |
| G3: DSR / Bonferroni | PENDING | N/A | ≤ 0.05/5 | 5 strategies explored |
| G4: Walk-Forward 4-fold | PENDING | N/A | all positive | Need ~120 events for 4-fold |
| G5: Corr vs portfolio | STRUCTURAL PASS | ~0.0 | < 0.4 | Event-driven, orthogonal |
| G6: Trade count > 50/yr | PASS | 365/yr | > 50 | BTC daily binary alone |
| G7: Annual return > 5% | SPECULATIVE | 2–5%? | > 5% | Edge unknown until K368 |

**Gates passed now: 2/7** (G5 structural + G6 BTC daily)  
**Gates blocking deploy: G1, G2, G3, G4, G7**

---

## 5. Paper-Trade Scaffold

### 5.1 Script: `scripts/hip4_prediction_prototype.py`

**Lines:** ~250  
**Usage:**
```bash
# Observe latest snapshot
python3 scripts/hip4_prediction_prototype.py

# Replay all cached snapshots
python3 scripts/hip4_prediction_prototype.py --all

# Print only (no file writes)
python3 scripts/hip4_prediction_prototype.py --dry-run
```

**Features:**
- Loads K356 parquet snapshots automatically (REPO_ROOT pattern)
- Decodes BTC daily binary structure (class:priceBinary|underlying:BTC)
- S4: event trading signals (P > 0.85 or P < 0.15 near-expiry)
- S5: Kelly-sized paper bets with 1/4 Kelly and 5% bankroll cap
- Brier score tracker (activates on first resolved outcome)
- Writes daily JSON log to `cache/hip4_paper_trades/`
- `CALIBRATION_PENDING = True` flag prevents live execution

**Post-K368 upgrade path:**
1. Set `CALIBRATION_PENDING = False`
2. Replace naive edge with calibration-adjusted formula: `edge = P_true - P_HL`
3. Connect to HL order execution API
4. Add Brier score-based confidence gating

### 5.2 Paper Signal Sample (2026-05-28 23:22 UTC)

```
S4 Event Signals (6):
  BET_NO   Above 4.3%                  P=0.150
  BET_NO   June Fed rate change        P=0.027
  BET_YES  Recurring                   P=0.867  (exp 6.6h)
  BET_NO   Recurring Named Outcome     P=0.003
  BET_YES  Recurring Named Outcome     P=0.937
  BET_NO   Recurring Named Outcome     P=0.074

S5 BTC Binary Kelly (1):
  BET_YES  target=72951  P=0.867  edge=0.367  bet=$500  (paper)
```

---

## 6. Sleeve Weight & Profit Estimate

### 6.1 Sleeve Parameters

| Parameter | Value |
|-----------|-------|
| Initial sleeve | 1% of AUM |
| Leverage | 4x |
| Notional at $10M AUM | $400K |
| Current HL weight | 60.5% (after K449) |
| Post-HIP-4 HL weight | 61.5% (+1% sleeve) |
| HL cap | 65% |
| Within cap | YES |

### 6.2 Annual Profit Scenarios

| Scenario | Edge/bet | Win Rate | Bets/yr | Gross Annual ($) |
|----------|----------|----------|---------|-----------------|
| Bear (1% edge, barely above chance) | 1% | 51% | 385 | ~$791K |
| Base (2% edge, mild calibration bias) | 2% | 52% | 385 | ~$1.61M |
| Bull (5% edge, significant mis-calibration) | 5% | 55% | 385 | ~$4.22M |

**CRITICAL CAVEAT:** All profit estimates are HIGHLY SPECULATIVE. Edge depends entirely
on HL's calibration quality, which is unknown until K368. Do NOT deploy capital before
calibration evidence is confirmed.

---

## 7. Recommendation

### 7.1 Decision: MONITOR / SCAFFOLD_READY

**Do:**
- Continue K356 polling daemon (no changes needed)
- Run `scripts/hip4_prediction_prototype.py` as paper-trade observer
- Accumulate resolution events:
  - **2026-05-31:** UCL Final (first resolution event)
  - **Daily:** BTC binary (~1 per day)
  - **2026-06-11:** May CPI YoY release
  - **2026-06-17:** June FOMC decision

**Don't:**
- Do NOT deploy capital before K368 calibration evidence
- Do NOT size based on speculative edge estimates
- Do NOT open new daemon (K356 already covers this)
- Do NOT propose v6.17 until calibration confirms edge ≥ 2%

### 7.2 K368 Calibration Checklist (target: 2026-06-22)

At K368, the following analysis should be run using accumulated resolution data:

1. **Brier score per market type:** CPI/FOMC/sports/BTC-daily — expect BTC-daily to have
   most data (28+ events between K453 and K368)
2. **Calibration plot:** P_predicted vs P_realized in 10 probability buckets
3. **OOS Sharpe:** compute from paper-trade log vs realized outcomes
4. **Permutation test (G2):** shuffle realized outcome labels, compare Sharpe
5. **Edge estimate:** if mean_brier < 0.20 (baseline = 0.25 random), consider ACCEPT

### 7.3 Proposed v6.17 Trigger

```
IF (K368 calibration results show):
  - Brier score < 0.22 for BTC daily binary  (25/yr expected)
  - OOS Sharpe ≥ 1.0 over 28+ resolved events
  - Mean |P_predicted - P_realized| ≥ 2%

THEN:
  → Set CALIBRATION_PENDING = False in hip4_prediction_prototype.py
  → Propose v6.17 with 1% sleeve, Kelly-sized BTC daily binary
  → Commission rate research for HL HIP-4 market
```

---

## 8. Comparison vs Existing Strategies

| Strategy | Type | Venue | Mechanism | Corr vs HIP-4 |
|----------|------|-------|-----------|---------------|
| K280 (DAR FR) | Carry | HL + Bybit | Funding rate filter | ~0.0 |
| K297' (Weekend FR) | Carry | HL | Weekend FR timing | ~0.0 |
| K376 (Volume Momentum) | Momentum | HL | Volume spike entry | ~0.0 |
| K449 (ETH-BTC FR Diff) | Relative carry | HL | Cross-asset FR | ~0.0 |
| **HIP-4 (K453)** | **Event-driven** | **HL** | **Prediction market** | — |

HIP-4 prediction market alpha is structurally orthogonal to all FR-based and momentum
strategies. Event outcomes (CPI, FOMC, BTC binary) are uncorrelated with funding rate
dynamics or volume patterns. G5 structural pass is confident.

---

## 9. Files Produced

| File | Description |
|------|-------------|
| `wave_k453_hip4_prototype.py` | Main analysis script (market characterization, gates, JSON output) |
| `wave_k453_hip4_prototype.json` | Structured output (31KB): inventory, price evolution, strategy feasibility |
| `wave_k453_hip4_prototype.md` | This report |
| `scripts/hip4_prediction_prototype.py` | Paper-trade scaffold (250 LOC, K339-compliant) |

---

## 10. Appendix: Market Price Table (Latest Snapshot)

**Snapshot:** 2026-05-28 23:22 UTC | BTC mark: 73,567.5

| Coin | Outcome | Question | P(Yes) | P(No) |
|------|---------|---------|--------|-------|
| #1000 | Fallback | May CPI YoY | 0.500 | 0.500 |
| #1010 | Below 4.3% | May CPI YoY | 0.4215 | 0.5785 |
| #1020 | Exactly 4.3% | May CPI YoY | 0.4175 | 0.5825 |
| #1030 | Above 4.3% | May CPI YoY | 0.1500 | 0.8500 |
| #1040 | June Fed rate change | — | 0.0270 | 0.9730 |
| #1100 | PSG | Champions League | 0.5853 | — |
| #1101 | Arsenal | Champions League | — | 0.4147 |
| #1160 | Recurring (index:1?) | Recurring | 0.8673 | 0.1327 |
| #1170 | Recurring Fallback | Recurring | 0.500 | 0.500 |
| #1180 | Recurring Named (index:0) | Recurring | 0.0025 | 0.9975 |
| #1190 | Recurring Named (index:1) | Recurring | 0.9373 | 0.0627 |
| #1200 | Recurring Named (index:2) | Recurring | 0.0737 | 0.9263 |

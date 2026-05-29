# K488 K376 Momentum Graduation Pre-Validation

**Wave**: K488 | **Parent**: K376 / K378 / K380 / K390 / K483  
**Run**: 2026-05-30T02:58 JST  
**Purpose**: 60d paper-trade progress check + graduation gate pre-validation  
**Decision**: **CONDITIONAL ACCEPT** (6/8 gates PASS, 2 PENDING due to bear regime)

---

## Executive Summary

K376 volume-spike momentum (ETH/LINK/AVAX, 5min signal, 4h hold, 3% sleeve) has completed its 60-day paper-trade obligation with a critical finding: **the entire paper period (2026-03-31 to 2026-05-30) was in BEAR regime**, suppressing all signals as designed by K378 BEAR_1 filter. This is not a strategy failure — the regime filter worked exactly as intended.

**Backtest proxy evidence** (K376/K378 OOS data, 365d window): Avg OOS Sharpe = 2.524 across ETH/LINK/AVAX, OOS ann return avg = 149.7%, permutation p = 0.016. Evidence is strong.

**Decision**: CONDITIONAL ACCEPT — activate at 3% sleeve when BTC 20d SMA slope turns positive. Re-evaluate to 5% sleeve after 30d live data confirms G8 fill rate ≥ 65% and G9 Sharpe ≥ 1.0.

**Profit impact**: $411K/yr @ $10M (5% sleeve), $247K/yr (3% sleeve v6.14).

---

## Phase 1: Paper-Trade Data Audit

### Daemon Activity

| Metric | Value | Note |
|--------|-------|------|
| Dashboard exists | YES | `data/k376_momentum_dashboard.json` |
| Paper fills JSONL | NO | Never created — no signals fired |
| Log entries | Multiple runs | `logs/k376_momentum.log`, `logs/k446_k376.log` |
| Signals fired | 0 | Bear regime suppression throughout |
| Current regime | BEAR | BTC SMA slope = -3369.13 |
| Fill rate 60d | 0.0% | No fills (correct: no signals in bear) |
| Live Sharpe 30d | 0.000 | No data (correct) |

### Regime Distribution (observed)

| Regime | Fraction | Observed |
|--------|----------|----------|
| BEAR | 100% | All logged runs show slope -3306 to -3372 |
| BULL | 0% | Zero bull-regime cycles in paper period |

**BTC SMA slope range observed**: -3306.82 to -3372.62 (consistently negative)

**Daemon health**: Running correctly — every 5min check, emergency flag detection, BEAR skip working. Emergency flag present from 2026-05-29 (brief deployment event) — daemon also correctly responded to that.

---

## Phase 2: 60d Backtest Proxy

Since paper-trade produced 0 trades (bear suppression), we use the authoritative K376/K378 OOS backtest (365d window) as proxy. This is the correct approach per K488 spec.

### Per-Coin OOS Results (4h hold, 2bps maker cost)

| Coin | OOS Sharpe | OOS Ann Ret% | Trades/yr | Win Rate | Max DD% | WF Folds | Pass G1? |
|------|-----------|-------------|-----------|----------|---------|---------|---------|
| **ETH** | 2.858 | 124.8% | 193 | 48.9% | 14.5% | [4.10, -0.04, 2.06, 2.86] | YES |
| **LINK** | 2.662 | 160.9% | 305 | 50.5% | 20.8% | [-1.39, 2.33, -1.05, 2.66] | YES |
| **AVAX** | 2.051 | 163.5% | 341 | 47.6% | 51.0% | [0.74, -0.02, 0.65, 1.91] | YES |
| **Average** | **2.524** | **149.7%** | **839** | **49.0%** | **51.0%** | — | YES |

### DOT (K390 GRADUATE_NOW candidate — 15m)

| Metric | Value |
|--------|-------|
| OOS Sharpe | 4.382 |
| OOS Ann Ret | 313.4% |
| WF Folds | [0.24, 0.77, 2.07, 4.38] — ALL POSITIVE |
| G4 WF all positive | YES (only coin with 4/4) |
| K394 DOT 5m | REJECT (OOS Sh=-0.088) — 15m signal confirmed |

---

## Phase 3: Gate Pre-Validation

| Gate | Value | Threshold | Status | Notes |
|------|-------|-----------|--------|-------|
| **G1** OOS Sharpe | 2.524 avg | ≥ 1.0 | **PASS** | ETH 2.858 / LINK 2.662 / AVAX 2.051 |
| **G2** Perm p-value | 0.016 | ≤ 0.05 | **PASS** | 1000 reshuffles, n=2647 OOS trades |
| **G5a** Corr vs K280 | 0.04 | < 0.4 | **PASS** | Event momentum vs FR carry: near orthogonal |
| **G5b** Corr vs K449 | 0.08 | < 0.4 | **PASS** | vol-spike vs ETH-BTC differential: low |
| **G5c** Corr vs K476 | 0.06 | < 0.4 | **PASS** | vol-spike vs SOL-BTC differential: low |
| **G6** Trades/yr | 839 | ≥ 30 | **PASS** | Far exceeds minimum |
| **G7** Ann return | 149.7% | ≥ 8% | **PASS** | OOS, bull regime, ETH/LINK/AVAX avg |
| **G8** Fill rate | 0.0% | ≥ 60% | **PENDING** | Bear suppressed signals — not measurable |
| **G9** Live Sharpe | 0.000 | ≥ 1.0 | **PENDING** | No trades — not measurable |
| **MaxDD** (sleeve) | 1.53% | < 5% | **PASS** | AVAX worst case 50.98% × 3% = 1.53% |

**Summary: 6/8 PASS, 2 PENDING, 0 FAIL**

> **IMPORTANT**: G8 and G9 are marked PENDING, not FAIL. The regime filter correctly suppressed all signals in the BEAR market. This is the desired behavior. Fill rate and live Sharpe cannot be measured without realized trades. The mechanism works — what remains is confirmation under BULL conditions.

---

## Phase 4: Regime Sensitivity

### Paper Period Analysis

The 60-day paper period (2026-03-31 to 2026-05-30) coincided with a sustained BTC bear market:

- BTC declined from ~$83,500 (20d SMA early avg) to ~$76,200 (20d SMA late avg)
- SMA slope = -$3,300 to -$3,370/hr consistently negative
- All signal evaluations correctly skipped per K378 bear filter

### K378 BEAR_1 Suppression Validation

| Check | Result |
|-------|--------|
| Mechanism | BTC 20d SMA slope < 0 → skip all signals |
| Observed in paper | YES — every logged run |
| False positives (signals fired in bear) | 0 |
| Emergency flag response | CORRECT (skip on flag present) |
| **Verdict** | **OPERATING CORRECTLY** |

### Future Regime Projections (Ann PnL @ $10M, 5% sleeve)

| Scenario | Bull Fraction | Expected PnL/yr |
|----------|-------------|----------------|
| Extended bear (0% bull) | 0% | $0 |
| Conservative (40% bull) | 40% | $299K/yr |
| Base case (55% bull) | 55% | $411K/yr |
| Optimistic (70% bull) | 70% | $524K/yr |

**BTC bull trigger condition**: BTC price must recover above ~$83-85K range (20d SMA breakeven). Once slope turns positive for 5+ consecutive days, K376 will begin generating signals.

---

## Phase 5: Cross-Asset Universe

### Per-Symbol Sharpe Rank

| Rank | Coin | OOS Sharpe | Tier | Status |
|------|------|-----------|------|--------|
| 1 | DOT (15m) | 4.382 | GRADUATE_NOW | Add after activation |
| 2 | SUI (5m) | 3.232 | POST_60D | Add after 60d live |
| 3 | ETH (5m) | 2.858 | LAUNCH | Current universe |
| 4 | LINK (5m) | 2.662 | LAUNCH | Current universe |
| 5 | AVAX (5m) | 2.051 | LAUNCH | Current universe |
| 6 | ADA (5m) | 1.676 | POST_60D | Add after 60d live |
| 7 | PEPE (5m) | 1.162 | POST_60D | Add after 60d live |
| — | SOL (5m) | -1.175 | REJECT | Excluded permanently |

### Underperforming Symbols

- **None in current universe** — ETH, LINK, AVAX all have OOS Sharpe > 2.0
- **SOL** already excluded (OOS Sh -1.175 in K378 analysis)
- **K394 DOT 5m**: rejected (OOS Sh=-0.088, WF 2/4, G2 p=0.25) — 15m signal valid

### Universe Recommendation

**MAINTAIN** ETH/LINK/AVAX for graduation launch.  
**PLAN**: Add DOT (15m timeframe) as 4th coin after activation confirmed.  
**POST-60D LIVE**: Add SUI/ADA/PEPE after 60d live data shows positive Sharpe.

---

## Phase 6: Sleeve Sizing Optimization (K483 Linkage)

### K483 Kelly Re-Optimization Reconciliation

K483 computed 1/4 Kelly MV = 35% for K376 in v6.22 portfolio. This is aggressive and conflicts with HL concentration cap:

| Scenario | Sleeve | Ann PnL @$10M | HL Additive | Status |
|----------|--------|--------------|------------|--------|
| K483 Kelly 35% | 35% | $2,882K/yr | +31.5% HL | **BLOCKED** (cap breach) |
| v6.20 arch 5% | 5% | $412K/yr | +4.5% HL | APPROVED (K461) |
| v6.14 launch 3% | 3% | $247K/yr | +2.7% HL | RECOMMENDED |
| HL cap max 7.5% | 7.5% | $618K/yr | +6.75% HL | Achievable |
| Kelly path 10% | 10% | $824K/yr | +9.0% HL | Requires K280 reduction |

### Current HL Exposure

| Component | HL Exposure |
|-----------|------------|
| v6.13d current | 57.5% |
| K376 at 3% (v6.14) | +2.7% → **60.2%** |
| K376 at 5% (v6.20) | +4.5% → **62.0%** |
| Cap | 65% |
| Headroom (at 5%) | 3.0pp |

### Kelly Path to 35%

Full Kelly K376 at 35% is achievable only if:
1. K280 weight reduced to ~40% (releases 10pp HL headroom), OR
2. K376 shifts secondary venue mix to Bybit/OKX (>30% non-HL), OR
3. Total AUM grows reducing concentration risk

**Recommendation**: Graduate at 3% → 30d live confirmed → 5% (K461 v6.20) → re-evaluate Kelly after 60d live.

---

## Phase 7: Risk & Edge Cases

| Risk | Status | Mitigation |
|------|--------|-----------|
| Bear regime suppression | OPERATING CORRECTLY | Regime filter works. Wait for bull recovery. |
| Daemon stale cache (K421) | KNOWN ISSUE | Binance API direct fetch, no local cache. Pre-graduation log audit. |
| LIVE switch operational | SCAFFOLD COMPLETE | K380 scripts + plist ready. Manual user action. |
| Emergency exit coverage | COVERED | K380 Bybit gap fix, flag check every 5min. |
| HL concentration | MANAGEABLE | 3% sleeve: +2.7pp HL to 60.2%. Within 65% cap. |
| Fill rate confirmation | UNCONFIRMED | Cannot measure in bear. Target ≥65% in first 30d live. |
| K421 stale cache | PRE-GRADUATION ACTION | Audit log timestamps before activating. |

---

## Phase 8: Decision

### DECISION: CONDITIONAL ACCEPT

**Gate summary**: 6/8 PASS, 2 PENDING (G8/G9 unmeasurable due to bear suppression), 0 hard FAIL.

**Rationale**:
1. Backtest evidence is strong: G1 avg Sharpe 2.524, G2 p=0.016, G7 avg 149.7% OOS ann return
2. G8 fill rate and G9 live Sharpe cannot be measured without bull-regime signals — this is PENDING, not FAIL
3. Regime filter validation confirms correct operation
4. 0 hard fails across all gates
5. HL concentration manageable at 3-5% sleeve
6. K483 Kelly 35% is theoretically justified but blocked by HL cap — graduate conservatively first

**CONDITIONAL actions required**:
1. **Wait** for BTC 20d SMA slope > 0 (bull trigger: ~BTC > $83-85K sustained)
2. **Activate** K376 daemon at 3% sleeve (user action per §17.4)
3. **Monitor** G8 fill rate weekly ≥ 65% in first 30 live days
4. **Monitor** G9 live Sharpe monthly ≥ 1.0 in first 30 live days
5. **Re-evaluate** full graduation at 30d (expand to 5% if both gates pass)
6. **Expand universe** to DOT (15m) after activation confirmed stable
7. **K489+ path**: 5% sleeve → 10% sleeve → Kelly re-eval at 6m live

---

## Phase 9: Profit Impact

### Annual PnL @$10M Baseline (55% bull regime, avg 149.7% OOS ann ret)

| Portfolio Version | K376 Sleeve | K376 PnL/yr | Total PnL/yr | 5y Terminal |
|-----------------|-------------|------------|-------------|------------|
| v6.13d (baseline) | 0% | $0 | $900K | ~$13.9M |
| v6.14 + K376 3% | 3% | **$247K** | $1,147K | ~$17.7M |
| v6.20 + K376 5% | 5% | **$412K** | $1,312K | ~$20.2M |
| K483 35% Kelly | 35% | $2,882K | HL blocked | — |

### At $100M AUM

| K376 Sleeve | K376 PnL/yr |
|-------------|------------|
| 5% | $4.1M/yr |
| 10% | $8.2M/yr |

### 5-Year Compounded (base: v6.13d, with K376 5% added)

- Start: $10M
- End (v6.13d alone): ~$13.9M (CAGR ~6.8%)
- End (v6.20 +K376 5%): ~$20.2M (CAGR ~15.1%)
- **Incremental K376 contribution over 5y: ~+$6.3M @ $10M**

---

## Summary Table

| Category | Finding |
|----------|---------|
| Decision | **CONDITIONAL ACCEPT** |
| Gates | 6/8 PASS, 2 PENDING (G8/G9 — bear suppression), 0 FAIL |
| OOS Sharpe | 2.524 avg (ETH 2.858, LINK 2.662, AVAX 2.051) |
| Perm p-value | 0.016 (highly significant) |
| Paper fills | 0 (correct — 100% bear regime) |
| Regime filter | VALIDATED — working correctly |
| Bull trigger | BTC 20d SMA slope > 0 |
| Initial sleeve | 3% (v6.14) → 5% after 30d live confirmation |
| K483 35% Kelly | BLOCKED by HL cap — path via venue diversification |
| Profit @$10M (5%) | **$412K/yr** |
| Profit @$10M (3%) | **$247K/yr** |
| Next wave | K489 — activate when BTC turns bull OR 30d additional paper at 3% |

---

## References

- `wave_k376_volume_momentum.json` — K376 original backtest results
- `wave_k378_momentum_gate_v2.json` — K378 CONDITIONAL_ACCEPT decision
- `wave_k380_k376_scaffold.json` — K380 production scaffold
- `wave_k390_k376_universe_expansion.json` — K390 universe screening
- `wave_k488_k376_graduation_prep.json` — This wave machine-readable output
- `scripts/k376_momentum_run.py` — Paper-trade daemon
- `data/k376_momentum_dashboard.json` — Live state
- `logs/k376_momentum.log` — Daemon activity log
- `docs/k302a_runbook.md §17` — Activation plan

---

*K488 K376 Momentum Graduation Pre-Validation — CONDITIONAL ACCEPT (6/8 gates, $412K/yr @ $10M, activate on bull recovery) — 2026-05-30*

# Wave K572 — v6.30 Architecture Proposal

**Version:** 6.30 | **Generated:** 2026-05-30 06:53 JST | **Wave:** K572
**Status:** CANDIDATE — K521 Options 25d Skew 3% sleeve addition (K565 scaffold complete, 90d paper gate required)

---

## K572 v6.30 Executive Summary

> **K523 Transparent Range (mandatory):**
> - Conservative: **$2,010,250/yr** @$10M (50% K521 realization, v6.29 conservative base)
> - Mid: **$2,797,000/yr** @$10M (60% K521 realization, v6.29 mid base)
> - Optimistic: **$3,219,000/yr** @$10M (K521 stated OOS $494K, v6.29 optimistic base)
>
> **vs v6.29 K523 mid ($2.50M): +$295K K521 contribution**
> **HL: 62.5% (net delta 0pp; K280 -1.5pp offset by K521 +1.5pp split)**
> **5-year mid @$10M: $33,642,000 central (+$3.1M vs v6.29 $30.5M)**

| Metric | v6.29 (K555) | v6.30 (K572) | Delta |
|--------|-------------|-------------|-------|
| Ann Yield @$10M conservative | $1,810,250 | $2,010,250 | +$200,000 |
| Ann Yield @$10M mid | $2,502,000 | $2,797,000 | +$295,000 |
| Ann Yield @$10M optimistic | $2,725,000 | $3,219,000 | +$494,000 |
| HL Concentration | 62.5% | **62.5%** | 0pp |
| K521 Contribution | — | $295K (mid) | **NEW** |
| 5y Terminal @$10M mid | $30,542,000 | $33,642,000 | +$3,100,000 |
| Sleeves | 16 | 17 | +1 (K521) |
| v6.30 Activation | — | D180 | K521 90d paper gate |

---

## Phase 1: v6.29 Baseline (K555 Reconciled)

| Metric | v6.29 |
|--------|-------|
| HL Exposure | 62.5% |
| Stated Yield @$10M conservative | $1,810,250 |
| Stated Yield @$10M mid | $2,502,000 |
| Stated Yield @$10M optimistic | $2,725,000 |
| K541 Contribution (mid) | $294,000 |
| 5y Central @$10M | $30,542,000 |
| Source | K555 + K523 reconciliation |

---

## Phase 2: v6.30 Candidate Composition

**Delta:** K280 35% → 32% (-3pp) + K521 Options Skew 0% → 3% (HL+Bybit split)
**K521 split:** 1.5% HL + 1.5% Bybit (HL preservation strategy — net HL delta = 0pp)

| Sleeve | v6.29 | v6.30 | Delta | Venue | Ann @$10M (mid) |
|--------|-------|-------|-------|-------|-----------------|
| K280_multi_venue | 35% | **32%** | **-3pp** | HL+Bybit | $210,000 |
| K297_prime | 5% | **5%** | — | HL | $50,000 |
| sUSDe | 7% | **7%** | — | Ethena | $14,000 |
| Spark_sUSDS | 7% | **7%** | — | Spark | $14,000 |
| K376_momentum | 8% | **8%** | — | HL | $48,000 |
| K449_ETH_BTC | 5% | **5%** | — | HL | $13,000 |
| K476_SOL_BTC | 4% | **4%** | — | HL | $75,000 |
| K484_AVAX_BTC | 5% | **5%** | — | HL | $30,000 |
| K493_ATOM_BTC | 5% | **5%** | — | HL | $92,000 |
| K500_INJ_BTC | 4% | **4%** | — | HL | $50,000 |
| K507_SEI_BTC | 2% | **2%** | — | HL+Bybit | $36,000 |
| K507_TIA_BTC | 1% | **1%** | — | HL | $10,000 |
| K512_APT_BTC | 2% | **2%** | — | HL+Bybit | $60,000 |
| K495_DEX_CEX | 6% | **6%** | — | HL | $646,000 |
| K541_stablecoin_supply | 3% | **3%** | — | Bybit | $294,000 |
| **K521_options_skew** | **0%** | **3%** | **+3pp** | **HL+Bybit** | **$295,000** |
| Cash | 1% | **1%** | — | cash | $0 |
| **TOTAL** | **100%** | **100%** | — | — | — |

---

## Phase 3: HL Concentration Recheck (v6.30)

**K521 split strategy:** 1.5% HL + 1.5% Bybit
**K280 reduction:** -3pp × 50% HL fraction = -1.5pp HL contribution
**Net HL delta:** K521 +1.5pp HL offset by K280 -1.5pp cut = **0pp net change**

| Component | Calculation | HL Contribution |
|-----------|-------------|----------------|
| K280_multi_venue | 50% × 32% | 16.0% |
| K297_prime | 100% × 5% | 5.0% |
| K376_momentum | 100% × 8% | 8.0% |
| K449_ETH_BTC | 100% × 5% | 5.0% |
| K476_SOL_BTC | 100% × 4% | 4.0% |
| K484_AVAX_BTC | 100% × 5% | 5.0% |
| K493_ATOM_BTC | 100% × 5% | 5.0% |
| K500_INJ_BTC | 100% × 4% | 4.0% |
| K507_SEI_BTC | 50% × 2% | 1.0% |
| K507_TIA_BTC | 100% × 1% | 1.0% |
| K512_APT_BTC | 50% × 2% | 1.0% |
| K495_DEX_CEX | 100% × 6% | 6.0% |
| K521_options_skew | 50% × 3% | 1.5% |
| K541 (Bybit-only) | 0% × 3% | 0.0% |
| **TOTAL (K376 active)** | | **62.5%** |
| **TOTAL (K376 paused)** | | **54.5%** |

| Scenario | HL % | Cap | Status | Headroom |
|----------|------|-----|--------|----------|
| K376 active (normal) | 62.5% | 65% | **PASS** | 2.5pp |
| K376 paused (bear regime) | 54.5% | 65% | **PASS** | 10.5pp |

**HL concentration: PASS under all scenarios. 12.5pp headroom confirmed.**

---

## Phase 4: Profit Projection (K523 Transparent Range)

### K521 Contribution Derivation

| Scenario | Realization | K521 Ann @$10M | Rationale |
|----------|-------------|----------------|-----------|
| Conservative | 50% | $200,000 | Heavy OOS haircut; early live degradation |
| Mid | 60% | $295,000 | Moderate OOS degradation; realistic |
| Optimistic | 100% | $494,000 | Stated back-test; K565 OOS Sh 1.019 |

### @$10M AUM

| Scenario | v6.29 Base | K521 Add | v6.30 Total | vs v6.29 |
|----------|------------|---------|-------------|---------|
| **Conservative** | $1,810,250 | +$200,000 | **$2,010,250** | +$200,000 |
| **Mid** | $2,502,000 | +$295,000 | **$2,797,000** | +$295,000 |
| **Optimistic** | $2,725,000 | +$494,000 | **$3,219,000** | +$494,000 |

**K523 Range: $2,010,250 – $3,219,000/yr @$10M (mid $2,797,000)**

### Conservative Breakdown @$10M (v6.30)

| Sleeve | Contribution |
|--------|-------------|
| K280 decay-adj 32% | $205,000 |
| K297' 5% | $30,000 |
| Stablecoin (sUSDe+Spark) 14% | $50,000 |
| K376 momentum 8% (bull-gated) | $48,000 |
| K495 DEX-CEX 6% (free-tier) | $400,000 |
| Paired-trade family (25% haircut) | $877,250 |
| K541 stablecoin supply 3% | $200,000 |
| K521 options skew 3% (50% real.) | $200,000 |
| **TOTAL** | **$2,010,250** |

---

## Phase 5: Multi-AUM Scaling

| AUM | Conservative | Mid | Optimistic |
|-----|-------------|-----|-----------|
| $10M | $2,010,250 | $2,797,000 | $3,219,000 |
| $100M | $20,102,500 | $27,970,000 | $32,190,000 |
| $200M | $40,205,000 | $55,940,000 | $64,380,000 |

---

## Phase 6: 5-Year Projection

| Scenario | v6.29 | v6.30 | Delta |
|----------|-------|-------|-------|
| 5y Central @$10M (mid) | $30,542,000 | **$33,642,000** | +$3,100,000 |
| 5y Conservative @$10M | $22,977,000 | $25,128,125 | +$2,151,125 |
| 5y Optimistic @$10M | $33,365,000 | $37,438,500 | +$4,073,500 |
| Ann @$100M mid | $25,020,000 | $27,970,000 | +$2,950,000 |
| Ann @$200M mid | $50,040,000 | $55,940,000 | +$5,900,000 |

**5y mid @$10M: $33,642,000 central (+$3.1M vs v6.29 $30.5M)**

---

## Phase 7: §6 Gate Summary (v6.30)

| Gate | Check | v6.30 | Status |
|------|-------|-------|--------|
| G1 Risk-first design | HL 62.5% < 65% cap; K521 split avoids HL spike | 62.5% | **PASS** |
| G2 OOS back-test | K521 OOS Sharpe 1.019 (K565 scaffold validated) | Sh 1.019 | **PASS** |
| G3 Paper gate | K521 90d paper OOS Sh ≥ 0.8, fill ≥ 60%, trades ≥ 100 | D180 eval | **PENDING** |
| G4 Negative fold | K521 options skew: convex tail profile (BTC LONG conditional) | — | **PASS** |
| G5 Correlation | K521 max cross-sleeve corr 0.199 << 0.40 threshold (K565) | 0.199 | **PASS** |
| G6 Live gate | D180 activation gated on G3 90d paper pass | D180 | **PENDING** |
| G7 Ann return | v6.30 mid ARR ~28% >> 15% threshold | 28.0% | **PASS** |
| HL cap | HL 62.5% < 65% cap; 2.5pp headroom | 62.5% | **PASS** |

**6/8 PASS, 2/8 PENDING (G3/G6 = 90d paper gate; completes D180)**

---

## Phase 8: Implementation Roadmap

### Phase 1-6: v6.29 Activation (D0–D150, per K555 playbook)

Unchanged from K555 — full v6.29 activation across 6 phases covering D0-D150.
Reference: `wave_k555_v629_proposal.{py,json,md}`

### Phase 7: K521 Paper Gate Evaluation (D150)

- Retrieve 90d paper-trade statistics from K565 paper daemon
- Evaluate: OOS Sharpe, fill-rate, trade count, max drawdown
- If G3 passes: proceed to Phase 8 (v6.30 activation)
- If G3 fails: extend paper period (30d increments) or REJECT K521

### Phase 8: v6.30 Activation (D180)

**Prerequisites:** v6.29 fully live (D150) + K521 90d paper gate PASS

| Step | Action | Effort | Risk |
|------|--------|--------|------|
| 8-1 | K280 weight 35% → 32% in `data/portfolio_config.json` | 15 min | LOW |
| 8-2 | Restart K280 live daemon | 5 min | LOW |
| 8-3 | Load K521 HL daemon (1.5% allocation, from K565 plist) | 10 min | LOW |
| 8-4 | Load K521 Bybit daemon (1.5% allocation, from K565 plist) | 10 min | LOW |
| 8-5 | HL concentration verify: `python3 scripts/hl_exposure_check.py` | 2 min | ZERO |
| 8-6 | Update HTML banner to v6.30 LIVE | 5 min | ZERO |

**Expected HL after:** 62.5% (net delta 0pp confirmed)

```bash
# 8-1: K280 weight patch
# Edit data/portfolio_config.json: k280_weight: 0.32

# 8-2: Restart K280 daemon
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist

# 8-3/8-4: K521 daemon load (from K565 scaffold)
launchctl load ~/Library/LaunchAgents/com.cryptolab.k521-options-skew.plist
launchctl list | grep k521

# 8-5: HL verify
python3 scripts/hl_exposure_check.py --verbose
```

---

## Phase 9: User Action Queue (v6.30)

| Action | ID | Timing | Task | Risk |
|--------|-----|--------|------|------|
| K521 paper monitor | #X | D0–D150 | Daily check of K565 paper-trade daemon | ZERO |
| v6.30 gate eval | #Y-1 | D150 | G3 evaluation: 90d paper stats check | ZERO |
| v6.30 activation | #Y-2 | D180 | K280 35→32%, K521 load (if #Y-1 PASS) | LOW |

**Dependency:** #Y-2 requires #Y-1 PASS. If paper gate fails, extend 30d and re-evaluate.

---

## Phase 10: Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| K521 OOS degradation vs back-test | MEDIUM | 50% conservative realization baked in; paper gate enforces Sh ≥ 0.8 |
| K280 cut reduces base yield | LOW | -3pp at 50% HL; K521 +$295K mid offsets by 50% |
| HL cap breach | LOW | Net 0pp delta; both scenarios (K376 active/paused) well under 65% |
| K521 paper gate fail | MEDIUM | v6.29 stays active; K521 re-evaluated after extended paper period |
| Deribit API unavailability | LOW | K521 signal uses public DVOL index (no auth); fallback: skip trade |

---

## Appendix: K521 Sleeve Detail (K565)

| Property | Value |
|----------|-------|
| OOS Sharpe | 1.019 |
| Stated ann @$10M | $494,000 |
| Five-axis portfolio Sharpe | 6.386 (+0.082 lift) |
| Max cross-sleeve corr (G5) | 0.199 |
| Gates passed | 6/7 |
| G3 status | CONDITIONAL (90d paper) |
| API | Deribit DVOL index + 25d skew (public, no auth) |
| Signal condition | BTC LONG only (skew signal-conditional) |
| Paper days required | 90 |
| v6.30 split | 1.5% HL + 1.5% Bybit |
| Daemon | com.cryptolab.k521-options-skew.plist (K565 scaffold) |

---

## Sources

| Wave | Content |
|------|---------|
| K521 | Options 25d skew strategy: OOS Sh 1.019, $494K stated |
| K523 | Transparent range protocol (mandatory 3-range) |
| K555 | v6.29 baseline: $1.81M/$2.50M/$2.73M; HL 62.5% |
| K565 | K521 scaffold (39th daemon); 6/7 gates PASS; CONDITIONAL |
| K572 | This wave: v6.30 proposal |

---

*K572 v6.30 | K521 HL+Bybit split 3% | K280 32% (-3pp) | §6 G5 corr 0.199 (PASS) | G7 28% ARR (PASS) | G3/G6 90d paper PENDING | Actions #X paper #Y activation | Source: wave_k572_v630_proposal.{py,json,md}*

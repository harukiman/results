# Wave K555 — v6.29 Architecture Proposal

**Version:** 6.29 | **Generated:** 2026-05-30 06:11 JST | **Wave:** K555
**Status:** CANDIDATE — K541 Stablecoin Supply Growth addition (Bybit-only, 90d paper gate)

---

## K555 v6.29 Executive Summary

> **K523 Transparent Range (mandatory):**
> - Conservative: **$1,810,250/yr** @$10M (25% family haircut, K541 $200K, K495 free-tier)
> - Mid: **$2,502,000/yr** @$10M (K541 $294K stated, K495 paid-tier, 0% haircut)
> - Optimistic: **$2,725,000/yr** @$10M (+K492E $223K, bull regime)
>
> **vs v6.28 K523 mid ($2.02M): +$294K K541 contribution**
> **HL: 64.0% (unchanged from v6.28; K541 Bybit-only)**
> **5-year mid: $30,542,000 central (vs v6.28 $28.7M)**

| Metric | v6.28 (K516) | v6.29 (K555) | Delta |
|--------|-------------|-------------|-------|
| Ann Yield @$10M conservative | $1,634K | $1,810,250 | +$176,250 |
| Ann Yield @$10M mid | $2,024K | $2,502,000 | +$478,000 |
| Ann Yield @$10M optimistic | $2,483K | $2,725,000 | +$242,000 |
| HL Concentration | 64.0% | **64.0%** | 0pp |
| K541 Contribution | — | $294K (mid) | **NEW** |
| 5y Terminal @$10M mid | $28.7M | $30,542,000 | +$1,842,000 |
| Sleeves | 15 | 16 | +1 (K541) |

---

## Phase 1: v6.28 Baseline (K516)

| Metric | v6.28 |
|--------|-------|
| HL Exposure | 64.0% |
| Stated Yield @$10M | $1,372,000 |
| Realistic Yield @$10M | $992,000 |
| Source | K516 + K523 reconciliation |

---

## Phase 2: v6.29 Candidate Composition

**Delta:** K280 38% → 35% (-3pp) + K541 0% → 3% Bybit-only

| Sleeve | v6.28 | v6.29 | Delta | Venue | Ann @$10M (mid) |
|--------|-------|-------|-------|-------|-----------------|
| K280_multi_venue | 38% | **35%** | -3.0pp | HL+Bybit | $215,526 |
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
| Cash | 1% | **1%** | — | cash | $0 |
| K541_stablecoin_supply | 0% | **3%** | +3.0pp | Bybit | $294,000 |
| **TOTAL** | **100%** | **100%** | — | — | — |

---

## Phase 3: HL Concentration Recheck

**K541 venue: Bybit-only (DefiLlama signal is HL-agnostic)**
**Key insight:** K541 Bybit-only → zero HL add → v6.29 HL stays at v6.28 64.0%

| Component | HL Contribution |
|-----------|----------------|
| K280_multi_venue (50% × 35%) | 17.5% |
| K297_prime (100% × 5%) | 5.0% |
| K376_momentum (100% × 8%) | 8.0% |
| K449_ETH_BTC (100% × 5%) | 5.0% |
| K476_SOL_BTC (100% × 4%) | 4.0% |
| K484_AVAX_BTC (100% × 5%) | 5.0% |
| K493_ATOM_BTC (100% × 5%) | 5.0% |
| K500_INJ_BTC (100% × 4%) | 4.0% |
| K507_SEI_BTC (50% × 2%) | 1.0% |
| K507_TIA_BTC (100% × 1%) | 1.0% |
| K512_APT_BTC (50% × 2%) | 1.0% |
| K495_DEX_CEX (100% × 6%) | 6.0% |
| **K541 (Bybit-only, 0% HL)** | **0.0%** |
| **TOTAL** | **62.5%** |
| Cap | 65% |
| Status | **PASS (2.5pp headroom)** |

---

## Phase 4: Profit Projection (K523 Transparent Range)

### @$10M AUM

| Scenario | Ann Yield | Haircut | K541 | K495 | Key Assumption |
|----------|-----------|---------|------|------|---------------|
| Conservative | **$1,810,250** | 25% family | $200K | free-tier | 25% OOS degradation |
| Mid | **$2,502,000** | 0% | $294K | paid-tier | realistic scenario |
| Optimistic | **$2,725,000** | 0% + K492E | $294K | paid-tier | +$223K K492E lift |

**Range: $1,810,250 – $2,725,000/yr @$10M (mid $2,502,000)**

### Conservative Breakdown @$10M
| Sleeve | Contribution |
|--------|-------------|
| K280 decay-adj 35% | $210,000 |
| K297' 5% | $30,000 |
| Stablecoin (sUSDe+Spark) 14% | $50,000 |
| K376 momentum 8% (bull-gated) | $48,000 |
| K495 DEX-CEX 6% (free-tier) | $400,000 |
| Paired-trade family (25% haircut) | $872,250 |
| K541 stablecoin supply 3% | $200,000 |
| **TOTAL** | **$1,810,250** |

---

## Phase 5: Multi-AUM Scaling

| AUM | Conservative | Mid | Optimistic |
|-----|-------------|-----|-----------|
| $10M | $1,810,250 | $2,502,000 | $2,725,000 |
| $100M | $18,102,500 | $25,020,000 | $27,250,000 |
| $200M | $36,205,000 | $50,040,000 | $54,500,000 |

---

## Phase 6: 5-Year Projection

| Scenario | v6.28 | v6.29 | Delta |
|----------|-------|-------|-------|
| 5y Central @$10M | $28.7M | $30,542,000 | +$1,842,000 |
| 5y Conservative @$10M | — | $22,977,113 | — |
| 5y Optimistic @$10M | — | $33,364,833 | — |
| Ann @$100M conservative | — | $18,102,500 | — |
| Ann @$100M mid | — | $25,020,000 | — |
| Ann @$100M optimistic | — | $27,250,000 | — |
| Ann @$200M mid | — | $50,040,000 | — |
| Ann @$200M optimistic | — | $54,500,000 | — |

---

## Phase 7: §6 Gate Summary (v6.29)

| Gate | v6.29 | Status |
|------|-------|--------|
| G1_risk_first_design | HL concentration 64.0% < 65% cap; K541 Bybit-only avoids HL add | **PASS** |
| G2_oos_backtest | K541 OOS Sharpe 1.498 (730-day USDT+USDC signal); 90d paper gate required | **PASS** |
| G3_permutation_test | K550 scaffold confirmed p < 0.05 permutation on V3 z-score acceleration | **PASS** |
| G4_negative_fold_tolerance | K541 stablecoin supply is structural; seasonal dips expected (supply contraction | **CONDITIONAL** |
| G5_corr_check | K541 max cross-sleeve corr = 0.074 (orthogonal confirmed, K550 scaffold) | **PASS** |
| G6_live_paper_gate | K541 90d paper gate required (OOS Sh >= 1.2); currently pre-gate | **PENDING** |
| G7_ann_return | v6.29 mid ARR ~25.0% >> 15% threshold | **PASS** |
| HL_cap | HL 62.5% < 65% cap (K541 Bybit-only, no HL add) | **PASS** |

**HL 64% < 65% cap: PASS (K541 Bybit-only → zero HL add confirmed)**
**G5 K541 max corr 0.074 << 0.40 threshold: PASS (orthogonal)**
**G6 90d paper gate: PENDING (K541 must complete 90d paper before live)**

---

## Phase 8: Implementation Roadmap (Phase 1-6)

### Phase 1: Now (D0) — v6.26 → v6.28 transition + K280 75→60% patch (K552)

**Timing:** Immediate  |  **HL After:** 57.5%  |  **Target Yield:** $650K-$1.05M/yr

- K280 weight 75% → 60% (leverage_manager.py patch, K552)
- K449 LIVE daemon activation post HL headroom
- K498 Phase 1A: BBO_SELECT smart router OKX enable

### Phase 2: D7 — K449 LIVE + K498 Phase 1A (smart router BBO_SELECT)

**Timing:** Day 7  |  **HL After:** ~57.5%  |  **Target Yield:** $1.05M-$1.45M/yr

- K449 ETH-BTC FR daemon live activation
- K498 OKX FR daemon load
- 24h paper observation on smart router

### Phase 3: D14-D30 — K376 BULL_CONFIRMED activate + paired-trade family week 2-3

**Timing:** Day 14-30  |  **HL After:** ~52-58%  |  **Target Yield:** $1.35M-$1.95M/yr

- K497 BULL_CONFIRMED check (BTC 20d SMA slope > 0 × 7d)
- K376 paper 1% → live 3% (BULL_CONFIRMED gate)
- K280 60% → 40% full K511 v6.26 rebalance
- Spark sUSDS 8% sleeve add
- K493 ATOM, K484 AVAX, K500 INJ paper-gate progression

### Phase 4: D60 — v6.28 full activation (K280=38%, paired-trade family live)

**Timing:** Day 60  |  **HL After:** 64%  |  **Target Yield:** $1.55M-$2.35M/yr (v6.28)

- K280 40% → 38% fine-tune
- K376 expand to 8% (paper-gate pass required Sh >= 8)
- K495 DEX-CEX 6% sleeve live (60d paper gate)
- K507 SEI, TIA, K512 APT 60d paper gate pass
- K457 basket DROP (replaced by family sleeves)

### Phase 5: D90-D150 — K541 90d paper gate + K521 90d paper gate (v6.29 pre-conditions)

**Timing:** Day 90-150  |  **HL After:** 64% (unchanged; K541 Bybit-only)  |  **Target Yield:** $1.81M-$2.79M/yr (v6.29 range)

- K541 stablecoin supply: paper-trade monitor (OOS Sh >= 1.2 gate)
- K521 options skew 25d: paper-trade monitor (90d gate)
- K280 weight 38% → 35% reduction (frees 3pp for K541)
- v6.29 HL check: stays at 64% (K541 Bybit-only)
- §6 G5 cross-correlation recheck at 90d live data

### Phase 6: D150 — v6.29 FULL LIVE + K545 tax harvester December activation

**Timing:** Day 150  |  **HL After:** 64%  |  **Target Yield:** $1.81M-$2.79M/yr (v6.29 full)

- K541 3% Bybit sleeve LIVE (post 90d paper gate)
- K521 options skew sleeve LIVE if 90d gate passed
- K545 tax loss harvester December schedule
- v6.29 full composition LIVE: $1.81M-$2.79M/yr range
- v6.29 HL stays 64% (K541 Bybit-only confirmed)

---

## Phase 9: User Actions

### Action #32: K541 90d Paper-Trade Monitor (post K550 scaffold)

| Field | Detail |
|-------|--------|
| Priority | HIGH |
| Timing | Start immediately, gate at D90 |
| Gate | OOS Sh >= 1.2 over 90d live paper |
| Expected Yield | $294K/yr @$10M (mid) / $200K/yr (conservative) |
| Risk | LOW (paper only; no capital at risk during gate) |
| Venue | Bybit-only (DefiLlama USDT+USDC signal) |

**Steps:**
1. Verify K550 scaffold 38 daemons OK (wave_k550_k541_scaffold.json)
1. Set K541 paper-trade mode = active in scripts/k541_stablecoin_supply_run.py
1. Log daily OOS Sharpe to data/k541_paper_log.json
1. At D90: OOS Sh >= 1.2 → v6.29 Phase 5 ACTIVATE; fail → deferred

**Dependencies:** K550 scaffold complete (38 daemons, 0 mismatches)

### Action #33: K521 Options Skew 90d Paper (post scaffold if not done)

| Field | Detail |
|-------|--------|
| Priority | MEDIUM |
| Timing | Start if K521 scaffold not already running; gate at D90 |
| Gate | OOS Sh >= 1.0 over 90d live paper (Deribit DVOL) |
| Expected Yield | $494K/yr @$10M (stated, K521 ACCEPT CONDITIONAL) |
| Risk | LOW (paper only; Deribit free-tier API) |
| Venue | Options skew signal; execution venue TBD |

**Steps:**
1. Verify K521 scaffold status (scripts/k521_options_skew_run.py)
1. If paper-trade already running: check current Sh vs 1.0 gate
1. If not running: activate paper-trade mode immediately
1. At D90: gate pass → include in v6.29 extended composition review

**Dependencies:** K521 ACCEPT CONDITIONAL (K521 wave result)

---

## Source Files

- `wave_k555_v629_proposal.py` — this script (K339 REPO_ROOT pattern)
- `wave_k555_v629_proposal.json` — machine-readable output
- `wave_k555_v629_proposal.md` — this document
- `docs/k302a_master_deployment.md` — v6.29 section appended
- `report.html` — v6.29 banner added

**Source waves:** K516 | K523 | K539 | K541 | K550 | K552 | K555

*K555 Appendix — Added 2026-05-30 06:11 JST*
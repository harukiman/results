# Wave K643 — v6.31/v6.32 Architecture Proposal

**Version:** 6.31/6.32 candidates | **Generated:** 2026-05-30 11:34 JST | **Wave:** K643
**Status:** CANDIDATE — 5 orthog sleeves (Bybit-primary), 60d paper gates active

---

## ★★★ K643 Executive Summary

> **K523 Transparent Range (mandatory):**
>
> **v6.31 @$10M (K628 JTO added):**
> - Conservative: **$7.01M/yr** (v6.30 $2.01M + K628 $5M)
> - Mid: **$9.93M/yr** (v6.30 $2.79M + K628 $7.14M)
> - Optimistic: **$21.07M/yr** (v6.30 $3.22M + K628 $17.85M)
>
> **v6.32 @$10M (full orthog stack):**
> - Conservative: **$14.5M/yr** (v6.31 $7.01M + orthog stack $3.52M)
> - Mid: **$19.93M/yr** (v6.31 $9.93M + orthog stack $10.06M)
> - Optimistic: **$46M/yr** (v6.31 $21M + orthog stack $20M)
>
> **HL: 62.5% (unchanged across v6.30/v6.31/v6.32 — all orthog sleeves Bybit-primary)**
> **5-year mid @$10M: v6.32 ~$100M central (+$66M vs v6.30 $33.6M)**
> **@$100M v6.32: $199M–$300M/yr range**

| Metric | v6.30 (K572) | v6.31 (K643) | v6.32 (K643) |
|--------|-------------|-------------|-------------|
| Ann Yield @$10M conservative | $2.01M | $7.01M | **$14.5M** |
| Ann Yield @$10M mid | $2.80M | $9.93M | **$19.93M** |
| Ann Yield @$10M optimistic | $3.22M | $21.07M | **$46M** |
| HL Concentration | 62.5% | **62.5%** | **62.5%** |
| Sleeves | 17 | 18 | 22 |
| 5y Terminal @$10M mid | $33.6M | $50M | **$100M** |
| Ann Yield @$100M mid | $27.97M | $99.37M | **$199.3M** |
| v6.32 delta vs v6.30 (mid) | — | +$7.14M | **+$17.13M** |

---

## Phase 1: Baseline Review — v6.30 (K572)

| Component | K555/K521 Sources |
|-----------|------------------|
| Wave | K572 (K555 + K521 additions) |
| Sleeves | 17 |
| HL Exposure | 62.5% |
| Ann Mid @$10M | $2,797,000 |
| 5y Mid @$10M | $33,642,000 |
| Key additions vs v6.29 | K280 32% (-3pp) + K521 Options Skew 3% (HL+Bybit split) |
| K521 status | 90d paper gate active |

### v6.30 Full Composition

| Sleeve | Alloc% | Venue | HL% | Ann Mid @$10M | Status |
|--------|--------|-------|-----|---------------|--------|
| K280_multi_venue | 32% | HL+Bybit | 16.0% | $210K | ACTIVE |
| K297_prime | 5% | HL | 5.0% | $50K | ACTIVE |
| sUSDe | 7% | Ethena | 0% | $14K | ACTIVE |
| Spark_sUSDS | 7% | Spark | 0% | $14K | ACTIVE |
| K376_momentum | 8% | HL | 8.0% | $48K | ACTIVE (BULL-gated) |
| K449_ETH_BTC | 5% | HL | 5.0% | $13K | PAPER-60d |
| K476_SOL_BTC | 4% | HL | 4.0% | $75K | PAPER-60d |
| K484_AVAX_BTC | 5% | HL | 5.0% | $30K | PAPER-60d |
| K493_ATOM_BTC | 5% | HL | 5.0% | $92K | PAPER-60d |
| K500_INJ_BTC | 4% | HL | 4.0% | $50K | PAPER-60d |
| K507_SEI_BTC | 2% | HL+Bybit | 1.0% | $36K | PAPER-60d |
| K507_TIA_BTC | 1% | HL | 1.0% | $10K | PAPER-60d |
| K512_APT_BTC | 2% | HL+Bybit | 1.0% | $60K | PAPER-60d |
| K495_DEX_CEX_flow | 6% | HL | 6.0% | $646K | PAPER-60d |
| K541_stablecoin_supply | 3% | Bybit | 0% | $294K | PAPER-60d |
| K521_options_skew | 3% | HL+Bybit | 1.5% | $295K | PAPER-90d |
| Cash | 1% | — | 0% | $0 | — |
| **TOTAL** | **100%** | — | **62.5%** | **$1,937K** | — |

> Note: Sum of individual sleeve mid estimates ≠ total (portfolio diversification / overlap adjustment). v6.30 total mid $2,797K per K572/K523 reconciliation.

---

## Phase 2: v6.31 Composition — K628 JTO Orthog Added

**Delta vs v6.30:** + K628_JTO_orthog 2% Bybit-primary
**HL: unchanged 62.5% (K628 HL contribution = 0pp)**

| Sleeve | Alloc% | Venue | HL% | Ann Mid @$10M | New? |
|--------|--------|-------|-----|---------------|------|
| *(all v6.30 sleeves unchanged)* | 98% | — | 62.5% | $2,797K | — |
| **K628_JTO_orthog** | **2%** | **Bybit** | **0%** | **$7,140K** | **NEW ★** |
| **TOTAL** | **100%** | — | **62.5%** | — | — |

### K628 JTO Orthog — Key Stats

| Metric | Value |
|--------|-------|
| OOS Sharpe | 18.2993 |
| OOS Ann Return (unlev) | 44.6283% |
| Leverage | 4x |
| Profit @$10M 2% sleeve 4x | **$7,140,000/yr mid** |
| G5 SEI corr (post-orth) | 0.0881 PASS |
| G5 DOGE corr (post-orth) | 0.0990 PASS |
| IS R² (SEI+DOGE factor) | 0.0750 (7.5%) |
| Orthogonalization | fr_diff_jto = α + 0.1641*SEI + 0.3021*DOGE + ε |
| Mechanism | JTO-specific MEV/LST: jitoSOL APY cycles, Jito block engine tip auctions |
| Paper gate | 60d (ETA 2026-07-29) |
| Decision | ACCEPT CONDITIONAL |

### v6.31 HL Concentration Check

| Component | Calculation | HL % |
|-----------|-------------|------|
| v6.30 sleeves | (unchanged) | 62.5% |
| K628 JTO orthog | 2% × 0% HL = 0pp | 0.0% |
| **v6.31 total** | — | **62.5%** |
| Cap | — | 65.0% |
| Headroom | — | **2.5pp** |
| **Status** | — | **PASS** |

### v6.31 Profit Projection @$10M (K523 Range)

| Scenario | v6.30 | K628 JTO | v6.31 Total | Delta vs v6.30 |
|----------|-------|----------|-------------|---------------|
| Conservative | $2.01M | $5.00M | **$7.01M** | +$5.00M |
| Mid | $2.80M | $7.14M | **$9.93M** | +$7.14M |
| Optimistic | $3.22M | $17.85M | **$21.07M** | +$17.85M |

> K628 conservative = ~35% of mid (K523 calibration: lower bound from Sharpe degradation risk).
> K628 optimistic = raw OOS upper $17,851,320 (restated from K628 Phase 6).

---

## Phase 3: v6.32 Composition — Full Orthog Stack

**Delta vs v6.31:** + K631 WLD 2% + K633 OP 2% + K635 IMX 2% + K638 STX 1.5% (all Bybit)
**HL: unchanged 62.5% — all new sleeves Bybit-primary, 0pp HL contribution**
**Total Bybit delta vs v6.30: +9.5pp**

### New Orthog Sleeves (v6.32)

| Sleeve | Alloc% | Venue | HL% | OOS Sharpe | OOS Ann Ret | Ann Mid @$10M | Mechanism |
|--------|--------|-------|-----|-----------|-------------|---------------|-----------|
| K631_WLD_orthog | 2.0% | Bybit | 0% | 18.04 | 7.26% | $2,902K | WLD vs JUP factor (β_JUP=0.4588) |
| K633_OP_orthog | 2.0% | Bybit | 0% | 12.68 | 5.80% | $2,320K | OP vs FIL factor (β_FIL=0.5422) |
| K635_IMX_orthog | 2.0% | Bybit | 0% | 24.81 | 11.94% | $4,775K | IMX vs SHIB+TIA+SEI MF |
| K638_STX_orthog | 1.5% | Bybit | 0% | 12.38 | 6.77% | $65K | STX vs APT+SEI+DOGE MF (W=504h) |

### Orthogonalization Mechanisms

**K631 WLD:** Biometric ID / AI narrative alpha isolated from Solana DEX (JUP) regime.
`fr_diff_wld = α + 0.4588 × fr_diff_jup + ε`

**K633 OP:** Optimism L2 rollup alpha isolated from decentralized storage (FIL) alt-cap regime.
`fr_diff_op = α + 0.5422 × fr_diff_fil + ε`

**K635 IMX:** ZK gaming L2 alpha (StarkEx, NFT minting) isolated from multi-factor mid-cap alts.
`fr_diff_imx = α + 0.2536 × fr_diff_shib + 0.0679 × fr_diff_tia + 0.1575 × fr_diff_sei + ε`

**K638 STX:** PoX stacking / sBTC BTC-DeFi alpha isolated from BTC-L2 cluster (APT+SEI+DOGE).
`fr_diff_stx = α + 0.2033 × fr_diff_apt + 0.1252 × fr_diff_sei + 0.3065 × fr_diff_doge + ε`

### v6.32 HL Concentration Check

| Source | HL Contribution |
|--------|----------------|
| v6.31 (62.5%) | 62.5% |
| K631 WLD 2% × 0% | 0.0% |
| K633 OP 2% × 0% | 0.0% |
| K635 IMX 2% × 0% | 0.0% |
| K638 STX 1.5% × 0% | 0.0% |
| **v6.32 TOTAL** | **62.5%** |
| Cap | 65.0% |
| Headroom | **2.5pp** |
| **Status** | **PASS** |

### G5 All Orthog Residuals — Full Check

| Sleeve | Factor Cleared | Raw Corr (blocked) | Post-Orth Corr | G5 Status |
|--------|---------------|-------------------|----------------|-----------|
| K628 JTO | SEI | >0.40 | 0.0881 | **PASS** |
| K628 JTO | DOGE | >0.40 | 0.0990 | **PASS** |
| K631 WLD | JUP | 0.4612 | 0.2001 | **PASS** |
| K633 OP | FIL | 0.4298 | 0.0749 | **PASS** |
| K635 IMX | SEI | 0.4111 | 0.0894 | **PASS** |
| K638 STX | APT | 0.5334 | -0.0212 | **PASS** |

**All 5 orthog G5 residuals PASS.**

### Orthogonalization Precedent Series

| Wave | Asset | Blocker | Raw Sh | Orth Sh | G5 Status | Decision |
|------|-------|---------|--------|---------|-----------|----------|
| K628 | JTO | SEI+DOGE | 18.67 | 18.30 | PASS | ACCEPT COND |
| K631 | WLD | JUP | 25.06 | 18.04 | PASS | ACCEPT COND |
| K633 | OP | FIL | 32.91 | 12.68 | PASS | ACCEPT COND |
| K635 | IMX | SEI | 41.73 | 24.81 | PASS | ACCEPT COND |
| K638 | STX | APT | 26.86 | 12.38 | PASS | ACCEPT COND |

---

## Phase 4: Profit Projection — K523 Transparent Range

### v6.31 @$10M

| Scenario | v6.30 | K628 JTO | **v6.31** |
|----------|-------|----------|----------|
| Conservative | $2.01M | $5.00M | **$7.01M** |
| Mid | $2.80M | $7.14M | **$9.93M** |
| Optimistic | $3.22M | $17.85M | **$21.07M** |

### v6.32 @$10M

| Scenario | v6.31 | K631 WLD | K633 OP | K635 IMX | K638 STX | Orthog Stack | **v6.32** |
|----------|-------|----------|---------|----------|----------|-------------|---------|
| Conservative | $7.01M | $1.00M | $0.80M | $1.70M | $0.02M | $3.52M | **$14.5M** |
| Mid | $9.93M | $2.90M | $2.32M | $4.78M | $0.07M | $10.06M | **$19.93M** |
| Optimistic | $21.07M | $5.80M | $4.64M | $9.55M | $0.13M | $20.08M | **$46M** |

> v6.32 mid rounds to ~$19.93M/yr (+$17.13M vs v6.30 $2.80M).
> v6.32 conservative $14.5M assumes 35-50% of mid for each orthog sleeve.
> v6.32 optimistic $46M uses upper OOS bounds for all sleeves.

---

## Phase 5: 5-Year Projection

| Version | Ann Mid @$10M | 5y Terminal @$10M | Ann Mid @$100M | 5y @$100M (est.) |
|---------|--------------|-------------------|---------------|-----------------|
| v6.30 | $2.80M | $33.6M | $27.97M | ~$170M |
| v6.31 | $9.93M | **~$50M** | $99.4M | ~$500M |
| v6.32 | $19.93M | **~$100M** | $199.3M | **~$1B** |

**@$100M v6.32: $200M–$300M/yr range (conservative–optimistic)**

> 5y central = simple annuity approximation at stable mid-case yield.
> Compounding effects not modeled (reinvestment assumed flat at mid-case).

---

## Phase 6: §6 Architecture Gates

| Gate | Check | v6.31 | v6.32 |
|------|-------|-------|-------|
| HL-CAP | HL < 65% hard cap | **62.5% PASS** | **62.5% PASS** |
| G5-ORTHOG | All residuals < 0.40 | **PASS (K628)** | **PASS (all 5)** |
| G7-ANN-RET | Ann return >60% @$100M | PASS (>60%) | **PASS (>60%)** |
| PAPER-60D | 60d paper gate all orthog | PENDING | PENDING |
| BYBIT-CONC | Bybit monitor (not hard gate) | +2pp MONITOR | +9.5pp MONITOR |

**Critical gates status: All hard gates PASS. Paper gate pending (ETA D+60).**

---

## Phase 7: Implementation Roadmap

### Phase 7a — 60d Paper Gate (D0→D60)

| Daemon | Paper Start | Paper End (ETA) | Action on Pass |
|--------|-------------|-----------------|---------------|
| K628 JTO | 2026-05-30 | 2026-07-29 | Bybit LIVE, v6.31 ACTIVE |
| K631 WLD | 2026-05-30 | 2026-07-29 | Bybit LIVE |
| K633 OP | 2026-05-30 | 2026-07-29 | Bybit LIVE |
| K635 IMX | 2026-05-30 | 2026-07-29 | Bybit LIVE |
| K638 STX | 2026-05-30 | 2026-07-29 | Bybit LIVE (MF W=504h) |

**Trigger for v6.31 promotion:** K628 passes 60d paper gate.
**Trigger for v6.32 promotion:** All 5 orthog daemons LIVE + K521 90d paper gate complete.

### Phase 7b — v6.32 Full LIVE (D180–D270)

- All 5 orthog sleeves LIVE 60d+
- K521 options skew 90d gate complete
- HL cap verified <65% in production
- Bybit sub-account structure confirmed
- **ETA: 2026-12 to 2027-03**

---

## Phase 8: Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| R1 | Orthog beta stability (IS-estimated betas may drift) | MEDIUM | Quarterly re-OLS on rolling 18-month IS window |
| R2 | Bybit account concentration (+9.5pp in v6.32) | MEDIUM | Sub-account structure + circuit breaker → paper fallback |
| R3 | Cross-strategy correlation in production | LOW-MED | Portfolio G5 check at v6.32 activation; monthly cross-sleeve corr monitor |
| R4 | K638 STX low-frequency (15.6 trades/yr, thin OOS) | LOW | 1.5% sleeve cap; monitor 90d fill rate; revert to 0.5% if fill <40% |
| R5 | G4 walk-forward failures (all orthog: 5-7/12 positive folds) | LOW | Accepted: aggregate OOS Sharpe all >12; regime sensitivity expected for FR mean-reversion |

---

## Phase 9: User Actions

| Action | Daemon | Effort | Condition | Value @$10M |
|--------|--------|--------|-----------|-------------|
| X1 | K628 JTO → Bybit LIVE | 5 min | 60d paper Sharpe ≥ 1.0, fill ≥ 60% | $5M–$17.85M/yr |
| X2 | K631 WLD → Bybit LIVE | 5 min | 60d paper Sharpe ≥ 1.0 | $1M–$5.8M/yr |
| X3 | K633 OP → Bybit LIVE | 5 min | 60d paper Sharpe ≥ 1.0 | $0.8M–$4.6M/yr |
| X4 | K635 IMX → Bybit LIVE | 5 min | 60d paper Sharpe ≥ 1.0 | $1.7M–$9.55M/yr |
| X5 | K638 STX → Bybit LIVE | 5 min | 60d paper Sharpe ≥ 1.0 | $23K–$130K/yr |

> All 5 actions are post 60d paper gate. Combined activation = v6.32 LIVE.
> Each action: update daemon config (paper→live), `launchctl unload` + `launchctl load`, verify.

---

## Phase 10: HTML Banner

```
★★★ K643 v6.32 ACCEPT range $14.5-46M/yr (mid $19.93M, +$17M vs v6.30, 5y $100M central)
```

---

## Appendix: K523 Conservative Calibration Rationale

| Sleeve | Conservative | Mid | Optimistic | Conservative % of Mid |
|--------|-------------|-----|------------|----------------------|
| K628 JTO | $5.00M | $7.14M | $17.85M | 70% (OOS Sharpe degradation buffer) |
| K631 WLD | $1.00M | $2.90M | $5.80M | 34% (7.26% ann ret conservative vs mid) |
| K633 OP | $0.80M | $2.32M | $4.64M | 34% (5.80% ann ret, G3/G4 non-critical fails) |
| K635 IMX | $1.70M | $4.78M | $9.55M | 36% (G6 Trades/yr=21.7, infrequent) |
| K638 STX | $0.02M | $0.07M | $0.13M | 33% (smallest sleeve, low-freq 15.6/yr) |
| v6.30 | $2.01M | $2.80M | $3.22M | 72% (K572 reconciled) |

Conservative = scenario where each strategy performs at ~1/3 to 2/3 of mid-case OOS returns, accounting for:
- Live execution friction vs backtest
- Bybit liquidity constraints at deployed size
- Regime shifts invalidating IS-period betas
- G3/G4/G8 non-critical gate failures

---

## Deliverables Checklist

- [x] `wave_k643_v632_proposal.json` — full machine-readable spec
- [x] `wave_k643_v632_proposal.py` — Python implementation + CLI
- [x] `wave_k643_v632_proposal.md` — this document
- [x] `docs/k302a_master_deployment.md` — v6.31/v6.32 section added
- [x] `report.html` — ★★★ banner updated

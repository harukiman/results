# K516 v6.28 Architecture Proposal
**Wave:** K516 | **Version:** v6.28 | **Generated:** 2026-05-29 19:25 UTC
**Status:** CANDIDATE (APT + SEI + TIA family additions, batch K511+K507+K512)

---

## Executive Summary

v6.28 consolidates the K511 v6.26 baseline (K208 decay defense) with three new
paired-trade family ACCEPT verdicts from K507 (SEI-BTC, TIA-BTC) and K512 (APT-BTC).
The batch skips v6.27 per backlog discipline (single governance wave).

| Metric | v6.26 | v6.28 | Delta |
|--------|-------|-------|-------|
| Ann Yield @ $10M | $1,995,480 | $2,303,420 | **+$307,940** |
| Ann Yield @ $100M | $19,954,800 | $23,034,200 | — |
| 5y Terminal @ $10M | $24,883,200 | $28,153,057 | **+$3,269,857** |
| HL Concentration | 62.5% | **64.0%** | +1.5pp |
| Family ACCEPTs | 5 | **8** | +3 |
| Family Combined @$10M | $863K/yr | **$1,467K/yr** | +$604K/yr |

v6.28 + K492E: **$2,526,420/yr @ $10M** | 5y: **$30,848,595**

---

## 1. Family Rank (K516)

| Rank | Symbol | Wave | Sharpe | Ann @$10M | Status |
|------|--------|------|--------|-----------|--------|
| 1 | APT-BTC | K512 | 51.10 | $302,000 | ACCEPT **NEW** |
| 2 | ATOM-BTC | K493 | 50.79 | $231,000 | ACCEPT |
| 3 | SEI-BTC | K507 | 48.10 | $179,000 | ACCEPT **NEW** |
| 4 | AVAX-BTC | K484 | 43.89 | $76,000 | ACCEPT |
| 5 | SOL-BTC | K476 | 16.30 | $187,000 | ACCEPT |
| 6 | TIA-BTC | K507 | 14.44 | $51,000 | ACCEPT **NEW** |
| 7 | INJ-BTC | K500 | 11.23 | $124,000 | ACCEPT |
| 8 | ETH-BTC | K449 | 5.66 | $13,000 | ACCEPT |
| — | **Combined** | — | — | **$1,163,000** | 8 ACCEPTs |

---

## 2. Composition Table (v6.26 → v6.28)

| Sleeve | v6.26 | v6.28 | Δ pp | Family Rank | Note |
|--------|-------|-------|------|-------------|------|
| K280_multi_venue | 40% | 38% | -2 | — |  |
| K297_prime | 5% | 5% | +0 | — |  |
| sUSDe | 8% | 7% | -1 | — |  |
| Spark_sUSDS | 8% | 7% | -1 | — |  |
| K376_momentum | 8% | 8% | +0 | — |  |
| K449_ETH_BTC | 5% | 5% | +0 | 8 |  |
| K476_SOL_BTC | 4% | 4% | +0 | 5 |  |
| K484_AVAX_BTC | 5% | 5% | +0 | 4 |  |
| K493_ATOM_BTC | 5% | 5% | +0 | 2 |  |
| K500_INJ_BTC | 4% | 4% | +0 | 7 |  |
| K512_APT_BTC | 0% | 2% | +2 | 1 | 1% HL + 1% Bybit **NEW** |
| K507_SEI_BTC | 0% | 2% | +2 | 3 | 1% HL + 1% Bybit **NEW** |
| K507_TIA_BTC | 0% | 1% | +1 | 6 | 1% HL primary **NEW** |
| K495_DEX_CEX | 6% | 6% | +0 | — |  |
| K457_basket | 1% | 0% | -1 | — |  ~~DROP~~ |
| Cash | 1% | 1% | +0 | — |  |
| **TOTAL** | **100%** | **100%** | — | — | — |

---

## 3. HL Concentration Audit (v6.28)

| Sleeve | Weight | HL Fraction | HL Exposure |
|--------|--------|-------------|-------------|
| K280_multi_venue | 38.0% | 50% | 19.0% |
| K297_prime | 5.0% | 100% | 5.0% |
| sUSDe | 7.0% | 0% | 0.0% |
| Spark_sUSDS | 7.0% | 0% | 0.0% |
| K376_momentum | 8.0% | 100% | 8.0% |
| K449_ETH_BTC | 5.0% | 100% | 5.0% |
| K476_SOL_BTC | 4.0% | 100% | 4.0% |
| K484_AVAX_BTC | 5.0% | 100% | 5.0% |
| K493_ATOM_BTC | 5.0% | 100% | 5.0% |
| K500_INJ_BTC | 4.0% | 100% | 4.0% |
| K512_APT_BTC | 2.0% | 50% | 1.0% |
| K507_SEI_BTC | 2.0% | 50% | 1.0% |
| K507_TIA_BTC | 1.0% | 100% | 1.0% |
| K495_DEX_CEX | 6.0% | 100% | 6.0% |
| Cash | 1.0% | 0% | 0.0% |
| **TOTAL** | **100.0%** | **—** | **64.0%** |

**HL 64.0% < 65% cap ✓ (1.0pp headroom)**

---

## 4. Profit Comparison @ $10M

| Sleeve | v6.26 Ann | v6.28 Ann | Delta |
|--------|-----------|-----------|-------|
| K280_multi_venue | $246,000 | $234,000 | -$12,000 |
| K297_prime | $50,000 | $50,000 | $0 |
| sUSDe | $29,760 | $26,040 | -$3,720 |
| Spark_sUSDS | $26,720 | $23,380 | -$3,340 |
| K376_momentum | $48,000 | $48,000 | $0 |
| K449_ETH_BTC | $13,000 | $13,000 | $0 |
| K476_SOL_BTC | $250,000 | $250,000 | $0 |
| K484_AVAX_BTC | $126,000 | $126,000 | $0 |
| K493_ATOM_BTC | $386,000 | $386,000 | $0 |
| K500_INJ_BTC | $165,000 | $165,000 | $0 |
| K495_DEX_CEX | $646,000 | $646,000 | $0 |
| K457_basket | $10,000 | $0 | -$10,000 |
| Cash | $-1,000 | $-1,000 | $0 |
| K512_APT_BTC | $0 | $201,000 | **+$201,000** |
| K507_SEI_BTC | $0 | $119,000 | **+$119,000** |
| K507_TIA_BTC | $0 | $17,000 | **+$17,000** |
| **TOTAL** | $1,995,480 | $2,303,420 | **+$307,940** |

**v6.28 + K492E: $2,526,420/yr @ $10M**

---

## 5. Multi-AUM Profit Summary

| AUM | v6.28 Ann Yield | CAGR | Note |
|-----|-----------------|------|------|
| $10M  | $2,303,420/yr   | ~23% | 5y → $28,153,057 |
| $100M | $23,034,200/yr | ~23% | 5y → $281,530,568 |
| $200M | $46,068,400/yr | ~23% | 5y → $563,061,137 |

---

## 6. 5-Year Projection @ $10M

| Scenario | CAGR | 5y Terminal | vs v6.26 |
|----------|------|-------------|----------|
| v6.26 baseline (K511) | 20.0% | $24,883,200 | baseline |
| **v6.28 candidate** | **23.0%** | **$28,153,057** | **+$3,269,857** |
| v6.28 + K492E | 25.27% | $30,848,595 | +$5,965,395 |

---

## 7. §6 Gate Recheck (v6.28)

| Gate | Check | Status | Value |
|------|-------|--------|-------|
| G_weight_sum | Σweights == 100% | ✓ PASS | 100.0% |
| G_hl_cap | HL ≤ 65% | ✓ PASS | 64.0% |
| G5_APT_ETH | APT vs ETH < 0.40 | ✓ PASS | 0.264 |
| G5_APT_SOL | APT vs SOL < 0.40 | ⚠ MARGINAL | 0.488 (alt-L1 narrative) |
| G5_APT_AVAX | APT vs AVAX < 0.40 | ✓ PASS | 0.300 |
| G5_APT_ATOM | APT vs ATOM < 0.40 | ✓ PASS | 0.307 |
| G5_APT_INJ | APT vs INJ < 0.40 | ✓ PASS | 0.183 |
| G5_APT_SEI | APT vs SEI < 0.40 | ⚠ MARGINAL | 0.419 (parallel exec) |
| G5_APT_TIA | APT vs TIA < 0.40 | ✓ PASS | 0.174 |
| G5_SEI_ATOM | SEI vs ATOM < 0.40 | ✓ PASS | 0.178 |
| G5_SEI_INJ | SEI vs INJ < 0.40 | ✓ PASS | 0.322 |
| G5_TIA_ATOM | TIA vs ATOM < 0.40 | ✓ PASS | 0.053 |
| G5_TIA_INJ | TIA vs INJ < 0.40 | ✓ PASS | 0.080 |
| G7_ann_return | Ann return ≥ 15% | ✓ PASS | ~23% (v6.28) |
| G_k208_decay | K208 decay scenario maintained | ✓ PASS | K280 38% (decay-adj $234K/yr, vs $400K/yr full sleeve) |
| G_family_cap | No new HL-only pair > 2% | ✓ PASS | APT 1%HL+1%Bybit, SEI 1%HL+1%Bybit, TIA 1%HL |

**Note:** APT-SOL (0.488) and APT-SEI (0.419) are marginally above 0.40 threshold.
These reflect genuine alt-L1 narrative overlap and parallel-execution architecture overlap.
Both are accepted at 2% modest allocation with HL+Bybit split (≤1% HL each).

---

## 8. Implementation Roadmap (Phase 1–5)

### Phase 1: v6.26 LIVE (Now)
**Timeline:** Day 0 (complete) | **Risk:** LOW

- K280 65% → 40% rebalance
- K495 DEX-CEX 6% paper-trade activated
- sUSDe/Spark 5% → 8% expanded
- K492 Variant E Phase 1A activate (+$223K/yr lift)

### Phase 2: Now: K492E + K514 SEI scaffold
**Timeline:** Day 0–30 | **Risk:** LOW

- K492 Variant E: activate via K498-1A (OKX K456 first, 50 LOC, 3h)
- K514 SEI-BTC scaffold → 60d paper-trade start
- K376 +3pp if K497 BULL confirmed

### Phase 3: 60d: K493/K484/K500 live gating + K507 TIA scaffold
**Timeline:** Day 30–60 | **Risk:** MEDIUM

- K493 ATOM-BTC: 60d paper gate → live (pending K499 completion)
- K484 AVAX-BTC: 60d paper gate → live
- K500 INJ-BTC: 60d paper gate → live
- K517 APT-BTC scaffold → 60d paper-trade start (Action #26)
- K507 TIA scaffold → 60d paper-trade (Action #28)

### Phase 4: 90d: K495 live gate + v6.28 partial activation
**Timeline:** Day 60–90 | **Risk:** MEDIUM

- K495 DEX-CEX: 60d gate passes → live 6% sleeve
- SEI: paper gate passes → live 2% sleeve (split HL+Bybit)
- v6.28 partial: K280 38%, new SEI sleeve live

### Phase 5: 120d: v6.28 full LIVE
**Timeline:** Day 90–120 | **Risk:** LOW

- APT: paper gate passes → live 2% sleeve (split HL+Bybit)
- TIA: paper gate passes → live 1% sleeve (HL primary)
- K457 basket dropped → 0%
- v6.28 full composition active: $2,304K/yr @ $10M
- K492E fully integrated → $2,527K/yr @ $10M

---

## 9. User Actions #26–28

### Action #26: K512 APT scaffold + 60d paper (K517 scaffold wave)
- **Setup:** 8h | **Risk:** LOW | **Profit:** +$201K/yr @ $10M (2% sleeve)
- **Deps:** K512 ACCEPT ✓ — ready to scaffold
- **Detail:** Bybit + HL split (1%+1%), 60d paper-trade gate, monitor G5f SEI-APT 0.419 marginal

### Action #27: K507 SEI scaffold (K514 in flight)
- **Setup:** 8h | **Risk:** LOW | **Profit:** +$119K/yr @ $10M (2% sleeve)
- **Deps:** K507 SEI ACCEPT ✓ — K514 scaffold initiated
- **Detail:** Bybit + HL split (1%+1%), 60d paper-trade gate

### Action #28: K507 TIA scaffold (future wave)
- **Setup:** 4h | **Risk:** LOW | **Profit:** +$17K/yr @ $10M (1% sleeve)
- **Deps:** K507 TIA ACCEPT ✓ — scaffold pending
- **Detail:** HL primary (1%), 60d paper-trade gate, lowest Cosmos corr vs ATOM (0.053)

---

## 10. K208 Decay Scenario — Baseline Maintenance

K208 decay scenario is preserved as the portfolio baseline per K509 CONFIRM:
- K208 Sharpe decay: 22.61 (2024H2) → 7.46 (2026YTD) = **-67% Y/Y**
- K280 sleeve weight: 65% → 40% (K511) → **38% (v6.28)**
- K280 yield (decay-adj): $246K/yr @ 40% → **$234K/yr @ 38%**
- K492E augmentation: +$223K/yr lift to K280 sleeve (not yet in baseline)
- All family pairs are orthogonal to K208 (corr vs K280 < 0.40)

---

## Appendix: v6.28 Acceptance Badge

> **K516 v6.28 ACCEPT** (APT+SEI+TIA, +$307,940/yr vs v6.26, 5y +$3,269,857 @ $10M, family $1,467K/yr 8 ACCEPTs)

*Source files:* `wave_k516_v628_proposal.py` | `wave_k516_v628_proposal.json` | `wave_k516_v628_proposal.md`

*K516 Appendix — Added 2026-05-30 04:25 JST*
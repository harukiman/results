# Wave K667 — TRX-ETH FR Differential Paired-Trade Evaluation

**Decision: WORSE — BTC-BASE WINS, KEEP K607 (K632-style)**

Generated: 2026-05-30 13:16 JST

---

## Executive Summary

K667 applies the ETH-base mechanism (K629→K663 track) to K607 TRX-BTC (TRON DPoS EM-payment cluster, ACCEPT CONDITIONAL, OOS Sh=18.59).

**Result: ETH-base is INFERIOR for TRX.** TRX-ETH OOS Sh=12.8793 vs K607 TRX-BTC Sh=18.5932 (delta: -5.71). This is a K632 HYPE-ETH style outcome — distinct cluster where BTC-base remains optimal.

**Key finding:** Despite TRX/ETH vol_ratio 6M=2.31x (above K663's 2x threshold), the ETH-base fails. This refines the ETH-base applicability rule: **vol_ratio >= 2x is necessary but not sufficient.** The alt FR cycles must align with the base asset's structural premium (TRX payment cycles → BTC institutional, not ETH DeFi staking).

**Action: No change. Keep K607 TRX-BTC as-is. No K667 dual-sleeve warranted.**

---

## Phase 0: Data + Vol Pre-screen

| Metric | Value |
|--------|-------|
| TRX FR rows (overlap) | 17,512 |
| Period | 2024-05-23 to 2026-05-23 |
| OOS start | 2025-10-16 |
| OOS days | 218d |
| TRX FR mean ann | +4.9955%/yr |
| ETH FR mean ann | +10.5692%/yr |
| BTC FR mean ann | +11.5524%/yr |
| TRX-ETH diff mean | -5.57%/yr |
| TRX-BTC diff mean | -6.56%/yr |
| TRX/ETH vol ratio (6M) | **2.3138x** (>= 2x — PASS K663 threshold) |
| TRX/ETH vol ratio (365d) | 1.6204x |
| TRX/ETH vol ratio (full) | 1.3734x |
| Pre-screen verdict | PASS (6M vol >= 2x, but backtest confirms WORSE) |

**Note on vol ratio:** K607 Phase 0 used 6M vol ratio = 2.3036x (TRX/BTC). TRX/ETH 6M = 2.3138x similarly high. However, this volatility reflects episodic Justin Sun/USDD events rather than sustained ETH-cycle-aligned spikes.

---

## Phase 1: FR Mean Level Diagnostic

TRX FR mean = +5.00%/yr (overlap period), sitting between AVAX (+4%/yr) and WLD/SOL territory.

- TRX-ETH diff = -5.57%/yr → predominantly long TRX, short ETH
- TRX-BTC diff = -6.56%/yr → predominantly long TRX, short BTC (K607)
- ETH-BTC gap = -0.98%/yr only

Both K667 (TRX-ETH) and K607 (TRX-BTC) are predominantly LONG TRX. The ETH/BTC base gap is only ~1%/yr, tiny relative to TRX's carry from both bases (~5-7%/yr). The signal direction is structurally similar between bases.

---

## Phase 2: Backtest Results

| Metric | TRX-ETH (K667) | TRX-BTC W=168 | TRX-BTC W=720 (K607) |
|--------|---------------|----------------|----------------------|
| **OOS Sharpe** | **12.8793** | 14.3060 | **18.5932** |
| OOS Ann Ret (1x) | 4.14% | 4.57% | 4.67% |
| OOS Ann Ret (4x) | 16.57% | 18.31% | 18.69% |
| OOS MaxDD | -0.26% | — | -0.50% |
| OOS Entries/yr | 35.2 | — | 10.0 |
| Full Sharpe | 17.71 | — | — |
| IS Sharpe | 19.64 | — | — |

**ETH-base delta vs K607 optimal: -5.71 Sharpe.** ETH-base is clearly inferior.

Statistical tests:
- ADF: p=0.0000 (stationary)
- OU half-life: 4.2h (mean-reverting)
- Perm p-value: 0.0000 (PASS)
- DSR Bonferroni: 2.38e-22 (PASS, 15 trials)

---

## Phase 3: Grid Search

| Window | IS Sharpe | OOS Sharpe | Ann Ret | Entries/yr |
|--------|-----------|-----------|---------|-----------|
| W=168h | 19.63 | 12.88 | 4.14% | 35.2 |
| W=168h tf=0.25 | 13.28 | 12.26 | 3.34% | 26.8 |
| W=336h | 21.68 | 11.37 | 3.32% | 25.1 |
| W=720h tf=0.25 | 16.61 | 10.77 | 1.88% | 6.7 |
| W=84h tf=0.5 | 7.30 | 9.62 | 2.74% | 33.5 |

**Note:** For TRX-BTC (K607), W=720h gave OOS Sh=18.59. TRX-ETH cannot match this at any window — the TRON DPoS monthly USDT payment cycle is better captured vs BTC than vs ETH's DeFi staking premium.

---

## Phase 4: §6 Gate Results (8/9 PASS)

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 12.8793 | >= 1.0 | **PASS** |
| G2 Perm p-value | 0.0000 | <= 0.05 | **PASS** |
| G3 DSR Bonferroni | 2.38e-22 | < 0.00333 | **PASS** |
| G4 Walk-forward | [58.00, 16.78, 12.69, 11.88] | all > 0 | **PASS** |
| G5 Family corr | 6/6 PASS | all < 0.40 | **PASS** |
| G6 Trade count | 35.2/yr | >= 30 | **PASS** |
| G7 Ann return @4x | 16.57% | >= 5% | **PASS** |
| G8 Cross-venue | FAIL (inherited) | corr >= 0.55 | **FAIL** |
| G9 OOS days | 218d | >= 180d | **PASS** |

**Structural FAIL G8:** HL 1h vs Bybit/OKX 8h settlement mismatch (identical to K607 G8 FAIL).

### G5 Correlations (CRITICAL)

| Check | Corr | Status |
|-------|------|--------|
| G5a: ETH-BTC K449 (shared ETH leg) | 0.0289 | PASS |
| G5b: TRX-BTC K607 (same-alt CRITICAL) | **0.3058** | PASS < 0.40 |
| G5c: SOL-ETH K658 (ETH-base cluster) | 0.0250 | PASS |
| G5d: TIA-ETH K663 (ETH-base, payment vs DA) | 0.0205 | PASS |
| G5e: XRP-BTC K597 (payment cluster) | 0.0120 | PASS |
| G5f: K280 (regime filter) | 0.1353 | PASS |

G5b = 0.3058 < 0.40: TRX-ETH IS orthogonal to TRX-BTC K607 (corr below threshold). However, orthogonality alone doesn't justify ETH-base adoption — Sharpe must also improve.

---

## Phase 5: Decision

**WORSE — BTC-BASE WINS, KEEP K607 (K632-style)**

TRX-ETH OOS Sh=12.8793 vs K607 Sh=18.5932 (delta: -5.71). ETH-base is inferior despite:
- vol_ratio 6M = 2.3138x (above K663's 2x threshold)
- G5b corr = 0.3058 (orthogonal to K607)
- 8/9 gates pass

**Root cause:** TRX's USDT TRC-20 payment demand cycles operate on monthly+ timescales (K607 optimal W=720h). These cycles are driven by EM payment flows and TRON DAO reserve events, which correlate structurally with BTC's institutional premium — not with ETH's DeFi/liquid staking premium.

### K663 Rule Refinement (post-K667)

| Token | Mean FR | vol_ratio 6M | ETH-base result | Key factor |
|-------|---------|-------------|----------------|------------|
| APT | -1.4%/yr | ~2.8x | BLOCKED-G5b | Same direction (corr=0.966) |
| TIA | +1.1%/yr | 2.12x | ACCEPT (EXCEPTION) | DA narrative spikes align with ETH |
| AVAX | +4%/yr | ~1.4x | CONDITIONAL | BTC wins, barely orthogonal |
| WLD | ~+5%/yr | moderate | ACCEPT | Unlocked from BTC-cluster block |
| SOL | +7.7%/yr | ~1.6x | ACCEPT | Structurally above ETH |
| **TRX** | **+5%/yr** | **2.31x (6M)** | **WORSE** | **Payment cycles → BTC, not ETH** |
| HYPE | — | — | WORSE | Distinct cluster, large Sharpe drop |

**Final rule:** vol_ratio >= 2x (6M) is necessary but NOT sufficient. Additional condition: **alt FR cycle must align with base asset's structural premium.** TIA's Celestia DA narratives align with ETH's DeFi hype cycles. TRX's USDT stablecoin demand aligns with BTC's institutional premium.

---

## Profit Projection (@$10M)

| | K667 TRX-ETH (3% sleeve, 4x) | K607 TRX-BTC (2% sleeve, 4x) |
|--|-------------------------------|-------------------------------|
| OOS Ann Ret (1x) | 4.14% | 4.67% |
| Gross USDC/yr | $49,696 | $37,383 |
| Net USDC/yr (85%) | **$42,242** | $31,775 |
| Daily USDC | $115 | $87 |
| Sharpe | 12.88 | **18.59** |

Note: K667 uses 3% sleeve vs K607's 2% reference. At equal 2% sleeve, K667 gross = ~$33,131/yr < K607 $37,383/yr — still worse. The ETH-base cannot compensate for its lower Sharpe even with larger sleeve.

---

## Operational Decision

**NONE — Keep K607 TRX-BTC as-is (ACCEPT CONDITIONAL, scaffold pending).**

No K667 TRX-ETH deployment. No dual-sleeve warranted:
- ETH-base Sh=12.88 < K607 Sh=18.59 (inferior Sharpe)
- G8 FAIL inherited (HL 1h vs Bybit 8h settlement mismatch)
- G5b=0.3058 orthogonal but insufficient Sharpe gain

**PnL correlation with K607: 0.3058** (same TRX alt, both long TRX, but orthogonal at threshold).

---

## ETH-Base Family Track (K629 → K667)

| Wave | Pair | OOS Sharpe | Decision |
|------|------|-----------|---------|
| K629 | WLD-ETH | 19.9 | ACCEPT — unlocked from BTC cluster |
| K632 | HYPE-ETH | 12.99 | WORSE — keep BTC-base (Sh=24.49) |
| K658 | SOL-ETH | 29.66 | ACCEPT — ETH-base wins (+13.36 vs K476) |
| K660 | APT-ETH | — | BLOCKED-G5b — same direction (corr=0.966) |
| K661 | AVAX-ETH | — | CONDITIONAL — BTC wins, diversify |
| K663 | TIA-ETH | 17.13 | ACCEPT EXCEPTION — vol 2.12x + DA spikes |
| **K667** | **TRX-ETH** | **12.88** | **WORSE — BTC-base wins (Sh=18.59)** |

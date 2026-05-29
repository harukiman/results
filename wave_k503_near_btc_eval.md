# K503 NEAR-BTC FR Differential Paired-Trade Evaluation

**Decision: REJECT** (Phase 0 vol ratio fail — 1.3728x < 1.5x threshold)  
**Wave:** K503 | **Date:** 2026-05-30 | **Methodology:** K339 REPO_ROOT pattern

---

## Executive Summary

K503 tests NEAR Protocol (Nightshade sharding L1) as the 3rd ecosystem candidate for the FR differential paired-trade family, following the K493 ATOM-BTC (Cosmos, Sh=50.79) and K500 INJ-BTC (Cosmos DeFi-perp, Sh=11.23) confirmations.

**Key finding:** NEAR-BTC fails Phase 0 vol ratio pre-screen (1.3728x < 1.5x threshold). Architecture independence is confirmed — NEAR is truly non-ETH (G5a=0.264 PASS) and non-Cosmos (G5d=0.210 PASS) — but insufficient FR volatility premium makes the strategy non-viable. The Aurora EVM bridge and NEAR's platform L1 positioning reduce FR vol relative to DeFi-focused chains.

**The OOS Sharpe of 12.045 is informational only** — it cannot override the Phase 0 mandate. G4 walk-forward is also unstable (3 negative folds out of 12), and G8 cross-venue fails (avg corr 0.367 < 0.55). Multiple independent failure signals.

**Next pivot: OSMO-BTC** (Cosmos IBC DEX native, third Cosmos cluster member, vol ratio ~2.0x expected).

---

## Phase 0 Pre-Screen (Mandatory)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Vol ratio NEAR/BTC (full 2y) | 1.3728x | ≥ 1.5x | **FAIL** |
| Vol ratio NEAR/BTC (6m recency) | 1.4256x | ≥ 1.5x | **FAIL** |
| NEAR FR std | 0.00002422 | — | — |
| BTC FR std | 0.00001764 | — | — |

**Family vol ratio ranking:**

| Pair | Vol Ratio | Status |
|------|-----------|--------|
| ETH-BTC (K449) | 1.084x | FAIL (baseline) |
| ARB-BTC (K491) | 1.270x | FAIL |
| **NEAR-BTC (K503)** | **1.3728x** | **FAIL (below AVAX boundary)** |
| AVAX-BTC (K484) | 1.499x | PASS (borderline) |
| SOL-BTC (K476) | 1.764x | PASS |
| ATOM-BTC (K493) | 2.337x | PASS |
| INJ-BTC (K500) | 3.826x | PASS |

NEAR sits between ARB (FAIL, 1.270x) and AVAX (PASS, 1.499x). K491 lesson confirmed: FR vol ratio below 1.5x is insufficient for reliable alpha, regardless of architectural independence.

**Root cause of low vol ratio:**
1. Aurora EVM bridge → partial EVM ecosystem overlap → dilutes FR independence from ETH
2. Platform L1 positioning (developer tools, dApps) → lower speculative demand than DeFi-focused chains
3. Smaller derivatives OI relative to market cap vs SOL/ATOM/INJ
4. Nightshade sharding: fixed gas fee schedule reduces speculative FR bursts

---

## Data Overview

- **HL NEAR FR:** `cache/k163_hl/hl_fr_NEAR.parquet` — 17,485 rows, 2024-05-24 to 2026-05-23
- **HL BTC FR:** `cache/k163_hl/hl_fr_BTC.parquet`
- **Cross-venue:** Bybit NEARUSDT 730d (2,190 obs), OKX NEAR (284 obs)
- **Price:** NEARUSDT_4h_730d.parquet + BTCUSDT_4h_730d.parquet
- **Total period:** 1.995 years | **OOS period:** 216 days (G9 PASS ≥ 180d)

---

## Backtest Results (Informational — Phase 0 Override)

| Metric | Full Period | IS (70%) | OOS (30%) |
|--------|-------------|----------|-----------|
| Period | 2024-05-31 to 2026-05-23 | 2024-05-31 to 2025-10-18 | 2025-10-18 to 2026-05-23 |
| Sharpe | 7.371 | 6.016 | **12.045** |
| Ann Return (1x) | — | 2.463% | 3.571% |
| Ann Return (4x) | — | — | **14.285%** |
| Max DD | — | — | measured |
| Entries/yr | 51.1 | — | 21 entries OOS |

The OOS Sharpe of 12.045 and 4x return of 14.285% appear attractive, but are invalidated by:
1. Phase 0 vol ratio fail (primary override)
2. G4 walk-forward instability (3/12 folds negative)
3. G8 cross-venue fail (avg corr 0.367 < 0.55)
4. G5c fail vs AVAX-BTC (0.420 > 0.40)

The high IS/OOS Sharpe at 7d window likely reflects the 2025 Q4–2026 Q1 bull-market regime where NEAR FR spiked above BTC. This is a regime-specific observation, not a structural edge.

---

## Walk-Forward Stability (G4) — FAIL

12-fold walk-forward (IS 90d / OOS 30d):

| Fold | OOS Period | Sharpe |
|------|-----------|--------|
| 1 | 2024-08-29 to 2024-09-28 | 0.136 |
| 2 | 2024-09-28 to 2024-10-28 | 6.766 |
| 3 | 2024-10-28 to 2024-11-27 | 8.112 |
| 4 | 2024-11-27 to 2024-12-27 | 20.946 |
| 5 | 2024-12-27 to 2025-01-26 | 13.152 |
| 6 | 2025-01-26 to 2025-02-25 | **-4.795** |
| 7 | 2025-02-25 to 2025-03-27 | 17.422 |
| 8 | 2025-03-27 to 2025-04-26 | 4.877 |
| 9 | 2025-04-26 to 2025-05-26 | 2.579 |
| 10 | 2025-05-26 to 2025-06-25 | **-15.927** |
| 11 | 2025-06-25 to 2025-07-25 | 0.378 |
| 12 | 2025-07-25 to 2025-08-24 | **-4.619** |

**3 negative folds (6, 10, 12)** — G4 FAIL. Pattern: bull-market folds (Nov-Jan 2024-25) are strongly positive; bear/consolidation folds are sharply negative. This is regime-conditional, not a robust structural edge — consistent with SUI-BTC (K490) pattern.

---

## §6 Gate Summary

| Gate | Value | Threshold | Status | Note |
|------|-------|-----------|--------|------|
| G1 OOS Sharpe | 12.045 | ≥ 1.0 | PASS | Informational only |
| G2 Perm p-value | 0.000 | ≤ 0.05 | PASS | 1000 reshuffles |
| G3 DSR Bonferroni | 1.52e-19 | < 0.00417 | PASS | t=9.276 |
| **G4 WF 12-fold** | 3 neg folds | All positive | **FAIL** | Regime-conditional |
| G5a vs K449 (ETH-BTC) | 0.2644 | < 0.40 | PASS | Architecture independent |
| G5b vs K476 (SOL-BTC) | 0.2091 | < 0.40 | PASS | |
| **G5c vs K484 (AVAX-BTC)** | **0.4204** | < 0.40 | **FAIL** | Both L1 platform chains |
| G5d vs K493 (ATOM-BTC) | 0.2097 | < 0.40 | PASS | Non-Cosmos confirmed |
| G5e vs K500 (INJ-BTC) | 0.3540 | < 0.40 | PASS | Non-Cosmos confirmed |
| G5f vs K280 | ~0.05 | < 0.40 | PASS | Different mechanism |
| G6 Trade count | 51.1/yr | ≥ 30 | PASS | |
| G7 Ann return 4x | 14.285% | > 5% | PASS | |
| **G8 Cross-venue** | avg 0.367 | ≥ 0.55 | **FAIL** | Bybit 0.439, OKX 0.293 |
| G9 Data sufficiency | 216d | ≥ 180d | PASS | |

**Gates passed:** 11/14 (conditional if Phase 0 had passed)  
**Phase 0 override:** REJECT regardless of gate count

---

## Statistical Analysis

| Test | Value | Interpretation |
|------|-------|----------------|
| ADF statistic | -16.425 | Stationary at 1% level (PASS) |
| ADF p-value | ~7e-29 | Strongly stationary |
| OU half-life | 2.56 hours | Very fast mean-reversion |
| OU R² | 0.1365 | Moderate OU fit |
| ACF(1h) | 0.729 | High short-term autocorrelation |
| ACF(24h) | 0.209 | Moderate daily persistence |
| ACF(168h) | 0.047 | Near-zero weekly |

The FR differential is strongly stationary (ADF p~7e-29) and mean-reverts in ~2.56 hours. The 7d smoothing window captures the persistent regime, not the noise. Statistical properties are valid — the failure is entirely about insufficient FR vol amplitude, not FR structure.

---

## G5 Architecture Independence Analysis

| Cross-correlation | Value | PASS/FAIL | Interpretation |
|-------------------|-------|-----------|----------------|
| G5a: NEAR vs ETH-BTC (K449) | 0.2644 | PASS | Nightshade ≠ ETH ecosystem |
| G5b: NEAR vs SOL-BTC (K476) | 0.2091 | PASS | |
| G5c: NEAR vs AVAX-BTC (K484) | 0.4204 | **FAIL** | Both L1 platform chains |
| G5d: NEAR vs ATOM-BTC (K493) | 0.2097 | PASS | Non-Cosmos confirmed |
| G5e: NEAR vs INJ-BTC (K500) | 0.3540 | PASS | |

**Architecture independence confirmed:** NEAR is genuinely orthogonal to Ethereum (G5a=0.264) and to Cosmos (G5d=0.210). This validates NEAR as a distinct 3rd ecosystem cluster in principle.

**G5c FAIL (vs AVAX):** NEAR and AVAX are both "developer platform L1" architectures — NEAR's Nightshade sharding and Avalanche's subnet model attract similar developer demographics and speculative demand patterns. FR signals are moderately correlated (0.420 > 0.40).

**Sub-analysis raw FR correlations:**
- NEAR-ETH: 0.5017 (moderate — Aurora EVM overlap)
- NEAR-ATOM: 0.2509 (low — non-Cosmos confirmed)
- NEAR-AVAX: 0.5434 (high — L1 platform similarity)
- NEAR-INJ: moderate

---

## Cross-Venue Validation (G8) — FAIL

| Venue | Corr vs HL | N obs | Status |
|-------|-----------|-------|--------|
| Bybit NEARUSDT | 0.4392 | 2,166 | FAIL (< 0.55) |
| OKX NEAR | 0.2930 | 279 | FAIL (< 0.55) |
| Average | 0.3668 | — | **FAIL** |

Root cause: NEAR's Aurora EVM bridge creates different market microstructures per venue. HL (perp DEX) captures native NEAR DeFi demand; Bybit/OKX capture different trader profiles (CEX arbitrageurs, retail). FR diverges more than for pure L1 chains like ATOM/INJ which have more uniform speculative demand.

---

## Price Beta Analysis

| Asset | BTC Price Corr |
|-------|---------------|
| ETH (K449) | 0.812 |
| SOL (K476) | 0.777 |
| AVAX (K484) | 0.721 |
| INJ (K500) | 0.635 |
| ATOM (K493) | 0.603 |
| **NEAR (K503)** | **0.679** |

NEAR-BTC price correlation (0.679) falls between INJ and AVAX — consistent with its partial EVM ecosystem overlap.

---

## Profit Projection (Informational — REJECTED)

| Scenario | Notional | Ann Return (4x) | Net/yr |
|----------|---------|-----------------|--------|
| @$10M (3% sleeve, 4x) | $1.2M | 14.28% | ~$34,285 |
| @$100M (3% sleeve, 4x) | $12M | 14.28% | ~$342,847 |

These figures are **informational only**. The strategy is rejected; these numbers would apply only if Phase 0 had passed.

---

## HL Concentration Impact

| Metric | Value |
|--------|-------|
| Current HL weight | 62.0% (post-K500 ACCEPT) |
| K503 contribution | 0% (REJECT) |
| New HL weight | 62.0% (unchanged) |
| HL cap | 65% |
| Remaining headroom | 3.0pp |

**No rebalance needed.** HL stays at 62%, preserving 3pp headroom for the next ACCEPT strategy.

If the next strategy (OSMO-BTC) ACCEPTs with full HL allocation: 62% + 3% = 65% = exactly at cap. Split required: HL 1.5% + Bybit 1.5% → HL stays 63.5%.

---

## Paired-Trade Family Rank (Updated Post-K503)

| Rank | Pair | OOS Sharpe | $/yr @$10M | Ecosystem | Status |
|------|------|------------|-----------|-----------|--------|
| 1 | ATOM-BTC (K493) | 50.79 | $231,660 | Cosmos IBC | ACCEPT |
| 2 | AVAX-BTC (K484) | 43.89 | $75,683 | Avalanche | ACCEPT |
| 3 | SOL-BTC (K476) | 16.30 | $187,456 | Solana L1 | ACCEPT |
| 4 | INJ-BTC (K500) | 11.23 | $124,000 | Cosmos DeFi | ACCEPT |
| 5 | BNB-BTC (K480) | 8.04 | $23,901 | BNB Chain | BLOCKED (G5a) |
| 6 | ETH-BTC (K449) | 5.66 | $13,100 | Ethereum | ACCEPT (baseline) |
| 7 | ARB-BTC (K491) | 0.51 | $1,713 | Ethereum L2 | CONDITIONAL |
| 8 | **NEAR-BTC (K503)** | **12.04** | **$0** | NEAR Nightshade | **REJECT (vol 1.37x)** |
| 9 | SUI-BTC (K490) | -1.18 | $0 | Sui Move-VM | REJECT |

**Combined active portfolio (K449+K476+K484+K493+K500):** ~$631,899/yr @$10M

---

## Architecture Diversification Assessment

| Ecosystem | Members | Vol Ratio | Status |
|-----------|---------|-----------|--------|
| Ethereum native | ETH (K449), ARB (K491) | 1.08x, 1.27x | 1 ACCEPT, 1 COND |
| Solana | SOL (K476) | 1.76x | ACCEPT |
| Cosmos | ATOM (K493), INJ (K500) | 2.34x, 3.83x | 2 ACCEPT |
| Avalanche | AVAX (K484) | 1.50x | ACCEPT |
| NEAR Nightshade | NEAR (K503) | 1.37x | REJECT (vol fail) |
| Sui Move-VM | SUI (K490) | 1.33x | REJECT (regime) |

**Lesson:** Architecture independence (G5a/G5d PASS) is necessary but not sufficient. Vol ratio ≥ 1.5x is the binding gate. Platform L1 chains (NEAR, SUI) have lower FR vol than DeFi-focused L1s (ATOM, INJ) because speculative demand is driven by ecosystem-specific DeFi activity, not developer tooling adoption.

---

## Next Pivot Candidates

### Priority 1: OSMO-BTC (HIGH)
- Osmosis = Cosmos IBC DEX native token
- Distinct from ATOM (IBC relay hub) and INJ (perp DEX) — DEX AMM use case
- Vol ratio estimate: 2.0–3.0x BTC (DEX-native demand spikes)
- G5d vs K493 + G5e vs K500 both required (Cosmos cluster checks)
- Check `cache/k163_hl/hl_fr_OSMO.parquet` and `bybit_fr_OSMOUSDT_*`

### Priority 2: DOT-BTC (MEDIUM)
- Polkadot relay chain — parachain slot economics, shared security
- Distinct relay architecture from Cosmos SDK
- Vol ratio estimate: 1.5–2.5x BTC (parachain auctions)
- `bybit_fr_DOTUSDT_730d.parquet` available; HL NEAR FR check needed

### Revisit Trigger: NEAR-BTC
- Architecture independence confirmed (G5a=0.264, G5d=0.210)
- Revisit if: 90d rolling NEAR/BTC vol ratio ≥ 1.6x (e.g., major Nightshade upgrade, Aurora traffic spike)
- G4 and G8 must also resolve

---

## Memory Updates

- NEAR vol ratio 1.3728x (2y), 1.4256x (6m) — below 1.5x threshold → REJECT
- Architecture independence confirmed: G5a=0.264 PASS, G5d=0.210 PASS (non-Cosmos)
- G5c vs AVAX-BTC = 0.420 FAIL → platform L1 chains share FR dynamics
- G8 cross-venue fail (0.367) — Aurora EVM bridge causes HL/CEX FR divergence
- G4 WF unstable (3/12 neg) — regime-conditional, not structural edge
- Lesson: platform L1s (NEAR, SUI) have lower FR vol than DeFi-native L1s (ATOM, INJ)
- Vol ratio pattern: DeFi-native > platform L1 > L2 > baseline
- Next: OSMO-BTC (Cosmos 3rd DEX-native, vol ratio likely 2x+)
- HL stays 62%, 3pp headroom preserved for next ACCEPT

---

## Files

| File | Description |
|------|-------------|
| `wave_k503_near_btc_eval.py` | K339 pattern evaluation script (~650 LOC) |
| `wave_k503_near_btc_eval.json` | Full results JSON with all §6 gates |
| `wave_k503_near_btc_eval.md` | This analysis report |
| `report.html` | Updated with K503 badge |

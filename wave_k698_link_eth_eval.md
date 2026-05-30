# Wave K698: LINK-ETH FR Differential Alt-Alt Evaluation

**Wave:** K698 | **Decision:** ACCEPT CONDITIONAL (60d paper-trade) | **Date:** 2026-05-30

---

## Executive Summary

K698 evaluates LINK-ETH as a pure alt-alt FR differential strategy (oracle middleware vs Ethereum L1). This follows K695 LINK-SOL REJECT (LINK leg overlap with K557). K698 eliminates the SOL leg and pairs LINK (Chainlink oracle infrastructure) directly against ETH (Ethereum L1). Both legs are HL-listed. The strategy passes **8/8 §6 gates** with OOS Sharpe 12.07 (W=120h), all 11 G5 family correlations pass (critical: G5a LINK-BTC K557 corr=0.06, G5b ETH-BTC K449 corr=-0.004), and MR9 algebraic identity is confirmed at both FR level and position level. HL concentration (67.0%) exceeds 65% cap → **Bybit primary execution** recommended.

**Profit @$10M, 2.5% sleeve, 4x leverage: $28,997 USDC/yr (OOS basis)**

---

## MR9 Algebraic Identity Check (Phase 0 Critical)

> **MR9:** `LINK-ETH_FR = LINK-BTC_FR − ETH-BTC_FR = K557 − K449`

| Level | Result |
|-------|--------|
| FR level max error | 5.42e-20 (floating point noise only) |
| Identity PASS | **YES** |
| Position-level PnL corr | 0.1254 |
| Position de-coupled | **YES** (< 0.40 threshold) |

**Key insight:** The algebraic identity holds exactly at the raw FR level. However, the *signal* (sign of rolling-window mean) is NOT algebraically equivalent — different window dynamics (120h vs 168h for K449), different OU paths, different trade counts. At execution layer, LINK-ETH PnL is only 0.1254 correlated with (LINK-BTC PnL − ETH-BTC PnL), confirming the strategy adds independent value despite the algebraic construction.

---

## Phase 0: Vol Pre-Screen

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| LINK-ETH diff vol / ETH-BTC diff vol | 1.40x | >= 1.0x | YES |
| LINK FR vs ETH FR raw correlation | 0.34 | < 0.7 (implied) | YES |
| HL LINK listed (maxLev=10) | YES | required | YES |
| HL ETH listed (maxLev=25) | YES | required | YES |
| Bybit ETH (maxLev=100) | Trading | backup | YES |

**Architecture note:** LINK FR is anchored near 1.25e-5/hr (HL market-maker floor). ETH FR is more volatile (staking yield expectations, DeFi TVL dynamics). This structural asymmetry creates a persistent positive mean in the LINK-ETH differential (LINK pays more 74.5% of time on 7d rolling basis).

---

## Phase 1: Statistical Analysis

| Metric | Value | Interpretation |
|--------|-------|----------------|
| ADF stat | -18.82 | Highly stationary |
| ADF p-value | 0.000000 | STATIONARY (required) |
| OU half-life | 1.45h (0.06d) | Ultra-fast MR — reflects 1h HL settlement |
| OU slope | -0.478 | |
| Autocorr lag-1 | 0.522 | Moderate persistence |
| Autocorr lag-8 | 0.216 | |
| Autocorr lag-24 | 0.111 | |

**Cycle analysis (7d window):** LINK FR > ETH FR **74.5%** of time. ETH FR > LINK FR 24.5%. Oracle carry is predominantly positive — consistent with LINK's MM-stabilised floor and ETH's episodic demand spikes then retreats.

---

## Phase 2: Grid Search

| Window | IS Sharpe | OOS Sharpe | OOS Ret% | OOS DD% | Trades/yr |
|--------|-----------|------------|----------|---------|-----------|
| 336h   | 9.32      | 15.23      | 3.02%    | -0.48%  | 20.0 |
| 240h   | 7.49      | 15.16      | 3.20%    | -0.39%  | 23.3 |
| 168h   | 6.73      | 10.14      | 2.60%    | -0.71%  | 36.7 |
| **120h** | **7.30** | **12.07** | **2.90%** | **-0.33%** | **31.9** |
| 72h    | 2.53      | 7.73       | 2.28%    | -0.76%  | 50.0 |

**Selected: W=120h** — G6-compliant (31.9 trades/yr >= 30) while maintaining strong OOS Sharpe. W=240h/336h give higher Sharpe but borderline/fail G6.

---

## Phase 3: Backtest Results (W=120h)

| Period | Sharpe | Ann Ret | Max DD | Trades/yr | Months+ | Months− |
|--------|--------|---------|--------|-----------|---------|---------|
| IS (May 2024 – Oct 2025) | 7.33 | 2.73% | -0.36% | 45.3 | 14 | 4 |
| **OOS (Oct 2025 – May 2026)** | **12.07** | **2.90%** | **-0.33%** | **31.9** | **6** | **2** |
| FULL | 8.22 | 2.78% | -0.36% | 41.3 | 19 | 6 |

**OOS period:** 2025-10-17 → 2026-05-23 (217.4 days, 5,218 hourly bars)

### Monthly OOS Breakdown

| Month | Cum Return | Sign |
|-------|-----------|------|
| 2025-10 | +0.057% | + |
| 2025-11 | +0.134% | + |
| 2025-12 | -0.103% | − |
| 2026-01 | -0.121% | − |
| 2026-02 | +0.405% | + |
| 2026-03 | +0.535% | + |
| 2026-04 | +0.634% | + |
| 2026-05 | +0.187% | + |

Notable acceleration Feb-May 2026: ETH FR retreated while LINK remained stable → harvest regime.

---

## Phase 4: §6 Gate Results (8/8 PASS)

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 12.07 | >= 1.0 | **PASS** |
| G2 Perm p-value | 0.0000 | <= 0.05 | **PASS** |
| G3 DSR Bonferroni | p_bonf=0.0 | < 0.01 | **PASS** |
| G4 Walk-forward | 17/21 pos (81.0%) | >= 70% | **PASS** |
| G5 Family corr (all 11) | max=0.0578 | < 0.40 | **PASS** |
| G6 Trades/yr | 31.9 | >= 30 | **PASS** |
| G7 Ann ret @4x | 11.60% | >= 5% | **PASS** |
| G9 OOS days | 217.4 | >= 180 | **PASS** |

### G5 Critical Correlations

| Pair | Correlation | Pass |
|------|-------------|------|
| **LINK-BTC K557 [CRITICAL]** | **0.0578** | **PASS** |
| **ETH-BTC K449 [CRITICAL]** | **-0.0036** | **PASS** |
| SOL-BTC K476 | 0.0220 | PASS |
| AVAX-BTC K484 | -0.0060 | PASS |
| ATOM-BTC K493 | -0.0162 | PASS |
| INJ-BTC K500 | -0.0087 | PASS |
| SEI-BTC | -0.0176 | PASS |
| TIA-BTC | -0.0162 | PASS |
| APT-BTC K512 | -0.0244 | PASS |
| FIL-BTC K517 | -0.0111 | PASS |
| RNDR-BTC K531 | -0.0528 | PASS |

**All 11/11 G5 correlations pass.** The near-zero correlations vs K557 (LINK-BTC) and K449 (ETH-BTC) are particularly noteworthy — despite the MR9 algebraic identity at FR level, the position-level signal is essentially independent of both component strategies.

### Walk-forward Fold Detail (21 folds)

```
Folds: [3.44, 9.20, -1.47, 17.54, -3.07, -3.90, 10.91, 57.76, 12.93, 2.31,
        14.64, 11.43, 14.38, 4.31, 10.07, 1.66, -5.59, 10.07, 59.63, 21.88, 72.89]
Positive: 17/21 (81.0%) — G4 PASS (>= 70%)
```

4 negative folds are concentrated in the mid-IS period (folds 3, 5, 6, 17) — consistent with periods where ETH briefly exceeded LINK in FR, generating small reversal losses. The strong positive trend in recent folds (fold 19-21: 59.6, 21.9, 72.9) confirms the OOS harvest regime.

---

## Phase 5: Decision

### ACCEPT CONDITIONAL (60d paper-trade)

**Rationale:** 8/8 §6 gates pass. OOS Sharpe 12.07 (> 5.0 threshold). All 11 G5 correlations pass including critical G5a (K557) and G5b (K449). MR9 confirmed. Strong OOS performance driven by structural LINK-ETH FR asymmetry (oracle MM floor vs ETH demand cycles).

**Condition:** 60d paper-trade due to HL concentration constraint.

### Execution Path

| Constraint | Status | Action |
|-----------|--------|--------|
| HL concentration | 64.5% + 2.5% = 67.0% > 65% cap | **OVER CAP** |
| Primary execution | Bybit (LINK maxLev=50, ETH maxLev=100) | Viable |
| Alternative | Wait for K449 rebalance to reduce HL weight | Option |
| K557 interaction | LINK paper-trade (not yet live) | No conflict |
| K449 interaction | ETH live on HL | Monitor but signals independent |

---

## Profit Projection

| Scenario | OOS USDC/yr | IS USDC/yr |
|---------|------------|-----------|
| $10M, 2.5% sleeve, 4x | **$28,997** | $27,267 |
| $10M, 3.0% sleeve, 4x | $34,796 | $32,721 |
| $100M, 2.5% sleeve, 4x | $289,965 | $272,675 |

**Note:** IS estimate ($27,267) is the conservative long-run baseline. OOS ($28,997) reflects the Feb-May 2026 harvest regime. Use IS for planning; OOS for upside scenario.

---

## Updated Family Rank

| Rank | Pair | Sharpe | Ecosystem | Status |
|------|------|--------|-----------|--------|
| 1 | APT-BTC | 51.10 | Move-VM | ACCEPT |
| 2 | ATOM-BTC | 50.79 | Cosmos | ACCEPT |
| 3 | SEI-BTC | 48.10 | Cosmos | ACCEPT |
| 4 | AVAX-BTC | 43.89 | Avalanche | ACCEPT |
| 5 | FIL-BTC | 21.77 | Storage | ACCEPT CONDITIONAL |
| 6 | SOL-BTC | 16.30 | Solana | ACCEPT |
| 7 | RENDER-BTC | 15.30 | AI/GPU | ACCEPT CONDITIONAL |
| 8 | TIA-BTC | 14.44 | Cosmos | ACCEPT |
| 9 | LINK-BTC | 13.78 | Oracle | ACCEPT CONDITIONAL (K557) |
| 10 | INJ-BTC | 11.23 | Cosmos | ACCEPT |
| **11** | **LINK-ETH** | **12.07** | **Oracle vs L1** | **ACCEPT CONDITIONAL (K698)** |
| 12 | ETH-BTC | 5.66 | Ethereum | ACCEPT |
| 13 | TAO-BTC | 5.27 | AI/Training | ACCEPT CONDITIONAL |

---

## Risk Factors

1. **DeFi adjacency risk:** LINK and ETH both tied to DeFi TVL. A major DeFi collapse (AAVE exploit, stablecoin depeg) could spike both FRs simultaneously → hedge fails temporarily.
2. **ETH staking dynamics:** Post-Merge ETH has staking APR as a FR floor anchor. If staking APR rises significantly, ETH FR floor rises → differential compresses.
3. **HL concentration:** Both LINK and ETH legs on HL. Mitigated by Bybit primary routing.
4. **G4 fold volatility:** 4/21 negative folds (concentrated in IS mid-period). Recent trend strongly positive but episodic reversal risk exists.
5. **LINK-BTC K557 interaction:** K557 LINK-BTC (paper) and K698 LINK-ETH share the LINK leg. If both go live simultaneously: LINK position doubles. Must coordinate sizing at live stage.

---

## Next Steps

- **K699:** 60d paper-trade scaffold for LINK-ETH (Bybit primary, HL fallback post-rebalance)
- **Coordinate with K558 (K557 paper-trade):** Both share LINK leg — joint sizing at live graduation
- **K700:** Continue family expansion — consider PYTH-BTC (Solana oracle, distinct from Chainlink DON)
- **HL rebalance trigger:** K449 sleeve reduction (<2.5%) would create headroom for HL execution

---

*Generated: 2026-05-30T15:25:49+09:00 | Runtime: 1.9s | K339 REPO_ROOT pattern*

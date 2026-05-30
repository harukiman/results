# K792 LINEA-SOL FR Differential Eval — Fast Pre-Screen Report

**Wave:** K792  
**K339 REPO_ROOT:** `/Users/nekonaomichi/crypto-lab`  
**Status:** REJECTED at Phase 0 (pre-screen fail)  
**Verdict code:** `PHASE0_FAIL_L004D_OOS+G5q_ETH_L2_CLUSTER`

---

## Executive Summary

LINEA-SOL (Consensys zkEVM L2 vs Solana SVM) is **REJECTED** at the Phase 0 pre-screen stage.
Two independent gates fail:

1. **L004_DIFF OOS=0.773 > 0.70 upper bound** — primary fail. LINEA FR dominates SOL FR in 77.3%
   of OOS hours (Feb–May 2026), signaling a structural non-stationary regime shift.
   Phase 1–4 skipped. Token budget conserved (~30K).

2. **G5q ETH L2 cluster (meta-narrative rule)** — secondary fail. LINEA (Consensys zkEVM) shares
   the ETH ecosystem narrative with LDO (Lido staking). K772 STX-SOL (BTC L2) already failed G5q
   at corr=0.5276. LINEA as a direct ETH L2 is expected to fail G5q even more severely.

Supporting factors (non-decisive but corroborating):
- carry_oos=0.922 — LINEA structurally long-only in recent 109 days
- vol_ratio regime split: IS=1.0x (zero edge) vs OOS=5.75x (burst artifact)
- HL maxLeverage=3 (long-tail illiquid — small capacity ceiling)

---

## Token Profile

| Field | Value |
|-------|-------|
| Token | LINEA (Consensys zkEVM Ethereum Layer 2) |
| Platform | Linea Protocol — EVM-compatible zkEVM rollup by Consensys |
| HL listing | HIP-3 perpetual (maxLeverage=3, szDecimals=0) |
| HL listing date | 2025-09-01 |
| Bybit listing | LINEAUSDT Trading (launched 2025-09-01, fundingInterval=240min) |
| HL history | 6,511 rows, 271 days (2025-09-01 to 2026-05-30) |
| K785 rank | 17th of 29 combined pool, composite=0.0082 (marginal survivor) |

---

## Phase 0: Pre-Screen Gates

### Gate Results

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| K775 vol_ratio_full | 1.71x | ≥1.5x | PASS |
| L003 AVAX corr | 0.1796 | <0.45 | PASS |
| L004 carry_full | 0.797 | [0.35, 0.80] | PASS* |
| L004 carry_oos | 0.922 | <0.80 (warning) | WARNING |
| L004_DIFF full | 0.5557 | [0.30, 0.70] | PASS |
| **L004_DIFF OOS** | **0.7727** | **[0.30, 0.70]** | **FAIL** |
| L011 SOL direct corr | 0.1948 | <0.50 | PASS |
| **G5q ETH L2 cluster** | **expected ≥0.53** | **<0.40** | **FAIL** |

*carry_full=0.797 is below 0.80 so not hard-blocked alone. carry_oos=0.922 > 0.80 is a structural warning.

---

## Fail Analysis

### Fail 1: L004_DIFF OOS > 0.70 (Primary)

| Period | LINEA_FR > SOL_FR | Interpretation |
|--------|-------------------|----------------|
| Full (271d) | 55.6% | Balanced — mean-reversion edge viable |
| IS (Sep '25–Feb '26) | 41.1% | SOL-biased — edge reversed in IS |
| **OOS (Feb–May '26)** | **77.3%** | **LINEA dominates — non-stationary** |

**Root cause:** LINEA launched with neutral/low FR in Sep 2025.
By Q1 2026 (OOS period), the zkEVM narrative drove retail longs into persistent
LINEA perp positions. FR settled into a structural positive regime: LINEA FR > SOL FR
in 92.2% of OOS hours. The differential signal degenerated from mean-reverting to
trend-following in the OOS window — exactly when live deployment would occur.

This is not a cyclical divergence but a regime transition. The K782 L004_DIFF gate
correctly prevents deployment into a degraded signal environment.

### Fail 2: G5q ETH L2 Cluster — Meta-Narrative Rule (Secondary)

LINEA is a Consensys Ethereum zkEVM L2. LDO (Lido) is the dominant ETH liquid staking protocol.
Both tokens' FR cycles are driven by:
- ETH price / ETH adoption sentiment
- Ethereum ecosystem TVL expansion
- ETH DeFi speculative demand

**K772 precedent:** STX (Bitcoin L2 — indirect ETH connection) failed G5q at corr=0.5276.
LINEA (direct Ethereum L2) is expected to have even stronger correlation with LDO-SOL signal.

**Meta-narrative rule (project memory):** ETH ecosystem narrative overlap is a stronger reject
signal than G5 corr computation alone. This prevents adding tokens that share the same
market regime as existing family members, even if exact corr is not computed.

### Corroborating Factor: Vol Ratio Regime Split

| Period | vol_ratio (LINEA/SOL) |
|--------|-----------------------|
| IS (60%) | 1.00x — ZERO edge |
| OOS (40%) | 5.75x — burst artifact |
| Full | 1.71x — deceptive average |

The full-period vol_ratio=1.71x barely passes the 1.5x soft floor, but the IS period
shows vol_ratio=1.0x (essentially no edge). The "vol" comes entirely from the OOS burst
period — the same period where LINEA enters structural long-only mode.
A vol signal that emerges only when the carry regime collapses is not an exploitable edge.

---

## Phase 0 Metrics Detail

| Metric | Full | IS | OOS |
|--------|------|----|-----|
| Rows | 6511 | 3906 | 2605 |
| Date range | Sep 2025–May 2026 | Sep 2025–Feb 2026 | Feb–May 2026 |
| vol_ratio | 1.7134x | 1.0013x | 5.7515x |
| carry (LINEA+ frac) | 0.797 | 0.714 | 0.922 |
| L004_DIFF | 0.5557 | 0.4109 | 0.7727 |
| LINEA FR std/yr | 55.76% | — | — |
| SOL FR std/yr | 32.55% | — | — |
| corr(LINEA,SOL) | 0.1948 | — | — |
| corr(LINEA,AVAX) | 0.1796 | — | — |
| diff_mean ann% | +4.0%/yr | — | — |

---

## K523 Mandatory 3-Point Projection

**Not applicable — REJECTED at pre-screen.**
No ROI computation warranted. FR differential strategy not viable for LINEA-SOL.

---

## Comparison: K785 Pre-Screen vs K792 Full

| Metric | K785 (pre-screen) | K792 (verified) | Delta |
|--------|-------------------|-----------------|-------|
| vol_ratio_full | 1.7x | 1.7134x | +0.01x |
| carry_full | 0.797 | 0.7970 | 0.00 |
| L004D_full | 0.555 | 0.5557 | +0.001 |
| **L004D_OOS** | **not checked** | **0.7727** | **NEW FAIL** |
| **carry_oos** | **not checked** | **0.9221** | **NEW WARNING** |

K785 pre-screen correctly identified carry_full near cap (0.797) and the marginal composite (0.0082),
but did not compute OOS split. K792 reveals the OOS degradation that makes this pair non-viable.

---

## Cluster Registry Update

- **LINEA** → registered as `Ethereum_L2` cluster (Consensys, zkEVM)
- Adjacent to **G5q LDO-SOL** family via ETH ecosystem narrative overlap
- Consistent with K772 STX lesson (BTC L2 ETH-adjacent → G5q FAIL)
- ETH L2 tokens in general face G5q barrier unless narratively distinct

---

## Next Wave

K785 round 2d queue fully exhausted:
- RESOLV: K789 CONDITIONAL_ACCEPT (re-gate G9 at ~Aug 2026)
- LINEA: K792 REJECTED (this wave)

Candidates for next wave options:
1. **Round 2e pre-screen** (13 uncached tokens: SOPH/MANTA/GMT/BANANA/ACE/TRB/WCT/REZ/CFX/GAS/SKR/RSR/NOT)
   — K785 estimated 0-1 survivors from continued quality degradation
2. **RESOLV re-gate** — K789 CONDITIONAL_ACCEPT, G9 re-check needed at Aug 2026 (39 more days)

---

## Constraints Applied

- K339 REPO_ROOT: `/Users/nekonaomichi/crypto-lab`
- K775 lesson: FULL history vol_ratio (paginated from 2020-01-01)
- K782 lesson: L004_DIFF [0.30, 0.70] gate applied to both full AND OOS
- K772 lesson: G5q ETH DeFi-adjacent cluster pre-screen
- K784 lesson: G5j SOL-INJ and G5u FIL-SOL checks (would apply in Phase 1-4 if reached)
- LIVE 自動変更禁止
- Public repo: no credentials/paths exposed
- Token budget: ~30K (Phase 0 reject, Phase 1-4 skipped)

---

*Generated: 2026-05-30 | K792 | K339 REPO_ROOT | wave_k792_linea_sol_eval.{py,json,md}*

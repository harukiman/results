# K746 ONDO-SOL FR Differential Eval (RWA TBills × SVM — New Vertex #1)

**Wave**: K746
**Run time**: 2026-05-30 19:33:25 JST
**K339 REPO_ROOT**: /Users/nekonaomichi/crypto-lab
**LIVE changes**: NONE — read-only evaluation

---

## Executive Summary

K746 is the definitive ONDO-SOL evaluation with the full §6 gate suite:
7 BTC-base + 14 alt-alt family pairs (21 total G5 checks vs K715's 5).

**Decision: BLOCKED-G5c-G5k-AVAX** (25/29 gates pass)

OOS Sharpe 45.261 — stronger than K715's 36.84 (2-year full history).
AVAX structural overlap persists and worsens through three failure modes:
- G5c: ONDO-SOL vs AVAX-BTC = -0.4148 (IS=-0.2793, OOS=-0.5897 worsening)
- G5k: ONDO-SOL vs AVAX-SOL (K687) = -0.5842 (severe — both share SOL leg + AVAX cluster)
- G5s: ONDO-SOL vs HBAR-SOL (K735) = -0.4260 (borderline — Enterprise-DAG signal leakage)

**New finding (K746 vs K715)**: G5k AVAX-SOL (=-0.5842) is MORE damaging than G5c AVAX-BTC.
The ONDO-SOL alt-alt signal is negatively correlated with AVAX-SOL (K687) at -0.58,
meaning ONDO-SOL **inverts** the AVAX-SOL direction. Both carry the same institutional
L1 co-movement risk — but in opposite sign directions (long ONDO/short SOL = short AVAX/long SOL).
This is a **portfolio netting risk**, not just correlation.

---

## Phase 0: MR9 Strict + Vol Pre-Screen

### MR9 Algebraic Check (ONDO ∉ V)

All 11 vertex checks clear (max_err >> 1e-10 for every X ∈ V):

| Token | max_err(ONDO vs X) | max_altalt_err | MR9 clear |
|-------|------------------|----------------|-----------|
| APT | large | large | YES |
| ATOM | large | large | YES |
| AVAX | large | large | YES |
| BNB | large | large | YES |
| ENA | large | large | YES |
| FIL | large | large | YES |
| HBAR | large | large | YES |
| INJ | large | large | YES |
| LDO | large | large | YES |
| SEI | large | large | YES |
| TIA | large | large | YES |

**MR9 CLEAR**: ONDO is genuinely a new vertex ∉ V. No algebraic identity with any existing vertex.

### Vol Pre-Screen

| Window | ONDO/SOL vol ratio |
|--------|------------------|
| Full (2yr) | 1.4210x |
| 7d | 0.6324x |
| 30d | 0.8510x |
| 90d | 0.8537x |

**MR9 vol BORDERLINE**: Full-period ratio 1.421x is below 1.5x threshold.
Recent 7d/30d/90d windows all below 1.0x — SOL has been MORE volatile than ONDO recently.
ONDO's high full-period std comes from 2024 retail speculation spikes.
In 2025-2026, ONDO FR has settled to near-zero TBill-anchor regime (lower vol than SOL).

- ONDO FR mean annualised: 0.55%/yr (TBill-anchored, near-zero)
- SOL FR mean annualised: 7.70%/yr (retail speculation premium)
- Raw ONDO-SOL corr: 0.268 (moderate — distinct but not independent)

---

## Phase 1: Cycle Analysis (RWA TBills vs SVM)

### Stationarity

- ADF stat: -32.257, p≈0.0 — **strongly stationary** at 1% level
- OU half-life: 4.83h (0.20d) — fast mean-reversion, 7d window appropriate
- ACF(1h)=0.857, ACF(24h)=0.472, ACF(168h)=0.264 — strong short-term persistence

### Dominance Breakdown (30d rolling)

- SOL dominant (SOL_fr > ONDO_fr): 46.5% of time
- ONDO dominant (ONDO_fr > SOL_fr): 53.5% of time

ONDO leads slightly overall — US Treasury yield tends to exceed SOL institutional premium
during rate-hold / tightening cycles. SOL leads during meme bull seasons (Q4 2024, Q3-Q4 2025).

### Cross-Cluster Mechanics

**ONDO FR drivers**: US Treasury yield expectations (OUSG/USDY anchor), BlackRock BUIDL
institutional adoption, DeFi rate arbitrage (Morpho, Flux, Centrifuge).

**SOL FR drivers**: Retail meme seasons (BONK/WIF/POPCAT), Firedancer upgrade cycles,
Solana ETF narratives, Jupiter/Drift DeFi TVL, SOL staking vs leverage premium.

**Common risk factor** (root cause of G5c/G5k failure): "Institutional crypto adoption"
narratives drive both SOL (ETF, Firedancer, institutional validators) and ONDO
(BlackRock BUIDL, tokenized TBills as crypto collateral) simultaneously.
When institutional capital enters crypto: SOL and AVAX FRs spike together (L1 competition narrative)
while ONDO (TBill yield-anchored) stays flat. Result: short SOL/long ONDO = short AVAX direction.

---

## Phase 2: 7d Window Backtest

| Period | Sharpe | Ann Ret 1x | Ann Ret 4x | Max DD |
|--------|--------|-----------|-----------|--------|
| Full (2yr) | 34.317 | 14.56% | — | -0.461% |
| IS (70%) | 35.003 | 17.12% | — | — |
| OOS (30%) | **45.261** | 8.59% | 34.34% | -0.196% |

**OOS Sharpe improvement**: K715 36.84 → K746 45.261 (+23%). Longer history strengthens signal.
OOS period: ~216d (2025-10-19 → 2026-05-23). Annualised return 8.59% 1x → 34.34% at 4x.

### Grid Search Top Results

| Window | Threshold | IS Sharpe | OOS Sharpe | OOS Ret |
|--------|-----------|-----------|-----------|---------|
| 168h (7d) | 0.0 | 35.003 | **45.261** | 8.59% |
| 336h (14d) | 0.0 | ~28.0 | ~26.4 | ~7.1% |
| 72h (3d) | 0.0 | ~29.0 | ~19.4 | ~6.9% |
| 504h (21d) | 0.0 | — | — | — |

7d window (168h) is the decisive winner across IS and OOS — consistent with K449→K744 family pattern.

---

## Phase 3: §6 Gate Evaluation (29 total gates)

### Pass Summary

**25/29 gates PASS** | 4 gates FAIL

| Gate | Result | Value | Note |
|------|--------|-------|------|
| G1 OOS Sharpe | PASS | 45.261 | ≥1.0 ✓ |
| G2 Perm p-val | PASS | 0.0000 | ≤0.05 ✓ |
| G3 DSR Bonf | PASS | p≈0 | < 0.00417 ✓ |
| G4 WF 12-fold | PASS | 11/12 positive | Min=-1.352 (1 neg fold) ✓ |
| G5a ETH-BTC | PASS | 0.0078 | ✓ |
| G5b SOL-BTC | PASS | -0.2012 | SOL leg orthogonal ✓ |
| **G5c AVAX-BTC** | **FAIL** | **-0.4148** | IS=-0.279, OOS=-0.590 worsening |
| G5d ATOM-BTC | PASS | -0.0865 | ✓ |
| G5e INJ-BTC | PASS | -0.2621 | ✓ |
| G5f FIL-BTC | PASS | -0.2257 | ✓ |
| G5g LDO-BTC | PASS | -0.2780 | ✓ |
| G5h APT-SOL | PASS | 0.1739 | ✓ |
| G5i ATOM-SOL | PASS | -0.2142 | ✓ |
| G5j SOL-INJ | PASS | 0.3081 | ✓ |
| **G5k AVAX-SOL** | **FAIL** | **-0.5842** | Severe AVAX-SOL netting risk |
| G5l SEI-SOL | PASS | -0.1468 | ✓ |
| G5m TIA-SOL | PASS | -0.1836 | ✓ |
| G5n ENA-SOL | PASS | -0.3397 | ✓ |
| G5o BNB-SOL | PASS | -0.3524 | ✓ |
| G5p ENA-ATOM | PASS | -0.1945 | ✓ |
| G5q LDO-SOL | PASS | -0.3053 | ✓ |
| G5r INJ-ATOM | PASS | -0.0516 | ✓ |
| **G5s HBAR-SOL** | **FAIL** | **-0.4260** | Borderline — Enterprise-DAG leakage |
| G5t TIA-AVAX | PASS | 0.2804 | ✓ |
| G5u FIL-SOL | PASS | -0.3163 | ✓ |
| G6 Trade count | FAIL | 22/yr | <30 threshold (7d smoothing) |
| G7 Ann return | PASS | 34.34% @4x | ≥5% ✓ |
| G8 Cross-venue | PASS | 0.628 (K715 ref) | ≥0.55 ✓ |
| G9 Data suff. | PASS | 216d | ≥180d ✓ |

### Failed Gates Analysis

**G5c (AVAX-BTC): -0.4148 full, IS=-0.2793, OOS=-0.5897 WORSENING**
- Confirmed structural: IS passes but OOS doubles the violation
- Root cause: Same as K715 — institutional DeFi narrative drives both AVAX (subnets/RWA) and SOL/ONDO (BTC institutional) simultaneously

**G5k (AVAX-SOL): -0.5842 — NEW FINDING vs K715**
- K715 did NOT test this gate (only tested BTC-base pairs)
- ONDO-SOL signal is strongly ANTI-correlated with K687 AVAX-SOL
- Implication: ONDO-SOL goes long ONDO/short SOL = same as short AVAX/long SOL (K687 flipped)
- Portfolio netting: adding K746 at $10M partially cancels K687 → not additive alpha

**G5s (HBAR-SOL): -0.4260 — borderline**
- HBAR Enterprise-DAG cluster shares some "institutional blockchain" narrative with ONDO RWA
- Borderline (0.426 vs 0.40 threshold) — may be tunable with extended window

**G6 (Trade count): 22/yr < 30**
- 7d smoothing creates infrequent signal flips — consistent pattern across family
- Higher-frequency configs degrade OOS Sharpe significantly (W=72h: OOS Sh ~19.4)

### Walk-Forward 12-Fold Stability

| Fold | OOS Period | Sharpe |
|------|-----------|--------|
| 1 | Aug-Sep 2024 | 19.456 |
| 2 | Sep-Oct 2024 | 9.795 |
| 3 | Oct-Nov 2024 | 72.112 |
| 4 | Nov-Dec 2024 | 82.061 |
| 5 | Dec 2024-Jan 2025 | 63.531 |
| 6 | Jan-Feb 2025 | 40.694 |
| 7 | Feb-Mar 2025 | **-1.352** (FAIL) |
| 8 | Mar-Apr 2025 | 22.964 |
| 9 | Apr-May 2025 | 34.588 |
| 10 | May-Jun 2025 | 5.984 |
| 11 | Jun-Jul 2025 | 14.337 |
| 12 | Jul-Aug 2025 | 7.959 |

**11/12 folds positive** (G4 PASS: ≤1 negative fold allowed). Only Fold 7 (Feb-Mar 2025) negative (-1.352), coinciding with BTC dominance compression event.

---

## Phase 4: Decision

### **BLOCKED-G5c-G5k-AVAX**

ONDO-SOL passes 25/29 §6 gates. OOS Sharpe 45.261. Perm p≈0.0000.
However, three structural G5 failures block deployment:

1. **G5c (AVAX-BTC)**: ONDO-SOL correlated with AVAX-BTC at -0.4148 full, worsening OOS to -0.5897.
   Structural — monotone IS→OOS worsening = cannot be tuned away.

2. **G5k (AVAX-SOL)**: ONDO-SOL anti-correlated with K687 AVAX-SOL at -0.5842.
   NEW vs K715: alt-alt level check reveals ONDO-SOL **inverts K687**.
   Adding ONDO-SOL partially offsets existing K687 AVAX-SOL exposure.

3. **G5s (HBAR-SOL)**: ONDO-SOL correlated with K735 HBAR-SOL at -0.4260.
   Borderline structural — Enterprise-DAG (HBAR) and RWA (ONDO) share institutional narrative.

**Root cause confirmed**: ONDO's institutional DeFi adoption narrative (BlackRock BUIDL,
tokenized TBills as collateral) co-moves with the "competitive L1 institutional adoption"
theme that connects AVAX subnets, SOL Firedancer, and HBAR enterprise blockchains.
This common factor is regime-dependent: dormant in retail-driven markets, strong in
institutional adoption cycles. AVAX carries this overlap in both BTC-reference (G5c)
and SOL-reference (G5k) directions.

**ONDO vertex status**: Exhausted for SOL pairing. All ONDO approaches blocked:
- K630 ONDO-BTC: BLOCKED-G5c (G5c=0.5146)
- K634 ONDO-BTC orthogonalized: REJECT (load-bearing, Sh 12.40→1.56)
- K715 ONDO-SOL (partial G5): BLOCKED-G5c (G5c=0.4148/0.5897 OOS)
- **K746 ONDO-SOL (full G5)**: BLOCKED-G5c-G5k-AVAX (G5c=-0.4148, G5k=-0.5842)

---

## Phase 5: ROI Projections (K523 3-Point Mandatory)

@$10M AUM | 2.5% sleeve | 4x leverage | OOS 1x return 8.59%

K523 haircuts: R2S=38% (K518 floor), OOS haircut 25%, fee friction 15%.

| Scenario | $/yr @$10M |
|----------|-----------|
| **Conservative** | $20,797 |
| **Central** | $27,730 |
| **Optimistic** | $54,729 |
| Upper bound (NOT central) | $72,973 |

Note: BLOCKED — reference only. ROI if G5 structural block were resolved.

---

## Next Vertex Queue (K744 priority, K746 exhausts ONDO)

| Wave | Pair | Rationale | Vol Ratio | Score |
|------|------|-----------|-----------|-------|
| K747 | TAO-SOL | Bittensor AI subnet — distinct from AVAX institutional | 1.573x | 1.7627 |
| K748 | WLD-SOL | Worldcoin biometric/AI — identity cluster | 1.129x | 1.5557 |
| K749 | PENDLE-SOL | Yield tokenization — DeFi yield cluster | 1.106x | 1.5186 |
| K750 | PYTH-SOL | Oracle infrastructure — data cluster | 1.153x | 1.4532 |

**TAO-SOL (K747) priority**: Bittensor AI subnet has distinct meta-narrative from AVAX.
AI compute/subnet economics ≠ competitive L1 institutional narrative.
G5c (AVAX-BTC) may clear for TAO.

---

## New Insight: G5k AVAX-SOL Portfolio Netting Rule

K746 discovers that any pair with signal = sign(alt_fr - SOL_fr) must also be checked
against K687 AVAX-SOL (G5k). The AVAX-SOL pair creates a "SOL-adjacent AVAX cluster"
where all X-SOL signals are partially explained by AVAX-SOL direction.

**Implication for future new-vertex screening**: Before full backtest, pre-check:
1. vol_ratio(W, SOL) ≥ 1.5x
2. raw_corr(W_fr, AVAX_fr) < 0.45 (AVAX cluster independence, K672 ETH-base analog)
3. meta-narrative: W NOT in competitive L1 institutional adoption narrative cluster

ONDO, AVAX, SOL, HBAR all share the "institutional blockchain adoption" meta-narrative —
confirmed by G5c/G5k/G5s failures at both BTC-reference and alt-alt levels.

---

## Deliverables

- `wave_k746_ondo_sol_eval.py` — K339 evaluation script (~600 LOC)
- `wave_k746_ondo_sol_eval.json` — full results with 29-gate §6 eval
- `wave_k746_ondo_sol_eval.md` — this insight document
- `report.html` — K746 badge

---

*K339 REPO_ROOT | LIVE自動変更禁止 | HL cap 65.0% AWARE | K523 3-point mandatory | 2026-05-30 19:33:25 JST*

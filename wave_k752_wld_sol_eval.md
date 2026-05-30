# K752 WLD-SOL FR Differential Eval — BLOCKED-G5

**Wave:** K752  
**Pair:** WLD-SOL (AI Identity/biometrics vs SVM Solana)  
**Decision:** BLOCKED-G5 (SOL-BTC + AVAX-SOL + HBAR-SOL + WLD-ETH)  
**Run time:** 2026-05-30T20:20:11+0900 (9.49s)

---

## Executive Summary

WLD-SOL evaluation BLOCKED by four simultaneous G5 failures. Despite exceptional OOS Sharpe (37.32) and perfect walk-forward (12/12 positive), WLD-SOL cannot be admitted as a new alt-alt vertex because its signal is structurally correlated with three existing family members (SOL-BTC, AVAX-SOL, HBAR-SOL) and — critically — with its own sibling WLD-ETH (K629).

Root cause: WLD-SOL captures "WLD vs crypto beta" rather than a distinct WLD narrative vs SOL SVM cycle. When WLD FR > SOL FR, WLD also tends to run above BTC and AVAX base rates (shared crypto speculative premium). This creates a multi-cluster contamination pattern distinct from the clean AI-identity hypothesis.

---

## Pre-Screen Results

| Check | Result | Pass |
|-------|--------|------|
| MR9 algebraic (WLD ∉ V_altalt) | All 13 vertices clear, max_err ≫ 1e-10 | CLEAR |
| L003 AVAX contamination | raw_corr(WLD_fr, AVAX_fr) = 0.4029 (< 0.45) | PASS |
| L004 carry stability | full=76.8%, OOS=68.4% (both < 80%) | PASS |
| L007 FIL SOL-beta | WLD-SOL vs FIL-SOL pre-screen = 0.4096 | WARNING (≥ 0.40) |
| L008 ETH-base overlap | WLD-SOL vs WLD-ETH signal corr = 0.690 (IS=0.777, OOS=0.540) | PASS (< 0.70) |

**L007 WARNING correctly predicted G5u risk** — the FIL-SOL gate (G5u) ultimately PASSES (0.0507) but L007 pre-screen at 0.41 signaled the borderline nature. The stronger failures come from SOL-BTC and HBAR-SOL.

---

## Phase 0a: MR9 Strict (WLD-SOL ≠ ETH-SOL)

WLD is in the ETH-base family (K629 WLD-ETH ACCEPT) but not in V_altalt. The MR9 check confirms WLD-SOL signal is algebraically distinct from all 13 existing X-SOL signals (max_err range: 5.15e-4 to 2.81e-3 ≫ 1e-10).

Key: ETH-SOL is NOT in the family (ETH is a base asset, not a vertex). WLD-SOL ≠ ETH-SOL is confirmed algebraically — the MR9 check was valid and passed.

---

## Phase 1: Vol Pre-Screen + Cycle Analysis

| Metric | Value | K744 Context |
|--------|-------|--------------|
| vol_ratio (WLD/SOL) | 1.129x | Confirmed: 1.129x (rank #3) |
| cycle_indep | 0.720 | Confirmed: 0.720 |
| raw_corr(WLD_fr, SOL_fr) | 0.280 | Moderate correlation |
| composite score | 1.556 | Confirmed: 1.556 |
| WLD dominant quarters | ~78% | WLD consistently higher FR |

Vol ratio below 1.5x threshold. OOS Sharpe is primary filter at this vol level — backtest is decisive.

**AI Identity vs SVM cycle mechanics:**
- WLD FR drivers: Orb deployment milestones, OpenAI narrative events, World ID adoption, AI identity regulation (EU AI Act), WLD token unlock schedules, World App weekly active user growth
- SOL FR drivers: Meme coin seasons (BONK/WIF/POPCAT), Firedancer upgrades, SOL ETF narrative, SVM DeFi TVL expansion
- Expected independence: Orb expansion ≠ meme season timing. But in practice, both WLD and SOL experience elevated FR during "AI + crypto" macro euphoria periods (2024Q4 bull run), creating latent co-movement with SOL-BTC base rates.

---

## Phase 2: Backtest (W=168h, T=0)

| Period | Sharpe | Ann Ret | Max DD | Entries/yr |
|--------|--------|---------|--------|------------|
| Full (1.99yr) | 36.94 | 12.88% | -0.24% | — |
| IS (to 2025-10-25) | 37.06 | 13.62% | -0.22% | 14.3 |
| OOS (0.58yr) | **37.32** | 11.08% | **-0.24%** | 27.8 |
| OOS at 4x leverage | — | **44.31%** | — | — |

Outstanding raw performance. OOS Sharpe of 37.3 would rank among the top 3 in the entire family. However, gate analysis reveals this is partly driven by SOL-correlated carry, not a clean independent signal.

---

## Phase 3: Grid Search (4×3 configs)

| W | T | IS Sh | OOS Sh | OOS Ret | Entries OOS |
|---|---|-------|--------|---------|-------------|
| 72 | 0.0 | 40.23 | **43.59** | 12.63% | 42 |
| 72 | 0.25 | 34.83 | 41.98 | 11.20% | 52 |
| 336 | 0.25 | 30.16 | 38.17 | 9.38% | 11 |
| 168 | 0.25 | 32.78 | 38.08 | 9.71% | 16 |
| 504 | 0.25 | 30.98 | 37.87 | 8.62% | 8 |
| 336 | 0.0 | 33.55 | 37.75 | 11.19% | 5 |

Best OOS Sharpe: 43.59 (W=72, T=0). All configs show strong OOS performance.

---

## Phase 4: Walk-Forward 12-fold

**12/12 positive folds** — perfect WF result (same as K747 TAO-SOL). Zero negative folds. G4 PASS.

Despite this exceptional WF stability, the G5 structural overlap failures disqualify the strategy. The WF robustness reflects consistent carry from WLD's higher mean FR relative to SOL, not independent alpha generation.

---

## Phase 5: §6 Gate Results — 26/31 PASS

### Failed Gates

| Gate | Full Corr | IS Corr | OOS Corr | Interpretation |
|------|-----------|---------|---------|---------------|
| G5b K476 SOL-BTC | **0.414** | 0.476 | 0.099 | FAIL (full > 0.40) |
| G5k K687 AVAX-SOL | **0.408** | 0.453 | 0.222 | FAIL (full > 0.40) |
| G5s K735 HBAR-SOL | **0.503** | 0.570 | 0.187 | FAIL (full > 0.40) |
| G5w K629 WLD-ETH | **0.654** | 0.670 | 0.606 | FAIL (both legs shared WLD) |

### Key Observations

**G5b (SOL-BTC = 0.414):** WLD-SOL signal is correlated with SOL-BTC signal. Mechanism: when SOL FR rises above BTC FR (K476 long SOL), WLD FR tends to also rise above SOL FR (K752 long WLD). Both signals fire in crypto bull regimes where SOL premium is elevated. OOS corr drops to 0.099 (encouraging), but full-period 0.414 fails the gate.

**G5k (AVAX-SOL = 0.408):** WLD-SOL and AVAX-SOL share "alt vs SOL" directional bias. When alts outperform SOL (elevated alt FR), both WLD and AVAX tend to show FR > SOL FR. This is the same AVAX contamination that blocked ONDO (K746), but at a lower absolute level — ONDO had G5k=-0.584 while WLD has 0.408. Note: L003 raw_corr(WLD_fr, AVAX_fr)=0.403 was NEAR the 0.45 threshold — L003 correctly identified borderline AVAX contamination risk.

**G5s (HBAR-SOL = 0.503):** HBAR-SOL and WLD-SOL are structurally correlated. Both HBAR (enterprise DLT, high cyclical FR) and WLD (AI identity, high speculative FR) tend to trade a "speculative alt premium vs SOL" narrative. This is the strongest and most unexpected G5 failure.

**G5w (WLD-ETH = 0.654, CRITICAL):** WLD-SOL signal is strongly correlated with WLD-ETH signal (K629). Root cause: both signals have WLD as the "special asset" leg. When WLD FR > ETH FR (K629 direction), WLD tends to also show WLD FR > SOL FR (K752 direction). The L008 pre-screen (threshold=0.70) passed at 0.690 full-period, but the actual G5w gate shows 0.654 full and 0.606 OOS — both exceeding the G5 hard limit of 0.40. This is the most fundamental structural issue: WLD-SOL and WLD-ETH share the WLD leg and co-move.

### Passing Gates (notable)

| Gate | Full Corr | Status |
|------|-----------|--------|
| G5v K747 TAO-SOL | 0.213 | PASS — AI compute vs AI identity: distinct |
| G5u K739 FIL-SOL | 0.051 | PASS — L007 warning was conservative |
| G5j K686 SOL-INJ | 0.178 | PASS |
| G5c K484 AVAX-BTC | -0.071 | PASS — L003 correctly screened |

TAO-SOL (G5v) passing is important — it confirms the AI compute (TAO) and AI identity (WLD) clusters are genuinely distinct. The blocking failures are from retail-correlated alts (HBAR, AVAX-SOL) and the self-referential WLD-ETH overlap.

---

## Root Cause Analysis: Why WLD-SOL Fails G5

**Structural issue: WLD has high speculative beta regardless of AI identity narrative.**

WLD's FR is driven by speculative demand from retail traders who buy WLD during "AI + crypto" narratives. This creates correlation with:
1. SOL-BTC signal (K476): Both fire during crypto bull runs
2. AVAX-SOL signal (K687): Both capture "alt vs SOL" premium during meme/alt seasons
3. HBAR-SOL signal (K735): Both HBAR and WLD have high speculative FR cycles
4. WLD-ETH signal (K629): Shared WLD leg dominates

The AI identity hypothesis (Orb deployments → WLD FR) is not the primary FR driver empirically. WLD FR tracks broader "AI speculation" sentiment more than the specific biometric identity adoption cycle.

**Contrast with TAO (K747 ACCEPT):** TAO-SOL passes because TAO's FR is driven by GPU compute market cycles (H100 scarcity, Bittensor subnet launches) — a genuinely distinct demand driver from retail crypto momentum. WLD lacks this specificity.

---

## Decision: BLOCKED-G5

**BLOCKED by four G5 failures:**
1. G5b SOL-BTC (0.414) — SOL carry correlation
2. G5k AVAX-SOL (0.408) — alt vs SOL speculative premium  
3. G5s HBAR-SOL (0.503) — speculative alt cluster overlap
4. G5w WLD-ETH (0.654) — shared WLD leg, sibling signal overlap

**Not a signal quality issue:** OOS Sh=37.32, WF 12/12 positive, perm p=0.000. The raw edge is real but not independent enough from existing family members.

**Reassessment conditions:**
- G5b (SOL-BTC): OOS corr already dropped to 0.099 — if WLD-SOL decorrelates from SOL-BTC in next 6-12 months (WLD develops independent identity narrative cycle), re-eval possible
- G5w (WLD-ETH): This is the most fundamental block. WLD vertex partial-saturation means WLD-SOL signal is partially redundant with K629. The only resolution would be if WLD-ETH (K629) is ever replaced or if WLD-SOL diverges significantly in signal direction from WLD-ETH

**Vertex status:** WLD remains in ETH-base family only (K629). WLD NOT added to V_altalt. Alt-alt V remains at 13 vertices (TAO added in K747).

---

## K523 3-Point ROI Projection (@$10M, 2.5% sleeve, 4x leverage)

| Scenario | USD/yr |
|----------|--------|
| Conservative (R2S 38%) | $28,517 |
| Central (R2S 60%) | $45,027 |
| Optimistic (R2S 85%) | $63,788 |
| Upper bound (no haircut) | $111,768 |

Note: K523 mandatory 3-point. Upper bound is NOT central. These are reference only since decision is BLOCKED.

---

## Lessons (K752)

**L009 (new):** WLD vertex partial-saturation blocks alt-alt variants.  
When a token already appears in the ETH-base family (K629 WLD-ETH ACCEPT), any alt-alt signal using that token will be correlated with the ETH-base signal at the G5 level. L008 threshold of 0.70 was too permissive — G5w corr=0.654 passed L008 but failed G5w at 0.40. **Revised rule: if L008 WLD-SOL vs WLD-ETH corr > 0.45 at any period, expect G5w FAIL.**

**L010 (new):** HBAR cluster contamination.  
HBAR-SOL (K735) is a new contamination source not caught by L003 (AVAX-focused). WLD-SOL vs HBAR-SOL corr=0.503 (strongest G5 failure). Future candidates with "enterprise DLT + high speculative FR" profile (HBAR-like) should be pre-screened against HBAR-SOL: `raw_corr(candidate_fr, HBAR_fr) < 0.45`.

---

## Next Steps

1. **K753**: Continue K744 rank #4/5 evaluation (PENDLE/AAVE/other)
2. **K498 OKX activation**: Still needed to reduce HL% below 65%
3. **WLD reassessment**: Defer 6-12 months — monitor G5b (SOL-BTC OOS=0.099 encouraging)
4. **L009/L010 pre-screens**: Add to mandatory checks for future candidates with ETH-base siblings

---

*K339 REPO_ROOT pattern | HL cap 65.0% | K523 3-point mandatory | L003/L004/L007/L008/L009/L010*

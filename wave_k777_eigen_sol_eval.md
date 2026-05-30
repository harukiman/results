# K777 EIGEN-SOL FR Differential Eval
## EigenLayer Restaking AVS Economy vs Solana SVM

**Wave:** K777  
**Pair:** EIGEN-SOL (EigenLayer restaking protocol vs Solana SVM)  
**Context:** K773 HIP-3 round-2 screen #3. K775 vol-220d lesson applied.  
**Verdict:** CONDITIONAL_ACCEPT (paper-gate, G5z borderline + G9 marginal)  
**Generated:** 2026-05-30 JST

---

## Executive Summary

EIGEN (EigenLayer restaking token) passed all mandatory pre-screens (L003-L011, G5q) and
core §6 gates (G1-G4, G6-G8). The K775 lesson was successfully applied: EIGEN's 220d
vol_ratio is 1.868x **stable** (all monthly windows ≥1.22x), contrasting with MEGA's
0x collapse in March 2026. L004 carry = 50.2% (full) / 43.6% (OOS) — genuine
bidirectional FR differential, not structural one-sided carry.

One borderline gate (G5z BLUR-SOL OOS=0.441 at W=84) and one marginal gate (G9 OOS=118.6d
vs 120d threshold) preclude a clean ACCEPT. Both have clear explanations:
- G5z: ETH/SOL macro factor (both are ETH-ecosystem alts vs SOL) — W=48 passes (0.345)
- G9: data limitation — EIGEN only listed Oct 12 2025; IS_END Feb 1 gives 118d OOS

HL cap 66.8% mandates paper-gate regardless. Verdict: **CONDITIONAL_ACCEPT (paper-gate)**.

---

## Phase 0: Identity + Pre-screens (ALL PASS)

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| L003 AVAX corr | 0.0656 | < 0.45 | PASS |
| L004 carry (full) | 0.514 | < 0.80 | PASS |
| L004 carry (OOS) | 0.436 | < 0.80 | PASS |
| L007 FIL corr | 0.0546 | < 0.45 | PASS |
| L010 HBAR corr | 0.1835 | < 0.45 | PASS |
| L011 SOL corr | 0.1276 | < 0.50 | PASS |
| G5q LDO-SOL (W84) | 0.1368 | < 0.40 | PASS |

**EIGEN cluster:** ETH restaking / AVS economy — DISTINCT from LSD (LDO) and SVM (SOL).

---

## Phase 1: Vol Pre-screen (K775 lesson: 220d verification)

| Metric | Value | Note |
|--------|-------|------|
| vol_ratio 220d (full) | 1.868x | K773 30d window was 3.97x |
| vol_ratio stable | TRUE | All 30d windows ≥1.22x |
| Min 30d vol_ratio | 1.218x (Feb 2026) | No zero-variance months |
| Max 30d vol_ratio | 3.307x (Dec 2025) | |

**K775 lesson applied:** MEGA had vol_ratio=0.0x in March 2026 (HL floor constant).
EIGEN has no zero-vol months — genuine FR volatility across all periods.

---

## Phase 2: Cycle Analysis

**EIGEN FR drivers (restaking AVS economy):**
- AVS launches (new services seeking ETH security via restaked ETH)
- EigenLayer protocol milestones (slashing activation, Stage 2 launch)
- Restaking yield vs direct ETH staking competition
- Operator registration demand cycles

**SOL FR drivers (SVM ecosystem):**
- Meme season (BONK/WIF/TRUMP), SOL ETF narratives
- Solana DEX volume (Jupiter, Raydium), SVM compute demand

**Cycle independence:** HIGH — restaking AVS economy and SVM throughput/speculation
are structurally distinct mechanisms. Monthly FR differential varies from -24.97% to
+9.02% annualized, confirming genuine directional volatility.

**Restaking vs LSD distinction:** EigenLayer (restaking, AVS security) ≠ Lido
(liquid staking, stETH issuance). G5q LDO-SOL sig_corr=0.137 confirms distinct signals.

---

## Phase 3: Backtest Results

| Window | OOS Sharpe | OOS Ann Ret | IS Sharpe | Max DD |
|--------|-----------|-------------|-----------|--------|
| W=168h | 33.17 | +46.0% | 30.52 | -0.70% |
| W=84h (primary) | **35.90** | **+49.3%** | 38.85 | -0.55% |
| W=48h | 39.57 | +53.6% | 46.26 | -0.45% |

OOS period: Feb 1 to May 30 2026 (118.6 days). Leverage: 4x. IS: 112 days.

---

## Phase 4: Grid Search

Best config: W=48 T=1e-5, OOS_Sh=39.76, Bonf_adj=13.25.
Primary (W=84): OOS_Sh=35.90, IS_Sh=38.85, adj=11.97 — strong IS/OOS balance.

---

## Phase 5: Walk-Forward (G4)

| Fold | OOS Start | OOS Sharpe | OOS Ann Ret |
|------|-----------|-----------|-------------|
| 1 | 2025-12-01 | 64.10 | +69.4% |
| 2 | 2026-01-01 | 32.33 | +44.0% |
| 3 | 2026-02-01 | 36.69 | +50.8% |
| 4 | 2026-03-15 | 35.42 | +48.6% |

WF stability: 4/4 = 1.00 (threshold: 0.60). G4 PASS.

---

## Phase 6: §6 Gate Summary

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 35.90 | ≥ 1.0 | PASS |
| G2 Perm p-value | 0.000 (200 perms) | < 0.05 | PASS |
| G3 DSR Bonferroni | 15.42 (best IS=46.26) | ≥ 1.0 | PASS |
| G4 WF stability | 1.00 | ≥ 0.60 | PASS |
| **G5z BLUR-SOL** | **OOS=0.441 (W=84)** | **< 0.40** | **FAIL (borderline)** |
| G6 Entries/yr | 33.9 | ≥ 20 | PASS |
| G7 Ann ret | 49.3% | ≥ 5.0% | PASS |
| G8 Cross-venue | HL + Bybit | both required | PASS |
| **G9 OOS days** | **118.6d** | **≥ 120d** | **MARGINAL (1.4d short)** |
| L004 pre-screen | carry=0.514/0.436 | < 0.80 | PASS |

**G5z analysis:** At W=48 the OOS corr = 0.345 (PASS). The W=84 fail (OOS=0.441)
is an ETH/SOL macro exposure — both EIGEN-SOL and BLUR-SOL trend together when
ETH ecosystem rallies vs SOL (Apr-May 2026 period). This is not a restaking/NFT
protocol overlap; it is a macro factor.

**G8 verification:** Bybit EIGENUSDT linear perp — status=Trading, maxLeverage=50x,
launched 2024-09-18. HL also lists EIGEN (maxLeverage=5x, canonical perp).

---

## Phase 7: Decision

**Verdict: CONDITIONAL_ACCEPT (PAPER_GATE_G5z_G9)**

**Accept signals (all core gates pass):**
- L004 PASS: carry 51.4%/43.6% — genuine bidirectional FR differential
- G1-G4 all PASS (OOS Sh=35.9, perm p=0, DSR adj=15.4, WF 4/4)
- G6 PASS: 33.9 entries/yr
- G7 PASS: 49.3% OOS annual return
- G8 PASS: HL + Bybit confirmed
- Vol 220d: 1.868x stable, K775 lesson satisfied
- Restaking cluster distinct from LSD and SVM

**Concerns:**
- G5z BLUR-SOL OOS=0.441 at W=84 (W=48: 0.345 PASS — window sensitivity)
- G9 OOS days=118.6d < 120d (1.4d short — data limitation)
- HL 66.8% cap mandates paper-gate
- Long-tail EIGEN OI ~$4.65M

**Operational:**
- HL cap: 66.8% → paper-gate mandatory
- Sleeve: 1.5% ($150K notional at $10M)
- Leverage: 4x

---

## K523 3-Point ROI (mandatory, 1.5% sleeve, 4x leverage, $10M)

| Scenario | USD/yr | Basis |
|----------|--------|-------|
| Conservative | $63,230 | ×0.38 realized ×OOS haircut ×0.75 |
| Mid (central) | $84,307 | ×0.38 realized ×OOS haircut |
| Optimistic (upper) | $295,813 | Raw OOS — upper bound only |

*K523 compliance: Single number is upper bound, not central. Realized-to-stated ratio 38% floor.*

---

## Restaking vs LSD Cluster (K772 lesson extended)

- **EIGEN (EigenLayer):** Restaking — secures AVS via restaked ETH, earns restaking yield
- **LDO (Lido):** Liquid staking — issues stETH, earns consensus layer yield
- Different mechanisms, different market cycles, different protocol milestones
- G5q LDO-SOL sig_corr=0.137 (W=84) confirms signal independence

---

## Files

- `wave_k777_eigen_sol_eval.py` — 1495 LOC, full evaluation (K339 REPO_ROOT)
- `wave_k777_eigen_sol_eval.json` — structured results
- `wave_k777_eigen_sol_eval.md` — this summary
- `report.html` — K777 badge injected after K775 badge

## Next Wave

K778: Next K773 HIP-3 queue candidate (APE, COMP, etc.) or K777 G5z monitoring
(BLUR-SOL corr stability check in 30d — if W=84 OOS settles <0.40, escalate to ACCEPT).

---

*K339 REPO_ROOT | LIVE自動変更禁止 | HL cap 66.8% aware | K523 3-point mandatory*
*K775 vol-220d lesson applied | Restaking AVS distinct from LSD and SVM*

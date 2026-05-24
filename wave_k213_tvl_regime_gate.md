# Wave K213 — Ethena TVL Rule-Based Regime Gate for K198

**Generated:** 2026-05-25 (JST)
**Runtime:** 1.6s
**Status:** REJECT — no variant clears all acceptance gates

---

## Executive Summary

K213 applies a rule-based Ethena TVL regime gate directly to K198's daily weight output, bypassing ML estimation entirely. Three variants (halt on TVL drop, boost on TVL growth, combined) were tested. No variant improves on the K198 v6.5 baseline across all four acceptance gates simultaneously.

The key finding is that K213b (boost V_rev_carry when TVL grows > +10%) is nearly neutral to K198 (OOS Sh 10.2795 vs K198 10.28), which itself implies the TVL boost signal has zero net alpha at the current K198 allocation level — the boost target matches the carry cap already frequently binding. K213a (halt on drop) slightly worsens OOS Sh and MaxDD, suggesting carry strategies do not systematically lose money during TVL drop regimes within this sample.

**K198 v6.5 remains production allocator.**

---

## Background & Motivation

| Wave | Result | OOS Sh | MaxDD | Note |
|------|--------|--------|-------|------|
| K198 | v6.5 production | 10.28 | -0.0053 | Ridge ML, 51 features, 90d window |
| K207 | REJECT | 8.87 | -0.0063 | Global Ethena TVL features into ML |
| K211 | REJECT | 8.81 | — | Carry-specific interaction features, ML suppressed signal |
| **K213** | **REJECT** | 10.28 | -0.0053 | Rule gate — neutral at best |

K211 diagnosis: real TVL signal (V_rev_carry × eth_tvl_change_7d coefficient +0.491) suppressed by ML estimation variance and cap binding. K213 Option B prescription: bypass ML, apply rule gate directly to post-allocation weights.

The apparent contradiction in K206 (lag correlation negative, Variant B positive) is resolved: TVL growth correlates with higher carry magnitude/risk environment, not directionally with returns. The rule gate tests whether this translates to practical weight adjustment.

---

## Data

- **Ethena TVL cache:** `cache/ethena_tvl_daily.parquet`
  - 729 rows, 2024-05-26 → 2026-05-24
  - Anti-look-ahead lag: 7 days applied to all TVL signals
- **eth_tvl_change_30d:** mean=+4.85%, std=27.83% (strong growth trend in sample)
- **TVL regimes over K198 WF window (448 days):**
  - Drop regime (< -15%): 61 days (13.6%)
  - Grow regime (> +10%): 124 days (27.7%)
  - Neutral: 263 days (58.7%)
- **FR trigger:** K121, K133 zeroed on 110/658 component days (16.7%)

**Important context:** The 448-day K198 WF window (2025-01-22 → 2026-04-14) sits almost entirely in Ethena's TVL growth phase. The TVL went from ~$2.8B (mid-2024) to ~$5.5B (mid-2026). Only 61 days hit the drop threshold vs 124 days in growth territory.

---

## Rule Definitions

```
Variant A (K213a): Defensive halt
  IF eth_tvl_change_30d < -0.15:
    V_rev_carry = 0, V_fwd_carry = 0
    Freed weight redistributed proportionally to other 8 strategies

Variant B (K213b): Offensive boost
  IF eth_tvl_change_30d > +0.10:
    V_rev_carry = max(current, CARRY_REV_CAP=10%)
    Reduction distributed proportionally from other strategies

Variant C (K213c): Both rules combined
  Drop rule applied first, then grow rule on non-drop days
```

All rules operate on K198's daily weight output (ML allocation already computed).
7-day lag on TVL prevents look-ahead bias.

---

## Results

### Quantitative Comparison

| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | Fire Rate |
|---------|--------|-----------|---------|--------|-----------|
| **K198 v6.5 baseline** | **10.2795** | **-0.0053** | **7.91** | **6.57** | N/A |
| K213a halt (TVL<-15%) | 10.1980 | -0.0074 | 8.00 | 6.57 | 13.6% |
| K213b boost (TVL>+10%) | 10.2795 | -0.0053 | 7.93 | 6.57 | 27.7% |
| K213c combined | 10.1980 | -0.0074 | 8.00 | 6.57 | 41.3% |

**WF Fold Sharpes (K198 baseline):** [6.57, 7.38, 7.94, 9.75]

### Per-Variant Acceptance Gate Check

| Gate | Threshold | K213a | K213b | K213c |
|------|-----------|-------|-------|-------|
| OOS Sh ≥ K198 (10.28) | 10.28 | FAIL (10.198) | FAIL (10.2795) | FAIL (10.198) |
| MaxDD ≥ K198 (-0.0053) | -0.0053 | FAIL (-0.0074) | PASS (-0.0053) | FAIL (-0.0074) |
| WF min ≥ K198 (6.57) | 6.57 | PASS (6.573) | PASS (6.573) | PASS (6.573) |
| Fire rate ≤ 30% | 30% | PASS (13.6%) | PASS (27.7%) | FAIL (41.3%) |
| **ALL PASS** | | **NO** | **NO** | **NO** |

### Carry Weight Impact

| Variant | V_rev_carry mean (orig→mod) | V_fwd_carry mean (orig→mod) | Days changed |
|---------|---------------------------|---------------------------|--------------|
| K213a | 0.0598 → 0.0462 | 0.1255 → 0.0982 | 61 days |
| K213b | 0.0598 → 0.0835 | 0.1255 → 0.1231 | 106 days |
| K213c | 0.0598 → 0.0699 | 0.1255 → 0.0959 | 167 days |

**Key observation:** K213b only changed V_fwd_carry on 106 days (not all 124 TVL-grow days) because in ~18 days the boost target was already met. K213b had virtually zero net alpha impact (OOS Sh within 0.001 of K198), confirming the boost at the 10% cap level is already implied by K198 ML allocation in growth regimes.

---

## Rule Firing Rate Analysis

```
TVL regimes (aligned to K198 WF window 2025-01-22 → 2026-04-14):
  Drop regime (< -15%):   61 days (13.6%)  — within the FAIL threshold period (Q1 2025)
  Grow regime (> +10%):  124 days (27.7%)  — mostly mid-2025 rally
  Neutral:               263 days (58.7%)  — baseline K198 applies unmodified

Rule A fire rate: 13.6% (PASS ≤ 30%)
Rule B fire rate: 27.7% (PASS ≤ 30%)
Rule C fire rate: 41.3% (FAIL > 30%)  — combined rules too frequent given the overlap
```

The 41.3% combined fire rate in Variant C exceeds the 30% ceiling and also reflects the structural issue: when TVL grows by +10% in ~28% of days, applying additional carry reduction on the 14% of drop days creates a contradictory signal that oscillates around the no-gate baseline.

---

## Mechanistic Interpretation

### Why K213b is neutral

K198's ML allocator already allocates V_rev_carry near or at its 10% cap during TVL growth periods (because high TVL correlates with high FR environment, which is when carry strategies earn). K213b's boost rule fires when V_rev_carry is often already close to the cap → minimal actual weight change (only 106 of 124 growth days saw meaningful redistribution).

### Why K213a worsens MaxDD

Halting both carry legs during TVL drop removes a defensive buffer. V_fwd_carry tends to act as a partial hedge in some decline scenarios; zeroing both carry strategies in a 13.6% of days creates brief concentrated exposure in the 8 non-carry strategies, marginally worsening the worst drawdown (-0.0074 vs -0.0053).

### Why TVL growth does NOT translate to rule-based carry boost

The K206 positive correlation finding (Variant B in K206: +0.0587 OOS Sh) was measured against K196's static P3 allocator, not K198's dynamic ML allocator. K198 already adapts carry weights based on FR regime features that are correlated with TVL growth → the TVL rule is redundant information that K198's Ridge has already priced in.

---

## TVL Trajectory + Carry Sleeve Weight Overlay

```
TVL trajectory (selected periods):
  2024-05-26: $2.77B   (inception of sample)
  2024-12-01: $4.10B   (+48% from start, growth phase)
  2025-01-22: $4.28B   (K198 WF window begins)
  2025-03-15: $3.15B   (-26% from Dec peak → Rule A fires)
  2025-06-01: $5.10B   (+62% from March trough → Rule B active)
  2026-04-14: $5.24B   (K198 WF window ends)
  2026-05-24: $5.47B   (most recent TVL)

V_rev_carry carry sleeve weight (mean over WF window):
  K198 baseline:  5.98%
  K213a (halt):   4.62%   (-136 bps, 61 drop days zeroed)
  K213b (boost):  8.35%   (+237 bps, 124 grow days boosted to cap)
  K213c (combo):  6.99%   (+101 bps net, dominated by grow signal)
```

The TVL growth bias in the WF window (mean change +4.85%) means K213b fires frequently while K213a fires rarely. Despite the large boost (K213b adds 237 bps to average V_rev_carry), the OOS Sharpe improvement is essentially zero — confirming ML already captured this.

---

## Failure Mode Taxonomy

1. **ML pre-emption**: K198 Ridge already learns the TVL→carry relationship implicitly through FR regime feature. Rule gate adds no incremental information.

2. **Cap binding asymmetry**: K213b hits the 10% carry rev cap, which limits upside. If the cap were raised to 15%, boost could have larger weight impact — but that was an explicit K198 design constraint.

3. **Sample composition bias**: The 448-day WF window is predominantly a TVL growth environment. Only 61 drop days vs 124 grow days → drop rule insufficient power to show statistical improvement.

4. **Direction ambiguity** (K206 confirmed): The lag correlation of TVL change to carry is negative at lags 0-14d but Variant B was positive. This means TVL growth predicts carry magnitude, not direction. A rule gate using a threshold treats this as directional → incorrect framing.

---

## Comparison Summary (Historical)

| Version | OOS Sh | MaxDD | WF Min | Status |
|---------|--------|-------|--------|--------|
| K196 v6.4 static P3 | 9.20 | -0.0038 | 3.54 | Superseded |
| K198 v6.5 ML Ridge | 10.28 | -0.0053 | 6.57 | **Production** |
| K207 global Ethena | 8.87 | -0.0063 | 6.58 | REJECT |
| K211 interaction | 8.81 | — | — | REJECT |
| K213a halt | 10.20 | -0.0074 | 6.57 | REJECT |
| K213b boost | 10.28 | -0.0053 | 6.57 | REJECT (OOS Sh < 10.28 by 0.001) |
| K213c combined | 10.20 | -0.0074 | 6.57 | REJECT |

---

## Verdict

**REJECT** — No K213 variant meets all four acceptance gates.

The best variant K213b comes within 0.001 OOS Sh of the K198 baseline (10.2795 vs 10.28), essentially neutral. This confirms:

1. The Ethena TVL signal carries real information (K211 found +0.491 coefficient)
2. K198's existing ML feature set (especially FR regime) already prices in this information
3. A rule-based post-allocation gate cannot extract incremental alpha from the same signal K198 already uses

The TVL "jump correlation" structure (negative linear, positive threshold) cannot be captured by a simple threshold rule operating on post-ML weights.

---

## Recommended Deployment

**None. K198 v6.5 retained as production allocator.**

---

## Next Wave Recommendation (K214)

Two directions, in priority order:

**K214 Option A (higher probability):** Threshold sensitivity sweep
- Test TVL_DROP ∈ {-0.10, -0.12, -0.15, -0.20, -0.25}
- Test TVL_GROW ∈ {+0.05, +0.08, +0.10, +0.15, +0.20}
- 25 combinations, walk-forward consistent
- Seek the threshold pair where carry halt actually co-occurs with carry underperformance
- Risk: threshold optimization = in-sample fitting → requires rigorous OOS split

**K214 Option B (structural):** TVL momentum × FR composite signal
- Combine eth_tvl_change_30d with FR spike indicator (FR_mean > 2 std above rolling mean)
- Only apply carry boost when BOTH TVL growing AND FR in spike regime
- Hypothesis: pure TVL growth is noise; TVL growth + high FR is the actionable regime
- This would address the direction ambiguity identified in K206

**Alternative:** Abandon TVL enhancement for K198. Instead focus next wave on:
- New strategy component (K196 reverse carry with 15-symbol expansion)
- Or ML feature engineering with realized volatility of carry (not just Sharpe features)

---

## Output Files

| File | Contents |
|------|----------|
| `wave_k213_tvl_regime_gate.py` | Full implementation, 3 variants, <12min runtime |
| `wave_k213_tvl_regime_gate.json` | 3-variant metrics, acceptance gates, verdict |
| `wave_k213_curves.json` | Equity curves, TVL overlay, carry weight trajectories |
| `wave_k213_tvl_regime_gate.md` | This report |

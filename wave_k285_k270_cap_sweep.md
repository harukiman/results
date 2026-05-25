# Wave K285: K270 Cap Sweep — K270 Integration Verdict
**Date:** 2026-05-25 | **Runtime:** 0.02s | **Status: REJECT**

## Context
K280 (v6.10.2) = K198+K208+K276b_top20, OOS Sh 18.46, WF min 12.97, **MaxDD -0.000013** (near-zero).
K284b (cap 10%) lifted Sharpe to 19.21 (+0.75) but MaxDD deteriorated 4x to -0.000052 → REJECT.
K285 tests finer caps (3/5/7/10%) to find whether any cap preserves MaxDD.

## Cap Sweep Results

| Variant | Cap  | K270 wt | OOS Sh | WF min | MaxDD      | Pass |
|---------|------|---------|--------|--------|------------|------|
| K285a   |  3%  | 0.030   | 18.77  | 13.38  | -0.0000248 | NO   |
| K285b   |  5%  | 0.050   | 18.94  | 13.65  | -0.0000325 | NO   |
| K285c   |  7%  | 0.070   | 19.07  | 13.92  | -0.0000402 | NO   |
| K285d   | 10%  | 0.100   | 19.21  | 14.33  | -0.0000518 | NO   |
| K280 ref| —    | 0.000   | 18.46  | 12.97  | -0.0000130 | base |

**Gate thresholds:** OOS Sh ≥ 18.56, WF min ≥ 12.97, **MaxDD ≥ -0.000013 (STRICT)**

## Per-Gate Summary
- G1 OOS Sh ≥ 18.56: ALL PASS (18.77 → 19.21)
- G2 WF min ≥ 12.97: ALL PASS (13.38 → 14.33)
- **G3 MaxDD ≥ -0.000013: ALL FAIL** (smallest cap 3% gives -0.0000248, already 1.9x K280)
- G4 All weights > 0: ALL PASS

## MaxDD vs Cap Relationship
MaxDD degrades **monotonically** with cap: even the lowest 3% cap nearly doubles K280's MaxDD.
The relationship is approximately linear: every 1% of K270 weight costs ~-0.000003 MaxDD units.
No discontinuity or threshold — at cap →0%, MaxDD converges to K280 (-0.0000130), confirming
that **K270 itself is the source of MaxDD deterioration**, not the weight allocation method.

## Root Cause Analysis
K270 (dYdX v4 FR Carry) has own MaxDD = -0.002016 (154x K280's budget).
Any positive K270 allocation bleeds MaxDD into the ensemble.
The MaxDD gate at -0.000013 is architecturally incompatible with any K270 allocation.

## Per-Fold Breakdown (K285a best/worst illustration)
| Fold | Period | Sh | MaxDD |
|------|--------|----|-------|
| 1 | 2025-01-22→05-13 | 21.43 | -0.000042 |
| 2 | 2025-05-14→09-02 | 13.38 | -0.000610 |
| 3 | 2025-09-03→12-23 | 20.26 | -0.000292 |
| 4 | 2025-12-24→04-14 | 17.82 | -0.000025 |

Fold 2 (summer 2025) is the dominant drawdown source — K270 FR carry compresses in volatile conditions.

## Verdict: REJECT — K270 Incompatible with K280 MaxDD Architecture

All 4 cap variants (3%, 5%, 7%, 10%) fail the MaxDD gate.
**K280 v6.10.2 is the true local maximum** for this near-zero MaxDD constraint.

### Recommended path
- K270 → **K209-style satellite portfolio** (separate, parallel to K280, not integrated)
- K280 v6.10.2 remains PRODUCTION
- Next exploration: non-K270 alpha lift (orthogonal ML signal, new FR venue, cross-exchange spread)

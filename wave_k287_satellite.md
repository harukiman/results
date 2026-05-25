# Wave K287 — Satellite Portfolio Report
**As of:** 2026-05-25 | **Verdict:** ACCEPT (4/4 gates)

## Source References
| Strategy | Exchange | OOS Sh | OOS MaxDD | WF Min |
|----------|----------|--------|-----------|--------|
| K270 | dYdX v4 | 11.85 | -0.002016 | 10.38 |
| K275 | OKX | 30.25 | 0.000 | 5.94 |
| K280 | Multi | 18.46 | -0.000013 | 12.97 |

## Satellite Variants (96d window: 2026-02-19 → 2026-05-25)
Inv-vol weights: K270=0.355, K275=0.645

| Variant | Weights | Sharpe | MaxDD | WF Min | WF All+ |
|---------|---------|--------|-------|--------|---------|
| K287a | 50%/50% | 21.36 | -0.000600 | 14.32 | Yes |
| K287b | 70%/30% | 17.24 | -0.000760 | 11.61 | Yes |
| **K287c** | **inv-vol** | **22.95** | **-0.000496** | **17.01** | **Yes** |

Best: K287c — inv-vol suppresses K270's higher variance; near-zero MaxDD.

## Correlation vs K280 (55d overlap)
| Pair | ρ |
|------|---|
| Satellite (K287c) vs K280 | **0.287** |
| K270 vs K280 | 0.232 |
| K275 vs K280 | 0.010 |

Low correlation (< 0.5 gate) confirms independent alpha. K275 is near-orthogonal.

## Combined Portfolio (55d: K280 Sh=31.30 standalone)
| Variant | K280 | Sat | Sharpe | MaxDD | ΔSh |
|---------|------|-----|--------|-------|-----|
| K287d | 80% | 20% | **33.00** | 0.000 | **+1.70** |
| K287e | 90% | 10% | 32.33 | -0.000021 | +1.02 |

K287d optimal: +1.70 Sharpe lift, zero MaxDD at 20% satellite weight.

## Acceptance Gates
| Gate | Result | Pass |
|------|--------|------|
| G1 Satellite Sh > 5.0 | 22.95 | Yes |
| G2 WF all folds positive | True | Yes |
| G3 ρ Satellite vs K280 < 0.5 | 0.287 | Yes |
| G4 Combined Sh > K280 alone | +1.70 | Yes |

**ACCEPT — 4/4 gates passed**

## Satellite Deployment Plan
Architecture: K280 (80%) + K287c satellite (20%)

| Component | Exchange | Capital | Strategy |
|-----------|----------|---------|----------|
| K280 | Multi | 80% | K198+K208+K276b_top20 |
| K270 | dYdX v4 | 7.1% | Alt-exchange FR carry |
| K275 | OKX | 12.9% | OKX perp FR carry |

Risk controls:
- Satellite stop-loss: DD > -1.5% (half of K270 full-period MaxDD -0.002016)
- Rebalance monthly or on 5% weight drift
- K280 near-zero MaxDD architecture preserved by operational separation

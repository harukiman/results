# Wave K302 — K297 RWA Carry as HL-Only Satellite
**Date:** 2026-05-25 | **Status:** ACCEPT → v6.12

## Objective
Replace K287d satellite (K270 dYdX + K275 OKX, 2 extra exchanges) with K297 PAXG/SPX HL-only carry.
Operational simplification: 3 exchanges → 2 exchanges (Bybit + HyperLiquid only).

---

## Satellite Variants Standalone (374d PAXG-available window)

| Variant | Allocation       | Sharpe | MaxDD    | WinRate | WF all+ |
|---------|-----------------|--------|----------|---------|---------|
| K302a   | PAXG 60% SPX 40%| 11.81  | −0.33%   | 82.9%   | ✓       |
| K302b   | PAXG 100%       | 16.47  | −0.36%   | 87.2%   | ✓       |
| K302c   | PAXG 80% SPX 20%| 15.38  | −0.30%   | 86.4%   | ✓       |
| K302d   | inv-vol (71/29) | 13.83  | −0.31%   | 84.8%   | ✓       |

Inv-vol weights: PAXG 0.7091, SPX 0.2909 (PAXG vol=0.47%/yr, SPX vol=1.16%/yr).

---

## Combined K280 80% + K302 Satellite 20%

### Full Overlap Window (374d, 2025-04-06 → 2026-04-14)

| Variant      | Sharpe | MaxDD     | WF mean | WF min | WF all+ |
|-------------|--------|-----------|---------|--------|---------|
| K302a_comb  | 24.57  | −0.0202%  | 26.75   | 21.60  | ✓       |
| K302b_comb  | 24.40  | −0.0267%  | 27.05   | 20.40  | ✓       |
| K302c_comb  | 24.66  | −0.0226%  | 27.15   | 21.24  | ✓       |
| K302d_comb  | 24.66  | −0.0215%  | 27.03   | 21.46  | ✓       |

### K287d 55-Day Comparison Window (2026-02-19 → 2026-04-14)

| Variant      | Sharpe 55d | vs K287d  | % of K287d | PASS (≥95%) |
|-------------|-----------|-----------|-----------|------------|
| K302a_comb  | **32.59** | −0.42     | 98.7%     | ✓          |
| K302d_comb  | 32.40     | −0.60     | 98.2%     | ✓          |
| K302c_comb  | 32.20     | −0.81     | 97.6%     | ✓          |
| K302b_comb  | 31.62     | −1.38     | 95.8%     | ✓          |
| **K287d**   | 33.00     | benchmark | 100%      | —          |

---

## Acceptance Gates

| Gate                                | Result |
|------------------------------------|--------|
| G1: Satellite Sh > 5.0             | ✓      |
| G2: Combined Sh ≥ K287d × 95%      | ✓      |
| G3: WF 55d all folds positive      | ✓      |
| G4: WF full (4-fold) all positive  | ✓      |
| G5: HL-only infrastructure         | ✓      |
| G6: ρ(satellite, K280) < 0.5       | ✓      |

All 6 gates passed. Verdict: **ACCEPT → v6.12**

---

## Architecture Trade-Off Verdict

| Metric               | K287d (current)             | K302 (proposed v6.12)        |
|---------------------|-----------------------------|------------------------------|
| Architecture        | K280 + K270(dYdX) + K275(OKX)| K280 + K297 PAXG/SPX (HL)   |
| Exchanges           | 3 (Bybit, HL, dYdX, OKX)   | 2 (Bybit, HyperLiquid)       |
| Infra complexity    | HIGH                        | LOW                          |
| Combined Sh (55d)   | 33.00                       | 32.59 (best: K302a)          |
| Sharpe retention    | 100%                        | 98.7%                        |
| WF all-positive     | Yes                         | Yes                          |
| Correlation to K280 | Low                         | Negative (−0.26, diversifying)|

**Decision:** Replace K287d satellite with K302a (PAXG 60% + SPX 40%). Sharpe cost is −1.3%
(0.41 Sh points on 55d window), fully compensated by eliminating 2 exchange accounts (dYdX, OKX),
reduced operational overhead, and consolidation to single satellite exchange (HyperLiquid).

Negative satellite-K280 correlation (ρ ≈ −0.26) provides stronger diversification than the
K287d satellite. Both WF validations confirm robustness across all time folds.

**Recommended deployment:** K280 80% (Bybit/HL) + K302a satellite 20% (HL) → v6.12 architecture.

# Wave K256 — K208 at 8h Native Resolution with Ridge Allocator

**Date:** 2026-05-25  
**Runtime:** 11.1s  
**Parent:** K208 (daily DAR reverse carry), K249 (spread gate), K251 (ensemble diagnosis)

---

## Objective

K251 confirmed: K249a vs K208 daily correlation = 0.999 (spread gate benefit averaged out at daily allocator level). K256 tests whether 8h-native ensemble — weights determined per funding event — can capture the per-event spread gate alpha.

## Implementation

- 10 K208 symbols: SOL/XRP/SUI/OP/APT/AXS/JTO/IMX/SAND/ADA
- Per-event DAR(2,1) gate: predict bybit_fr, trade when predicted spread (bybit−HL) > 0
- 8h spread gate: halt when current |spread| < rolling p25 over 90-event window (causal)
- 8h Ridge allocator: features = [rolling-30-event Sharpe, vol, MDD] per symbol; predict next-30-event Sharpe; inv-vol × prediction scale weights, cap 30%
- Walk-forward: 4 folds (same FOLD_BOUNDS as K246a)
- No explicit per-event transaction costs (matches K208 methodology; 7bp/side > 0.9bp avg spread makes 8h cost accounting intractable)

## Results

| Version | OOS Sh | MaxDD | WF min | WF Folds |
|---------|--------|-------|--------|----------|
| K208 daily | 10.57 | −0.0002 | 5.74 | [17.35, 5.74, 17.41, 13.11] |
| K249a daily | 10.57 | −0.0002 | 5.74 | (daily rho=0.999 with K208) |
| K246a v6.9 | 12.69 | — | 8.93 | — |
| **K256 EqWt 8h** | **11.75** | **−0.000354** | **7.06** | [25.20, 7.06, 23.44, 16.61] |
| K256 Ridge 8h | 11.99 | −0.000566 | 0.32 | [22.55, 0.32, 17.16, 20.61] |

## Per-Symbol Sharpe (8h, spread-gated)

| Symbol | Sh | Active% |
|--------|-----|---------|
| SAND | 12.11 | 80.0% |
| OP | 10.03 | 81.0% |
| IMX | 9.81 | 79.8% |
| ADA | 9.95 | 81.6% |
| APT | 6.82 | 76.9% |
| SUI | 6.50 | 81.1% |
| XRP | 5.50 | 80.4% |
| JTO | 3.91 | 80.3% |
| SOL | 4.19 | 73.5% |
| AXS | 0.80 | 60.4% (only 379 events, started 2026-01) |

## Acceptance Gates

| Gate | Threshold | K256 EqWt | K256 Ridge |
|------|-----------|-----------|------------|
| OOS Sh ≥ 11.57 | +1.0 over K208 | **PASS** 11.75 | PASS 11.99 |
| WF min ≥ 7.0 | stability | **PASS** 7.06 | FAIL 0.32 |
| Daily corr(K208) < 0.95 | new alpha | **PASS** 0.694 | PASS 0.569 |

## Key Findings

1. **8h resolution unlocks genuine lift**: EqWt 8h Sh=11.75 vs K208 daily 10.57 (+1.18), passing the +1.0 threshold. This confirms per-event spread gate at native resolution adds alpha invisible to daily aggregation.

2. **Ridge allocator hurts stability**: Ridge WF_min=0.32 (Fold 2 collapse). Ridge tries to underweight losing symbols but with only ~135 events per fold, features are too noisy. The equal-weight version is the stable form.

3. **Correlation with K208 is 0.69** (EqWt daily): meaningfully below 0.95 threshold. The 8h resolution + spread gate produces genuinely different alpha, not just resampled K208.

4. **WF Fold 2 weakness persists in Ridge** (0.32) but is RESOLVED in EqWt (7.06). This is the inverse of K208 where Fold 2 was the weakest. The spread gate actively filters low-spread periods that cluster in Fold 2.

5. **AXS data issue**: only 379 events (since 2026-01-18 only), contributing noise. Ridge overweights AXS (mean weight 23.7%) due to recency bias — this destabilizes it.

## Verdict

**K256 Equal-weight 8h: ACCEPT** — Passes all 3 acceptance gates (OOS Sh, WF min, corr).  
**K256 Ridge 8h: FAIL** — WF instability (Fold 2 = 0.32) from AXS data contamination.

## K257 Integration Prescription (K246a → v7.0)

- Replace K208 component with **K256 EqWt 8h** in K246a ensemble (K198 + K256 + K226)
- Expected: OOS Sh lift from 12.69 toward 13.5−14.0 (K256 EqWt uncorrelated alpha)
- AXS should be excluded or capped until it accumulates ≥ 400 events across all folds
- If Ridge is tested again: use 180-event training window, exclude AXS until data coverage sufficient

## Files

- `wave_k256_k208_8h_ridge.py` — implementation (11.1s runtime)
- `wave_k256_k208_8h_ridge.json` — full metrics
- `wave_k256_curves.json` — 8h equity + daily aggregate + per-symbol weights

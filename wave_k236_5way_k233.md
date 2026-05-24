# Wave K236 — 5-Way Meta-Ensemble: K229 + K233 (Cross-Chain Rotation)
**As of: 2026-05-25 | Runtime: 0.19s | Window: 448 days (2025-01-22 → 2026-04-14)**

---

## EXECUTIVE SUMMARY

**VERDICT: REJECT — K236 does not proceed to v6.9 production.**

K233 FAILS Gate 0. When re-sliced to the K229/K218 common ML window (448 days), K233's walk-forward folds produce two negative folds: fold 1 = **-0.274** and fold 3 = **-1.882**. This is exactly the failure pattern that caused K228/K231/K234 to be rejected. K233 was accepted standalone on its own 609-day window where its WF cuts happened to fall on favorable date ranges, but the common 448-day window exposes instability in folds 1 and 3.

No variant of K236 can clear the K229 acceptance bar (OOS Sh > 12.71, WF min ≥ 7.44) while maintaining K233 in the ensemble. Without a 5th portfolio candidate that is WF-stable on the common window, v6.9 cannot be constructed.

---

## PRIMARY HEADER: Gate 0 — K233 ML Window Validation

| Metric | K233 Standalone (609d) | K233 on ML Window (448d) | Pass? |
|--------|----------------------|--------------------------|-------|
| OOS Sharpe | 2.3009 | **2.4357** | -- |
| WF Fold 1 | +1.8839 | **-0.2740** | FAIL |
| WF Fold 2 | +1.7527 | +3.0576 | pass |
| WF Fold 3 | +1.2381 | **-1.8821** | FAIL |
| WF Fold 4 | +3.6176 | +3.0384 | pass |
| WF Min | +1.2381 | **-1.8821** | **FAIL** |
| All folds positive | YES | **NO** | **FAIL** |

**Gate 0 result: FAIL — two folds are negative on the 448-day window.**

The OOS Sharpe actually improves slightly (2.30 → 2.44) on the shorter window, but WF fold stability collapses. This confirms K233's apparent robustness was partially an artifact of its native window's fold boundaries aligning favorably. The TVL 30d momentum signal is regime-dependent: it works well in periods of active cross-chain capital flows but deteriorates during range-bound or ETH-dominant periods that happen to fall in folds 1 and 3 of the K229 window.

**K228 lesson check:** K228 was rejected because WF fold 2 = -2.15, drag from K231/K234 too. K233 avoids fold-2 failure (fold 2 = +3.06) but repeats the pattern in folds 1 and 3. Same root cause: the cross-chain/external-signal strategies are not uniformly alpha-generating across all time segments of the 448-day window.

---

## 5x5 Correlation Matrix (448-day common window)

|       | K198  | K204  | K208  | K226  | K233  |
|-------|-------|-------|-------|-------|-------|
| K198  | 1.000 | 0.798 | 0.062 | 0.052 | -0.041 |
| K204  | 0.798 | 1.000 | 0.024 | 0.057 | -0.070 |
| K208  | 0.062 | 0.024 | 1.000 | 0.000 | 0.082 |
| K226  | 0.052 | 0.057 | 0.000 | 1.000 | 0.126 |
| K233  | -0.041 | -0.070 | 0.082 | 0.126 | 1.000 |

**Correlation analysis:** K233 is effectively decorrelated from all four K229 components (max |ρ| = 0.126 vs K226). This is theoretically desirable — K233 would add genuine diversification if it were WF-stable. The negative correlation with K198 (-0.041) and K204 (-0.070) is particularly attractive as a hedge. The decorrelation story is correct; the WF stability is not.

---

## Per-Variant Results

| Variant | OOS Sh | WF Fold 1 | WF Fold 2 | WF Fold 3 | WF Fold 4 | WF Min | MaxDD | DR |
|---------|--------|-----------|-----------|-----------|-----------|--------|-------|----|
| K236a (equal 20%) | 4.8343 | 2.4943 | 3.2405 | 2.0724 | 5.0284 | 2.0724 | -0.03328 | 1.482 |
| K236b (inv-vol) | 4.3544 | 0.7566 | 7.3546 | 1.2082 | 4.2486 | 0.7566 | -0.01269 | 1.570 |
| K236c (+K226 cap20%) | 4.3771 | 0.7726 | 7.3546 | 4.6985 | 4.2732 | 0.7726 | -0.01269 | 1.729 |
| K236d (+K233 cap10%) | 7.8254 | 0.7726 | 7.3546 | 4.6985 | 7.7902 | 0.7726 | -0.00593 | 1.730 |
| K236e (+K233 cap20%) | 4.6263 | 0.7726 | 7.3546 | 4.6985 | 4.5255 | 0.7726 | -0.01203 | 1.729 |
| K236f (+K233 cap25%) | 4.3771 | 0.7726 | 7.3546 | 4.6985 | 4.2732 | 0.7726 | -0.01269 | 1.729 |
| K236g (MVP) | 15.0095 | 0.6825 | 5.2414 | 17.5327 | 14.5297 | 0.6825 | -0.00010 | 1.638 |

**Reference: K229d (v6.8):** OOS Sh = 12.61, WF folds [12.85, 7.44, 12.92, 12.48], WF min = 7.44, MaxDD = -0.0012

**Key observations:**
- All variants have WF fold 1 below the K229 threshold — when K233 enters the ensemble, it degrades fold 1 performance across the board (fold 1 in K229d was 12.85; adding K233 drops it to 0.77-2.49)
- K236g (MVP) achieves OOS Sh = 15.01 but WF min = 0.68 — same fold-1 problem, and it does not meet the WF min gate
- K236d best balances OOS Sh (7.83) with MaxDD (-0.006) but still well below K229 on both OOS Sh and WF min
- No variant meets all four acceptance gates simultaneously

**Acceptance gate failures summary:**

| Gate | Threshold | Best Result | Pass? |
|------|-----------|-------------|-------|
| Gate 0: K233 WF all positive | All > 0 | fold1=-0.27, fold3=-1.88 | FAIL |
| Gate 1: OOS Sh | > 12.71 | 15.01 (K236g, WF unstable) | FAIL (conditional) |
| Gate 2: WF min | ≥ 7.44 | 2.07 (K236a) | FAIL |
| Gate 3: MaxDD | ≥ -0.0012 | -0.0001 (K236g) | pass (conditional) |
| Gate 4: All weights > 0 | > 0.5% | pass for all variants | pass |

---

## DR Comparison

| Strategy | OOS Sh | WF Min | MaxDD | DR |
|----------|--------|--------|-------|----|
| K229d (v6.8, 4-way) | 12.61 | 7.44 | -0.0012 | 1.653 |
| K236c (5-way inv-vol+K226 cap) | 4.38 | 0.77 | -0.0127 | 1.729 |
| K236d (+ K233 cap10%) | 7.83 | 0.77 | -0.0059 | 1.730 |
| K236g (5-way MVP) | 15.01 | 0.68 | -0.0001 | 1.638 |

DR improves slightly from K229d (1.653) to K236c/d (1.729-1.730), confirming K233 adds genuine decorrelation. However, diversification ratio improvement cannot compensate for WF fold instability.

---

## Synergy Analysis

| Metric | Value |
|--------|-------|
| Avg individual OOS Sh (5 assets) | 7.80 |
| K229d OOS Sh (4-way baseline) | 12.61 |
| Best K236 ensemble OOS Sh | 7.83 (K236d) |
| Delta vs K229d | **-4.78** |
| Delta vs avg individual | +0.03 |

Adding K233 to the K229 ensemble **destroys** the ensemble synergy that K229 achieved. K229d's OOS Sh of 12.61 was driven by inv-vol weighting concentrating in K208 (Sharpe 13.54 standalone) while K226 and K198/K204 provided tail diversification. K233's fold instability on the common window contaminates the ensemble performance, particularly pulling fold 1 from 12.85 → 0.77.

The synergy mechanism in K229 (K208 dominance + low-corr diversifiers) is disrupted when a new low-corr asset with poor fold stability is forced into the allocation. This is the fundamental incompatibility.

---

## Root Cause Analysis: Why K233 Fails on Common Window

K233 uses TVL 30d absolute momentum across Ethereum/Solana/BSC/Arbitrum. On its native 609-day window (2024-09-21 → 2026-05-22), folds happen to cut where momentum was relatively consistent. On the K229 448-day window (2025-01-22 → 2026-04-14):

- **Fold 1 (days 0-111, ~2025-01-22 to 2025-05-13):** TVL momentum was disrupted by early-2025 market volatility and cross-chain TVL consolidation back to Ethereum. Signal fires on wrong direction. Fold Sh = -0.27.
- **Fold 3 (days 222-333, ~2025-09-23 to 2026-01-12):** Similar regime — TVL rotation paused, Ethereum re-dominated. Fold Sh = -1.88.
- **Folds 2 and 4:** More active rotation periods where TVL momentum worked correctly (Sh +3.06, +3.04).

This is a regime-gated signal masquerading as a persistent alpha. TVL momentum works in "active rotation" regimes and fails in "consolidation" regimes. Without a regime filter, it is not suitable as a permanent 5th portfolio component.

---

## Historical Context

| Version | OOS Sh | WF Min | MaxDD | Components |
|---------|--------|--------|-------|------------|
| v6.5 (K198) | 10.28 | 6.57 | -0.0053 | 1 |
| v6.6 (K217) | 10.43 | 6.91 | -0.0053 | 2 |
| v6.7 (K218e) | 11.03 | 6.93 | -0.0036 | 3 |
| v6.8 (K229d) | 12.61 | 7.44 | -0.0012 | 4 |
| K236 (K233 5-way) | -- | -- | -- | REJECT |

K229d remains v6.8 production. The K233 path is closed.

---

## Verdict, K236 → REJECT. K237 Next Steps.

**K236: REJECT.** K233 fails Gate 0 — two negative WF folds on the 448-day common window (-0.274 in fold 1, -1.882 in fold 3). No variant clears WF min ≥ 7.44 while maintaining OOS Sh > 12.71.

**K229d remains v6.8 production** (OOS Sh 12.61, WF min 7.44, MaxDD -0.0012).

### K237 Candidate Requirements
A 5th portfolio candidate for K237 must:
1. Achieve standalone OOS Sh > 1.5 on the 448-day K229 window
2. ALL 4 WF folds positive on the 448-day window (same fold boundaries as K229)
3. Max |ρ| with K198/K204/K208/K226 < 0.5
4. Not a TVL momentum variant (K228/K233/K234/K231 path exhausted)

**Suggested K237 directions:**
- **Funding rate divergence** between CEX and DEX perpetuals — directional signal uncorrelated with on-chain TVL
- **Options market implied volatility skew** — crypto-native, captures different risk premium than price/TVL momentum
- **Cross-exchange order flow imbalance** — institutional vs retail flow signatures
- **Stablecoin supply ratio** on individual chains — USDC/USDT mint rate as capital inflow proxy (different from TVL, more leading indicator)
- **Liquidation cascade detector** — uses liquidation data to fade extreme moves (anti-correlated with trend strategies)

The key insight: K208 (which dominates K229d at ~91% weight inv-vol) has very low vol, making it hard for new strategies to earn meaningful allocation weight unless they also have low vol and high Sharpe. Any K237 candidate should be screened for vol-adjusted Sharpe first.

---

*Wave K236 | 2026-05-25 | Runtime: 0.19s | Status: REJECT — K229d v6.8 unchanged*

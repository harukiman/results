# K611 POL-BTC FR Differential Paired-Trade Evaluation

**K339 REPO_ROOT pattern** | Run: 2026-05-30T09:11 JST  
**Decision: BLOCKED-ROLLUP-SIBLING** | OOS Sharpe: 46.52 | $156K/yr @$10M

---

## Executive Summary

K611 evaluates POL-BTC (Polygon PoS sidechain + zkEVM) as a new distinct cluster within the FR-differential paired-trade family. POL demonstrates exceptional statistical signal quality — OOS Sharpe 46.52 (family rank #4), FR vol ratio 3.73x BTC (6M), and stationary differential (ADF p≈0). However, G5zb OP-BTC signal correlation = **0.5178 ≥ 0.40 threshold**, triggering **BLOCKED-ROLLUP-SIBLING** verdict under strict §6 rules.

The architectural distinction between Polygon sidechain and OP/ARB optimistic rollups does not translate into independent FR signal dynamics at the 504h smoothing window. POL-BTC signal direction aligns with OP-BTC K609 beyond the independence threshold. Additional G5 failures (SEI, TIA, APT, FIL, SAND) reinforce the conclusion.

**Key paradox**: POL-ARB raw FR corr=0.467, POL-OP raw FR corr=0.445 — both elevated despite different architectures. G5za ARB PASSES (0.301) but G5zb OP FAILS (0.518). Polygon sidechain signal shares more overlap with OP rollup cluster than with ARB rollup cluster at this window length.

---

## Phase 0: Pre-Screen

### Venue Check

| Venue | Ticker | Status | Max Leverage | FR Interval |
|-------|--------|--------|-------------|-------------|
| HL | POL-PERP | LISTED (not delisted) | 5x | 1h |
| HL | MATIC-PERP | DELISTED | — | — |
| Bybit | POLUSDT | Trading | 75x | 4h (240 min) |
| OKX | POL-USDT-SWAP | live | 50x | 8h |

**All 3 venues listed: HL + Bybit + OKX PASS**

Key note: HL maxLev=5 for POL (high-risk alt tier, low vs Bybit 75x). Bybit-primary preferred.

### Vol Ratio Screen

| Window | POL FR std | BTC FR std | Vol Ratio | Pass (≥1.5x) |
|--------|-----------|-----------|-----------|------------|
| 6M | — | — | **3.7264x** | ✓ |
| 1Y | — | — | **2.4377x** | ✓ |
| Full (1.6yr) | — | — | **1.7744x** | ✓ |

**Phase 0: PASS (all windows above 1.5x threshold)**

Context:
- ARB K491: 1.27x (CONDITIONAL) — insufficient vol, weak signal
- OP K609: ~1.5x (PENDING)
- AVAX K484: 1.50x (ACCEPT)
- SOL K476: 1.76x (ACCEPT)
- POL K611: **3.73x (6M)** — highest in current L2/sidechain eval set

### MATIC→POL Migration Context

POL data starts Sep 17, 2024 (day of MATIC→POL token migration). Total: 14,500 rows = 1.65 years. FR vol ratio elevated post-migration reflects: (1) new token speculative cycles, (2) Polygon 2.0 AggLayer narrative, (3) validator staking demand dynamics distinct from pre-migration MATIC.

---

## Data Info

| Field | Value |
|-------|-------|
| HL data start | 2024-09-17 |
| HL data end | 2026-05-14 |
| Total rows | 14,500 |
| Total years | 1.598 |
| OOS start | 2025-11-20 |
| OOS end | 2026-05-14 |
| OOS years | 0.479 (175d) |
| FR frequency | 1h (HL), 4h (Bybit), 8h (OKX) |

---

## Statistical Analysis

### ADF Stationarity

| Metric | Value |
|--------|-------|
| ADF statistic | -10.3051 |
| p-value | ~0 |
| Critical 1% | -3.4305 |
| Stationary at 1% | **YES** |

POL-BTC FR differential is strongly stationary. Mean-reversion confirmed — foundational assumption holds.

### Ornstein-Uhlenbeck Half-Life

| Metric | Value |
|--------|-------|
| Half-life | **4.08h (0.17d)** |
| Lambda (θ) | positive |
| Mean-reverting | YES |

Very fast mean-reversion (4h). Consistent with POL's high-vol sidechain nature. The 504h smoothing window extracts persistent regime-level direction from this fast-reverting but persistent bias structure.

### Autocorrelation

| Lag | ACF |
|----|-----|
| 1h | 0.8299 |
| 24h | 0.3276 |
| 168h | 0.1012 |

Strong 1h autocorrelation confirms signal persistence. Rolling mean at 504h exploits this for regime-level direction bias.

### L2 Cluster Cross-Analysis

| Pair | Raw FR Corr | Implication |
|------|------------|-------------|
| POL-ARB | 0.4666 | Elevated — both ETH ecosystem |
| POL-OP | 0.4453 | Elevated — L2 rollup proximity |
| POL-ETH | 0.4288 | ETH checkpoint anchoring |

Note: Raw FR correlation ≠ signal direction correlation (G5 tests smoothed signal alignment, not raw FR levels). G5za ARB signal PASSES (0.301 < 0.40) while G5zb OP signal FAILS (0.518 ≥ 0.40).

---

## Grid Search

| Window | TF | OOS Sharpe | IS Sharpe | OOS ret%/yr | Entries |
|--------|-----|-----------|-----------|------------|---------|
| 504h | 0.0 | **46.52** | 8.86 | 16.28% | 1 |
| 336h | 0.0 | 42.20 | 14.25 | 15.50% | 1 |
| 168h | 0.0 | 33.62 | 15.54 | 14.01% | 1 |
| 72h | 0.0 | 34.99 | 7.41 | 15.25% | 1 |

Best config: W=504h, TF=0.0 (always-on, no threshold).

**Critical caveat**: OOS entries=1 (single trade direction across 175d OOS). The "Sharpe" is dominated by one persistent regime (BTC FR > POL FR throughout OOS). This is structurally distinct from K449/K476 which have 100+ entries/yr. The G6 gate (≥30 trades/yr) is impacted by short data history.

---

## Backtest Results

### Best Config: W=504h, TF=0.0

| Period | Sharpe | Ann Ret% | Max DD% | Entries | Years |
|--------|--------|----------|---------|---------|-------|
| Full | 20.81 | 6.77% | -0.75% | 25 | 1.60 |
| In-Sample | 8.86 | 2.69% | — | 24 | 1.12 |
| **Out-of-Sample** | **46.52** | **16.28%** | -0.24% | 1 | 0.48 |

OOS period: 2025-11-20 to 2026-05-14

**Interpretation**: The OOS Sharpe of 46.52 reflects a single-direction persistent regime where BTC FR > POL FR over ~175 days. This is a regime-level carry trade, not a signal with many independent trade events. The IS Sharpe of 8.86 (with 24 entries) is a more realistic expectation of typical periods.

---

## Statistical Tests

| Test | Result | Pass |
|------|--------|------|
| G1: OOS Sharpe | 46.52 ≥ 1.0 | ✓ |
| G2: Permutation p | 0.000 ≤ 0.05 | ✓ |
| G3: DSR Bonferroni p | 0.000 ≤ 0.00417 | ✓ |
| G4: Walk-forward (12-fold) | min_fold=-17.0 → not all positive | ✗ |

G4 FAILS: Walk-forward 12-fold not all positive. min_fold_sharpe=-17.0. POL's short history (1.6yr) limits WF stability — some folds fall during the MATIC→POL transition regime with adverse FR direction.

---

## §6 Gate Results

| Gate | Value | Threshold | Pass |
|------|-------|-----------|------|
| G1: OOS Sharpe | 46.52 | ≥1.0 | ✓ |
| G2: Perm p-val | 0.000 | ≤0.05 | ✓ |
| G3: DSR Bonf | 0.000 | ≤0.00417 | ✓ |
| G4: Walk-forward | min=-17.0 | all ≥0 | ✗ |
| G5a: ETH | 0.1751 | <0.40 | ✓ |
| G5b: SOL | 0.3529 | <0.40 | ✓ |
| G5c: AVAX | 0.2638 | <0.40 | ✓ |
| G5d: ATOM | 0.1652 | <0.40 | ✓ |
| G5e: INJ | 0.3218 | <0.40 | ✓ |
| G5f: SEI | 0.4935 | <0.40 | **✗** |
| G5g: TIA | 0.4203 | <0.40 | **✗** |
| G5h: APT | 0.5064 | <0.40 | **✗** |
| G5i: FIL | 0.4427 | <0.40 | **✗** |
| G5j: K280 | ~0.05 | <0.40 | ✓ |
| G5k: RNDR | -0.069 | <0.40 | ✓ |
| G5l: TAO | 0.3287 | <0.40 | ✓ |
| G5m: LINK | N/A | <0.40 | ✓ (skip) |
| G5n: TON | N/A | <0.40 | ✓ (skip) |
| G5o: SAND | 0.4274 | <0.40 | **✗** |
| G5q: AXS | NaN | <0.40 | ✓ (skip) |
| G5r: DOGE | 0.3348 | <0.40 | ✓ |
| G5s: UNI | 0.0702 | <0.40 | ✓ |
| G5t: SHIB | 0.3414 | <0.40 | ✓ |
| G5u: AAVE | -0.022 | <0.40 | ✓ |
| G5v: CRV | 0.2385 | <0.40 | ✓ |
| G5w: WIF | 0.1786 | <0.40 | ✓ |
| G5x: LTC | 0.2936 | <0.40 | ✓ |
| G5y: BCH | 0.2963 | <0.40 | ✓ |
| G5z: JUP | 0.2489 | <0.40 | ✓ |
| **G5za: ARB** | **0.3015** | **<0.40** | **✓** |
| **G5zb: OP** | **0.5178** | **<0.40** | **✗ CRITICAL** |
| G5zc: BONK | 0.2619 | <0.40 | ✓ |
| G5zd: PEPE | 0.2310 | <0.40 | ✓ |
| G5ze: COMP | 0.2513 | <0.40 | ✓ |
| G5zf: TRX | -0.001 | <0.40 | ✓ |
| G6: Trades/yr | 2.1/yr | ≥30 | **✗** |
| G7: Return 4x | 65.1% | ≥5% | ✓ |
| G8: Cross-venue | 0.643 | ≥0.55 | ✓ |
| G9: OOS days | 175d | ≥180d | **✗** |

**Gates: 30/39 PASS | G5 FAIL: SEI, TIA, APT, FIL, SAND, OP**

---

## Decision Analysis

### BLOCKED-ROLLUP-SIBLING

**Primary blocker: G5zb OP corr=0.5178 ≥ 0.40**

The POL-BTC signal direction at W=504h aligns with the OP-BTC K609 signal beyond the independence threshold. Despite Polygon's distinct sidechain architecture vs Optimism's OP Stack rollup:

1. **Both are ETH-ecosystem L2/sidechain tokens**: Shared macro alt-coin regime (bull/bear market periods) causes correlated FR direction at 504h smoothing
2. **Post-MATIC→POL migration**: The new POL token established a FR regime that coincides with OP's Superchain expansion period (Sep 2024 onwards)
3. **G5za ARB PASSES (0.301)**: Paradoxically, POL is MORE correlated with OP than ARB despite both being "rollup" tokens. This may reflect the overlapping listing timelines and shared Sep-2024 alt-season dynamics.

**Additional G5 failures at W=504h**:
- G5f SEI: 0.4935 (Cosmos ecosystem — same direction regime at 21d window)
- G5g TIA: 0.4203 (Cosmos DA layer — shared alt direction)
- G5h APT: 0.5064 (Move-VM, top family Sharpe — dominant regime signal bleeds)
- G5i FIL: 0.4427 (Storage sector overlap at 21d window)
- G5o SAND: 0.4274 (Gaming/Metaverse sector)

At shorter windows (72h-336h) G5 results may differ — the 504h window (21d) is the issue. At 168h (7d) OOS Sharpe is still 33.62 with potentially fewer G5 failures.

### Smaller Window Investigation

| Window | OOS Sh | ARB corr | OP corr | SEI corr | APT corr |
|--------|--------|---------|---------|---------|---------|
| W=504h | 46.52 | 0.301 ✓ | 0.518 ✗ | 0.493 ✗ | 0.506 ✗ |

Note: G5 correlations were computed at the best_window (504h). At W=168h or W=336h, signal direction changes more frequently, which may reduce alignment with slower-moving family signals. This represents a potential avenue for a follow-up eval with different window/G5 combo.

---

## Cross-Venue Validation

| Venue | Obs | HL Corr | G8 Pass |
|-------|-----|---------|---------|
| Bybit POLUSDT | 3,265 | **0.6430** | ✓ |
| OKX POL-USDT-SWAP | — | not available | N/A |

G8 PASSES on Bybit. FR signal is real across venues. Note: Bybit has 4h FR intervals vs HL 1h — resampled to 4h for comparison. High correlation (0.643) confirms POL FR dynamics are consistent across venues.

---

## Profit Projection

| AUM | Sleeve | Leverage | Gross/yr | Net/yr (80%) |
|-----|--------|---------|---------|------------|
| $10M | 3.0% | 4x | $195,376 | **$156,301** |
| $100M | 3.0% | 4x | $1,953,758 | **$1,563,006** |

Based on OOS ann ret = 16.28% × 4x leverage = 65.1%/yr (1x basis = 16.28%).

**Caveat**: OOS is 175d with only 1 entry/direction. The actual realized profit depends on regime persistence. The 3.0% sleeve assumes BLOCKED status — not allocated.

---

## HL Concentration

| Metric | Value |
|--------|-------|
| Current HL weight | 64.5% |
| K611 sleeve | 3.0% |
| New HL weight | **67.5%** |
| HL cap | 65.0% |
| **Status** | **BREACH** |

HL POL-PERP maxLev=5 (high-risk alt tier). Even if POL were ACCEPTED, Bybit-primary would be required due to (1) HL breach at 65% cap and (2) HL's low maxLev=5 limiting leverage.

---

## Family Rank

POL-BTC OOS Sharpe 46.52 = family rank **#4** (hypothetical, BLOCKED status).

| Rank | Pair | Sharpe | Status |
|------|------|--------|--------|
| 1 | APT-BTC | 51.10 | ACCEPT |
| 2 | ATOM-BTC | 50.79 | ACCEPT |
| 3 | SEI-BTC | 48.10 | ACCEPT |
| **4** | **POL-BTC** | **46.52** | **BLOCKED** |
| 5 | AVAX-BTC | 43.89 | ACCEPT |
| 6 | SHIB-BTC | 38.48 | ACCEPT COND |
| 7 | SAND-BTC | 33.63 | ACCEPT COND |
| 8 | JUP-BTC | 29.90 | ACCEPT COND |
| 19 | AAVE-BTC | 11.35 | ACCEPT COND |
| 22 | ETH-BTC | 5.66 | ACCEPT |
| — | ARB-BTC | 0.509 | CONDITIONAL |

POL would rank #4 if G5 gates passed — highest-Sharpe BLOCKED token in family history.

---

## Polygon Sidechain Cluster Status

| Pair | Decision | OOS Sh | Vol ratio | Notes |
|------|---------|--------|----------|-------|
| ARB-BTC K491 | CONDITIONAL | 0.509 | 1.27x | Vol too low |
| OP-BTC K609 | PENDING | TBD | ~1.5x | Rollup cluster eval |
| **POL-BTC K611** | **BLOCKED-ROLLUP-SIBLING** | **46.52** | **3.73x** | G5zb OP fail |

**Polygon sidechain cluster: BLOCKED** — POL signal correlated with OP rollup signal beyond independence threshold. The L2/sidechain FR differential family is increasingly constrained by intra-cluster signal overlap.

### L2/Sidechain Family Summary

- ARB K491: Vol too low (1.27x) → CONDITIONAL (weak signal)
- OP K609: Eval in progress
- POL K611: Vol very high (3.73x) but correlated with OP signal → BLOCKED

The L2/sidechain cluster appears to share a dominant macro alt-season regime direction that overrides architectural differences in FR signal direction at 21d smoothing windows.

---

## POL Characteristics

| Feature | Value |
|---------|-------|
| Architecture | PoS Sidechain + zkEVM (not optimistic rollup) |
| Token migration | MATIC→POL, Sep 2024 |
| HL maxLev | 5x (low, high-risk alt tier) |
| Bybit maxLev | 75x |
| OKX maxLev | 50x |
| FR vol vs BTC (6M) | 3.73x |
| FR mean ann | 4.58%/yr (POL) vs 11.08%/yr (BTC) |
| OU half-life | 4.08h |
| ADF stationary | YES (p≈0) |
| POL-ARB raw FR corr | 0.4666 |
| POL-OP raw FR corr | 0.4453 |
| POL-ETH raw FR corr | 0.4288 |

---

## Key Insights & Lessons

1. **Architecture ≠ Signal independence**: Polygon's sidechain PoS architecture (vs OP/ARB rollups) does not produce independent FR signal direction at 21d window. Macro alt-season regimes dominate.

2. **MATIC→POL migration effect**: The token migration created elevated FR vol (3.73x) but the resulting signal overlaps with OP's Superchain expansion period — both post-Sep 2024 narratives.

3. **G5za ARB PASSES (0.301)**: Interestingly, POL is more independent from ARB than from OP. This may be because ARB's FR dynamics are more ETH-rollup specific (Ethereum user fee model), while OP's Superchain narrative created broader alt-token correlation with POL.

4. **The vol paradox**: High vol ratio (3.73x) generates high OOS Sharpe (46.52) but also correlates with more family signals (APT, SEI, TIA, FIL, SAND, OP all breach 0.40). High-vol alt-coins tend to share macro regime direction more strongly.

5. **Short history caveat**: Only 1.65yr of POL data. G9 OOS days=175d just below 180d threshold. WF has limited folds. Future evaluation with 2yr+ of data may change G5 results.

6. **Next steps**: If OP K609 is also BLOCKED, the entire L2/sidechain ETH-derived cluster may be structurally correlated at 21d+ windows. Consider shorter smoothing windows or regime-conditional gating.

---

## Commit Reference

```
git commit -m "K611 POL-BTC FR differential paired-trade eval (Sh 46.52, $156K/yr @$10M, family rank #4, Polygon sidechain BLOCKED-ROLLUP-SIBLING)"
```

**Decision: BLOCKED-ROLLUP-SIBLING**  
**Polygon sidechain cluster: BLOCKED (G5zb OP corr=0.518)**  
**Next pivot: K612 — next family member evaluation or OP K609 completion**

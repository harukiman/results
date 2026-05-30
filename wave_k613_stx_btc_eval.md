# K613 STX-BTC FR Differential Paired-Trade Evaluation

**K339 REPO_ROOT pattern** | Run: 2026-05-30T09:25 JST  
**Decision: BLOCKED-G5 (APT)** | OOS Sharpe: 26.86 | $41K/yr @$10M (overridden)

---

## Executive Summary

K613 evaluates STX-BTC (Stacks — BTC-secured L2 via PoX consensus) as a potential new **BTC-L2 cluster** within the FR-differential paired-trade family. STX is architecturally unique: the only major smart contract platform anchored to Bitcoin via Proof-of-Transfer (PoX), with ZERO ETH exposure.

**Phase 0 PASS**: STX vol ratio = 5.81x BTC (6M), 3.69x (1Y), 2.28x (full) — highest in the BTC ecosystem eval set. All 3 venues confirmed (HL maxLev=5, Bybit maxLev=50, OKX maxLev=20).

**BTC cluster tests PASS**: Critical independence from BTC forks confirmed — G5w LTC corr=0.225 (PASS), G5x BCH corr=0.145 (PASS). ETH L2 independence confirmed — G5z ARB corr=0.226 (PASS), G5za OP corr=0.333 (PASS).

**Fatal G5 failure**: G5h APT corr=0.533 ≥ 0.40 threshold. STX-BTC signal direction aligns with APT-BTC at W=504h. Additional failures: SEI (0.481), SAND (0.423), DOGE (0.439). Per strict §6 rules: **BLOCKED-G5 (APT)**.

**Key paradox**: OOS Sharpe 26.86 would rank #8 in the family (between PEPE-BTC and BCH-BTC), but G5 gate failure blocks deployment. Trade count critically low at best config (1 OOS trade, 1.7/yr at W=504h TF=1.0) — structural G6 failure even without G5 issue.

---

## Phase 0: Pre-Screen

### Venue Check

| Venue | Ticker | Status | Max Leverage | FR Interval |
|-------|--------|--------|-------------|-------------|
| HL | STX-PERP | LISTED (isDelisted=False) | 5x | 1h |
| Bybit | STXUSDT | Trading | 50x | 8h (480 min) |
| OKX | STX-USDT-SWAP | live | 20x | — |

**All 3 venues listed: HL + Bybit + OKX PASS**

Note: HL maxLev=5 for STX (high-risk alt tier). Bybit maxLev=50 preferred for position sizing.

### Vol Ratio Screen

| Window | STX/BTC Vol Ratio | Pass (≥1.5x) |
|--------|------------------|-------------|
| 6M | **5.8147x** | PASS |
| 1Y | **3.6854x** | PASS |
| Full (1.98yr) | **2.2781x** | PASS |

**Phase 0: PASS (all windows strongly above 1.5x threshold)**

Context — BTC/ETH ecosystem vol ratios:
- ARB K491: 1.27x (CONDITIONAL) — ETH rollup, insufficient vol
- OP K609: ~1.48x (BLOCKED-G5 FIL) — ETH rollup
- BCH K605: 1.72x (ACCEPT CONDITIONAL) — BTC fork
- AVAX K484: 1.50x (ACCEPT) — Layer 1
- STX K613: **5.81x (6M)** — highest in BTC/ETH ecosystem eval set

### FR Characteristics

| Metric | STX | BTC |
|--------|-----|-----|
| Mean FR (annualized) | 7.93% | 11.40% |
| FR std (1h intervals) | 0.000040 | 0.000017 |
| FR data rows (HL) | 17,359 | 17,512 |
| Date range | 2024-05-30 to 2026-05-23 | — |

BTC carries more FR than STX on average (11.40% vs 7.93% annualized). FR diff mean = 3.96e-6 (slightly positive → BTC FR > STX FR tendency). FR diff std = 3.80e-5 — substantial variation for carry exploitation.

### BTC Cluster Raw FR Correlations (Phase 0 exploratory)

| Pair | Raw FR Corr | Interpretation |
|------|-------------|----------------|
| STX-BCH | 0.298 | BTC L2 vs BTC fork — moderate, below signal threshold |
| STX-LTC | 0.385 | BTC family — higher raw corr but below signal corr threshold |
| STX-ARB | 0.384 | BTC L2 vs ETH rollup — similar to LTC (alt-coin macro corr) |
| STX-OP | 0.381 | BTC L2 vs ETH rollup cluster |

Raw FR correlations are all below 0.40 at the FR level, suggesting good decorrelation in the underlying rate. However, signal-level correlations (after smoothing) can differ significantly — G5 tests the smoothed signal, not raw FR.

---

## Phase 1: Data Acquisition

### HL STX FR Cache
- **Source**: Hyperliquid `/info` fundingHistory API — full history fetched and cached
- **File**: `cache/k163_hl/hl_fr_STX.parquet` (17,519 rows, 2024-05-30 to 2026-05-30)
- **Merged with BTC**: 17,359 rows (inner join on hourly timestamp)

### Bybit STX FR Cache
- **Source**: Bybit `v5/market/funding/history` API — 730d history fetched
- **File**: `cache/bybit_fr_STXUSDT_730d.parquet` (13,191 rows — includes pre-HL listing)
- **Interval**: 8h (480 min) settlement cycles

---

## Phase 2: Statistical Analysis

### Stationarity (ADF Test)

| Metric | Value |
|--------|-------|
| ADF statistic | -13.4685 |
| p-value | ~0.0 (< 1e-6) |
| 1% critical | -3.4307 |
| Stationary at 1% | **YES** |

STX-BTC FR differential is strongly stationary. Mean-reversion confirmed with high confidence — ADF well below 1% critical value.

### Ornstein-Uhlenbeck Mean-Reversion

| Metric | Value |
|--------|-------|
| Lambda (decay rate) | 0.4747 |
| Half-life | **1.46 hours (0.06 days)** |
| Long-run mean | 3.96e-6 |
| R-squared | 0.2373 |

**Very fast mean-reversion** — half-life of only 1.46 hours. This explains why the 504h smoothing window (21 days) is critical: the FR differential noise reverts in ~1.5h, but structural regime shifts (PoX stacking cycles, Bitcoin narrative events) persist for weeks. The 504h window filters noise and captures only durable FR regime changes.

### Autocorrelation

| Lag | ACF |
|-----|-----|
| 1h | 0.5253 |
| 24h | 0.1824 |
| 168h (1wk) | 0.1075 |

Strong 1h autocorrelation (0.525) confirms short-term FR persistence, consistent with PoX stacking cycle mechanics. ACF decays by 24h (0.182) and further by 1 week (0.108), suggesting both fast-reverting noise and slower structural signals.

### Comparison: BTC vs ETH Ecosystem Pairs

| Pair | FR Corr | Signal (W=504h) | Architecture |
|------|---------|----------------|-------------|
| STX-BCH (raw) | 0.298 | 0.145 | BTC L2 vs BTC PoW fork |
| STX-LTC (raw) | 0.385 | 0.225 | BTC L2 vs BTC PoW alt |
| STX-ARB (raw) | 0.384 | 0.226 | BTC L2 vs ETH rollup |
| STX-OP (raw) | 0.381 | 0.333 | BTC L2 vs ETH rollup cluster |
| STX-APT (signal) | — | **0.533** | BTC L2 vs Cosmos-adjacent L1 |
| STX-SEI (signal) | — | **0.481** | BTC L2 vs Cosmos-adjacent L1 |

**Key finding**: STX-BCH/LTC/ARB/OP all PASS at signal level (<0.40). The G5 failures are not from BTC-family or ETH-L2 clusters, but from high-vol L1s (APT, SEI) that dominate the 504h-smoothed signal space.

---

## Phase 3: Backtest

### Grid Search Results (12 configs: 4 windows × 3 thresholds)

| Window (h) | TF | IS Sharpe | OOS Sharpe | OOS Ret/yr | Entries/yr |
|-----------|-----|----------|-----------|------------|------------|
| 504 | 1.0 | 10.41 | **26.86** | 4.27% | 1.7 |
| 336 | 1.0 | 12.99 | 24.33 | 4.39% | 5.1 |
| 504 | 0.5 | 11.79 | 19.71 | 5.03% | 19.1 |
| 336 | 0.5 | 12.11 | 17.85 | 5.31% | 29.2 |
| 168 | 0.0 | 11.02 | 17.85 | 10.06% | 27.2 |

**Selected: W=504h, TF=1.0** (highest OOS Sharpe = 26.858)

**Critical note**: The best OOS Sharpe config has only 1 OOS trade (1.7/yr) — catastrophically below the G6 threshold of 30/yr. The W=168h, TF=0.0 config (17.85 Sharpe, 27.2 entries/yr) approaches G6 compliance but still fails. No config achieves both high Sharpe AND adequate trade count.

### Main Backtest (W=504h, TF=1.0)

| Period | Sharpe | Ann Return | Max DD | Entries |
|--------|--------|-----------|--------|---------|
| IS (1.35yr) | 10.413 | 1.476%/yr | — | 3 |
| OOS (0.58yr) | **26.858** | 4.275%/yr | -0.04% | 1 |
| Full (1.92yr) | 15.666 | 2.316%/yr | -0.19% | 4 |

OOS max DD = -0.04% — essentially zero drawdown because there is only 1 trade. The elevated Sharpe is a consequence of very few trades at the W=504h config.

### Walk-Forward Stability (12-fold, IS 90d / OOS 30d)

| Fold | OOS Period | Sharpe | Entries |
|------|-----------|--------|---------|
| 1 | 2024-08-28 to 2024-09-27 | 0.0 | 0 |
| 2 | 2024-09-27 to 2024-10-27 | 0.0 | 0 |
| 3 | 2024-10-27 to 2024-11-26 | 0.0 | 0 |
| 4 | 2024-11-26 to 2024-12-26 | **46.69** | 2 |
| 5-11 | 2024-12 to 2025-07 | 0.0 | 0 |
| 12 | 2025-07-24 to 2025-08-23 | 0.0 | 0 |

WF "all_positive = True" because Sharpe=0.0 (zero trades) is counted as non-negative. This is structurally a degenerate result — the strategy has almost no trades in most WF windows. The signal is so slow (504h smoothing) that 30d OOS windows often have 0 entries. G4 pass is nominal.

---

## Phase 4: §6 Gate Evaluation

### Gate Summary: 32/38 PASS

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 26.858 | ≥ 1.0 | **PASS** |
| G2 Perm p-value | 0.0 | ≤ 0.05 | **PASS** |
| G3 DSR Bonferroni | 0.0 | < 0.004167 | **PASS** |
| G4 Walk-forward 12-fold | all_pos=True | all positive | PASS (nominal) |
| G5h APT-BTC | 0.5334 | < 0.40 | **FAIL** |
| G5f SEI-BTC | 0.4805 | < 0.40 | **FAIL** |
| G5r DOGE-BTC | 0.4392 | < 0.40 | **FAIL** |
| G5o SAND-BTC | 0.4228 | < 0.40 | **FAIL** |
| G5w LTC-BTC | 0.2248 | < 0.40 | **PASS** |
| G5x BCH-BTC | 0.1446 | < 0.40 | **PASS** |
| G5z ARB-BTC | 0.2261 | < 0.40 | **PASS** |
| G5za OP-BTC | 0.3325 | < 0.40 | **PASS** |
| G5b SOL-BTC | 0.3824 | < 0.40 | PASS |
| G6 Trade count | 1.7/yr | ≥ 30/yr | **FAIL** |
| G7 Ann return @4x | 17.10% | ≥ 5% | **PASS** |
| G8 Cross-venue corr | 0.4888 | ≥ 0.55 | **FAIL** |
| G9 Data sufficiency | 210d | ≥ 180d | **PASS** |

### Critical G5 Analysis

**STX-BTC signal PASSES all BTC and ETH L2 critical tests:**
- G5w LTC (BTC family): 0.225 PASS — BTC-L2 cluster distinct from BTC family
- G5x BCH (BTC fork): 0.145 PASS — BTC-L2 cluster distinct from BTC fork
- G5z ARB (ETH L2): 0.226 PASS — BTC-L2 cluster distinct from ETH L2
- G5za OP (ETH rollup): 0.333 PASS — BTC-L2 cluster distinct from ETH rollup cluster

**STX-BTC signal FAILS against high-vol L1/L2 family members:**
- G5h APT-BTC: **0.533 FAIL** (fatal — max corr pair)
- G5f SEI-BTC: 0.481 FAIL
- G5r DOGE-BTC: 0.439 FAIL
- G5o SAND-BTC: 0.423 FAIL

**Interpretation**: At W=504h (21-day smoothing), STX-BTC signal direction aligns with APT-BTC, SEI-BTC, DOGE-BTC, and SAND-BTC. These are all high-vol assets that tend to be jointly long or short relative to BTC in extended (weeks-long) FR regimes. The W=504h threshold filter creates so few trades that the single OOS trade direction happens to match these other family members. This is a window-selection artifact combined with genuine market correlation in broad crypto risk regimes.

---

## Phase 5: HL Concentration

| Metric | Value |
|--------|-------|
| Current HL weight (v6.40+) | 64.5% |
| K613 sleeve (BLOCKED) | N/A |
| New HL weight | 64.5% (unchanged) |
| HL cap | 65.0% |
| Headroom | 0.5pp |
| Status | BLOCKED — no allocation change |

HL STX-PERP maxLev=5 would limit position sizing anyway. Decision is BLOCKED-G5, so no HL concentration impact.

---

## Phase 6: Decision

**BLOCKED-G5 (APT)**

### Decision Rationale

G5 family correlation check failed: APT corr=0.5334 ≥ 0.40 threshold. STX-BTC signal (W=504h, TF=1.0) is correlated with APT-BTC signal. Per strict §6 rules: BLOCKED.

Additional structural failures:
- **G6 FAIL**: Only 1 OOS trade (1.7/yr vs 30/yr threshold) — strategy has insufficient activity at best config
- **G8 FAIL**: Bybit-HL cross-venue correlation = 0.4888 < 0.55 threshold
- G4 NOMINAL: WF folds mostly 0-trade — not meaningful stability evidence

Gates: 32/38 PASS. OOS Sh=26.858 (would rank #8 in family).

### Why BLOCKED Despite Strong Sharpe

The high OOS Sharpe (26.86) is an artifact of the W=504h high-threshold configuration:
1. Only 1 OOS trade — any single profitable trade yields astronomical Sharpe
2. The strategy essentially switches position once per year at this config
3. The 504h (21-day) smoothing window creates a near-static signal
4. G6 (30 trades/yr) failure is structural — not a borderline case

At more practical configs (W=168h, TF=0.0, 27 entries/yr, Sh=17.84), G5 failures remain:
- SEI, DOGE, SAND still fail at W=168h (broader alt-coin regime correlation persists)
- Trade count still marginal (27.2/yr vs 30/yr)

### BTC L2 Cluster Verdict

**PARTIAL POSITIVE**: STX does achieve architectural independence from BTC forks and ETH L2s at the signal level. The PoX mechanism creates genuinely distinct FR dynamics vs BCH/LTC (fork mechanics) and ARB/OP (ETH infrastructure). However, at long smoothing windows, STX-BTC correlates with the broad crypto alt-season signal (APT/SEI/DOGE), which is not ecosystem-specific.

**BTC L2 cluster hypothesis**: NOT CONFIRMED as independent cluster under current §6 rules. STX is not a BTC-fork cluster duplicate, but it is an alt-coin signal duplicate at the relevant smoothing scale.

---

## Profit Projection (@$10M — overridden by BLOCKED)

| Metric | Value |
|--------|-------|
| OOS Ann Return (1x) | 4.275%/yr |
| OOS Ann Return (4x) | 17.10%/yr |
| Sleeve (BLOCKED) | 2% conditional |
| Gross/yr @$10M (2%, 4x) | ~$51K |
| Net/yr @$10M (80%) | **$41K** |
| Net/yr @$100M (80%) | **$410K** |

**BLOCKED — no deployment. Profit projection hypothetical only.**

---

## Family Rank (Hypothetical — BLOCKED)

If STX were accepted (OOS Sh=26.858), it would rank:

| Rank | Pair | Sharpe | Status |
|------|------|--------|--------|
| 7 | JUP-BTC | 29.895 | ACCEPT CONDITIONAL |
| **8** | **STX-BTC** | **26.858** | **BLOCKED-G5 (APT)** |
| 9 | BCH-BTC | 26.002 | ACCEPT CONDITIONAL |

STX would slot between JUP-BTC (K606) and BCH-BTC (K605) — competitive Sharpe in the upper-middle of the family.

---

## Conclusions & Next Steps

### What This Wave Confirms

1. **BTC-L2 cluster architecture is distinct**: STX signal passes all BTC fork (BCH/LTC) and ETH L2 (ARB/OP) critical tests. PoX mechanics do create different FR dynamics at the raw FR level.

2. **G5 failures are window-dependent**: At W=504h, the STX signal becomes so infrequent (1-4 trades/full period) that its direction aligns with the broad "alt-coin vs BTC" regime signal (APT/SEI/DOGE all short together in crypto bear phases). This is not a fundamental correlation — it is an artifact of the extreme threshold filter.

3. **Trade count is the structural bottleneck**: No config simultaneously achieves Sh≥5, entries≥30/yr, and G5 all-PASS. The STX FR differential has very long regime persistence (PoX cycles), which conflicts with the G6 trade frequency requirement.

4. **Raw FR decorrelation is strong**: STX-BCH=0.298, STX-ARB=0.384 at the FR level — suggesting genuine ecosystem independence. If a lower-smoothing approach (W=48-72h) were tested with regime detection, G5 correlation might improve.

### Potential Paths to Unlock

- **Window shortening**: Test W=48-72h (2-3 day smoothing) — faster signal cycling may reduce G5 correlation with APT/SEI while maintaining Sharpe above 1.0
- **Regime-filtered version**: If BTC/STX regime aligns with PoX 2-week cycle, a calendar-aware signal might decorrelate from APT/SEI
- **Data accumulation**: sBTC launch, Nakamoto upgrade, 2025+ data may create new STX-specific FR patterns — re-evaluate in 6 months

### BTC L2 Cluster Status

| Candidate | Status | Notes |
|-----------|--------|-------|
| BCH K605 | ACCEPT CONDITIONAL | BTC fork cluster (payment utility) |
| LTC K600 | ACCEPT CONDITIONAL | BTC family (SHA-256 PoW) |
| **STX K613** | **BLOCKED-G5 (APT)** | BTC-L2 (PoX) — cluster exists but G5 fails |

BTC-L2 cluster remains **open** — STX shows promise but cannot be confirmed under current §6 gates due to G5 APT correlation and G6 trade count failure.

---

*K339 REPO_ROOT pattern | Generated 2026-05-30T09:25 JST | Runtime 5.0s*

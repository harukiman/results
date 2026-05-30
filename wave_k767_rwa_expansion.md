# K767 K297' RWA Expansion Analysis — 4-Provider Diversification

Generated: 2026-05-30 22:00 JST

## Executive Summary

K297' RWA yield sleeve currently concentrated in single provider (sUSDe, K344).
K767 proposes 4-provider diversification across sUSDe/Spark sUSDS/USDY/Mountain USDM,
expanding sleeve from 5% to 20% of AUM ($500K → $2M), with K523 3-point uplift:
- Conservative: $56,270.0/yr ($21,383.0 realized @38%)
- Central: $78,660.0/yr ($29,891.0 realized @38%)
- Optimistic: $103,400.0/yr ($39,292.0 realized @38%)
- Central uplift vs baseline: +$69,360.0/yr

## Phase 1: Current RWA State

| Provider | Status | AUM % | APY | Deployed |
|----------|--------|-------|-----|---------|
| sUSDe (Ethena, K344) | ACTIVE_PAPER | 5% | 3.72% | 50% (OC HALF) |
| Spark sUSDS (K473) | PROPOSED | 0% | 3.34% | — |
| USDY (Ondo, K415) | CONDITIONAL | 0% | 4.5% | — |
| Total RWA yield | — | 5% | 3.72% eff. | — |

Single-provider HHI = 1.0 (maximum concentration).

## Phase 2: Provider Universe

### Selected (4 providers)

| Provider | Weight | APY | Restriction | Mechanism |
|----------|--------|-----|-------------|-----------|
| sUSDe (Ethena) | 35% | 4.02% (30d EMA) | None | Synthetic ETH staked |
| Spark sUSDS | 25% | 3.67% (30d mean) | None | DSR / Sky governance |
| USDY (Ondo) | 25% | 4.5% | Non-US only | Tokenized T-bills |
| Mountain USDM | 15% | 4.6% | KYC-light | Tokenized T-bills |

### Excluded

| Provider | Reason |
|----------|--------|
| BUIDL (BlackRock) | $100K minimum + accredited investor only |
| OUSG (Ondo) | Overlaps with USDY; accredited investor + non-US |
| Maple Finance MPL | Undercollateralized + 30d lock; credit risk too high |
| HypurrFi | K337/K345 DROP_LINE — memory: TVL -49% structural failure |

## Phase 3: Diversification Analysis

**HHI**: 1.0 → 0.26 (significant reduction, theoretical minimum ~0.25 for 4 equal-weight)

**Mechanism diversity**: 4 distinct yield drivers:
1. ETH funding rate / synthetic carry (sUSDe)
2. DSR governance rate / MakerDAO (Spark sUSDS)
3. US T-bill direct (USDY)
4. US T-bill KYC-light (USDM)

**Geo-strategy**:
- US residents: sUSDe + Spark + USDM (3 providers, ~3.85% blended)
- Non-US residents: all 4 providers (~4.20% blended)

## Phase 4: K523 3-Point Uplift (@$10M, 20% sleeve = $2M)

| Scenario | Blended APY | Deployed | Annual Yield | Realized (38%) |
|----------|-------------|----------|-------------|----------------|
| Conservative | 3.31% | 85% | $56,270.0 | $21,383.0 |
| Central (Mid) | 4.14% | 95% | $78,660.0 | $29,891.0 |
| Optimistic | 5.17% | 100% | $103,400.0 | $39,292.0 |

**Baseline** (sUSDe only, K344 OC HALF, 5% AUM): $9,300/yr

**K523 WARNING**: Central is NOT upper bound. K518 38% haircut applied.
sUSDe optimistic (+25%) contingent on ETH staking + funding environment surge.
USDM/USDY rates track Fed funds rate (currently ~4.3%).

## Implementation

- Daemon: `scripts/k767_rwa_diversified.py` (74th daemon)
- Plist: `scripts/com.cryptolab.k767-rwa-diversified.plist`
- Allocation: `data/rwa_allocation.json`
- Schedule: Weekly Sunday 03:00 JST rebalance
- Mode: PAPER_TRADE=True default

## References

| Wave | Description |
|------|-------------|
| K344 | sUSDe OC sleeve (K344_susde_oc_daily_run.py) |
| K415 | USDY sleeve scaffold (K415_usdy_sleeve_run.py) |
| K473 | Spark sUSDS APY monitor (spark_usds_monitor.py) |
| K523 | 3-point projection mandate |
| K518 | 38% realized-to-stated ratio floor |
| K297 | K297' satellite sleeve (PAXG/SPX) |

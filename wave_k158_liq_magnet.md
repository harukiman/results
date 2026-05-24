# Wave K158 — Liquidation Cluster Magnet (R6-14)

**PROXY DISCLAIMER:** This is a parametric proxy of CoinGlass-style
liquidation clusters built from volume-spike + directional candle bars at
assumed 10x leverage. CoinGlass's actual heat-map is not
publicly scrapable historically. Results below test whether the proxy
signal carries economic information; this is NOT a verbatim replication of
CoinGlass's reported >70% hit rate.

**As-of:** 2026-05-24T16:47:16.281286+00:00Z
**Wall time:** 332.3s
**Universe:** 56 symbols, 4381 4H bars over 730d

## Cluster Detection Frequency (primary, vol_z >= 2.0)

- bull-spawn bars: **4,381** (1.786% of panel cells)
- bear-spawn bars: **3,589** (1.463% of panel cells)
- assumed leverage: **10x**, long-liq at -10.0% from entry

## Variant Performance

| variant | netSR | OOS SR | MaxDD | p_perm | null_mean | DSR_oos | n_trades | sweep% | gates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V_long_sweep | -0.45 | +0.63 | -20.60% | 0.610 | -0.28 | 0.00 | 816 | 36.2% | 3/6 |
| V_short_fade | -0.41 | -1.65 | -21.35% | 0.320 | -0.66 | 0.00 | 836 | 36.2% | 2/6 |
| V_zone_2pct | +0.43 | +0.71 | -13.49% | 0.125 | +0.10 | 0.00 | 1363 | 28.5% | 4/6 |
| V_zone_5pct | +3.07 | +3.90 | -14.63% | 0.000 | +1.93 | 1.00 | 3903 | 36.2% | 6/6 |

## Naive Baseline Comparison (long after vol-spike, no cluster)

This is a **critical sanity check**. If the variant Sharpe is not
materially above this baseline Sharpe, the cluster-magnet rule is
not adding incremental edge over the 'just be long after vol spike'
directional factor.

| baseline | SR | MaxDD | n_trades |
|---|---:|---:|---:|
| baseline_long_volspike_vz2.0_hold12 | -1.45 | -37.47% | 2673 |
| baseline_long_volspike_vz1.5_hold12 | -3.23 | -56.57% | 4924 |

## § Mini Gates (per variant)

### V_long_sweep
- `oos_sr_ge_0_5`: **True**
- `p_perm_lt_0_05`: **False**
- `max_dd_gt_neg40`: **True**
- `cost_stress_robust`: **False**
- `dsr_oos_pos`: **False**
- `n_trades_ge_30`: **True**
- **pass 3/6 - all_pass: False**

### V_short_fade
- `oos_sr_ge_0_5`: **False**
- `p_perm_lt_0_05`: **False**
- `max_dd_gt_neg40`: **True**
- `cost_stress_robust`: **False**
- `dsr_oos_pos`: **False**
- `n_trades_ge_30`: **True**
- **pass 2/6 - all_pass: False**

### V_zone_2pct
- `oos_sr_ge_0_5`: **True**
- `p_perm_lt_0_05`: **False**
- `max_dd_gt_neg40`: **True**
- `cost_stress_robust`: **True**
- `dsr_oos_pos`: **False**
- `n_trades_ge_30`: **True**
- **pass 4/6 - all_pass: False**

### V_zone_5pct
- `oos_sr_ge_0_5`: **True**
- `p_perm_lt_0_05`: **True**
- `max_dd_gt_neg40`: **True**
- `cost_stress_robust`: **True**
- `dsr_oos_pos`: **True**
- `n_trades_ge_30`: **True**
- **pass 6/6 - all_pass: True**

## Verdict

**REJECT**

Primary V_long_sweep fails gates (3/6); OOS SR +0.63, p_perm 0.610, DSR_oos 0.00, MaxDD -20.60%, n_trades 816. The proxy cluster signal does not carry a reliable economic edge in this 730d sample. The CoinGlass >70% hit rate is likely an artifact of selective in-sample presentation, or it relies on heat-map data dimensions not available in OHLCV alone (per-exchange OI, leverage tiering, taker direction). Recommend NOT deploying without paid CoinGlass historical access; re-test if/when those data become available.

SANITY CHECK on best variant V_zone_5pct: full SR +3.07 vs naive 'long-after-volspike, no cluster' baseline (baseline_long_volspike_vz2.0_hold12) SR -1.45. Cluster-magnet incremental edge over baseline = +4.53 SR, which is a genuine improvement — the cluster geometry filter DOES help. However, the cross-sectional permutation null mean = +1.93: even when we shuffle WHICH symbol each cluster spawns in (preserving the overall timing pattern of cluster availability across the market), the strategy still produces substantial Sharpe. This means most of the edge is in TIMING (be long when many clusters exist across the universe), NOT in per-symbol identity. A 2024-2026 bull market means market-wide long bias during high-vol periods is largely a directional bet. Recommend cautious paper-trade with explicit comparison vs equal-vol long-only crypto basket; if V_zone_5pct OOS SR materially exceeds basket OOS SR over 90+ days forward, upgrade to live. Otherwise treat as a closet-beta exposure.

### Note on proxy nature

- The bull/bear cluster spawn rule (vol_z>=2 + |body|>=0.5%) is a
  proxy for 'high-leverage entry'. It can match clusters at very
  different leverage tiers; we collapse to 10x as a single point estimate.
- The sweep% column shows what fraction of spawned long-liq clusters
  were actually touched by price within their 90-bar (15d) lifetime.
  If sweep% is high, the magnet hypothesis directionally holds (price
  often reaches the proxy liq level). If approach%/sweep% is low, the
  hypothesis is decoupled at this scale.
- Implementation uses single-cluster-per-symbol tracking (the most-
  recently-spawned active cluster). This understates trade frequency vs
  the full multi-cluster list but is robust to cluster-list explosion.
- A real CoinGlass-grade test would require per-exchange OI history,
  leverage-tier OI breakdowns, and taker-direction trade tape - none
  of which are publicly retrievable in 730d historical form within
  the wall-time budget for this wave.

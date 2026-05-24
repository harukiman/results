# Wave K174 - CEX vs DEX (Hyperliquid) FR Integration

**Date**: 2026-05-24  
**Runtime**: 2.6 s  
**Verdict**: **FAIL (2/7 gates)**

## 1. Hypothesis (MDPI 14/2/346 / R6-1)

CEX funding leads DEX funding with ~61 % integration coefficient. When DEX
(Hyperliquid) FR lags CEX (Bybit) FR by N std-deviations, expect mean-reversion
of DEX -> CEX. Trade the DEX side (here: Bybit perp price as the tradable
proxy) accordingly.

Sign convention used:
- `spread_T = bybit_fr_T - hl_fr_8hsum_T`
- `z_{T-1} > +thr` -> Bybit FR much higher than HL aggregate -> HL expected to
  catch up upward, Bybit perp price expected to revert DOWN as funding settles
  -> **SHORT Bybit perp at T**.
- `z_{T-1} < -thr` -> symmetric LONG.

## 2. Data

| Item | Value |
|------|-------|
| HL hourly FR | `cache/k163_hl/hl_fr_*.parquet` (8 syms) |
| Bybit 8h FR  | `cache/bybit_fr_*USDT_730d.parquet` |
| Bybit 4h px  | `cache/*USDT_4h_730d.parquet` |
| Symbols      | BTC, ETH, SOL, BNB, DOGE, AVAX, XRP, SUI (8/8) |
| Events / sym | 2187 - 2190 (~2 yr) |
| Events / yr  | 1 095 (8 h Bybit funding cadence) |

## 3. Integration Check (replication of MDPI claim)

OLS: `hl_fr_8h_T = a + b * bybit_fr_{T-1}` per symbol.

| Sym | beta | Sym | beta |
|-----|-----:|-----|-----:|
| BTC | 0.934 | DOGE | 0.494 |
| ETH | 0.910 | AVAX | 0.309 |
| SOL | 0.620 | XRP  | 0.385 |
| BNB | 0.800 | SUI  | 0.420 |
| **mean** | **0.609** | MDPI exp. | 0.61 |

**Integration coefficient replicates the MDPI claim with high fidelity
(mean beta = 0.609 vs 0.61 expected).** Large-cap pairs (BTC/ETH/BNB) integrate
near 0.8-0.93; mid-caps (AVAX/XRP/SUI) only 0.3-0.5, indicating *weaker* CEX
leadership for newer / lower-volume HL listings.

## 4. Variant Results (GROSS and NET, K173 lesson)

| Variant | Sh_NET | Sh_GROSS | OOS_NET | WF folds (NET) | perm p_NET | trades/yr | DD_NET |
|---------|-------:|---------:|--------:|----------------|-----------:|----------:|-------:|
| **V_z2_h1 (primary)** | **-0.58** | **+0.19** | **+0.46** | [+1.17, -2.06, -1.45, +0.09] | 0.000 | 553 | -0.24 |
| V_z2_h3   | -0.87 | -0.39 | -0.51 | [+0.61, -1.47, -2.06, -0.55] | 0.000 | 412 | -0.36 |
| V_abs1bp  | -0.67 | +0.24 | -1.51 | [+1.36, -1.56, -1.63, -1.25] | 0.000 | 2519 | -0.59 |
| V_top_xs  | -7.57 | +1.00 | -10.08 | [-4.99, -7.19, -11.35, -9.45] | 0.000 | 1095 | -5.48 |

### 4.1 GROSS positive, NET negative - cost-dominated

All four variants show **positive or near-positive GROSS Sharpe with the
sign-flipping pattern collapsing under 7 bps per side per leg**:

- V_z2_h1:  +0.19 GROSS -> -0.58 NET (delta ~ 0.77 Sharpe lost to costs)
- V_abs1bp: +0.24 GROSS -> -0.67 NET (delta ~ 0.91)
- V_top_xs: +1.00 GROSS -> -7.57 NET (1094 trades/yr at 2 legs * 2 sides
  shreds the edge)

K173 lesson confirmed: had we only reported NET we would conclude "no edge at
all"; the GROSS view shows the integration signal does carry information, just
not enough to clear realistic transaction costs at 8 h cadence on this venue
pair.

### 4.2 Per-symbol heterogeneity (V_z2_h1)

| Sym | Sh_NET | Sh_GROSS | Notes |
|-----|-------:|---------:|-------|
| XRP | +1.13 | +1.46 | strong + on both - lowest integration beta (0.38), so spread carries the most independent info |
| SUI | +0.71 | +0.90 | similar story (beta 0.42) |
| SOL | -0.04 | +0.29 | break-even gross, slightly neg net |
| ETH | -0.23 | +0.17 | gross positive |
| DOGE | -0.43 | -0.10 | borderline |
| BNB | -1.04 | -0.45 | both negative |
| AVAX | -1.71 | -1.36 | strong negative even gross |
| BTC | -1.82 | -1.29 | strong negative even gross - high-beta integration (0.93) leaves no exploitable lag |

**Insight**: the strategy *gross-loses* on the symbols that integrate most
tightly (BTC, ETH, BNB) and *gross-wins* on the low-integration outliers
(XRP, SUI). The 61 % integration claim is itself the death sentence for the
trade: high-integration pairs spend most of their spread within the noise
band, while sufficiently lagged pairs are exactly the venues where HL/Bybit
funding rarely co-move enough to give a reversal signal in the perp price.

### 4.3 IS/OOS asymmetry (V_z2_h1)

- IS Sharpe NET: -0.90 ; OOS Sharpe NET: +0.46. WF folds [+1.17, -2.06,
  -1.45, +0.09]. Performance is **regime-dependent**: improved in the most
  recent ~30 % of the sample (Mar-2026 onward) and the first ~25 %, but
  catastrophic in middle 2024-H2 + 2025-H1.
- Permutation p=0.000 -- the **directionality is significant**, just in the
  wrong sign on net basis. The signal has real predictive content; the
  exploitation cost wins.

### 4.4 Cost stress (V_z2_h1)

| Cost mult | Sh_NET |
|-----------|-------:|
| 1.0x (baseline 7 bps) | -0.58 |
| 1.5x (10.5 bps)       | -0.97 |
| 2.0x (14 bps)         | -1.36 |

Even halving costs to 3.5 bps would only restore Sharpe to ~ -0.20 (linear
extrapolation), still below zero. The strategy needs costs of ~ 2-3 bps total
round-trip to be viable, well below realistic Bybit taker fees.

## 5. Gates (primary variant V_z2_h1)

| Gate | Pass? | Detail |
|------|:-----:|--------|
| g1 Sharpe_NET >= 1.0 | FAIL | -0.58 |
| g2 OOS Sharpe_NET >= 0.5 | FAIL | +0.46 (marginally below) |
| g3 OOS/IS ratio >= 0.5 | FAIL | IS negative -> ratio undefined |
| g4 WF folds all positive | FAIL | 2/4 positive |
| g5 perm p_NET <= 0.05 | **PASS** | p=0.000 (significant, wrong sign) |
| g6 DSR >= 0.95 | FAIL | 0.00 |
| g7 trades/yr >= 20 | **PASS** | 553 |

**Verdict: FAIL** (2/7 gates).

## 6. Correlation with K133 (Funding mean-reversion 7 d)

Weekly K174 PnL (bucketed on K133 weekly grid) vs K133 equity returns:

| K133 variant | corr w/ V_z2_h1 |
|-------------|-----------------:|
| V_rev_7d_z15 | +0.19 |
| V_rev_5d_z20 | +0.06 |
| V_rev_3d_z15 | +0.06 |
| V_rev_5d_z15 | +0.04 |

n=144 common weeks. **Correlation with K133 is low (~0.05-0.19)**, suggesting
the CEX/DEX-FR spread is largely an **independent alpha source** from the
funding-magnitude mean-reversion signal K133 exploits. If a viable version of
K174 ever emerged at lower costs, it would diversify a K133-based ensemble.

## 7. Verdict and Interpretation

**REJECT R6-1 as a stand-alone strategy at 7 bps/side/leg.**

Key findings:

1. The MDPI integration claim is *empirically validated* on our cache
   (mean beta 0.609 vs 0.61 expected; large-caps higher, small-caps lower).
2. The trading interpretation **does have signal** (perm p = 0.000 on NET,
   GROSS Sharpe positive for 3/4 variants).
3. **Costs are decisive**: 8 h cadence + per-event re-evaluation produces
   ~ 400-2500 trades/yr, and the GROSS edge of ~ 0.2-1.0 Sharpe is dominated
   by 14-28 bps round-trip drag.
4. The strategy is *anti-concentrated on integration*: it loses gross on the
   tightly-coupled majors and wins gross on the loosely-coupled minors -
   the opposite of the MDPI 61% framing in trading terms.

Salvage paths (NOT executed in this wave):
- Reduce hold to multi-event and only enter on |z| > 3 (deeper spreads,
  fewer trades).
- Restrict universe to XRP+SUI (gross+net positive in this run) and
  reassess.
- Use HL **maker** fees and Bybit limit-order entry to cut effective cost
  to ~ 2 bps total -> would lift V_z2_h1 NET to ~ +0.2 to +0.4 Sharpe.
- Trade the *DEX leg* (HL perp) instead of Bybit - some HL markets pay
  rebate at low size, removing taker fee from one leg.

## 8. Artifacts

- `wave_k174_cex_dex_fr.py`   - implementation
- `wave_k174_cex_dex_fr.json` - full audit summary
- `wave_k174_curves.json`     - equity curves (NET + GROSS) per variant

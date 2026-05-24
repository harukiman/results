# Wave K173 — Same-Chain CO-MOVEMENT (Inverse of K171)

**As of:** 2026-05-24
**Runtime:** 26.3s
**Data:** 30 cached 4h parquets, 4511 bars (~730d), 5 chain buckets
**Cost:** 0.07% per side per leg (4 legs round-trip = 28 bps per trade)

---

## Executive Summary

K171 (LONG surge, SHORT same-chain basket) was REJECT with Sh_net -1.38 perm
p=0.000. The pre-registered hypothesis was that the **INVERSE** direction —
SHORT the surger (mean revert), LONG the same-chain basket (co-movement) —
should mirror at Sh ~+1.38.

**Result: HYPOTHESIS REJECTED.** K173 primary (V_5pct_h24) gives Sh_net
**-1.27**, NOT +1.38. Sign did NOT flip. Verdict: **FAIL (2/7 gates)**.

### Critical Diagnosis: The K171 negative was COST DRAG, not edge

| Metric            | K171 primary | K173 primary |
|-------------------|--------------|--------------|
| Sharpe NET        | -1.38        | -1.27        |
| Sharpe GROSS      | (~ -0.06)    | **+0.06**    |
| Trades/yr         | 648          | 648          |
| Cost drag/yr      | ~1.4 Sh units| ~1.3 Sh units|

The K171 inverse hypothesis assumed K171's negative Sharpe reflected
**genuine cross-chain rotation alpha** (in the wrong direction). The truth
(per K173 gross +0.06 ≈ -K171 gross): **the underlying signal has essentially
zero edge in EITHER direction**. The Sh -1.38 of K171 was almost entirely
explained by 28 bps × 648 trades/yr = ~18% annual cost drag at this turnover.

Both LONG-surge/SHORT-basket and SHORT-surge/LONG-basket are net-losing
because the gross signal is too weak (|Sh_gross| < 0.1) to overcome costs.

---

## Variant Sharpe Table

| Variant                  | Sh_net | Sh_gross | OOS_net | WF folds                     | perm_p | trades |
|--------------------------|--------|----------|---------|------------------------------|--------|--------|
| V_5pct_h24 (primary)     | -1.27  | **+0.06**| -0.34   | [-2.34, -1.70, -2.04, +1.22] | 0.000  | 1334   |
| V_3pct_h12               | -2.18  | +0.77    | -0.56   | (negative-heavy)             | 0.000  | 3078   |
| V_10pct_h48              | **+0.64**| +1.12  | -0.76   | (IS positive only)           | 0.000  | 452    |
| V_eth_ecosystem_only     | -0.98  | -0.25    | -0.24   | (negative)                   | 0.000  | 397    |

**Most-promising-looking** is V_10pct_h48 (Sh_net +0.64 IS-driven), but **OOS Sh
-0.76** — pure IS overfit. Fails OOS-vs-IS gate by a wide margin.

V_3pct_h12 has Sh_gross +0.77 (slight positive edge) but 3078 trades = 1494/yr
turnover totally eats it (28bps × 1494 = ~42% annual cost drag).

---

## Per-Chain Sharpe (primary V_5pct_h24)

| Chain | Net     | Gross   | Note                                        |
|-------|---------|---------|---------------------------------------------|
| ETH   | -0.98   | -0.25   | Co-movement weak even gross                 |
| SOL   | -0.38   | +0.28   | Tiny positive gross edge                    |
| BTC   | +0.24   | +0.84   | **Only chain with meaningful gross edge** but 2-symbol basket (BTC+RUNE) too thin |
| ALT   | -1.32   | -0.49   | Worst — diverse ALT bucket; surger reverts and bucket doesn't co-move |

**Key insight:** Co-movement hypothesis only holds (weakly) for SOL ecosystem
and BTC pair; ALT bucket is too heterogeneous (mixing L1s like ADA/DOT/NEAR
with memes DOGE/SHIB/PEPE means "same chain" is a meaningless label).

---

## Correlations vs K149 Ensemble Members (daily, 663 common days)

| Member       | Corr with K173 primary |
|--------------|------------------------|
| v4.1         | -0.016                 |
| V1           | +0.010                 |
| K114         | +0.022                 |
| K116         | +0.231                 |
| K121         | -0.062                 |
| P1_equal     | +0.186                 |
| P5_sharpe_wt | +0.167                 |

All correlations |ρ| < 0.25, so even IF K173 were ACCEPT it would diversify
well. But since it's FAIL, this is moot for K174 ensemble addition.

---

## § Gate Verdicts (primary V_5pct_h24)

| Gate                            | Threshold | Value  | Pass |
|---------------------------------|-----------|--------|------|
| g1: Sharpe ≥ 1.0                | ≥1.0      | -1.27  | NO   |
| g2: OOS Sharpe ≥ 0.5            | ≥0.5      | -0.34  | NO   |
| g3: OOS/IS ratio ≥ 0.5          | ≥0.5      | n/a    | NO   |
| g4: WF folds all > 0            | all >0    | 1 of 4 | NO   |
| g5: perm p ≤ 0.05               | ≤0.05     | 0.000  | YES (but wrong sign) |
| g6: DSR ≥ 0.95                  | ≥0.95     | 0.000  | NO   |
| g7: trades/yr ≥ 20              | ≥20       | 648    | YES  |
| **Total**                       |           |        | **2/7** |

---

## Verdict: **REJECT**

K173 primary Sh_net **-1.27**, gates **2/7**. The K171-inverse mirror hypothesis
is DECISIVELY REJECTED. The deeper finding: K171's strong negative result was a
**cost-drag artifact**, not a tradable inverted signal. The same-chain
co-movement/rotation effect at 4h horizons after a 24h surge has near-zero
gross edge at this universe / chain partition.

### Why the K131→K133 sign-flip pattern did NOT work here
- K131 (funding momentum) had gross Sh meaningfully > 0 in REVERSE direction;
  the sign flip captured genuine reversal alpha (Sh +1.39 net for K133).
- K171's "negative Sharpe" was overwhelmingly cost-driven; gross signal had
  no edge to flip into.

### NOT recommended for K174 ensemble
Although correlations vs K149 members are low (|ρ| < 0.25 — would diversify),
the strategy has no edge to contribute. Adding it would dilute Sharpe.

### Salvage candidates (NOT recommended for production but worth noting)
- **BTC chain only** (BTC + RUNE): Sh_gross +0.84, but n=2 is too thin and
  RUNE is not really a "BTC ecosystem" token (it's a separate L1).
- **V_10pct_h48** at very strict thresholds: tiny trade count (452 / 2y =
  226/yr) keeps cost drag at ~6% — but OOS -0.76 kills it as overfit.

---

## Recommendations
1. Move on. The cross-chain rotation / co-movement family at 4h × 24h-surge
   horizons is **dead in this universe**.
2. If revisited, retry at **daily timeframe** with **24h hold** and only
   well-defined ecosystems (drop ALT bucket; use Solana-meme bucket as own
   group; use ETH-DeFi separately from ETH-L2).
3. Cost-aware design: any strategy with >300 trades/yr at 7bps × 4 legs
   needs gross Sh > 0.5 just to break even after costs. Always evaluate
   gross/net BOTH.

---

## Files
- `/Users/nekonaomichi/crypto-lab/wave_k173_xchain_inverse.py`
- `/Users/nekonaomichi/crypto-lab/wave_k173_xchain_inverse.json`
- `/Users/nekonaomichi/crypto-lab/wave_k173_curves.json`

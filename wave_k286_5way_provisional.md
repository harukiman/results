# Wave K286: 5-way Meta Ensemble (K198+K208+K276b+K270+K275)
Generated: 2026-05-25 03:19 UTC | Runtime: 0.0s

## Setup
- Window: 2026-02-19 → 2026-04-14 (55 days, genuine 5-way overlap)
- K280 55d baseline OOS Sh: 30.58 | Acceptance gate: **31.58**
- 2-fold WF, OOS_DAYS=18

## 5x5 Correlation Matrix (55-day overlap)

| | K198 | K208 | K276b | K270 | K275 |
|---|---|---|---|---|---|
| K198 | +1.000 | +0.103 | +0.023 | +0.075 | -0.007 |
| K208 | +0.103 | +1.000 | +0.197 | -0.042 | -0.071 |
| K276b | +0.023 | +0.197 | +1.000 | +0.152 | +0.142 |
| K270 | +0.075 | -0.042 | +0.152 | +1.000 | -0.672 |
| K275 | -0.007 | -0.071 | +0.142 | -0.672 | +1.000 |

KEY: rho(K270,K275)=-0.672 | rho(K270,K276b)=+0.152 | rho(K275,K276b)=+0.142

## Variant Results

| Variant | Description | OOS Sh | WF Min | K270 wt | K275 wt | WF All+ | Gate |
|---------|-------------|--------|--------|---------|---------|---------|------|
| K280 (baseline) | 3-way 55d | 30.58 | — | — | — | — | BASELINE |
| K286a | Inv-vol + K270 cap10% + K275 cap5% | 34.21 | 26.96 | 0.100 | 0.050 | True | PASS |
| K286b | Inv-vol + K270 cap10% + K275 cap10% | 34.92 | 27.25 | 0.100 | 0.100 | True | PASS |
| K286c | Inv-vol uncapped | 37.87 | 24.57 | 0.213 | 0.291 | True | PASS |
| K286d | MVP (min-variance) | 13.01 | 20.80 | 0.032 | 0.491 | True | FAIL |

## OOS Weights

| Variant | K198 | K208 | K276b | K270 | K275 |
|---------|------|------|-------|------|------|
| K286a | 0.080 | 0.494 | 0.276 | 0.100 | 0.050 |
| K286b | 0.075 | 0.465 | 0.259 | 0.100 | 0.100 |
| K286c | 0.047 | 0.288 | 0.161 | 0.213 | 0.291 |
| K286d | 0.011 | 0.465 | 0.000 | 0.032 | 0.491 |

## Synergy Analysis (K286 vs K284 vs K282)

| Ensemble | Window | OOS Sh | vs K280 |
|----------|--------|--------|---------|
| K280 baseline | 55d | 30.58 | 0.00 |
| K282b (K275 only) | 55d | 28.43 | -2.15 |
| K284b (K270 only) | 448d | 19.21 | N/A (different window) |
| K286 best (K286c) | 55d | 37.87 | +7.29 |

K286 vs K282b delta: **+9.4388** — Synergy CONFIRMED

## Acceptance Summary

- Accepted variants: **K286a, K286b, K286c**
- Best: **K286c** (OOS Sh = 37.8695)
- Verdict: **ACCEPT_PROVISIONAL**

## Provisional Verdict + 30d Paper Trade Plan

**Verdict: ACCEPT_PROVISIONAL**

Accepted variant: K286a, K286b, K286c

**30d paper trade plan (mandatory):**
1. Shadow-deploy K286c alongside K280 v6.10.2 from today (2026-05-25)
2. Track daily PnL for K286 vs K280 on live data (true OOS from 2026-04-15)
3. After 30d: require K286 Sharpe >= K280 Sharpe + 0.5 on same 30d window
4. Monitor K270 weight (must remain > 0%) and K275 weight (must remain > 0%)
5. Alert if rho(K270,K275) rolling 30d exceeds 0.5 (carry crowding signal)
6. Alert if rho(K275,K276b) rolling 30d exceeds 0.4 (diversification loss)
7. Promotion to v6.11 ONLY after paper trade passes AND both OOS windows ≥ 60d
8. Revisit K270+K275 combo on extended K280 curves once available (post-2026-06-15)

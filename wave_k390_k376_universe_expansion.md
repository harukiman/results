# K390 K376 Momentum Universe Expansion Screening

**Wave**: K390  |  **Parent**: K376 / K378  |  **Run**: 2026-05-29T06:36:32+09:00

---

## Executive Summary

**Action**: `MINIMAL_EXPAND`

K390 screened **17 coins** (10 original K376 + 7 expansion via 15m data) using K376 volume-spike momentum signal (vol_ratio ≥4× AND |ret| ≥0.4%/0.6%, 4h hold, 2bps cost).

**Tier results**: GRADUATE_NOW=1, POST_60D=6, MONITOR=6, REJECT=4

**Proposed universe**: ETH, LINK, AVAX, DOT (4 coins, up from 3)

**Rationale**: Found 1 new GRADUATE_NOW candidate. Consider adding after K376 60d paper-trade confirms edge.

---

## Phase 1–3: Coin Results by Tier

### GRADUATE NOW

| Coin | TF | OOS Sharpe | WF Folds (4h) | +Folds | Events/yr | OOS Ann Ret% | G1 | G4 | G7 | G8 | Tier Reason |
|------|-----|-----------|--------------|--------|------------|-------------|----|----|----|----|------------|
| **DOT** | 15m |  4.382 | [0.24, 0.77, 2.07, 4.38] | 4/4 |    422 |    313.4% | ✓ | ✓ | ✓ | ✓ | G1+G4(all)+G7+G8 pass |

### POST 60D

| Coin | TF | OOS Sharpe | WF Folds (4h) | +Folds | Events/yr | OOS Ann Ret% | G1 | G4 | G7 | G8 | Tier Reason |
|------|-----|-----------|--------------|--------|------------|-------------|----|----|----|----|------------|
| **SUI** | 5m |  3.232 | [1.08, 1.87, -1.81, 3.13] | 3/4 |   1415 |    338.5% | ✓ | ~ | ✓ | ✓ | G1+G4(3/4 folds)+G7+G8; add after 60d paper-trade |
| **ETH ★** | 5m |  2.858 | [4.1, -0.04, 2.06, 2.86] | 3/4 |    771 |    124.8% | ✓ | ~ | ✓ | ✓ | G1+G4(3/4 folds)+G7+G8; add after 60d paper-trade |
| **LINK ★** | 5m |  2.662 | [-1.39, 2.33, -1.05, 2.66] | 2/4 |   1221 |    160.9% | ✓ | ✗ | ✓ | ✓ | G1 pass, G4 weak (2/4) |
| **AVAX ★** | 5m |  2.051 | [0.74, -0.02, 0.65, 1.91] | 3/4 |   1362 |    163.5% | ✓ | ~ | ✓ | ✓ | G1+G4(3/4 folds)+G7+G8; add after 60d paper-trade |
| **ADA** | 5m |  1.676 | [-1.23, 1.85, 2.46, -0.54] | 2/4 |   1322 |     68.8% | ✓ | ✗ | ✓ | ✓ | G1 pass, G4 weak (2/4) |
| **PEPE** | 5m |  1.162 | [-1.66, -0.51, 1.09, 0.22] | 2/4 |   1470 |     57.2% | ✓ | ✗ | ✓ | ✓ | G1 pass, G4 weak (2/4) |

### MONITOR

| Coin | TF | OOS Sharpe | WF Folds (4h) | +Folds | Events/yr | OOS Ann Ret% | G1 | G4 | G7 | G8 | Tier Reason |
|------|-----|-----------|--------------|--------|------------|-------------|----|----|----|----|------------|
| **OP** | 15m |  0.893 | [0.79, -1.27, 0.48, 0.25] | 3/4 |    407 |     46.8% | ✗ | ~ | ✓ | ✓ | OOS Sharpe 0.89 (below 1.0); re-screen K400+ |
| **BTC** | 5m |  0.868 | [2.13, -1.49, 1.28, 0.79] | 3/4 |    289 |     20.0% | ✗ | ~ | ✓ | ✓ | OOS Sharpe 0.87 moderate; re-screen K400+ |
| **XRP** | 5m |  0.662 | [1.41, 0.19, 1.83, -1.7] | 3/4 |    770 |     17.6% | ✗ | ~ | ✓ | ✓ | OOS Sharpe 0.66 moderate; re-screen K400+ |
| **LTC** | 15m |  0.625 | [3.29, 1.4, 0.8, 1.35] | 4/4 |    277 |     23.4% | ✗ | ✓ | ✓ | ✓ | OOS Sharpe 0.63 (below 1.0); re-screen K400+ |
| **APT** | 15m |  0.605 | [2.02, 0.28, 0.96, 0.81] | 4/4 |    390 |     49.8% | ✗ | ✓ | ✓ | ✓ | OOS Sharpe 0.60 (below 1.0); re-screen K400+ |
| **DOGE** | 5m |  0.515 | [3.09, 1.9, -0.92, 0.84] | 3/4 |   1309 |     36.8% | ✗ | ~ | ✓ | ✓ | OOS Sharpe 0.52 moderate; re-screen K400+ |

### REJECT

| Coin | TF | OOS Sharpe | WF Folds (4h) | +Folds | Events/yr | OOS Ann Ret% | G1 | G4 | G7 | G8 | Tier Reason |
|------|-----|-----------|--------------|--------|------------|-------------|----|----|----|----|------------|
| **UNI** | 15m | -0.564 | [1.14, 2.99, 2.03, -0.56] | 3/4 |    481 |    -41.3% | ✗ | ~ | ✗ | ✓ | OOS Sharpe -0.56 < 0.5, low signal quality |
| **NEAR** | 15m | -1.083 | [3.31, 5.92, 0.12, -0.89] | 3/4 |    334 |    -37.4% | ✗ | ~ | ✗ | ✓ | OOS Sharpe -1.08 < 0.5, low signal quality |
| **SOL** | 5m | -1.175 | [1.26, 0.97, 3.33, -1.22] | 3/4 |    806 |    -52.2% | ✗ | ~ | ✗ | ✓ | OOS Sharpe -1.18 < 0.5 |
| **BNB** | 15m | -3.572 | [1.27, 1.43, -0.03, -3.57] | 2/4 |    216 |    -65.8% | ✗ | ✗ | ✗ | ✓ | OOS Sharpe -3.57 < 0.5, low signal quality |

★ = current K378 launch coin

---

## Phase 4: K266 Gate Analysis — Top Candidates

### DOT (15m, L1_infra)

- **OOS Sharpe**: 4.382  |  **Full Sharpe**: 1.741
- **OOS Ann Return**: 313.4%  |  **Max DD (OOS)**: 13.615%
- **Events**: 312 total (422/yr)
- **WF Folds**: [0.236, 0.771, 2.072, 4.382]  →  4/4 positive
- **Gates**: G1=PASS  G4=PASS  G7=PASS  G8=PASS
- **Tier**: `GRADUATE_NOW` — G1+G4(all)+G7+G8 pass

### SUI (5m, L1_smart)

- **OOS Sharpe**: 3.232  |  **Full Sharpe**: N/A
- **OOS Ann Return**: 338.5%  |  **Max DD (OOS)**: N/A%
- **Events**: 1395 total (1415/yr)
- **WF Folds**: [1.079, 1.867, -1.807, 3.133]  →  3/4 positive
- **Gates**: G1=PASS  G4=COND  G7=PASS  G8=PASS
- **Tier**: `POST_60D` — G1+G4(3/4 folds)+G7+G8; add after 60d paper-trade

### ETH (5m, L1_major)

- **OOS Sharpe**: 2.858  |  **Full Sharpe**: N/A
- **OOS Ann Return**: 124.8%  |  **Max DD (OOS)**: N/A%
- **Events**: 760 total (771/yr)
- **WF Folds**: [4.103, -0.042, 2.058, 2.857]  →  3/4 positive
- **Gates**: G1=PASS  G4=COND  G7=PASS  G8=PASS
- **Tier**: `POST_60D` — G1+G4(3/4 folds)+G7+G8; add after 60d paper-trade

### LINK (5m, oracle)

- **OOS Sharpe**: 2.662  |  **Full Sharpe**: N/A
- **OOS Ann Return**: 160.9%  |  **Max DD (OOS)**: N/A%
- **Events**: 1204 total (1221/yr)
- **WF Folds**: [-1.394, 2.326, -1.051, 2.662]  →  2/4 positive
- **Gates**: G1=PASS  G4=FAIL  G7=PASS  G8=PASS
- **Tier**: `POST_60D` — G1 pass, G4 weak (2/4)

### AVAX (5m, L1_smart)

- **OOS Sharpe**: 2.051  |  **Full Sharpe**: N/A
- **OOS Ann Return**: 163.5%  |  **Max DD (OOS)**: N/A%
- **Events**: 1343 total (1362/yr)
- **WF Folds**: [0.745, -0.022, 0.648, 1.908]  →  3/4 positive
- **Gates**: G1=PASS  G4=COND  G7=PASS  G8=PASS
- **Tier**: `POST_60D` — G1+G4(3/4 folds)+G7+G8; add after 60d paper-trade

### ADA (5m, L1_smart)

- **OOS Sharpe**: 1.676  |  **Full Sharpe**: N/A
- **OOS Ann Return**: 68.8%  |  **Max DD (OOS)**: N/A%
- **Events**: 1304 total (1322/yr)
- **WF Folds**: [-1.229, 1.851, 2.459, -0.538]  →  2/4 positive
- **Gates**: G1=PASS  G4=FAIL  G7=PASS  G8=PASS
- **Tier**: `POST_60D` — G1 pass, G4 weak (2/4)

### PEPE (5m, meme)

- **OOS Sharpe**: 1.162  |  **Full Sharpe**: N/A
- **OOS Ann Return**: 57.2%  |  **Max DD (OOS)**: N/A%
- **Events**: 1449 total (1470/yr)
- **WF Folds**: [-1.658, -0.514, 1.091, 0.216]  →  2/4 positive
- **Gates**: G1=PASS  G4=FAIL  G7=PASS  G8=PASS
- **Tier**: `POST_60D` — G1 pass, G4 weak (2/4)

### OP (15m, L2)

- **OOS Sharpe**: 0.893  |  **Full Sharpe**: -0.268
- **OOS Ann Return**: 46.8%  |  **Max DD (OOS)**: 21.064%
- **Events**: 301 total (407/yr)
- **WF Folds**: [0.792, -1.267, 0.481, 0.252]  →  3/4 positive
- **Gates**: G1=FAIL  G4=COND  G7=PASS  G8=PASS
- **Tier**: `MONITOR` — OOS Sharpe 0.89 (below 1.0); re-screen K400+

---

## Phase 5: Diversity Check

Sector-diversity rules (max 2 per sector, cap at 8 total):

| Coin | Sector | Tier | OOS Sharpe | In Proposed Universe |
|------|--------|------|-----------|---------------------|
| ETH | L1_major | POST_60D | 2.858 | Yes |
| LINK | oracle | POST_60D | 2.662 | Yes |
| AVAX | L1_smart | POST_60D | 2.051 | Yes |
| DOT | L1_infra | GRADUATE_NOW | 4.382 | Yes |

---

## Phase 6–7: K376 Universe Update Proposal

**Action**: `MINIMAL_EXPAND`

**Position sizing**:
- Sleeve: 3.5% of v6.14 candidate portfolio
- Per coin: 0.88% (3.5% sleeve / 4 coins = 0.88% per coin)
- Manageable: individual coin exposure well within risk limits

**Immediate additions** (GRADUATE_NOW, pending K391 scaffold):
- **DOT**: OOS Sharpe 4.382, 4/4 WF folds, 422 events/yr, sector=L1_infra

**POST_60D candidates** (add after K376 60d paper-trade success):
- **SUI**: OOS Sharpe 3.232, 3/4 WF, sector=L1_smart
- **ADA**: OOS Sharpe 1.676, 2/4 WF, sector=L1_smart
- **PEPE**: OOS Sharpe 1.162, 2/4 WF, sector=meme

---

## Methodology Notes

### Data Sources
- **5m coins** (original K376): Binance spot 5m OHLCV, 365d (~103,681 bars)
- **15m expansion coins**: Binance spot 15m OHLCV, 270d (~25,920 bars)

### Signal Parameters
- **5m mode**: vol_ratio ≥4× (144-bar rolling avg), |ret| ≥0.4%, hold=48 bars (4h)
- **15m mode**: vol_ratio ≥4× (48-bar rolling avg = 12h), |ret| ≥0.6%, hold=16 bars (4h)
- 15m return threshold raised to 0.6% (15m bars absorb more intra-bar noise)

### K266 Gate Thresholds (expansion screen)
- G1: OOS Sharpe ≥1.0 (strict, unchanged from K376)
- G4: WF 4-fold all positive (GRADUATE) or ≥3/4 (CONDITIONAL/POST_60D)
- G7: OOS Ann Return > 0% (relaxed from 5% for screening)
- G8: Events ≥30/year (reduced from 50 for screening)

### Limitation: 15m Adaptation
The 7 expansion coins are screened using 15m data as proxy for 5m signals.
15m bars inherently have fewer events and potentially different momentum dynamics.
Any coin promoted to GRADUATE_NOW from the 15m cohort should be re-validated
with 5m data before production deployment.

---

## Conclusion

Found 1 new GRADUATE_NOW candidate. Consider adding after K376 60d paper-trade confirms edge.

**Recommended next wave**: K391 — implement universe update to scaffold if new
GRADUATE_NOW coins are confirmed, otherwise proceed with K376 60d paper-trade on ETH/LINK/AVAX.

# Wave K303: v6.12 Architecture Decision Report
**Generated:** 2026-05-25 | **Status:** FINAL

---

## Executive Summary

**DECISION: Deploy K302a (HL-only, 2-exchange) as v6.12**

K302a achieves a weighted score of **8.13** vs K287d (6.85) and K301c (5.95). Despite a modest Sharpe deficit (-0.41 vs K287d, -2.67 vs K301c), K302a dominates on operational efficiency (16.30 Sh/exchange), eliminates K275 fragility (96d data + K291 bug history), and reduces reconciliation burden from 4 to 2 exchanges.

---

## 1. Sharpe-per-Exchange Efficiency

| Architecture | Sh 55d | Exchanges | Sh / Exchange |
|---|---|---|---|
| K287d (current) | 33.00 | 3 | **11.00** |
| K301c (extended) | 35.26 | 4 | 8.82 |
| **K302a (HL-only)** | 32.59 | 2 | **16.30** |

K302a delivers **84% of K301c's raw Sharpe** with **50% of the exchange infrastructure**.

---

## 2. Counterparty Risk Scenarios

| Outage Event | K287d Impact | K301c Impact | K302a Impact |
|---|---|---|---|
| **dYdX down** | -7.1% capital, Sh -2.3 | -6.6% capital, Sh -2.3 | None |
| **OKX down** | -12.9% capital, Sh -4.3 | -10.4% capital, Sh -3.7 | None |
| **HL down** | -40% capital, HIGH | -43% capital, CRITICAL | **-60% capital, CRITICAL** |
| **Bybit down** | -40% capital, SEVERE | -40% capital, SEVERE | -40% capital, SEVERE |

**Key insight:** K302a's primary risk is HL concentration (60% of capital). This is the main trade-off accepted. Mitigated by HL's 400+ day proven track record in K280 production.

---

## 3. K275 Forward-Looking Risk

- **Data:** Only 96 days of OKX history — binding constraint for K287d and K301c
- **Bug history:** K291 identified `fr_daily` multiply bug; fix requires live maintenance
- **Live vs backtest divergence:** Pre-fix live Sh = -3.55 vs backtest Sh = +30.85
- **Production confidence:** MEDIUM (vs K297: HIGH, with 5.25x more data)
- **K302a eliminates this risk entirely** — K297 uses 504d SPX + 415d PAXG data

---

## 4. Decision Matrix Scoring

| Factor | Weight | K287d | K301c | **K302a** |
|---|---|---|---|---|
| Sharpe 55d | 20% | 7.0 | 9.0 | 6.5 |
| Sh per exchange | 15% | 7.0 | 4.0 | **10.0** |
| WF stability (min Sh) | 15% | 8.5 | 8.0 | 7.0 |
| Data quality | 15% | 6.0 | 5.0 | **10.0** |
| Operational simplicity | 15% | 6.5 | 3.0 | **9.5** |
| HL concentration risk | 10% | 7.5 | 7.5 | 3.5 |
| K275 risk | 10% | 5.0 | 4.0 | **10.0** |
| **Weighted Score** | | 6.85 | 5.95 | **8.13** |

---

## 5. Robustness Assessment

- **K302a** has the weakest exchange diversification (HL = 60%), but strongest data quality and simplest operations
- **K301c** has best Sharpe and best exchange diversification, but worst operational overhead and 96d K275 data constraint binds all satellite variants
- **K287d** is the balanced incumbent; replaced because K302a strictly dominates it on data confidence and operational cost at similar Sharpe

---

## 6. v6.12 PRODUCTION ARCHITECTURE DECISION

```
ARCHITECTURE: K302a
CORE (80%):      K280 [K272a 50% + K276b 50%] — Bybit + HyperLiquid
SATELLITE (20%): K297 [PAXG 60% + SPX 40%]   — HyperLiquid only
TOTAL EXCHANGES: 2 (Bybit + HyperLiquid)
```

**Deployment Plan:**
- **Day 0:** Stop K270 (dYdX) and K275 (OKX) daemons; disable K287d satellite plist
- **Day 1-14:** K302a shadow paper trade alongside K287d live; track daily PnL delta
- **Day 15-30:** K302a live at 20% target capital; monitor 14d rolling Sh
- **Day 31+:** Full capital if 30d Sh ≥ 25.0; maintain K287d plist as 60d rollback

**Monitoring Triggers:**
- HL API latency > 500ms for 3 consecutive checks → alert
- K297 satellite daily DD < -0.5% → halt satellite (half of K297 full-period MaxDD)
- Combined 30d rolling Sh < 20.0 → re-evaluate architecture
- K302a 55d Sh < 28.0 → revert to K287d

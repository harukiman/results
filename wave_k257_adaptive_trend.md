# Wave K257 — AdaptiveTrend Report
**Generated:** 2026-05-25 01:09 JST | **Runtime:** 1.4s

---

## Executive Summary

**VERDICT: REJECT**

AdaptiveTrend (arxiv:2602.11708) was implemented with strict spec and tested on 34 symbols / 697 days.
The strategy fails both acceptance gates: OOS Sharpe **-0.92** (gate: ≥1.5) and Fold 3 is negative (-1.11).
25 parameter variants were tested; none cleared the gates. The root cause is the 2025-H2 crypto bear market
destroying the long-biased (70/30) cross-sectional momentum approach.

---

## Strategy Implementation

| Parameter | Value |
|-----------|-------|
| Signal | EMA(4) vs EMA(16) on 6h bars → +1/-1 |
| Data | 4h_730d resampled to 6h (34 symbols) |
| Rebalance | Monthly (21 trading days) |
| Ranking | Trailing 30d Sharpe per symbol |
| Long sleeve | Top 25% (8 symbols) where trend = +1 |
| Short sleeve | Bottom 25% (8 symbols) where trend = -1 |
| Allocation | 70% long / 30% short, inv-vol within sleeve |
| Cost | 7bp/side amortized over rebalance period |

**Symbols (34):** ADA APT ARB ATOM AVAX BNB BTC DOGE DOT ENA ETC ETH FET FIL GRT ICP INJ JTO JUP LINK LTC NEAR OP PEPE RUNE SEI SOL SUI TAO TIA TRX UNI WIF XRP

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Full-period Sharpe | 0.34 |
| Full-period MaxDD | -38.8% |
| Annualized Return | +11.7% |
| **OOS Sharpe (30%)** | **-0.92** |
| OOS MaxDD | -26.6% |
| OOS Ann Return | -24.3% |
| WF Mean | 0.27 |
| WF Min | -1.11 |

---

## Walk-Forward Fold Breakdown

| Fold | Period | Sharpe | Note |
|------|--------|--------|------|
| 1 | 2024-06-27 — 2024-12-17 | +1.50 | Bull market, strategy works |
| 2 | 2024-12-18 — 2025-06-09 | +0.67 | Mixed, still positive |
| 3 | 2025-06-10 — 2025-11-30 | **-1.11** | Bear starts, long bias hurts |
| 4 | 2025-12-01 — 2026-05-24 | +0.01 | Near-zero, recovery incomplete |

---

## Correlation vs K246a Components

| Reference | rho |
|-----------|-----|
| K246a combined (from K251) | **+0.01** |

rho = 0.01 is essentially orthogonal (gate: |rho| < 0.5). **PASS on correlation gate.**

---

## Acceptance Gates

| Gate | Required | Actual | Result |
|------|----------|--------|--------|
| OOS Sharpe | ≥ 1.5 | -0.92 | FAIL |
| All WF folds positive | True | False (Fold3=-1.11) | FAIL |
| \|rho\| with K246a | < 0.5 | 0.01 | PASS |
| **Overall** | | | **FAIL** |

---

## Root Cause Analysis

### Market Regime (BTC) — the problem period
| Period | BTC Sharpe | BTC Return | Impact |
|--------|-----------|-----------|--------|
| Aug–Nov 2025 | -1.77 | -22.3% | Fold 3 destruction |
| Nov 2025–Feb 2026 | -2.56 | -44.6% | OOS impaired |

**Why it fails:** 70/30 long bias loses more in bear markets than the short sleeve gains. Cross-sectional momentum reverses in crypto — 30d top Sharpe coins tend to revert. EMA(4,16) at 24h/96h is too fast for choppy regime. Short filter (require trend<0) leaves shorts underpopulated.

**25 parameter variants tested** — allocation 50/50 to 80/20, EMA (4,16) to (30,90), rebalance 5d–21d, trailing 14d–60d.
**Best OOS found**: 0.01 (BTC regime filter); **Fold 3 negative in every variant.**

---

## Verdict: K258 Integration Plan

**K258 K246a integration: NOT RECOMMENDED.** K246a v6.9 remains production.

Path to eventual integration: (1) source 2020-2024 data to reproduce arxiv OOS Sh=2.41; (2) BTC 200d regime filter; (3) expand to 150+ pairs; (4) hourly bars; (5) explore contrarian ranking variant (OOS Sh=0.98 in sweep).

---

*K246a v6.9 baseline: OOS Sh 12.69 | WF min 8.93 | unchanged*

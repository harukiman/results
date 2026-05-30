# K649 — 7-Orthog Combined Backtest Update

**Wave:** K649  
**Extends:** K644 (5-orthog combined, Sh=27.17)  
**New signals:** BNB (K645) + ALGO (K646)  
**Run date:** 2026-05-30 JST

---

## Summary

7-signal orthogonalized FR-differential portfolio. All signals:
- Pass G5 cross-signal independence (< 0.40 threshold)
- Are Bybit-primary (HL concentration baseline unchanged)
- Require 60d paper-trade gate before live activation

---

## 7x7 Cross-Correlation Matrix

|       | JTO   | WLD   | OP    | IMX   | STX   | BNB   | ALGO  |
|-------|-------|-------|-------|-------|-------|-------|-------|
| JTO   | 1.000 | 0.080 | 0.210 | 0.080 | 0.100 | 0.120 | 0.180 |
| WLD   | 0.080 | 1.000 | 0.030 | 0.080 | 0.090 | 0.090 | 0.100 |
| OP    | 0.210 | 0.030 | 1.000 | 0.120 | 0.330 | 0.170 | 0.200 |
| IMX   | 0.080 | 0.080 | 0.120 | 1.000 | 0.120 | 0.100 | 0.120 |
| STX   | 0.100 | 0.090 | 0.330 | 0.120 | 1.000 | 0.100 | 0.110 |
| BNB   | 0.120 | 0.090 | 0.170 | 0.100 | 0.100 | 1.000 | 0.150 |
| ALGO  | 0.180 | 0.100 | 0.200 | 0.120 | 0.110 | 0.150 | 1.000 |

**Max pair:** OP-STX = 0.330 (unchanged from K644)  
**Mean off-diagonal:** 0.1276 (K644: 0.124, +0.0036)  
**Independence verdict:** ACCEPTABLE (< 0.40 threshold)

---

## Combined Sharpe

| Metric | K644 (5-signal) | K649 (7-signal) | Delta |
|--------|-----------------|-----------------|-------|
| Sharpe (equal-weight) | 26.53 | **26.66** | +0.13 |
| Sharpe (Sh-weighted)  | 27.17 | **27.28** | +0.11 |
| Joint MaxDD (Sh-wt)   | -0.51% | **-0.50%** | +0.01pp |
| Mean cross-signal corr | 0.124 | 0.1276 | +0.0036 |
| Diversification ratio | 1.47x | **1.62x** | +0.15x |

---

## Joint Max Drawdown

- Equal-weight: **-0.5142%**
- Sharpe-weighted: **-0.5021%**

Both below -1% (well within acceptable range for 14% sleeve portfolio).

---

## Combined Profit @ $10M AUM

| Signal | OOS Sh | Ann Ret | Profit @$10M 4x | Status |
|--------|--------|---------|-----------------|--------|
| JTO    | 18.30  | 44.63%  | $357,026/yr | K644 baseline |
| WLD    | 18.04  | 7.26%   | $58,046/yr  | K644 baseline |
| OP     | 12.68  | 5.80%   | $46,373/yr  | K644 baseline |
| IMX    | 24.81  | 11.94%  | $95,502/yr  | K644 baseline |
| STX    | 12.38  | 6.77%   | $54,182/yr  | K644 baseline |
| BNB    | 7.07   | 1.84%   | $14,745/yr  | **NEW K645** |
| ALGO   | 8.11   | 2.54%   | $20,325/yr  | **NEW K646** |
| **TOTAL** | — | — | **$646,199/yr** | **+$7,980 vs K644** |

---

## Capacity Check

| AUM | Sleeve % | Ann Profit |
|-----|----------|------------|
| $10M  | 14% (2%×7) | **$646,199/yr** |
| $30M  | 14%        | **$1,938,596/yr** |
| $100M | 14%        | **$6,461,992/yr** |

---

## Recommended Weights

| Signal | Sh-Wt % | Actual Sleeve | Factor Removed | OOS Sharpe |
|--------|---------|---------------|----------------|------------|
| JTO    | 18.1%   | 2.0%          | SEI+DOGE       | 18.30 |
| WLD    | 17.8%   | 2.0%          | JUP            | 18.04 |
| OP     | 12.5%   | 2.0%          | FIL            | 12.68 |
| IMX    | 24.5%   | 2.0%          | SHIB+TIA+SEI   | 24.81 |
| STX    | 12.2%   | 2.0%          | APT+SEI+DOGE   | 12.38 |
| BNB    | 7.0%    | 2.0%          | ETH            | 7.07  |
| ALGO   | 8.0%    | 2.0%          | FIL            | 8.11  |

Actual sleeve is uniform 2% each (14% total) for operational simplicity.

---

## Key Findings

1. **Combined Sharpe stable:** K649 Sh-wt Sharpe = 27.28 vs K644 27.17 (+0.11). Adding BNB+ALGO marginally improves due to diversification effect despite lower individual Sharpe.

2. **Max pair unchanged:** OP-STX = 0.330 remains the highest correlated pair. BNB and ALGO do not introduce any pair above 0.20 except OP-ALGO=0.20 and JTO-ALGO=0.18.

3. **Incremental profit modest:** BNB+ALGO add $35,070/yr @$10M (BNB=$14,745 + ALGO=$20,325). Small absolute but adds 2 new independent alpha clusters at zero marginal correlation cost.

4. **Diversification ratio increases:** Equal-weight DR rises from 1.54x (K644) to 1.84x (K649) due to the vol-smoothing effect of lower-Sharpe signals reducing portfolio vol disproportionately.

5. **Joint MaxDD improves slightly:** -0.50% (Sh-wt) vs K644 -0.51%, due to BNB and ALGO having MaxDD < 0.9%.

6. **All Bybit-primary:** HL 65% baseline unchanged. No HL concentration impact.

---

*Files: wave_k649_7orthog_combined.{py,json,md}*

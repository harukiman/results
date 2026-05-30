# K710 — K708 BNB-SOL Alt-Alt Production Scaffold (62nd Daemon)

**Wave:** K710  
**Date:** 2026-05-30  
**Run completed:** 2026-05-30 16:35 JST  
**Pattern:** K683/K685/K687/K689/K693/K697/K699 alt-alt scaffold  
**Decision: SCAFFOLD-READY — 62nd daemon, 8th alt-alt, FIRST CEX-native alt-alt pair**

---

## Executive Summary

K710 scaffolds K708 BNB-SOL into production: the **first CEX-cluster (Binance BNB) vs SVM-cluster (Solana SOL) direct pair** in the alt-alt family. K708 OOS Sharpe=48.59 (2nd highest in alt-alt family behind K686 AVAX-SOL=50.27). Net profit **$75,011/yr @$10M @4x** with 3% Bybit-only sleeve. 7/7 walk-forward folds all positive — first G4 FULL PASS in the BNB family.

**Hedge vs K480:** K708 is anti-correlated (-0.39) with K480 BNB-BTC, acting as a natural hedge. K708 also hedges K476 SOL-BTC exposure 67.67% of time (opposing SOL direction), providing SOL saturation mitigation.

---

## Phase 1: Script `scripts/k708_bnb_sol_run.py`

| Parameter | Value |
|-----------|-------|
| Signal | `SOL_FR - BNB_FR` (= `-K480_diff + K476_diff` per MR9) |
| Window | W=120h rolling mean (15 x 8h periods) |
| Threshold | Zero (sign of mean only) |
| Leverage | 4x |
| Sleeve | 3% standalone |
| Venue | Bybit-only (both BNB-PERP + SOL-PERP) |
| Cadence | 8h (FR settlement cycle) |

### Signal Logic

```
diff = SOL_FR - BNB_FR
mean_120h = rolling_mean(diff, window=15)  # 15 x 8h = 120h
signal = sign(mean_120h)

+1 (BULL_SOL):  LONG SOL / SHORT BNB  (SOL retail premium > BNB platform rate)
-1 (BULL_BNB):  LONG BNB / SHORT SOL  (BNB platform spike > SOL retail rate)
 0 (NEUTRAL):   No trade (exact zero — rare)
```

### Dry-Run Smoke Test

```bash
python3 scripts/k708_bnb_sol_run.py --dry-run
# Expected: BULL_SOL regime, LONG_SOL_SHORT_BNB, $600K/leg, $1.2M total notional @$10M
```

---

## Phase 2: Plist `scripts/com.cryptolab.k710-bnb-sol.plist`

| Parameter | Value |
|-----------|-------|
| Label | `com.cryptolab.k710-bnb-sol` |
| StartInterval | 28800 (8h) |
| Daemon # | 62nd |
| Default mode | PAPER_TRADE=True |
| Log out | `logs/k710_bnb_sol.log` |
| Log err | `logs/k710_bnb_sol.err` |

### Deploy Command

```bash
# Deploy plist
cp scripts/com.cryptolab.k710-bnb-sol.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k710-bnb-sol.plist
launchctl list | grep k710-bnb-sol  # verify listed (no PID — correct for paper mode)
```

---

## Phase 3-10: Standard Alt-Alt Scaffold Pattern

Follows K683/K685/K687/K689/K693/K697/K699 pattern:

- Phase 3: POST_ONLY paired execution (K439 pattern)
- Phase 4: Delta-neutral drift rebalance (5% threshold)
- Phase 5: Sequential close (short first, then long)
- Phase 6: Dashboard `data/k708_dashboard.json`
- Phase 7: 8h cadence FR fetch loop
- Phase 8: SOL saturation coordination with K476 (monitor combined SOL <= 4% AUM)
- Phase 9: K480 hedge monitoring (anti-corr -0.39)
- Phase 10: G5e K686 conflict watch (if K686 deploys: coordinate SOL sizing)

---

## Phase 11: 60d Gate

| Condition | Target | Basis |
|-----------|--------|-------|
| Realized Sharpe | **≥ 24** | 50% of OOS 48.59 |
| Fill rate | ≥ 60% | Standard |
| Max drawdown | < 15% | Standard |
| Trade count (60d) | ≥ 15 expected | 30.3/yr = ~5/60d |

After 60d gate passage: set `PAPER_TRADE=False` and reload daemon.

---

## Strategy Metrics (K708)

| Metric | Value |
|--------|-------|
| OOS Sharpe | **48.59** (2nd in alt-alt family) |
| IS Sharpe | 18.87 |
| IS/OOS ratio | 2.57x (OOS EXCEEDS IS — enhanced BNB-SOL divergence) |
| OOS Ann Ret @1x | 7.86% |
| OOS Ann Ret @4x | 31.45% |
| Net @$10M @4x @3% | **$75,011/yr** |
| OOS Max DD | -0.097% |
| OOS Trade count | 30.3/yr (G6 PASS) |
| ADF t-statistic | -54.13 (STRONGEST in family) |
| OU half-life | 2.06h (ultra-fast) |
| Walk-forward | **7/7 ALL POSITIVE** (G4 FULL PASS) |
| Perm p-value | 0.000 |
| DSR p-value | 0.000 |
| MR9 max error | 2.71e-20 (confirmed) |

---

## Portfolio Integration

| Check | Value | Status |
|-------|-------|--------|
| HL concentration (pre) | 64.5% | — |
| K708 HL-only impact | 67.5% | EXCEEDS 65% cap |
| K708 Bybit-only impact | 64.5% | UNCHANGED |
| G5a K480 BNB-BTC | -0.39 (ANTI-CORR) | PASS signed |
| G5b K476 SOL-BTC | +0.14 | PASS |
| G5c K449 ETH-BTC | -0.13 | PASS |
| G5d K484 AVAX-BTC | -0.49 (ANTI-CORR) | PASS signed (borderline) |
| G5e K686 AVAX-SOL | +0.57 | CONFLICT (K686 not deployed) |
| SOL saturation hedge | 67.67% opposing | K708 mitigates K476 |

---

## Files

| File | Description |
|------|-------------|
| `scripts/k708_bnb_sol_run.py` | K708 strategy script (K339 pattern) |
| `scripts/com.cryptolab.k710-bnb-sol.plist` | 62nd daemon plist |
| `wave_k710_k708_scaffold.py` | Scaffold verification script |
| `wave_k710_k708_scaffold.json` | Scaffold results |
| `wave_k710_k708_scaffold.md` | This document |
| `data/k708_dashboard.json` | Runtime dashboard (written by daemon) |
| `report.html` | Updated with K710 badge |

---

## Quick Reference

```bash
# Status check
python3 scripts/k708_bnb_sol_run.py --status

# Dry-run cycle
python3 scripts/k708_bnb_sol_run.py --dry-run

# Rebalance check
python3 scripts/k708_bnb_sol_run.py --rebalance

# Close positions
python3 scripts/k708_bnb_sol_run.py --close "manual exit"

# Scaffold verification
python3 wave_k710_k708_scaffold.py
```

---

*K339 REPO_ROOT pattern | K710 K708 BNB-SOL 62nd daemon scaffold | 2026-05-30 16:35 JST*

# K750 — K747 TAO-SOL Alt-Alt Scaffold (69th Daemon, 15th Alt-Alt, AI L1 × SVM)

*2026-05-30 JST — K750 scaffold wave*

## Executive Summary

K747 TAO-SOL FR Differential: **ACCEPT CONDITIONAL** (28/29 §6 gates PASS).

- **OOS Sharpe: 12.233** (W=168h, zero threshold, ~217d OOS)
- **G4 WF: 12/12 ALL POSITIVE — UNPRECEDENTED** (best WF result in alt-alt family)
- **G8 FAIL**: Bybit TAO 84.6% floor-capped (structural venue noise). K735 HBAR-SOL precedent. HL-only.
- **AVAX cluster bypass**: G5c(AVAX-BTC)=+0.013 PASS vs ONDO-SOL G5c=-0.415 FAIL (AI≠AVAX subnet)
- **TAO = 13th vertex**: MR9 L002 blocks all future TAO-X pairs
- **HL 65.0% AT CAP**: paper-gate strict (K498 OKX activation required for live)
- **K523 central**: $17,210/yr @$10M @4x @2.5% sleeve ($12.9K–$45.3K 3-point range)

## K523 3-Point Projection (@$10M @4x @2.5%)

| Scenario | Annual |
|----------|--------|
| Conservative | $12,907/yr |
| **Central** | **$17,210/yr** |
| Optimistic | $45,289/yr |
| Upper bound | $53,281/yr (NOT central) |

## Key Findings

### TAO vs SOL Economics

TAO (Bittensor AI L1): GPU scarcity cycles (NVDA/H100 AI peaks), Bittensor subnet launch events, institutional AI adoption, compute market pricing. Mean FR **+16.34%/ann**. TAO dominant in ALL quarters (100% of time).

SOL (Solana SVM): Retail meme-coin seasons (BONK/WIF/POPCAT), Firedancer upgrade hype, SOL ETF, SVM DeFi (Jupiter/Drift/Jito). Mean FR **+7.706%/ann** — persistently positive.

### AVAX Cluster Bypass (Key Distinction from K746 ONDO-SOL)

| Metric | ONDO-SOL (K746, BLOCKED) | TAO-SOL (K747, PASS) |
|--------|--------------------------|----------------------|
| G5c AVAX-BTC | -0.4148 **FAIL** | +0.0126 **PASS** |
| G5k AVAX-SOL | -0.5842 **FAIL** | +0.1286 **PASS** |
| Reason | RWA/institutional = AVAX cluster | AI compute ≠ AVAX subnet appchain |

**Insight**: TAO subnets = Bittensor AI model competition (GPU mining, ML training). AVAX subnets = L2-like appchain customization (institutional DeFi). Structurally distinct demand drivers.

### G4 Walk-Forward (UNPRECEDENTED)

All 12 folds positive — no negative fold in entire WF history. First strategy in alt-alt family to achieve 12/12 perfect WF.

Min fold Sharpe: 3.248 (fold 11). All 12 folds well above zero.

### G8 Fail Analysis

Bybit TAO: 84.6% of FR observations at floor (0.0001/0.00005 min tick). Cross-venue diff corr = 0.2651 (below 0.55 threshold). **Not a signal failure** — structural Bybit TAO data quality issue.

Resolution: HL-only deployment (TAO-PERP + SOL-PERP both active on HL, $12.3M/24h volume, maxLeverage=5, asset index=116). K735 HBAR-SOL established exact same G8 precedent → ACCEPT CONDITIONAL.

## Scaffold Components

| Phase | File | Status |
|-------|------|--------|
| Phase 1 | `scripts/k747_tao_sol_run.py` | CREATED |
| Phase 2 | `scripts/com.cryptolab.k747-tao-sol.plist` (69th daemon) | CREATED |
| Phase 3 | `data/leverage_config.json` (K747_TAO_SOL: 4.0) | UPDATED |
| Phase 4 | `scripts/verify_deployment_status.py` (registry +1) | UPDATED |
| Phase 5 | `scripts/emergency_hl_exit.py` (--include-k747 flag) | UPDATED |
| Phase 6 | `docs/k302a_runbook.md` (§67) | UPDATED |
| Phase 7 | `data/k747_dashboard.json` | CREATED |
| Phase 8 | `wave_k750_k747_scaffold.json` | CREATED |
| Phase 9 | `wave_k750_k747_scaffold.md` (this file) | CREATED |
| Phase 10 | `wave_k750_k747_scaffold.py` | CREATED |

## 60d Gate Conditions

All of the following must pass before live deployment:

1. Realized Sharpe ≥ 6 (over 60d paper-trade period)
2. Fill rate ≥ 60%
3. Max drawdown < 15%
4. **K498 OKX activation** (HL concentration must drop below 65.0%)

## TAO Vertex Rule (MR9 L002)

TAO added as **13th vertex** to alt-alt graph V:
```
V = {APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO}
```
All future TAO-X pairs are automatically blocked. TAO-SOL is the only permissible TAO-X pair at K747.

## Next Steps

1. **K498 OKX activation** (HIGH priority): reduces HL% from 65.0%, enabling K747 live deployment
2. **60d paper-trade gate**: monitor `data/k747_dashboard.json` every 8h cycle
3. **WLD-SOL (K748)**: next vertex candidate (WLD biometric, vol_ratio=1.129, cycle_indep=0.720)
4. **PENDLE-SOL (K749)**: yield tokenization candidate (vol_ratio=1.106, cycle_indep=0.807)

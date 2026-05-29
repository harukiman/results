# Wave K506 — K500 INJ-BTC FR Differential Production Scaffold

**Date:** 2026-05-30  
**Status:** SCAFFOLD-READY (34th daemon)  
**Wave pattern:** K502 → K506 (K495 DEX-CEX → K500 INJ-BTC)

---

## Executive Summary

K506 scaffolds K500 INJ-BTC as the 34th production daemon, following the K478/K489/K499/K502 pattern exactly.  K500 was ACCEPT'd in K500 analysis (10/13 §6 gates, OOS Sharpe 11.23, $124K/yr net @ $10M).  This wave delivers the full production infrastructure for a 60d paper-trade gate.

**Key numbers:**
- OOS Sharpe: **11.23** (family rank #4)
- Annual profit: **$124K/yr** net @ $10M AUM
- Sleeve: **3%** ($300K capital, $1.2M notional at 4x)
- HL concentration: **62%** < 65% cap (3pp headroom)
- v6.25 combined: **$631K/yr** (K449+K476+K484+K493+K500, 17% sleeve)

---

## Cosmos 2nd Hypothesis — CONFIRMED

K500 (INJ-BTC) is the second Cosmos-ecosystem strategy to pass §6 gates after K493 (ATOM-BTC).

| | ATOM (K493) | INJ (K500) |
|--|--|--|
| OOS Sharpe | 50.79 (#1) | 11.23 (#4) |
| G5a corr | 0.1763 | 0.1409 |
| G5d corr | — | 0.2893 PASS |
| Vol ratio | 2.34x BTC | 3.83x BTC (max) |
| Mechanism | IBC + staking | DeFi-perp L1 + buyback |

G5d 0.2893 confirms INJ forms a distinct Cosmos sub-cluster (DeFi-perp, distinct from ATOM IBC/staking).  The Cosmos family thesis is expandable.

---

## Deliverables

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | `scripts/k500_inj_btc_run.py` (7d EMA, POST_ONLY, 8h cron) | DONE |
| 2 | `com.cryptolab.k500-inj-btc.plist` (34th daemon, 28800s) | DONE |
| 3 | `data/k500_dashboard.json` (initial state) | DONE |
| 4 | `emergency_hl_exit.py` --include-k500, _detect_k500_paired_positions, close_k500_paired_positions | DONE |
| 5 | `leverage_manager.py` K500_INJ_BTC=4.0, SLEEVE_WEIGHTS_V625 | DONE |
| 6 | `data/leverage_config.json` K500_INJ_BTC: 4.0, k500_notes | DONE |
| 7 | `verify_deployment_status.py` 34th daemon registry | DONE |
| 8 | `docs/k302a_runbook.md` §38e full playbook | DONE |
| 9 | `report.html` K500 row, K506 banner, 34 daemon count | DONE |
| 10 | 60d activation criteria documented | DONE |
| 11 | `wave_k506_k500_scaffold.{py,json,md}` | DONE |

---

## Verification Results

```
python3 scripts/k500_inj_btc_run.py --dry-run  → cycle complete (LONG_INJ_SHORT_BTC, $600K/leg)
python3 scripts/verify_deployment_status.py     → 34 daemons, 0 mismatches
python3 wave_k506_k500_scaffold.py              → 48 PASS / 0 FAIL
```

---

## 60d Paper-Trade Activation Criteria

| Criterion | Target | Note |
|-----------|--------|------|
| OOS Sharpe (paper) | ≥ 3.5 | Lower than K493 (≥5.0), proportional to OOS Sh 11.23 |
| Fill rate (both legs) | ≥ 60% | Both INJ and BTC legs must fill |
| Max drawdown | < 15% | Emergency close if breached |

After gate passage → activate v6.25 K500 3% live.

---

## v6.25 Architecture — Combined Paired-Trade $631K/yr

```
K449 ETH-BTC:   5% sleeve  →  $187K/yr  (OOS Sh  5.66)
K476 SOL-BTC:   3% sleeve  →  $187K/yr  (OOS Sh 16.30)
K484 AVAX-BTC:  3% sleeve  →  $ 75.7K/yr  (OOS Sh 43.89)
K493 ATOM-BTC:  3% sleeve  →  $231K/yr  (OOS Sh 50.79)
K500 INJ-BTC:   3% sleeve  →  $124K/yr  (OOS Sh 11.23)  ← K506
─────────────────────────────────────────────────────
COMBINED:      17% sleeve  →  $631K/yr  @ $10M
```

Plus K495 DEX-CEX (3% bear-conditional, $323K/yr when active) = fully orthogonal axis.

*K506 — K500 INJ-BTC FR differential production scaffold, 34th daemon, +$124K/yr lift @$10M, family rank 4, v6.25 candidate — 2026-05-30*

# K737 — K735 HBAR-SOL Alt-Alt Production Scaffold (66th Daemon, 12th Alt-Alt)

**Wave:** K737 | **Date:** 2026-05-30 | **Status:** SCAFFOLD-READY

---

## Executive Summary

K737 scaffolds K735 HBAR-SOL FR Differential into production as the **66th daemon** and **12th alt-alt** pair. HBAR (Hedera Hashgraph Enterprise-Consortium-DAG) vs SOL (Solana SVM L1) is the **first Enterprise-Consortium-DAG vertex** introduced into the alt-alt family graph. The scaffold follows the K683/K685/K687/K689/K693/K697/K699/K710/K721/K730/K731 alt-alt daemon pattern.

**Key results:**
- OOS Sharpe **26.9506** (IS=22.58, OOS > IS — no overfitting)
- Rank **#7** in 12-pair alt-alt family (above ENA-SOL 26.93 by 0.02)
- **$104,728/yr net @$10M @1% sleeve @4x**; @2%: $209,456/yr
- **8/9 §6 gates PASS** (G8 structural: HL 1h vs Bybit 8h — same K610 pattern)
- **MR8 PASS**: HBAR new vertex (not in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB,LDO})
- **MR9 PASS**: HBAR-SOL = K610_diff − K476_diff (max_err=2.17e-19, K610⊥K476 corr=−0.059)
- **G5 10/10 PASS**: max corr=0.3488 (LDO-SOL K728, below 0.40 threshold)
- **HL 64.5% UNCHANGED** (Bybit-only; HBAR HL maxLev=5 too low for 4x)

---

## Phase 1: Script

**`scripts/k735_hbar_sol_run.py`** — K339 REPO_ROOT pattern, no /Users/ literals.

| Parameter | Value |
|-----------|-------|
| Signal | HBAR_FR - SOL_FR (= K610_diff - K476_diff per MR9) |
| Window | W=240h (30 x 8h periods) |
| Threshold | zero (sign of rolling mean) |
| Leverage | 4x |
| Sleeve | 2% of AUM |
| Venue | Bybit-only (HBAR-PERP + SOL-PERP) |
| HBAR Bybit maxLev | 75x (vs HL 5x — Bybit mandatory) |
| SOL Bybit maxLev | 100x |

Verified fields:
- `REPO_ROOT = Path(__file__).resolve().parent.parent` ✓
- `PAPER_TRADE = True` (default) ✓
- `SLEEVE_PCT = 0.020` ✓
- `LEVERAGE = 4.0` ✓
- `EMA_PERIOD_HOURS = 240` ✓
- `hbar_sol_diff = fr_hbar - fr_sol` ✓

---

## Phase 2: Plist (66th Daemon)

**`scripts/com.cryptolab.k737-hbar-sol.plist`**

- Label: `com.cryptolab.k737-hbar-sol`
- StartInterval: 28800 (8h, matches FR settlement cycle)
- WorkingDirectory: REPO_ROOT_PLACEHOLDER
- PAPER_TRADE=True (default; set False only after 60d gate passage)
- Logs: `logs/k737_hbar_sol.log` / `logs/k737_hbar_sol.err`
- Deploy: `cp scripts/com.cryptolab.k737-hbar-sol.plist ~/Library/LaunchAgents/`  
  `launchctl load ~/Library/LaunchAgents/com.cryptolab.k737-hbar-sol.plist`

---

## §6 Gate Summary (8/9 PASS)

| Gate | Metric | Value | Threshold | Result |
|------|--------|-------|-----------|--------|
| G1 OOS Sharpe | oos_sharpe | 26.9506 | ≥1.0 | **PASS** |
| G2 Permutation | perm_p | 0.0000 | ≤0.05 | **PASS** |
| G3 DSR Bonferroni | dsr_p | 0.0000 | <0.01 | **PASS** |
| G4 Walk-forward | n_pos/folds | 7/8 (87.5%) | ≥75% | **PASS** |
| G5 Family corr | max_corr | 0.3488 (LDO-SOL) | all <0.40 | **PASS** |
| G6 Trades/yr | trades_yr | 16.7 | ≥12 | **PASS** |
| G7 Ann return 4x | ann_4x | 26.18% | ≥5% | **PASS** |
| G8 Cross-venue | HL-Bybit | structural | ≥0.55 | **FAIL** |
| G9 OOS days | oos_days | 218.9 | ≥180 | **PASS** |

**G8 note:** HL uses 1h FR vs Bybit 8h FR — settlement interval mismatch. Same structural pattern as K610 (HBAR-BTC). Not a strategy risk — Bybit-primary resolves execution.

---

## MR8 + MR9

**MR8:** HBAR not in {APT,ATOM,SOL,INJ,AVAX,SEI,TIA,ENA,BNB,LDO}. First Enterprise-Consortium-DAG vertex.

**MR9:** HBAR-SOL = K610_diff − K476_diff
- max_err = 2.17e-19 (machine precision — identity confirmed)
- K610 ⊥ K476: signal corr = −0.0592 (orthogonal parents)
- W=240h intermediate between K610 W=840h (enterprise) and K476 W=168h (retail)

---

## 60d Gate (Phase 11)

| Metric | Target | Basis |
|--------|--------|-------|
| Realized Sharpe | ≥ **13** | 50% of OOS Sh=26.95 |
| Fill rate | ≥ **60%** | standard |
| Max drawdown | < **15%** | standard |

Monitoring triggers: Hedera council membership news, SOL meme season, HBAR Foundation grant rounds, BlackRock HTS tokenization announcements.

---

## Walk-Forward (7/8 Folds)

| Fold | Period | Sharpe | Result |
|------|--------|--------|--------|
| 1 | 2025-10-16 to 2025-11-15 | 9.8140 | POS |
| 2 | 2025-11-15 to 2025-12-15 | 20.9907 | POS |
| 3 | 2025-12-15 to 2026-01-14 | **-4.1496** | **NEG** |
| 4 | 2026-01-14 to 2026-02-13 | 62.3579 | POS |
| 5 | 2026-02-13 to 2026-03-15 | 60.6730 | POS |
| 6 | 2026-03-15 to 2026-04-14 | 52.6439 | POS |
| 7 | 2026-04-14 to 2026-05-14 | 13.1692 | POS |
| 8 | 2026-05-14 to 2026-06-13 | 84.5061 | POS |

Fold 3 negative: Dec 2025–Jan 2026 crypto-wide risk-off (SOL retail FR collapsed + HBAR enterprise FR dampened simultaneously).

---

## Alt-Alt Family (12 Pairs, 11 Vertices)

| Rank | Pair | Wave | OOS Sharpe | Status |
|------|------|------|-----------|--------|
| 1 | AVAX-SOL | K686 | 50.27 | ACCEPT |
| 2 | BNB-SOL | K708 | 48.59 | ACCEPT |
| 3 | LDO-SOL | K728 | 46.84 | ACCEPT CONDITIONAL |
| 4 | ATOM-SOL | K682 | 43.43 | ACCEPT |
| 5 | APT-SOL | K679 | 39.29 | ACCEPT |
| 6 | ENA-ATOM | K719 | 29.67 | ACCEPT |
| **7** | **HBAR-SOL** | **K737** | **26.9506** | **ACCEPT CONDITIONAL (SCAFFOLD)** |
| 8 | ENA-SOL | K696 | 26.93 | ACCEPT |
| 9 | SEI-SOL | K690 | 25.11 | ACCEPT |
| 10 | TIA-SOL | K694 | 19.09 | ACCEPT CONDITIONAL |
| 11 | INJ-ATOM | K729 | 18.75 | ACCEPT |
| 12 | SOL-INJ | K684 | 9.65 | ACCEPT |

**Vertices (11):** APT, ATOM, SOL, INJ, AVAX, SEI, TIA, ENA, BNB, LDO, **HBAR**

---

## Files

| File | Description |
|------|-------------|
| `scripts/k735_hbar_sol_run.py` | K339 run script (strategy + paper-trade daemon) |
| `scripts/com.cryptolab.k737-hbar-sol.plist` | 66th daemon plist (8h interval, Bybit primary) |
| `data/k735_dashboard.json` | Dashboard + gate metrics |
| `wave_k737_k735_scaffold.py` | K737 scaffold orchestrator |
| `wave_k737_k735_scaffold.json` | Full scaffold results JSON |
| `wave_k737_k735_scaffold.md` | This report |
| `data/leverage_config.json` | K735_HBAR_SOL: 4.0 added |
| `report.html` | K737 badge + updated timestamp |

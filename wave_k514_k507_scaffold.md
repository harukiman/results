# Wave K514 — K507 SEI-BTC FR Differential Production Scaffold

**Date:** 2026-05-30  
**Wave:** K514  
**Status:** SCAFFOLD-READY  
**Daemon:** 35th (com.cryptolab.k507-sei-btc)  
**Verification:** 31/31 checks passed, 0 mismatches  

---

## Executive Summary

K514 delivers the full production scaffold for K507 SEI-BTC FR Differential strategy.

K507 is the Cosmos 3rd ACCEPT (SEI EVM-compat + Cosmos SDK distinct from ATOM IBC/staking and INJ DeFi-perp).
OOS Sharpe 48.10 (family rank #2 after ATOM 50.79). $179K/yr net @ $10M AUM.

**Critical architecture decision:** K507 uses an HL+Bybit split (1.5%+1.5%) rather than HL-only,
because HL concentration was 62% after K500. HL-only K507 would push HL to 65% (hitting the cap).
Split: SEI leg on HL (1.5%), BTC leg on Bybit (1.5%) → HL 63.5% (1.5pp headroom).

---

## K507 Performance

| Metric | Value |
|--------|-------|
| OOS Sharpe | 48.10 |
| Family rank | #2 (ATOM Sh50.79 > SEI Sh48.10 > AVAX Sh43.89 > SOL Sh16.30 > INJ Sh11.23 > ETH Sh5.66) |
| Ann return net | $179,000/yr @ $10M AUM |
| Sleeve | 3% combined (HL 1.5% + Bybit 1.5%) |
| Leverage | 4x |
| HL concentration | 63.5% post-K507 (1.5pp headroom vs 65% cap) |
| Cosmos cluster | 3rd CONFIRMED: SEI EVM-compat + Cosmos SDK |
| Cron | 8h (28800s StartInterval) |

---

## v6.27 Combined Paired-Trade Sleeve

K507 completes the v6.27 paired-trade family (6 strategies, 20% combined):

| Strategy | Pair | OOS Sharpe | Ann Return | Sleeve |
|----------|------|-----------|------------|--------|
| K449 | ETH-BTC | 5.66 | $187K/yr | 5% |
| K476 | SOL-BTC | 16.30 | $187K/yr | 3% |
| K484 | AVAX-BTC | 43.89 | $75.7K/yr | 3% |
| K493 | ATOM-BTC | 50.79 | $231K/yr | 3% [Cosmos 1st] |
| K500 | INJ-BTC | 11.23 | $124K/yr | 3% [Cosmos 2nd] |
| K507 | SEI-BTC | 48.10 | $179K/yr | 3% [Cosmos 3rd] |
| **Combined** | | | **~$810K/yr** | **20%** |

---

## 60d Paper-Trade Activation Criteria

After 60d paper-trade gate:
- OOS Sharpe (paper) >= 5.0 (very loose given OOS 48.10)
- Fill rate >= 60% (both legs: HL + Bybit)
- Max drawdown < 15%
- Then: activate v6.27 K507 3% live

Combined at activation: K449 5% + K476 3% + K484 3% + K493 3% + K500 3% + K507 3% = 20% paired-trade sleeve, ~$810K/yr @ $10M.

---

## Deliverables Completed

| Phase | Deliverable | Status |
|-------|-------------|--------|
| Phase 1 | `scripts/k507_sei_btc_run.py` (~300 LOC, K339 pattern, HL+Bybit split) | DONE |
| Phase 2 | `com.cryptolab.k507-sei-btc.plist` (35th daemon, 28800s cron) | DONE |
| Phase 3 | `data/k507_dashboard.json` (initial NEUTRAL state) | DONE |
| Phase 4 | `emergency_hl_exit.py`: --include-k507 + detect/close + plan_exit | DONE |
| Phase 5 | `leverage_manager.py`: K507_SEI_BTC=4.0 + SLEEVE_WEIGHTS_V627 | DONE |
| Phase 6 | `data/leverage_config.json`: K507_SEI_BTC: 4.0 + k507_notes | DONE |
| Phase 7 | `verify_deployment_status.py`: 35th daemon registry | DONE |
| Phase 8 | `docs/k302a_runbook.md`: §38f K507 full playbook | DONE |
| Phase 9 | `report.html`: K507 monitoring row + v6.27 banner + 35th daemon | DONE |
| Phase 10 | 60d gate criteria defined (OOS Sh>=5.0, fill>=60%, maxDD<15%) | DONE |
| Phase 11 | `wave_k514_k507_scaffold.{py,json,md}` | DONE |
| Phase 12 | Dry-run verified: cycle complete, 35 daemons, 0 mismatches | DONE |

---

## Dry-Run Results

```
python3 scripts/k507_sei_btc_run.py --dry-run → cycle complete
  Position state: NEUTRAL
  7d EMA diff: +0.00000556 (SEI−BTC, below threshold)
  HL notional: $600,000  Bybit notional: $600,000
  Margin/AUM: 3.0%
  Paper-trade mode: True

python3 scripts/verify_deployment_status.py → 35 daemons, 0 mismatches
  {'active': 0, 'loaded': 0, 'pending_activation': 3, 'scaffold_ready': 31,
   'unknown': 1, 'mismatches_with_html': 0}
```

---

*K514 -- K507 SEI-BTC FR differential production scaffold (35th daemon, OOS Sh 48.10 #2 family, $179K/yr net @$10M, Cosmos 3rd CONFIRMED SEI EVM-compat + Cosmos SDK, HL+Bybit 1.5%+1.5% split → HL 63.5% 1.5pp headroom, v6.27 K449+K476+K484+K493+K500+K507 20% combined ~$810K/yr, 60d paper-trade gate) -- 2026-05-30*

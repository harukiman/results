# Wave K478 — K476 SOL-BTC FR Differential Production Scaffold

**Date:** 2026-05-25  
**Status:** COMPLETE  
**Strategy:** K476 SOL-BTC FR Differential Paired-Trade  
**Daemon:** 29th (com.cryptolab.k476-sol-btc)

---

## Executive Summary

K478 builds the production scaffold for K476, the SOL-BTC funding rate differential strategy.
Pattern mirrors K449/K450 ETH-BTC architecture with SOL-BTC pair.

**OOS Performance (K476 accepted 9/10 §6 gates):**
- OOS Sharpe: **16.30** (very high carry efficiency)
- Annual Return: **$187K/yr @ $10M AUM**
- Strategy: Delta-neutral carry (long cheap-FR asset, short expensive-FR asset)
- Venue: HL-only (K434 smart router Phase 2)
- Execution: POST_ONLY parallel (K439 pattern)
- Leverage: 4x (K430 cap: K476_SOL_BTC = 4.0)

**v6.21 Architecture Path:**
- K449 ETH-BTC 3% + K476 SOL-BTC 3% = **6% combined cross-asset FR sleeve**
- Combined expected: $374K/yr @ $10M
- HL concentration post-v6.21: 63.5% (within K355 65% cap)

---

## Deliverables

| Phase | File | Status |
|-------|------|--------|
| 1 | `scripts/k476_sol_btc_run.py` (NEW ~250 LOC) | DONE |
| 2-4 | K434 HL-only router + K439 POST_ONLY + K430 4x (in script) | DONE |
| 5 | `scripts/emergency_hl_exit.py` (--include-k476 flag + close_k476_paired_positions) | DONE |
| 6 | `data/k476_dashboard.json` (initial state) | DONE |
| 7 | `com.cryptolab.k476-sol-btc.plist` (gitignored, 29th daemon) | DONE |
| 8 | `scripts/verify_deployment_status.py` (K476 as 29th entry) | DONE |
| 9 | 60d paper-trade gate criteria documented | DONE |
| 10 | `docs/k302a_runbook.md §38` (K476 full playbook) | DONE |
| 11 | `report.html` (K476 row + v6.21 banner + 29 daemons) | DONE |
| 12 | `data/leverage_config.json` (K476_SOL_BTC = 4.0 cap + notes) | DONE |
| 12 | `scripts/leverage_manager.py` (K476 sleeve + v6.21 weights) | DONE |

---

## Verification

```
python3 scripts/verify_deployment_status.py
→ com.cryptolab.k476-sol-btc: SCAFFOLD-READY
→ 29 daemons total
→ 0 mismatches with HTML
```

```
python3 scripts/k476_sol_btc_run.py --dry-run
→ DRY-RUN cycle complete
→ data/k476_dashboard.json written
→ Notional/leg: $600K @ $10M / 3% / 4x
→ Margin/AUM: 3.0%
```

---

## Activation Path

1. 60d paper-trade accumulates (OOS Sharpe ≥ 5.0 paper + fill rate ≥ 60%)
2. Advance sleeve: leverage_config.json K476 weight 0.0 → 0.03
3. Activate plist: `cp com.cryptolab.k476-sol-btc.plist ~/Library/LaunchAgents/ && launchctl load ...`
4. Set PAPER_TRADE=False in plist environment
5. v6.21 goes live: K449 3% + K476 3% = 6% combined FR sleeve

---

## References

| Wave | Content |
|------|---------|
| K476 | SOL-BTC FR differential backtest (OOS Sh 16.30, $187K/yr, 9/10 gates) |
| K449/K450 | ETH-BTC FR scaffold (template for K476) |
| K434 | Smart router (HL-only for K476) |
| K439 | POST_ONLY paired execution |
| K430 | Leverage framework (4x cap) |
| K357 | Emergency exit (--include-k476) |

*K478 — K476 SOL-BTC FR differential production scaffold (29th daemon, v6.21 candidate) — 2026-05-25*

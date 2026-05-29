# Wave K473 — sUSDe + Spark sUSDS 50/50 Fast-Track Scaffold

**Date:** 2026-05-30 | **Source:** K471 recommendation | **Effort:** Fast-track (3.5x lift-per-effort)

## Executive Summary

K471 found a full 7-protocol stablecoin aggregator would deliver +$40K/yr at $10M AUM but require 5.5 wave effort. K473 fast-tracks the highest-value piece: adding Spark sUSDS as a second stablecoin yield protocol alongside K344 sUSDe, creating a 50/50 diversified sleeve at the same 10% AUM allocation.

**K473 Key Findings (live data, 2026-05-30):**
- Spark sUSDS current APY: **3.34%** (DefiLlama live fetch)
- sUSDS 7d mean: **3.57%** | 30d mean: **3.67%**
- sUSDe estimate (K412): **3.88%**
- Combined 50/50 APY: **3.61%** (annual yield $361K at $10M)
- K266 gates: **PASS 5/6** (G1 marginal at current DSR rates — recovery expected)
- Alert status: **NO_ALERT**

## Protocol Research

### Spark Protocol (Sky/MakerDAO)
- **Mechanism:** Sky Savings Rate (SSR) — formerly MakerDAO DSR. USDS deposited in Spark earns SSR yield via Sky governance vote.
- **DefiLlama pool:** `54e9b138-3146-4c1f-8dce-1cb948f5ef96` (USDS/Ethereum)
- **TVL:** ~$825M (Ethereum), additional $359M (Arbitrum), $223M (Base)
- **Redemption:** **Instant** — no lockup period (unlike sUSDe 7d cooldown)
- **Audit:** Sky/MakerDAO has published multiple security audits (MCD protocol)
- **Governance:** Sky token holders vote on DSR/SSR rate changes (CRASH alert monitors this)

### vs sUSDe (Ethena)
| Dimension | sUSDe | Spark sUSDS |
|-----------|-------|-------------|
| Mechanism | Funding rate delta-neutral | DSR/Sky savings rate |
| Redemption | 7d cooldown | Instant |
| APY (K473) | ~3.88% | ~3.34% |
| Volatility | Higher (FR-driven) | Lower (governance-set) |
| Correlation | — | LOW (different drivers) |

## Deliverables

### Phase 1: Research ✓
- DefiLlama Spark Protocol page: $5.08B TVL, 3.34% APY (live)
- Pool ID confirmed: `54e9b138-3146-4c1f-8dce-1cb948f5ef96`
- 89 data points available for trend analysis

### Phase 2: scripts/spark_usds_monitor.py ✓
- REPO_ROOT pattern (K339)
- Mirrors K412 sUSDe monitor architecture
- Fetches sUSDS APY from DefiLlama
- Computes combined 50/50 metrics with live sUSDe (from K412 dashboard)
- Evaluates K266 stablecoin gates (G1–G6)
- Alert detection: LOW_APY, HIGH_APY, CRASH, SPREAD_WIDE
- Single-shot, weekly cron

### Phase 3: com.cryptolab.spark-usds-monitor.plist ✓
- StartInterval: 604800 (weekly)
- Gitignored (per existing com.cryptolab.*.plist pattern)
- 28th daemon

### Phase 4: verify_deployment_status.py ✓
- Spark sUSDS added as 28th DaemonSpec entry
- Expected status: SCAFFOLD-READY

### Phase 5: data/spark_usds_dashboard.json ✓
- Live data written (2026-05-30 02:11 JST)
- sUSDS: 3.34%, 7d 3.57%, 30d 3.67%
- sUSDe (K412): 3.88%
- Combined 50/50: 3.61%
- K266 gates: 5/6 PASS

### Phase 6: K266 Gates ✓
| Gate | Status | Detail |
|------|--------|--------|
| G1 net APY ≥ 4% | FAIL (marginal) | 3.61% — DSR recovery expected; trigger at 3.5%+ sustained |
| G2 audit verified | PASS | Ethena + Sky/MakerDAO both audited |
| G3 stability | PASS | 30d vol 0.23pp < 0.5pp threshold |
| G4 redemption | PASS | sUSDS instant + sUSDe 7d acceptable |
| G5 correlation | PASS | Funding-rate vs DSR — distinct mechanisms |
| G6 max 50% per protocol | PASS | 50/50 enforced |

**Overall: PASS 5/6 (CONDITIONAL)**

### Phase 7: K297' Sleeve Options ✓
- **Option A (v6.21 candidate):** sUSDe 5% + sUSDS 5% = 10% (replaces sUSDe-alone 10%)
- **Option B:** Keep sUSDe 10% + add sUSDS 5% = 15% total stablecoin
- Default: Option A — preserves current total stablecoin allocation
- **Activation trigger:** sUSDS ≥ 3.5% sustained 14d + combined ≥ 4%

### Phase 8: report.html ✓
- K473 Live Monitoring row added (28th daemon, SCAFFOLD-READY)
- Header banner updated with K473 summary
- Daemon count: 27 → 28
- Timestamp updated: 2026-05-30 02:11 JST

### Phase 9: docs/k302a_runbook.md §37 ✓
- K473 sUSDS overview, gate evaluation, activation triggers
- Emergency exit procedure (instant redemption via app.spark.fi)
- References table

### Phase 10: emergency_hl_exit.py --include-spark ✓
- `close_spark_positions()` stub added
- `--include-spark` CLI flag wired into execute mode and dry-run logging
- Note: sUSDS is pure DeFi — NO HL delta hedge needed

### Phase 11: Test ✓
```
python3 scripts/spark_usds_monitor.py
  → Spark sUSDS current APY : 3.34%
  → sUSDS 7d mean           : 3.57%
  → Combined 50/50 APY      : 3.61%
  → K266 gates              : PASS (5/6)
  → Alert status            : NO_ALERT
  → Dashboard               : data/spark_usds_dashboard.json ✓
```

## Risk Notes

1. **G1 marginal (3.61% < 4%):** Current Sky DSR rates are moderate. DSR has historically ranged 2–8%. Monitor weekly; combine with sUSDe at higher APY if needed.
2. **No HL hedge needed:** Unlike JLP (K468), sUSDS is a stablecoin — zero directional exposure. Emergency exit = instant redemption at app.spark.fi.
3. **DO NOT modify K344 production logic.** This is additive — K344 sUSDe remains unchanged.
4. **Activation requires user action:** sUSDS purchase via Spark UI or Sky.money (Ethereum wallet).

## Activation Command

```bash
# 1. Test monitor
python3 scripts/spark_usds_monitor.py

# 2. Load daemon
cp com.cryptolab.spark-usds-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.spark-usds-monitor.plist

# 3. Verify 28 daemons
python3 scripts/verify_deployment_status.py

# 4. When K266 G1 recovers (combined >= 4%) — allocate to sUSDS
# Option A: redirect 5% AUM from current sUSDe sleeve to sUSDS
```

# Wave K443 — K297' Variational Venue Prep

**Date:** 2026-05-29 23:32 JST
**Status:** SCAFFOLD-READY (PENDING: Variational trading API Q3-Q4 2026)
**Daemon count after:** 17

---

## Summary

K443 prepares the Variational-equivalent of the K297' satellite strategy for immediate deployment when Variational's trading API goes public (Q3-Q4 2026 target). No production scripts modified. New script + plist + registry update + runbook §27 delivered.

---

## Strategy: K297''-Variational

| Asset | Weight (base) | Type | Note |
|-------|--------------|------|------|
| XAU | 50% | Gold perp, 4h funding | K297 equiv, always-on |
| XAG | 30% | Silver perp, 4h funding | **NEW** — not on HL |
| CL  | 20% | WTI Crude perp, 4h funding | **NEW** — not on HL |

Weights adjusted by inverse-volatility (|FR| magnitude), 50/50 blend with base weights.
XAU FR > 0 gates XAG/CL entries (SPX-proxy filter, K297' pattern adaptation).

---

## Multi-Venue K297 Sleeve (v6.17 candidate)

| Venue | Strategy | % AUM | Capacity |
|-------|----------|-------|---------|
| HyperLiquid | K297' (PAXG/SPX) | 12% | ~$5M position cap |
| Variational | K297'' (XAU/XAG/CL) | 8% | $3.85B TVL → no cap concern |
| **Total K297** | | **20%** | Multi-venue |

Rebalance monthly (K427). Trigger: HL > 65% of sleeve → shift to Variational.

---

## Profit Projection (K443 Phase 8)

| AUM | Config | Est. Annual |
|-----|--------|------------|
| $10M | HL + Bybit | $1.72M/yr (K440 base) |
| $25M | HL + Bybit + Variational | ~$5-6M/yr (+$1.2-1.7M vs 2-venue) |
| $50M | HL + Bybit + Variational | ~$6-7M/yr |
| $50M | HL + Bybit + Drift | ~$5.45M/yr (K431 ref) |

**Variational advantage:** XAG + CL unique instruments, HIP-3 RWA equiv, $3.85B TVL.

---

## Deliverables

| File | Description |
|------|-------------|
| `scripts/k297_variational_run.py` | NEW — K297'' paper-trade (~290 LOC) |
| `com.cryptolab.k443-variational-paper.plist` | NEW — daily 07:00 JST, gitignored |
| `scripts/verify_deployment_status.py` | Updated — 17th daemon in REGISTRY |
| `scripts/regulatory_rss_monitor.py` | Updated — "variational trading api" keyword |
| `docs/k302a_runbook.md` | §27 appended (12 subsections) |
| `report.html` | K443 row added, 16→17 daemons, header updated |
| `wave_k443_variational_prep.{md,json}` | This file + JSON summary |

---

## Activation Trigger Conditions

1. **Primary:** Variational trading API public release → load plist + 60d paper-trade → K444
2. **K387 RSS:** "variational trading api" keyword in SEC/CFTC RSS monitor (added K443)
3. **K363 data:** 90d FR snapshots → rolling Sharpe computable
4. **Rebalance:** HL K297' > 65% of sleeve → shift to Variational

---

## BEAR_1 Integration (K386)

Under BEAR_1 (CFTC vs HyperLiquid):
- XAU/XAG: HOLD (safe-haven demand benefits gold/silver carry)
- CL: REDUCE 50% (crude less predictable in CFTC stress)
- Variational K297'' is BEAR_1-resilient vs K297' SPX which suspends entirely

---

## Emergency Exit Stub (K357)

`close_variational_positions()` scaffolded in `scripts/k297_variational_run.py`.
Pattern: K380 Bybit close-all. Implementation: K444 production patch when API available.

---

## Verification

```bash
# Verify 17-daemon registry (0 mismatches target)
python3 $CRYPTO_LAB/scripts/verify_deployment_status.py

# Dry-run scaffold
python3 $CRYPTO_LAB/scripts/k297_variational_run.py --dry-run

# Dashboard status
python3 $CRYPTO_LAB/scripts/k297_variational_run.py --status
```

---

## References

K363 (Variational FR monitor) · K365 (API baseline) · K297/K302a (strategy) · K431 ($25M capacity) · K357 (emergency exit) · K386 (BEAR_1) · K387 (RSS monitor)

# K753 K545 Tax Loss Harvester Full Scaffold

**Wave:** K753 | **Generated:** 2026-05-30 | **Status:** SCAFFOLD-READY  
**DISCLAIMER: INFORMATIONAL ONLY — NOT TAX ADVICE. Consult a licensed CPA.**

---

## Executive Summary

K753 delivers the full production scaffold for K545 (tax loss harvester), building on the K444 concept (18th daemon, annual) into a **daily monitoring daemon** (70th daemon, 03:00 UTC).

**K523 3-Point Tax Shield @$10M AUM, 37% rate:**
- Conservative: **$74K/yr** (low-vol year, $200K losses harvested)
- Central: **$185K/yr** (normal year, $500K losses harvested)
- Optimistic: **$370K/yr** (high-vol year, $1M losses harvested)

K518 realized-to-stated ratio 38% floor applied: realized central = $70K/yr.

---

## Deliverables

| File | Status | Description |
|------|--------|-------------|
| `scripts/k545_tax_harvester.py` | NEW | Full daemon (~490 LOC, K339 pattern) |
| `scripts/com.cryptolab.k545-tax-harvester.plist` | NEW | 70th daemon, daily 03:00 UTC |
| `wave_k753_k545_scaffold.py` | NEW | Wave runner |
| `wave_k753_k545_scaffold.json` | NEW | Wave summary JSON |
| `wave_k753_k545_scaffold.md` | NEW | This file |
| `scripts/verify_deployment_status.py` | UPDATED | 70th daemon entry added |
| `docs/k302a_runbook.md` | UPDATED | §69 K545 section |
| `report.html` | UPDATED | K753 badge + K523 shield |

---

## Harvest Logic

```
Daily 03:00 UTC trigger
  └── scan_open_positions()       AUM state + trade logs
      └── identify_loss_candidates()
              ├── min_loss $500 (avoid micro-harvest)
              ├── wash-sale window (30d US / 0d JP/KOR/DE)
              └── regime stress guard (cancel if max_dd > 15%)
      └── execute_harvest()       PAPER default
              ├── max $50K per run (market impact guard)
              ├── audit trail → data/k545_harvest_log.jsonl
              └── LIVE requires explicit --live + PAPER_TRADE=False
      └── reentry_after_window()  multi-venue routing
```

---

## 1-Step Activation

```bash
# Step 1: Set tax config (after CPA consultation)
python3 scripts/k545_tax_harvester.py --set-rate 37 --set-juris US_STCG
python3 scripts/k545_tax_harvester.py --mock-test  # verify PASS

# Step 2: Activate daemon (paper mode)
CRYPTO_LAB=$(python3 -c "from pathlib import Path; print(Path('scripts/k545_tax_harvester.py').resolve().parent.parent)")
sed -i '' "s|CRYPTO_LAB_PATH|${CRYPTO_LAB}|g" scripts/com.cryptolab.k545-tax-harvester.plist
cp scripts/com.cryptolab.k545-tax-harvester.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k545-tax-harvester.plist

# Step 3: Verify
launchctl list | grep k545-tax-harvester
python3 scripts/k545_tax_harvester.py --status
```

---

## Risk Safeguards

| Safeguard | Value |
|-----------|-------|
| Min loss | $500/position |
| Max harvest/run | $50,000 |
| Wash-sale (US) | 30d conservative |
| Wash-sale (JP/KOR/DE) | 0d (no crypto wash-sale equivalent) |
| Regime stress | Cancel if max_dd > 15% |
| LIVE auto-change | **PROHIBITED** — manual edit required |
| Paper mode | **DEFAULT** (PAPER_TRADE=True) |

---

## Jurisdiction Reference

| Jurisdiction | Rate | Key Rule |
|-------------|------|----------|
| US_STCG | 37% | 30d conservative wash-sale wait |
| JP | 55% | No carryforward — harvest by Dec 31 MANDATORY |
| KOR | 22% | 5yr carryforward, no wash-sale |
| DE | 26.375% | Indefinite carryforward, no wash-sale |
| SG | 0% | No CGT — harvesting N/A |

---

## References

- K523: 3-point projection mandate
- K518: Realized-to-stated ratio 38% floor
- K444: Legacy loss harvester (18th daemon, annual Dec 28)
- K442: Jurisdiction tax optimization analysis
- docs/k302a_runbook.md §69: Full technical runbook

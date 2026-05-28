# K368 HIP-4 Calibration — WAVE RESERVED
**Status:** RESERVED — execution scheduled 2026-06-22  
**Original placeholder created:** K409 (2026-05-29)  
**Target date:** 2026-06-22 (adjusted from 2026-06-10 per K409 / K408 math)  
**Predecessor:** K395 (calibration prep + K368 design)

> **DO NOT execute this wave before 2026-06-22.**
> This placeholder reserves the K368 wave number for the HIP-4 BTC recurring calibration analysis.

---

## Reservation Rationale

K368 was originally reserved for HIP-4 calibration at 2026-06-10. K408 determined this was infeasible (N=14 BTC daily outcomes unreachable in 12 days with daemon not loaded). K409 pushed the target to 2026-06-22 (24-day window, N=23 possible, 9-day buffer).

The wave number K368 is **dedicated to the HIP-4 calibration**. Do not reassign it to unrelated topics.

---

## Expected Data State on 2026-06-22

### If daemon activated (best case)

| Item | Expected Value |
|------|---------------|
| Snapshots in cache/hl_hip4_snapshots/ | ~6,912 (288/day × 24 days) |
| BTC daily resolution events | N ≈ 23 |
| K368 decision gate eligible | ACCEPT / WATCH / MONITOR |
| CPI May resolution (2026-06-10) | ✓ Captured (12 days before K368) |
| FOMC June resolution (2026-06-18) | ✓ Resolved 4 days before K368 |

### If manual fetch only (fallback)

| Item | Expected Value |
|------|---------------|
| Snapshots in cache/hl_hip4_snapshots/ | ~24 (1/day manual) |
| BTC daily resolution events | N ≈ 23 (if run daily) |
| K368 decision gate eligible | ACCEPT / WATCH / MONITOR (if N=23) |

### If daemon never activated + no manual fetch

| Item | Expected Value |
|------|---------------|
| Snapshots in cache/hl_hip4_snapshots/ | 4 (existing from K356/K395) |
| BTC daily resolution events | N = 0 (no new snapshots) |
| K368 decision gate eligible | INCONCLUSIVE → K450+ |
| K368 value | CPI single-event Brier only (N=1 per bucket) |

---

## Analysis Structure (K395 Phase 6 Design)

### Phase 1: Data Load
```python
from pathlib import Path
import pandas as pd

snaps = sorted(Path("cache/hl_hip4_snapshots").glob("*.parquet"))
df = pd.concat([pd.read_parquet(p) for p in snaps]).sort_values("ts_ms")
print(f"Total snapshots: {len(snaps)}")
print(f"Date range: {pd.to_datetime(df.ts_ms.min(), unit='ms')} → {pd.to_datetime(df.ts_ms.max(), unit='ms')}")
```

### Phase 2: BTC Recurring Daily Calibration
- Target coin: `#1050` (Yes side), daily settlement at 06:00 UTC
- For each settlement day: extract last `mid_price` before 06:00 UTC
- Compute `outcome_binary` = 1 if BTC mark ≥ target_price, else 0
- Metrics: Brier score, log loss, 10-bin calibration curve, calibration_gap_pct

### Phase 3: CPI Single-Event Accuracy
- May 2026 CPI YoY BLS release: 2026-06-10T12:30 UTC
- Compare K356 implied probs (Below 36.8%, Exactly 43.7%, Above 22.9%) vs actual
- Compute single-event Brier per bucket

### Phase 4: FOMC Cross-Venue Check
- FOMC June resolution: 2026-06-18
- By K368 (2026-06-22): FOMC outcome is known 4 days prior
- Fetch final HL `#1041` price pre-resolution vs Polymarket closing price
- Compute spread vs K353 baseline (0.0035)

### Phase 5: Secondary Market Check
- UCL Final (resolved ~2026-05-31): PSG vs Arsenal — historical Brier check
- Compare K356 PSG price (57.8%) vs actual result

### Phase 6: Decision Gate + Output
```
N ≥ 14 AND gap > 3%    → ACCEPT  → K369 trade prototype
N ≥ 14 AND 1% ≤ gap ≤ 3% → WATCH → extend +14 days, K380
N ≥ 14 AND gap < 1%    → MONITOR → no edge, continue collecting
10 ≤ N < 14            → INCONCLUSIVE_DIRECTIONAL → trend hypothesis, K380+
N < 10                 → INCONCLUSIVE → K450+ recheck, mandatory daemon activation
```

---

## Pre-Wave Checklist (Run on 2026-06-22)

- [ ] Confirm snapshot count: `ls cache/hl_hip4_snapshots/ | wc -l`
- [ ] Confirm N BTC outcomes available: run Phase 1 + 2 script
- [ ] Confirm CPI May 2026 actual value (BLS release 2026-06-10)
- [ ] Confirm FOMC June 2026 decision (2026-06-18 outcome)
- [ ] Confirm UCL Final result (resolved before 2026-06-01)
- [ ] Confirm BTC price at each 06:00 UTC settlement (check HL mark price logs)
- [ ] Run `python3 wave_k368_hip4_calibration.py` (to be created at wave time)

---

## Deliverables (to create on 2026-06-22)

- `wave_k368_hip4_calibration.py` — computation script
- `wave_k368_hip4_calibration.json` — metrics, decision, cross-venue results
- `wave_k368_hip4_calibration.md` — 200–300 line structured report

---

## History

| Wave | Date | Event |
|------|------|-------|
| K353 | 2026-05-24 | HIP-4 prediction market MONITOR (cross-venue <2%) |
| K356 | 2026-05-26 | HIP-4 daemon scaffold, 3 test snapshots collected |
| K360 | ~2026-05-27 | Daemon status verification — NOT activated |
| K395 | 2026-05-29 | Calibration prep, fallback plan, K368 design |
| K408 | 2026-05-29 | Math feasibility: N=11 at 2026-06-10 → INCONCLUSIVE |
| **K409** | **2026-05-29** | **Target adjusted → 2026-06-22, INCONCLUSIVE_DIRECTIONAL added** |
| K368 | **2026-06-22** | **RESERVED — actual calibration analysis executes here** |

---

*K368 wave number reserved by K409. Execute on 2026-06-22.*

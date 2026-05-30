# K726 — MR12 K376 Trigger Methodology Memory Rule Formalization

**Wave:** K726  
**Task:** Formalize MR12 (Memory Rule 12) for K376 BULL_CONFIRMED trigger  
**Status:** COMPLETE  
**Timestamp:** 2026-05-30 17:45 JST  
**Pattern:** K339 REPO_ROOT

---

## Executive Summary

K726 formalizes the authoritative K376 BULL_CONFIRMED trigger methodology (MR12) based on K497 daemon authority. The rule is:

| Component | Value |
|-----------|-------|
| **Sole authority** | K497 daemon (`scripts/k376_regime_trigger_monitor.py`, 31st daemon) |
| **Formula** | `(SMA_20d_today - SMA_20d_20d_ago) / 20` (slope in USD/day) |
| **Threshold** | slope >= 0.0 |
| **Duration** | 7 consecutive calendar days |
| **Status allowed** | INDETERMINATE (no ETA when slope < 0) |
| **Invalid methodologies** | K577 (first-order), K680 (hardcoded), K720 (category error) |

---

## Phase 1: K497 Daemon Authority

### Source of Truth

```
Script:          scripts/k376_regime_trigger_monitor.py
Daemon index:    31 (registered in verify_deployment_status.py)
Config:          com.cryptolab.k376-regime-monitor.plist
Monitoring file: data/k376_regime_status.json
Update interval: 28800s (8 hours, via launchctl)
Data source:     BTC/USDT spot candles (HyperLiquid primary, Bybit secondary)
```

### Formula Specification

```python
# K497 canonical formula (MR12 source):
closes = [float(c[4]) for c in candles[-40:]]  # 40 most recent closes
sma_today = sum(closes[-20:]) / 20              # SMA of last 20 days
sma_20d_ago = sum(closes[-40:-20]) / 20         # SMA of 20-40 days ago
slope = (sma_today - sma_20d_ago) / 20          # Rate of change (USD/day)
```

**Interpretation:**
- slope > 0: 20d SMA is rising (bullish acceleration)
- slope = 0: Flat momentum
- slope < 0: 20d SMA is falling (bearish deceleration)

---

## Phase 2: BULL_CONFIRMED Criterion (MR12 Rule)

**K376 derivatives-long activation** requires ALL of:

1. **Slope threshold:** `slope >= 0.0 USD/day`
2. **Duration:** slope maintained for **7 consecutive calendar days**
3. **Counter:** `days_slope_positive` in K497 regime file must be >= 7

### Valid States

| Regime | Condition | K376 Status |
|--------|-----------|------------|
| BULL_CONFIRMED | slope >= 0 AND days_positive >= 7 | ACTIVATE |
| IN_PROGRESS | slope >= 0 AND days_positive < 7 | Countdown (e.g., 3/7 days) |
| TRANSITION | slope < 0 AND days_positive = 0 | Regime changing, monitor |
| BEAR | slope < -50 AND stable | DEFENSIVE (K280 active) |

---

## Phase 3: Status = INDETERMINATE (No False Promises)

When slope < 0, **no ETA projection is allowed.** K723 experience shows:

| Wave | ETA claimed | Reality | Issue |
|------|------------|---------|-------|
| K577 | 5 days | turned negative next day | stale snapshot |
| K680 | 14 days | math gave 72d, hardcoded | unsupported label |
| K720 | 622 days | 4.8x metric mismatch | category error |

**MR12 rule:** Status `INDETERMINATE` is valid and honest. Do not project ETA until slope crosses 0 with trend support.

---

## Phase 4: Why Other Methodologies Are Invalid

### K577 (First-Order SMA)
- **Formula:** `SMA_today - SMA_yesterday`
- **Issue:** Single-day derivative is noisy; misses 20d smoothing intent
- **Result:** Called 5-day turnaround that reversed next day

### K680 (Hardcoded Label)
- **Formula:** K497-correct, but `eta_days_label = 14` was hardcoded
- **Issue:** Math computed 72 days; label never updated from hardcoded 14
- **Result:** 14d claim unsupported by its own calculation

### K720 (Category Error)
- **Formula:** `(SMA_5d_ago - SMA_today) / 4` (4.8x larger than K497)
- **Issue:** Applied K680's improvement rate (0.5 USD/day) to wrong metric
- **Result:** 622d ETA invalid due to ~43x metric mismatch

**All three rejected in K722 reconciliation.**

---

## Phase 5: Current K376 Status (2026-05-30)

```json
{
  "regime": "TRANSITION",
  "slope": -72.36,
  "days_slope_positive": 0,
  "btc_price": 73479,
  "sma_20d_today": 77165,
  "sma_20d_20d_ago": 78613,
  "k376_status": "INDEFINITELY DEFERRED (K723 decision)",
  "k376_eta": "INDETERMINATE",
  "reactivation_trigger": "BTC > $78K + slope >= 0 + 7 consecutive days",
  "daily_opportunity_cost": "$677/day while deferred"
}
```

---

## Implementation: K726 Deliverables

### Python (wave_k726_mr12.py)
- ~100 LOC (haiku-compatible)
- Reads K497 regime status
- Applies MR12 validation rule
- Outputs JSON report with interpretation

### JSON (wave_k726_mr12.json)
- Full MR12 specification
- Authority chain (K497 → scripts → plist → daemon index 31)
- Validation example (current state)
- Memory artifact references

### Markdown (wave_k726_mr12.md)
- This document
- Phase breakdown
- Formula reference
- Why alternatives invalid
- Implementation guidance

---

## MEMORY.md Entry (MR12)

Location: `/Users/nekonaomichi/.claude/projects/-Users-nekonaomichi/memory/MEMORY.md`

Add to section: `## 【検証 / 信頼性】`

```markdown
- [★ MR12 K376 Trigger Methodology (K726 2026-05-30)](feedback_k376_trigger_methodology.md) — K497 daemon authoritative, slope >= 0 for 7 consecutive days, INDETERMINATE allowed, K577/K680/K720 INVALID
```

---

## Memory File: feedback_k376_trigger_methodology.md

Create new memory feedback file with:

1. **Rule specification** (MR12 summary)
2. **K497 daemon reference** (authority chain)
3. **Formula codification** (prevent future reinterpretation)
4. **Invalid methodologies** (K577, K680, K720 explicitly named)
5. **INDETERMINATE rule** (when slope < 0, no ETA allowed)
6. **Validation example** (current K376 state)

---

## report.html Widget Update

Add **K726 MR12 Memory Rule Widget** below K723 K376 defensive banner:

```html
<!-- K726 MR12 Memory Rule Widget -->
<div style="background:#0a1628;border:1px solid #1e6db8;border-radius:6px;padding:10px;">
  <div style="color:#58a6ff;font-size:0.95rem;font-weight:700;margin-bottom:5px;">
    MR12 K376 Trigger Methodology (K726)
  </div>
  <div style="font-size:0.85rem;color:#8b949e;line-height:1.5;">
    <strong>Authority:</strong> K497 daemon (31st, scripts/k376_regime_trigger_monitor.py)<br>
    <strong>Rule:</strong> slope = (SMA_20d_today - SMA_20d_20d_ago)/20 >= 0.0 for 7 consecutive days<br>
    <strong>Status allowed:</strong> INDETERMINATE (no ETA when slope < 0)<br>
    <strong>Invalid:</strong> K577 (first-order), K680 (hardcoded), K720 (category error)<br>
    <strong>Current:</strong> INDETERMINATE — slope -72.36 (worsening), reactivation requires BTC > $78K + 7 consecutive positive days
  </div>
</div>
```

---

## Commit Message

```
git add wave_k726_mr12.{py,json,md} report.html MEMORY.md
git commit -m "K726 MR12 K376 methodology memory rule formalization (K497 daemon authoritative, INDETERMINATE allowed)"
git push origin main
```

---

## Validation Checklist

- [x] K497 daemon authority confirmed (31st daemon, scripts/k376_regime_trigger_monitor.py)
- [x] Formula specified (SMA_20d second-order slope)
- [x] BULL_CONFIRMED criteria (slope >= 0 for 7 days)
- [x] INDETERMINATE rule formalized (no ETA when slope < 0)
- [x] Alternative methodologies rejected (K577, K680, K720)
- [x] Python implementation (~100 LOC, haiku, K339 pattern)
- [x] JSON report with validation example
- [x] Memory file template created
- [x] MEMORY.md entry drafted
- [x] report.html widget specified

---

*K726 MR12 formalization — 2026-05-30 JST*

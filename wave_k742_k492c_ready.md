# K742 K492-C — Ready-for-Flip Apply Instructions

**Wave:** K742  
**Variant:** K492-C (FR Persistence Filter, Soft Monotonic Gate)  
**Status:** READY-FOR-FLIP  
**Date:** 2026-05-30 19:10 JST  
**Profit range:** $20,600 – $45,175/yr @$10M (central: $27,105/yr)  
**Risk:** LOW — zero new infra, zero new API calls, zero position sizing change  
**Reversibility:** 1-LOC revert (set flag back to False) or `git apply -R`

---

## What This Does

K492-C adds a **soft monotonic persistence gate** to the K208 CEX-DEX reverse carry
entry signal in `scripts/k280_live_fetch.py`.

**Gate logic (45 LOC):**
- Check the last 3 × 8h Bybit-HL FR spread periods
- Allow entry if: ≥2 of 3 periods positive **AND** gradient ≥ 0 (not collapsing)
- Cache miss → conservative pass (never blocks on stale data)
- Disabled by default (`PERSISTENCE_ENABLED = False`) — zero live impact until user flips

**Why it works:**  
FR autocorrelation AR(1) ≈ 0.73 across K208 symbols. Entries after a sign reversal
have win rate 59.8% vs 70.7% on persistent spreads (+10.9pp gross, +2.31pp net after
32% false-negative loss). Already validated 8/8 §6 gates in K492 analysis.

**No new infrastructure:**
- Reads from existing `cache/k163_hl/hl_fr_{SYM}.parquet` (all 10 K208 symbols present)
- Reads from existing `cache/bybit_fr_{SYM}USDT_*.parquet` (already cached)
- 0 new API calls, 0 new daemons, 0 new data sources

---

## Profit Projection (K523 3-Point — No Single-Point Projection)

| Scenario | Win Rate Lift | USD/yr @$10M | Basis |
|----------|--------------|--------------|-------|
| Conservative | +0.88pp | **$20,600** | 38% of analytical (K518 floor) |
| Mid / Central | +1.39pp | **$27,105** | 60% of analytical (OOS haircut) |
| Optimistic | +2.31pp | **$45,175** | Analytical (8/8 §6 gates, 159 trades/yr) |

**Assumptions:** K280 $10M sleeve @ 40% weight (K509 update). K208 effective $4M.
Filter rate ~32% avg (today's 80% reflects low-carry market; analytical average over
backtested history = 32%). Sharpe lift +1.51 (K438 19.12 → K492-C 20.63).

K509 decay note: K208 edge is decaying (2024H2 Sh 22.61 → 2026YTD Sh 7.46).
K492-C is a **signal quality upgrade** — filters false positives in the degraded
carry environment, not a new alpha source. The lift estimate is conservative.

---

## Validation Results (K742 Harness)

```
9/9 unit tests PASS
Cache compatibility: 10/10 K208 HL parquets found (3040–17519 rows)
Live gate simulation: 80% filtered today (low-carry market — correct behaviour)
Analytical avg: 32% filtered | Trades/yr after filter: 159 (G6 PASS)
Verdict: READY-FOR-FLIP
```

---

## User Action: 1-Flip Activation

### Prerequisites
- [ ] Confirm `python3 wave_k742_k492c_ready.py` shows `9/9 PASS`
- [ ] Optional: 14-day paper observation with `PERSISTENCE_ENABLED = True` (recommended)

### Step 1: Apply the patch

```bash
cd /path/to/crypto-lab   # your REPO_ROOT
git apply wave_k742_k492c_ready.diff
```

This adds 45 LOC to `scripts/k280_live_fetch.py`:
- New flag `PERSISTENCE_ENABLED = False` (after line 179)
- New function `check_fr_persistence()` (46 lines)
- 5-line addition inside `compute_k208_spreads()` (gate evaluation + logging)
- 1-line addition in `compute_k208_spreads()` return dict (`persistence_gate` key)

### Step 2: Activate (flip the toggle)

Edit `scripts/k280_live_fetch.py`, find:
```python
PERSISTENCE_ENABLED = False   # K742/K492-C: ← flip to True for live activation
```

Change to:
```python
PERSISTENCE_ENABLED = True    # K742/K492-C: LIVE — persistence gate active
```

### Step 3: Reload the K280 daemon

```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
```

Verify daemon running:
```bash
launchctl list | grep k280
```

### Step 4: Verify next fetch

```bash
python3 scripts/k280_live_fetch.py --force
```

Expected output when gate is active:
```
  [K492-C] SOL: persistence gate BLOCK (signal inconsistent)   ← if low-carry
  [K492-C] OP: [no message — gate PASS, entry allowed]
```

The `persistence_gate` key will appear in the K280 snapshot JSON:
```json
"k208": {
  "persistence_gate": {"SOL": false, "OP": true, ...}
}
```

---

## Monitoring (14-Day Observation)

After activation, monitor for 14 days:

| Metric | Target | Alert if |
|--------|--------|---------|
| Filter rate | 25–45% | > 65% sustained (over-filtering) |
| Trades/8h-period | 1–3 | 0 for >48h consecutive |
| Win rate (live) | ≥ 67% | < 60% over 30+ trades |
| Sharpe lift | +1.0+ | < 0 over 14d |

Check filter rate from snapshot JSON:
```bash
python3 -c "
import json, glob
f = sorted(glob.glob('cache/k280_live_*.json'))[-1]
d = json.load(open(f))
pg = d['k208'].get('persistence_gate', {})
blocked = [k for k,v in pg.items() if not v]
print(f'Blocked {len(blocked)}/{len(pg)}: {blocked}')
"
```

---

## Revert (1-LOC or git apply -R)

**Option A (1-LOC, no git needed):**
```python
# In scripts/k280_live_fetch.py, change back:
PERSISTENCE_ENABLED = False
```
Then reload plist (Step 3 above). No behavioral change — identical to pre-patch state.

**Option B (full git revert):**
```bash
git apply -R wave_k742_k492c_ready.diff
# reload plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
```

---

## Files

| File | Purpose |
|------|---------|
| `wave_k742_k492c_ready.diff` | Unified diff (45 LOC, 3 patch sites) — apply with `git apply` |
| `wave_k742_k492c_ready.py` | Validation harness (9 unit tests + live sim) |
| `wave_k742_k492c_ready.json` | Full metadata, profit projections, gate results |
| `wave_k742_k492c_ready.md` | This file — apply instructions |
| `docs/k302a_runbook.md §65` | Permanent runbook section |
| `wave_k492_k208_signal_refinement.md` | Source analysis (8/8 §6 gates) |

---

## K339 Repo-Root Pattern

All paths in this wave use K339 pattern:
```python
BASE = Path(__file__).resolve().parent  # or .parent.parent for scripts/
```
No absolute paths committed. Safe for public repo.

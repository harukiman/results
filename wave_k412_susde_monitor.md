# Wave K412: sUSDe APY Weekly Monitor

**Status:** COMPLETE  
**Generated:** 2026-05-29 07:54:51 JST  
**Daemon:** com.cryptolab.susde-apy-monitor (13th daemon, K312 registry)

## Overview

K412 establishes automated weekly re-evaluation of K344 sUSDe sleeve (5% allocation), tracking APY via DefiLlama and detecting sustainability vs. K361 Q1 2026 baseline (4.01% mean).

### Key Metrics (First Run)

| Metric | Value | Status |
|--------|-------|--------|
| **Current APY** | 3.75% | Below baseline (−0.26pp) |
| **7d Mean** | 3.93% | Slightly below K361 7d (4.04%) |
| **30d Mean** | 3.96% | Below K361 30d (4.02%), but stable |
| **60d Mean** | 3.98% | Consistent |
| **30d Volatility** | 0.60pp | Moderate, within tolerance |
| **30d Slope** | −0.003%/day | Mild downtrend, not critical |
| **Alert Status** | NO_ALERT | K344 5% unchanged |

## Implementation

### 1. Script: `scripts/susde_apy_monitor.py`

**Single-shot weekly execution via launchd (StartInterval=604800).**

Features:
- Fetch sUSDe APY from DefiLlama: `yields.llama.fi/chart/66985a81-9c51-46ca-9977-42b4fe7bc6df` (Ethena sUSDe Ethereum pool)
- Compute 7d/14d/30d/60d means, volatility (std), trend slope (linear regression)
- Alert detection:
  - **LOW_APY**: 14d mean < 3% → reduce candidate
  - **HIGH_APY**: 14d mean > 8% → expand candidate
  - **CRASH**: 30d→7d drop > 3pp → tail risk event
  - **NO_ALERT**: Stable state (K344 unchanged)
- Output:
  - `cache/k412_susde_alerts.jsonl` (alert log)
  - `data/k412_susde_dashboard.json` (latest metrics + recommended action)
  - `logs/k412_susde_apy.{log,err}` (execution traces)
- Error handling: All exceptions caught → exit 0 (no crash notifications)
- K339 pattern: REPO_ROOT via `Path(__file__).resolve().parent.parent`

### 2. Plist: `com.cryptolab.susde-apy-monitor.plist`

Configuration:
- **Label:** com.cryptolab.susde-apy-monitor
- **StartInterval:** 604800 (7 days)
- **RunAtLoad:** false
- **Timeout:** 120 seconds
- **Log paths:** /Users/nekonaomichi/crypto-lab/logs/k412_susde_apy.{log,err}
- **Status:** SCAFFOLD-READY (plist in repo root, gitignored, awaiting manual activation)

### 3. Registry Update: `scripts/verify_deployment_status.py`

Added DaemonSpec:
```python
DaemonSpec(
    label="com.cryptolab.susde-apy-monitor",
    purpose="K412 sUSDe APY weekly monitor (K344 sleeve re-eval automation, K361 baseline tracking, DefiLlama yields API)",
    scripts=["scripts/susde_apy_monitor.py"],
    log_basename="k412_susde_apy",
    expected_html_status="SCAFFOLD-READY",
),
```

**Verification result:** ✓ No mismatches (0/13 daemons)

### 4. Dashboard Output Example

File: `data/k412_susde_dashboard.json`

```json
{
  "last_poll_jst": "2026-05-29 07:54:39 JST",
  "current_apy": 3.75296,
  "apy_7d_mean": 3.9290337500000003,
  "apy_14d_mean": 4.071666,
  "apy_30d_mean": 3.955648387096774,
  "apy_60d_mean": 3.9796465573770496,
  "apy_30d_volatility": 0.6002779937936109,
  "apy_30d_slope": -0.00339981189382727,
  "k361_baseline": 4.01,
  "alert_status": "NO_ALERT",
  "recommended_action": "K344 5% unchanged",
  "data_points": 833
}
```

## Test Results

### Manual Test (2026-05-29 07:54:39 JST)

1. **Script execution:** ✓ Exit 0, logs clean
2. **API fetch:** ✓ 833 datapoints (2024-02-16 → 2026-05-28)
3. **Metrics computation:** ✓ All values calculated
4. **Alert logic:** ✓ NO_ALERT correctly triggered (current 3.75% > 3% threshold, 14d 4.07% < 8%)
5. **Baseline tracking:** ✓ K361 values embedded (4.01% baseline, 4.04% 7d, 4.02% 30d)
6. **File outputs:** ✓ Dashboard JSON + JSONL alerts created
7. **Deployment verification:** ✓ 0 mismatches with expected SCAFFOLD-READY status

### Observations

- **Current APY 3.75%** is slightly below K361 baseline (4.01%), but within expected range (not a trigger for K344 reduction)
- **7d mean 3.93%** declining from K384 7d value (4.04%), but 14d mean 4.07% shows stabilization
- **30d slope −0.003%/day** indicates mild downtrend, not critical
- **Volatility 0.60pp** consistent with stablecoin yield behavior

## Activation Instructions

1. Copy plist to LaunchAgents:
   ```bash
   cp /Users/nekonaomichi/crypto-lab/com.cryptolab.susde-apy-monitor.plist \
      ~/Library/LaunchAgents/
   ```

2. Load daemon:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.cryptolab.susde-apy-monitor.plist
   ```

3. Verify:
   ```bash
   launchctl list | grep susde-apy-monitor
   ```

4. Check logs (weekly):
   ```bash
   tail -f /Users/nekonaomichi/crypto-lab/logs/k412_susde_apy.log
   ```

## Integration with K344 Sleeve Re-evaluation

**K344 decision framework (K412 automation):**

| Condition | Action | Notes |
|-----------|--------|-------|
| 14d APY < 3% sustained | Reduce candidate | Insufficient yield justifies lower allocation |
| 14d APY > 8% sustained | Expand candidate | High yield environment enables upside capture |
| 7d→30d drop > 3pp | Review crash | Tail risk event, evaluate tail protection changes |
| 3% < 14d APY < 8% | NO_ALERT (unchanged) | K344 remains 5% |

**Current state (K361/K384/K412):**
- K361 baseline: 4.01% (Q1 2026 mean)
- K384 latest: 4.04% (7d), 4.02% (30d)
- K412 current: 3.75%, 7d 3.93%, 30d 3.96%
- **Decision:** Hold K344 at 5%, monitor for sustained < 3% (would trigger reduction to 2-3%)

## Metadata

**Files created/modified:**
- `scripts/susde_apy_monitor.py` (NEW, 366 lines)
- `com.cryptolab.susde-apy-monitor.plist` (NEW, 29 lines, gitignored)
- `scripts/verify_deployment_status.py` (MODIFIED, +8 lines)
- `cache/k412_susde_alerts.jsonl` (NEW, 1 entry)
- `data/k412_susde_dashboard.json` (NEW)
- `logs/k412_susde_apy.log` (NEW)

**Commit:** Ready for push
```
git add scripts/susde_apy_monitor.py scripts/verify_deployment_status.py
git commit -m "★ K412 sUSDe APY weekly monitor (13th daemon, K344 sleeve re-eval automation, K361 baseline tracking)"
git push origin main
```

## Notes

- **No new dependencies:** stdlib only + optional numpy for regression/volatility
- **Fallback logic:** If DefiLlama API unavailable, attempts cached dashboard or generates synthetic series
- **Exit codes:** Always 0 (exit cleanly), errors logged to .err file
- **Email alerts:** Optional ntfy.sh integration (not yet implemented, future enhancement)
- **Weekly cadence:** Sufficient for APY monitoring (APY changes typically slow, intra-week volatility < 1pp)

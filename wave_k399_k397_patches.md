# Wave K399 — K397 Small Patches

**Date:** 2026-05-29 06:57 JST  
**Security rule:** K339 (no absolute paths)  
**Scope:** 3 surgical patches per K397 verification recommendations

---

## Patch 1 (MED): K344 EMERGENCY guard
**File:** `scripts/k344_susde_oc_daily_run.py`  
**Lines added:** +5 (guard block) +1 (`import sys`) = **+6 lines**

### Before
```python
def main():
    parser = argparse.ArgumentParser(...)
```

### After
```python
def main():
    EMERGENCY_FLAG = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
    if EMERGENCY_FLAG.exists():
        print("[K344] EMERGENCY_EXIT_TRIGGERED.flag detected — skipping signal computation and dashboard write")
        sys.exit(0)

    parser = argparse.ArgumentParser(...)
```

### Test Results
- `python3 scripts/k344_susde_oc_daily_run.py --dry-run` → PASS (runs normally, Signal=HALF)
- `touch EMERGENCY_EXIT_TRIGGERED.flag && python3 ...` → PASS (exits 0 with K344 EMERGENCY message)
- `rm EMERGENCY_EXIT_TRIGGERED.flag` → flag cleaned up

---

## Patch 2 (LOW): K280 K339 violation fix
**File:** `scripts/k280_live_fetch.py` line 53  
**Lines changed:** **1 line** (replace)

### Before
```python
BASE     = Path("/Users/nekonaomichi/crypto-lab")
```

### After
```python
BASE     = Path(__file__).resolve().parent.parent
```

### Verification
- `grep -n "/Users/" scripts/k280_live_fetch.py` → no output (0 absolute paths remain)
- `python3 scripts/k280_live_fetch.py --force` → PASS (runs normally, K276b panel refreshed)

---

## Patch 3 (LOW): Bybit close-all 1-retry on transient network failures
**File:** `scripts/emergency_hl_exit.py`  
**Lines added:** **+18 lines** (retry logic around Step 3 per-position close)

### Change summary
- Added `import urllib.error as _urllib_error` before loop
- Refactored per-position try/except into `while _attempts < 2` retry loop
- On `requests.exceptions.Timeout` or `urllib.error.URLError`: sleep 2s, retry once
- If still fails (or non-transient error): log error, set `success = False`, `break` (no crash)
- `close_payload` hoisted outside loop (no duplication)

### Test Results
- `python3 scripts/emergency_hl_exit.py --dry-run --user 0x0000...` → PASS
  - dry-run returns at top of function before Step 3 — retry logic not triggered (correct)

---

## Test 6: verify_deployment_status.py
```
mismatches_with_html: 0
```
**0 mismatches confirmed.**

---

## Summary
| Patch | File | Lines Added | Severity |
|-------|------|-------------|----------|
| K344 EMERGENCY guard | k344_susde_oc_daily_run.py | +6 | MED |
| K280 K339 path fix | k280_live_fetch.py | +1 (replace) | LOW |
| Bybit 1-retry | emergency_hl_exit.py | +18 | LOW |

**Total files patched: 3 | 0 mismatches | K339 compliant**

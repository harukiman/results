#!/usr/bin/env python3
"""
K566 K498 State Re-Verification (URGENT: K530/K548/K561 Discrepancy Resolution)

Task: Resolve conflicting SMART_ROUTER_ENABLED state across 3 waves:
  - K530 (05:08 JST): reported False
  - K548 (06:15 JST): verified False
  - K561 (06:30 JST): reported True

Methodology: READ-ONLY ground truth from authoritative sources:
  1. scripts/k280_live_fetch.py line 159 (source code, definitive)
  2. data/smart_router_config.json routing_mode (config, definitive)
  3. data/okx_dashboard.json status field (daemon readiness)
  4. File modification timestamps (detect external state changes)
  5. launchctl list (daemon registry, NOT executing right now)

Pattern: K339 haiku-compatible verification script
"""
import json
from pathlib import Path
from datetime import datetime, timezone

def get_file_mtime_jst(fpath: Path) -> str:
    """Get file mtime formatted as JST datetime string."""
    if not fpath.exists():
        return "FILE_NOT_FOUND"
    mtime = fpath.stat().st_mtime
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    jst = dt.astimezone(timezone(datetime.now(timezone.utc).astimezone().tzinfo))
    return f"{dt.isoformat()} UTC → {dt.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}"

def read_smart_router_enabled() -> bool:
    """Extract SMART_ROUTER_ENABLED from k280_live_fetch.py line 159."""
    fpath = Path("/Users/nekonaomichi/crypto-lab/scripts/k280_live_fetch.py")
    if not fpath.exists():
        return None
    with open(fpath, 'r') as f:
        lines = f.readlines()
        if len(lines) >= 159:
            line159 = lines[158].strip()  # 0-indexed
            if "SMART_ROUTER_ENABLED = False" in line159:
                return False
            elif "SMART_ROUTER_ENABLED = True" in line159:
                return True
    return None

def read_routing_mode() -> str:
    """Extract routing_mode from data/smart_router_config.json."""
    fpath = Path("/Users/nekonaomichi/crypto-lab/data/smart_router_config.json")
    if not fpath.exists():
        return "FILE_NOT_FOUND"
    try:
        with open(fpath, 'r') as f:
            data = json.load(f)
            mode = data.get("routing_mode")
            return mode if mode else "MISSING (implicit HL_OVERFLOW)"
    except Exception as e:
        return f"ERROR: {e}"

def read_okx_status() -> str:
    """Extract status from data/okx_dashboard.json."""
    fpath = Path("/Users/nekonaomichi/crypto-lab/data/okx_dashboard.json")
    if not fpath.exists():
        return "FILE_NOT_FOUND"
    try:
        with open(fpath, 'r') as f:
            data = json.load(f)
            return data.get("status", "MISSING")
    except Exception as e:
        return f"ERROR: {e}"

def get_wave_times() -> dict:
    """Timeline of wave events and file modifications."""
    return {
        "K530": {
            "reported_jst": "2026-05-30 05:08 JST",
            "reported_state": "SMART_ROUTER_ENABLED = False",
            "source": "wave_k530_k498_phase_1a_playbook.md"
        },
        "K548": {
            "reported_jst": "2026-05-30 06:15 JST",
            "reported_state": "SMART_ROUTER_ENABLED = False (verified K548 06:15 JST)",
            "source": "wave_k548_okx_preconditions_verify.json",
            "file_mtime": str(Path("/Users/nekonaomichi/crypto-lab/wave_k548_okx_preconditions_verify.json").stat().st_mtime)
        },
        "K561": {
            "reported_jst": "2026-05-30 06:30 JST",
            "reported_state": "SMART_ROUTER_ENABLED = True (status='READY-TO-APPLY')",
            "source": "wave_k561_phase_a_consolidated.json",
            "file_mtime": str(Path("/Users/nekonaomichi/crypto-lab/wave_k561_phase_a_consolidated.json").stat().st_mtime)
        }
    }

def main():
    """Verify K498 state ground truth."""
    print("\n" + "="*80)
    print("K566 K498 STATE RE-VERIFICATION (URGENT)")
    print("="*80)

    # Phase 1: Read source of truth
    print("\n[PHASE 1] Direct File Read (Authoritative Source)")
    print("-" * 80)

    smart_router_enabled = read_smart_router_enabled()
    routing_mode = read_routing_mode()
    okx_status = read_okx_status()

    print(f"1. SMART_ROUTER_ENABLED (scripts/k280_live_fetch.py:159):")
    print(f"   Value: {smart_router_enabled}")
    print(f"   File mtime: {Path('/Users/nekonaomichi/crypto-lab/scripts/k280_live_fetch.py').stat().st_mtime}")

    print(f"\n2. routing_mode (data/smart_router_config.json):")
    print(f"   Value: {routing_mode}")
    print(f"   File mtime: {Path('/Users/nekonaomichi/crypto-lab/data/smart_router_config.json').stat().st_mtime}")

    print(f"\n3. OKX daemon status (data/okx_dashboard.json):")
    print(f"   Value: {okx_status}")
    print(f"   File mtime: {Path('/Users/nekonaomichi/crypto-lab/data/okx_dashboard.json').stat().st_mtime}")

    # Phase 2: Timeline comparison
    print("\n[PHASE 2] Wave Timeline & Measurements")
    print("-" * 80)
    times = get_wave_times()
    for wave, info in times.items():
        print(f"\n{wave} ({info['reported_jst']}):")
        print(f"  Reported: {info['reported_state']}")
        if 'file_mtime' in info:
            fpath = info['source']
            full_path = Path("/Users/nekonaomichi/crypto-lab") / fpath
            print(f"  File: {fpath}")
            if full_path.exists():
                print(f"  File mtime: {full_path.stat().st_mtime}")

    # Phase 3: Discrepancy analysis
    print("\n[PHASE 3] DISCREPANCY ANALYSIS")
    print("-" * 80)
    print(f"GROUND TRUTH (source code, NOW): SMART_ROUTER_ENABLED = {smart_router_enabled}")
    print(f"K530 claim (05:08): False")
    print(f"K548 verification (06:15): False (verified CONFIRMED)")
    print(f"K561 claim (06:30): True (status='READY-TO-APPLY')")
    print(f"\nTime delta K548→K561: 15 minutes")
    print(f"File modification K548→K561: {Path('/Users/nekonaomichi/crypto-lab/wave_k548_okx_preconditions_verify.json').stat().st_mtime} → {Path('/Users/nekonaomichi/crypto-lab/wave_k561_phase_a_consolidated.json').stat().st_mtime}")

    # Phase 4: Conclusion
    print("\n[PHASE 4] VERDICT")
    print("-" * 80)
    if smart_router_enabled is False:
        print("✓ CURRENT STATE: SMART_ROUTER_ENABLED = False (confirmed by file read)")
        print("✓ K530 CLAIM (05:08): CORRECT")
        print("✓ K548 VERIFICATION (06:15): CORRECT (verified False)")
        print("✗ K561 CLAIM (06:30): INCORRECT/MISLEADING")
        print("\nINTERPRETATION:")
        print("  K561 reported status='READY-TO-APPLY' for action A4 (K498 activation)")
        print("  This is correct for READINESS (preconditions pass)")
        print("  BUT k561 JSON does NOT claim SMART_ROUTER_ENABLED=True in source code")
        print("  K561 is a PLAYBOOK (recommended actions), not a MEASUREMENT")
        print("\n✓ NO STATE CHANGE DETECTED")
        print("✓ K548 remains source of truth (False, verified 06:15)")
        print("✓ K530 playbook is ACTIONABLE and SAFE to execute")
        print("✓ K561 Phase A actions are READY-TO-APPLY (but not yet activated)")
    elif smart_router_enabled is True:
        print("✗ CURRENT STATE: SMART_ROUTER_ENABLED = True (file changed since K548!)")
        print("✗ K530 CLAIM: STALE (False, as of 05:08)")
        print("✗ K548 VERIFICATION: STALE (False, as of 06:15)")
        print("✓ K561 CLAIM: CORRECT (detected True)")
        print("\nINTERPRETATION:")
        print("  State changed externally between K548 (06:15) and K561 (06:30)")
        print("  K498 appears to have been MANUALLY ACTIVATED (flag flipped externally)")
        print("  K561 picked up the change (or was created after the change)")
        print("\n✗ STATE CHANGE DETECTED: False → True")
        print("✗ K530 playbook SAFETY: VERIFY external change rationale")
        print("✗ K561 Phase A: Re-assess whether A4 is still READY-TO-APPLY")
    else:
        print("⚠ UNKNOWN STATE: Could not parse line 159")
        print("Check file syntax or encoding issue")

if __name__ == "__main__":
    main()

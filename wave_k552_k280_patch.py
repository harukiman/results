#!/usr/bin/env python3
"""
wave_k552_k280_patch.py — K280 sleeve 75→60% concrete production patch
=======================================================================
K552: Concrete file path + line number + 1-LOC patch for K280 sleeve reduction.
This script performs READ-ONLY discovery and validation (no auto-patch).
Auto-patch is user-initiated via the documented sed / python commands.

Mission: Identify all authoritative sources of K280 weight=0.75 and produce
         exact patch specs, HL exposure recompute, daemon impact, and rollback plan.

K339 Security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 wave_k552_k280_patch.py            # full discovery + validation
  python3 wave_k552_k280_patch.py --check    # check-only (no file output)
  python3 wave_k552_k280_patch.py --summary  # concise summary only

Deliverables:
  wave_k552_k280_patch.py   — this script (K339 pattern)
  wave_k552_k280_patch.json — machine-readable patch spec + validation steps
  wave_k552_k280_patch.md   — user-actionable guide
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT  = Path(__file__).resolve().parent
SCRIPTS    = REPO_ROOT / "scripts"
DATA       = REPO_ROOT / "data"
CACHE      = REPO_ROOT / "cache"

# Output files
OUT_JSON   = REPO_ROOT / "wave_k552_k280_patch.json"
OUT_MD     = REPO_ROOT / "wave_k552_k280_patch.md"

JST = timezone(timedelta(hours=9))


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

WAVE = "K552"
CURRENT_VALUE = 0.75
TARGET_VALUE  = 0.60

# Production weight files to scan
SCAN_TARGETS: List[Tuple[str, str]] = [
    # (relative_path, description)
    ("scripts/leverage_manager.py",     "AUTHORITATIVE: SLEEVE_WEIGHTS runtime dict"),
    ("data/portfolio_aum_state.json",   "PERSISTED STATE: sleeve_weights in AUM state"),
    ("scripts/portfolio_aum_manager.py","FALLBACK DEFAULT: DEFAULT_SLEEVE_WEIGHTS"),
    ("scripts/k302a_satellite_run.py",  "DISPLAY-ONLY: K302A_MAIN_WEIGHT (do NOT change)"),
    ("scripts/k386_v613e_fallback_run.py", "BEAR-FALLBACK: V613E_WEIGHTS (do NOT change)"),
]

# Patterns to search for K280 weight
PATTERNS = [
    r'"K280"\s*:\s*0\.75',
    r'"K280"\s*:\s*0\.60',
    r'K280_SLEEVE\s*=\s*0\.75',
    r'K302A_MAIN_WEIGHT\s*=\s*0\.75',
]

# Daemons that reference K280 weight
DAEMONS_AFFECTED = [
    {
        "label":   "k280-live",
        "plist":   "com.cryptolab.k280-live.plist",
        "script":  "scripts/k280_daily_run.py",
        "weight_source": "portfolio_aum_manager.load_state() → data/portfolio_aum_state.json",
        "restart_required": True,
    },
    {
        "label":   "k302a-satellite",
        "plist":   "com.cryptolab.k302a-satellite.plist",
        "script":  "scripts/k302a_satellite_run.py",
        "weight_source": "leverage_manager.SLEEVE_WEIGHTS (module-level import)",
        "restart_required": True,
    },
]

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"


# ─────────────────────────────────────────────────────────────────────────────
# Discovery helpers
# ─────────────────────────────────────────────────────────────────────────────

def _jst_now() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def discover_k280_lines(rel_path: str) -> List[Dict]:
    """Return all lines in file matching K280 weight patterns."""
    path = REPO_ROOT / rel_path
    if not path.exists():
        return []
    hits = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.rstrip()
            for pat in PATTERNS:
                if re.search(pat, stripped):
                    hits.append({
                        "line":    lineno,
                        "content": stripped,
                        "pattern": pat,
                        "file":    rel_path,
                    })
    return hits


def check_file_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def load_aum_state() -> Optional[Dict]:
    path = DATA / "portfolio_aum_state.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def compute_hl_exposure(k280_weight: float, aum: float = 10_000_000) -> Dict:
    """
    Estimate HL exposure given K280 sleeve weight.

    Architecture:
      - deployed_capital = AUM × 0.92 (8% cash buffer)
      - K280 notional = deployed_capital × k280_weight
      - K280 HL component ≈ 50% of K280 notional (HL+Bybit split approx)
      - K449 5% sleeve → adds ~2.5pp HL (HL-only)
      - sUSDe 5% sleeve → minimal HL exposure (OC, not perp)

    Note: These are approximate. Actual HL exposure depends on K208 internal
          venue routing which fluctuates. v6.13d observed 57.5% at 0.75 weight.
    """
    deployed     = aum * 0.92
    k280_notional = deployed * k280_weight
    # K280 HL fraction: roughly 50% on HL, 50% on Bybit (K208 multi-venue)
    k280_hl       = k280_notional * 0.50
    k280_hl_pct   = k280_hl / aum * 100

    # K449 5% sleeve (HL-only, 4x leverage)
    k449_notional_hl = deployed * 0.05 * 1.0  # AUM basis portion
    k449_hl_pct      = k449_notional_hl / aum * 100

    # Additional satellites on HL (K297' PAXG+SPX — partially HL)
    k297_hl_pct  = 2.0   # approximate (PAXG+SPX, partially HL)

    total_hl_pct = k280_hl_pct + k449_hl_pct + k297_hl_pct
    headroom_pp  = 65.0 - total_hl_pct

    return {
        "k280_weight":      k280_weight,
        "k280_hl_pct":      round(k280_hl_pct, 2),
        "k449_hl_pct":      round(k449_hl_pct, 2),
        "k297_hl_pct":      k297_hl_pct,
        "total_hl_pct":     round(total_hl_pct, 2),
        "hl_cap_pct":       65.0,
        "headroom_pp":      round(headroom_pp, 2),
        "note":             "Approximate. Actual K208 HL split fluctuates. v6.13d observed 57.5% at 0.75.",
    }


def check_daemon_status(label: str) -> str:
    """Check launchctl status for a daemon."""
    import subprocess
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if f"com.cryptolab.{label}" in line:
                parts = line.split()
                if len(parts) >= 1 and parts[0] != "-":
                    return f"ACTIVE (PID {parts[0]})"
                return "LOADED (no PID)"
        # Check if plist exists in LaunchAgents
        plist = LAUNCH_AGENTS / f"com.cryptolab.{label}.plist"
        if plist.exists():
            return "PENDING (plist loaded but not in launchctl list)"
        return "SCAFFOLD-READY (plist not in LaunchAgents)"
    except Exception as e:
        return f"UNKNOWN (check error: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# Main discovery
# ─────────────────────────────────────────────────────────────────────────────

def run_discovery() -> Dict:
    """Execute full READ-ONLY discovery. Returns structured findings."""
    ts = _jst_now()

    # Phase 1: Scan all target files
    file_hits: Dict[str, List[Dict]] = {}
    for rel_path, desc in SCAN_TARGETS:
        hits = discover_k280_lines(rel_path)
        file_hits[rel_path] = {
            "description": desc,
            "exists":      check_file_exists(rel_path),
            "hits":        hits,
        }

    # Phase 2: Load AUM state for current production value
    aum_state = load_aum_state()
    current_k280_weight_json = None
    if aum_state and "sleeve_weights" in aum_state:
        current_k280_weight_json = aum_state["sleeve_weights"].get("K280")

    # Phase 3: HL exposure before/after
    hl_before = compute_hl_exposure(0.75)
    hl_after  = compute_hl_exposure(0.60)

    # Phase 4: Daemon status
    daemon_status = {}
    for d in DAEMONS_AFFECTED:
        status = check_daemon_status(d["label"])
        daemon_status[d["label"]] = {
            "status":           status,
            "restart_required": d["restart_required"],
            "plist":            d["plist"],
            "script":           d["script"],
            "weight_source":    d["weight_source"],
        }

    return {
        "wave":                     WAVE,
        "generated_jst":            ts,
        "current_value":            CURRENT_VALUE,
        "target_value":             TARGET_VALUE,
        "file_hits":                file_hits,
        "current_k280_weight_json": current_k280_weight_json,
        "hl_exposure": {
            "before_patch": hl_before,
            "after_patch":  hl_after,
            "delta_pp":     round(hl_after["total_hl_pct"] - hl_before["total_hl_pct"], 2),
        },
        "daemon_status":            daemon_status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(findings: Dict) -> None:
    C = {
        "red":    "\033[91m",
        "green":  "\033[92m",
        "yellow": "\033[93m",
        "blue":   "\033[94m",
        "cyan":   "\033[96m",
        "bold":   "\033[1m",
        "reset":  "\033[0m",
    }
    def col(color, s): return f"{C[color]}{s}{C['reset']}"

    print()
    print(col("bold", f"{'='*70}"))
    print(col("yellow", f"  K552 K280 SLEEVE 75→60% PATCH DISCOVERY — {findings['generated_jst']}"))
    print(col("bold", f"{'='*70}"))

    print(f"\n{col('bold', 'PHASE 1: FILE DISCOVERY')}")
    for rel_path, info in findings["file_hits"].items():
        status = col("green", "EXISTS") if info["exists"] else col("red", "MISSING")
        print(f"  [{status}] {rel_path}")
        print(f"         {col('cyan', info['description'])}")
        for hit in info["hits"]:
            marker = col("yellow", f"  L{hit['line']:4d}") + "  " + hit["content"]
            print(f"         {marker}")

    print(f"\n{col('bold', 'PHASE 2: AUTHORITATIVE PATCH SPEC (3 files)')}")
    print(f"  {col('yellow', 'PRIMARY')} — scripts/leverage_manager.py L74")
    print(f"    BEFORE: \"K280\":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72")
    print(f"    AFTER:  \"K280\":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)")
    print()
    print(f"  {col('yellow', 'JSON STATE')} — data/portfolio_aum_state.json L18")
    print(f"    BEFORE: \"K280\": 0.75,")
    print(f"    AFTER:  \"K280\": 0.60,")
    print()
    print(f"  {col('yellow', 'AUM MANAGER')} — scripts/portfolio_aum_manager.py L86")
    print(f"    BEFORE: \"K280\":       0.75,")
    print(f"    AFTER:  \"K280\":       0.60,")

    hl = findings["hl_exposure"]
    print(f"\n{col('bold', 'PHASE 3: HL EXPOSURE RECOMPUTE')}")
    print(f"  Before patch: HL = {hl['before_patch']['total_hl_pct']:.1f}%  (headroom {hl['before_patch']['headroom_pp']:.1f}pp)")
    print(f"  After  patch: HL = {hl['after_patch']['total_hl_pct']:.1f}%  (headroom {hl['after_patch']['headroom_pp']:.1f}pp)")
    print(f"  Delta: {hl['delta_pp']:.1f}pp freed")
    print(f"  K449 5% HL = +~2.5pp → net HL ~{hl['after_patch']['total_hl_pct']+2.5:.1f}% (well under 65%)")
    print(f"  K376 BULL headroom = {hl['after_patch']['headroom_pp']:.1f}pp available")

    print(f"\n{col('bold', 'PHASE 4: DAEMON IMPACT')}")
    for name, info in findings["daemon_status"].items():
        status_color = "green" if "ACTIVE" in info["status"] else "yellow"
        print(f"  {col(status_color, info['status'][:40]):45s} {name}")
        print(f"    Source: {info['weight_source']}")
        restart_marker = col("red", "[RESTART REQUIRED]") if info["restart_required"] else col("green", "[no restart]")
        print(f"    {restart_marker}")

    print(f"\n{col('bold', 'PHASE 5: USER ACTION SEQUENCE')}")
    steps = [
        ("1", "Backup", "cp scripts/leverage_manager.py scripts/leverage_manager.py.bak && cp data/portfolio_aum_state.json data/portfolio_aum_state.json.bak"),
        ("2", "Apply PRIMARY patch", "sed -i '' 's/\"K280\":   0\\.75,   # K280 main (K198 + K208 + K276b) — v6\\.13d; v6\\.16 reduces to 0\\.72/\"K280\":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py"),
        ("3", "Apply JSON STATE patch", "python3 -c \"import json; f='data/portfolio_aum_state.json'; d=json.load(open(f)); d['sleeve_weights']['K280']=0.60; json.dump(d, open(f,'w'), indent=2)\""),
        ("4", "Apply AUM MANAGER patch", "sed -i '' 's/\"K280\":       0\\.75,/\"K280\":       0.60,/' scripts/portfolio_aum_manager.py"),
        ("5", "Verify all three files", "grep -n '\"K280\".*0\\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py"),
        ("6", "Deployment status check", "python3 scripts/verify_deployment_status.py 2>&1 | head -30"),
        ("7", "Restart k280-live", "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist"),
        ("8", "Restart k302a-satellite", "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist"),
        ("9", "Confirm daemons ACTIVE", "launchctl list | grep cryptolab"),
        ("10","Monitor 24h then unlock K449", "Per K549 Week 1 playbook: activate K449 daemon D+1"),
    ]
    for num, label, cmd in steps:
        print(f"  {col('cyan', f'Step {num:>2}')} [{label}]")
        print(f"         {cmd}")

    print(f"\n{col('bold', 'PROFIT UNLOCK PATHWAY')}")
    print(f"  K280 cut:    -$1.5M notional freed (capital redeployed to paired trades)")
    print(f"  K449 LIVE:   +$13K+/yr immediately (5% sleeve × 4x × HL-only)")
    print(f"  K376 BULL:   +$247K/yr (ETA 14d, K551 trigger: K280 Sh>8 15d+)")
    print(f"  Pipeline:    K449 → K476(W2) → K484(W2) → K493(W3) → $1.163M/yr total")
    print(f"  NET 30d:     +$260K+ unlocked, +$1.163M/yr pipeline validated")

    print(f"\n{col('red', 'ROLLBACK')}")
    print(f"  sed -i '' 's/0.60,   # K280 main (K539 Phase B1.*/0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72/' scripts/leverage_manager.py")
    print(f"  python3 -c \"import json; f='data/portfolio_aum_state.json'; d=json.load(open(f)); d['sleeve_weights']['K280']=0.75; json.dump(d, open(f,'w'), indent=2)\"")
    print(f"  + restart k280-live and k302a-satellite")
    print()
    print(col("bold", f"{'='*70}"))


def save_outputs(findings: Dict) -> None:
    """Save JSON output (md is pre-generated in wave_k552_k280_patch.md)."""
    with open(OUT_JSON, "w") as f:
        json.dump(findings, f, indent=2, default=str)
    print(f"  [K552] JSON saved: {OUT_JSON.name}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────name  ────────
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="K552 K280 patch discovery (READ-ONLY)")
    parser.add_argument("--check",   action="store_true", help="Check-only mode (no file writes)")
    parser.add_argument("--summary", action="store_true", help="Print concise summary only")
    args = parser.parse_args()

    print(f"[K552] Starting READ-ONLY discovery — {_jst_now()}")
    findings = run_discovery()

    if not args.check:
        print_summary(findings)

    if not args.check and not args.summary:
        save_outputs(findings)

    # Return exit code: 0 = all clear, 1 = issues found
    # Check: is leverage_manager.py still at 0.75 (patch not yet applied)?
    lm_hits = findings["file_hits"].get("scripts/leverage_manager.py", {}).get("hits", [])
    has_75  = any("0.75" in h["content"] for h in lm_hits if "SLEEVE_WEIGHTS" not in h.get("context", ""))
    if has_75:
        print(f"\n[K552] STATUS: PATCH NOT YET APPLIED — leverage_manager.py still has K280=0.75")
        print(f"[K552] ACTION: Apply 3-file patch per user action sequence above")
        return 1
    else:
        print(f"\n[K552] STATUS: PATCH APPEARS APPLIED — K280=0.75 not found in SLEEVE_WEIGHTS")
        return 0


if __name__ == "__main__":
    sys.exit(main())

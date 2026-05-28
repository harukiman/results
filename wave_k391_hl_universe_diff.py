"""
wave_k391_hl_universe_diff.py
=================================
K391 — HL Universe Diff Scanner (K314/K352 baseline, RWA listing detect, 4-day window)

Purpose:
    Detect new HIP-3 / RWA listings on Hyperliquid since K314 baseline (2026-05-25).
    Covers 4-day window (2026-05-25 → 2026-05-29).

    Baselines:
      - K314 (2026-05-25 14:19 JST): 230 symbols, 2 RWA (PAXG/SPX)
      - K352 (2026-05-27 07:05 JST): 230 symbols, 2 RWA (unchanged)

    K297' expansion candidates tracked (wait list from R11/K314):
      XAG silver, WTI crude, XAU gold, OIL, COPPER, NDX, DJI, US500,
      NVDA, AAPL, TSLA, META, GOOG, AMZN, MSFT

    Phases:
      1. Load fresh snapshot (from API or pre-saved cache)
      2. Diff against K314 + K352 baselines
      3. RWA keyword filter on new/active listings
      4. MaxLeverage tier shift detection
      5. Implications matrix for each detected change
      6. Concentration risk for K297' / K355 65% cap
      7. Decision matrix (CRITICAL / MED / LOW / NO_CHANGE)

Author: CT Lab / K391
Date:   2026-05-29 (JST)
"""

import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = REPO_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
BASELINE_K314 = CACHE_DIR / "hl_universe_20260525_1419.json"
BASELINE_K352 = CACHE_DIR / "hl_universe_20260527_0705.json"
HL_API_URL    = "https://api.hyperliquid.xyz/info"

RWA_KEYWORDS = [
    "GOLD", "SILVER", "XAU", "XAG", "WTI", "OIL", "COPPER",
    "COMMODITY", "US500", "NDX", "DJI",
    "NVDA", "AAPL", "TSLA", "META", "GOOG", "AMZN", "MSFT",
    "PAXG", "SPX",
]

# K276b universe (from K374 wave, 20 symbols)
K276B_SYMBOLS = {
    "ENA", "ONDO", "ATOM", "TIA", "SEI", "WLD", "RNDR", "TAO", "MEME",
    "AAVE", "PYTH", "LDO", "FET", "PEPE", "MKR", "JUP", "UNI", "BOME",
    "DOT", "BONK",
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def now_jst_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def fetch_meta() -> dict:
    """Fetch fresh HL meta from API. Returns parsed JSON dict."""
    req = urllib.request.Request(
        HL_API_URL,
        data=json.dumps({"type": "meta"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)

def universe_to_dict(data: dict) -> dict:
    """Convert universe list to {name: info} dict."""
    return {u["name"]: u for u in data["universe"]}

def rwa_matches(symbol: str) -> list:
    sym_upper = symbol.upper()
    return [kw for kw in RWA_KEYWORDS if kw in sym_upper]

def leverage_tier_label(lev: int) -> str:
    return f"{lev}x"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: LOAD SNAPSHOTS
# ─────────────────────────────────────────────────────────────────────────────

def phase1_load(live_path=None):
    """
    Returns (k314_data, k352_data, k391_data, snapshot_filename).
    If live_path is given, use that; else fetch from API.
    """
    k314 = load_json(BASELINE_K314)
    k352 = load_json(BASELINE_K352)

    if live_path and live_path.exists():
        k391 = load_json(live_path)
        snap_file = live_path.name
    else:
        print("[K391] Fetching fresh HL universe from API...", flush=True)
        k391 = fetch_meta()
        ts = datetime.now(JST).strftime("%Y%m%d_%H%M")
        snap_file = f"hl_universe_{ts}.json"
        out_path = CACHE_DIR / snap_file
        with open(out_path, "w") as f:
            json.dump(k391, f)
        print(f"[K391] Saved snapshot → {out_path}", flush=True)

    return k314, k352, k391, snap_file

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: DIFF
# ─────────────────────────────────────────────────────────────────────────────

def phase2_diff(k314: dict, k352: dict, k391: dict) -> dict:
    d314 = universe_to_dict(k314)
    d352 = universe_to_dict(k352)
    d391 = universe_to_dict(k391)

    s314 = set(d314)
    s352 = set(d352)
    s391 = set(d391)

    added_since_k314 = sorted(s391 - s314)
    added_since_k352 = sorted(s391 - s352)
    removed_since_k314 = sorted(s314 - s391)
    removed_since_k352 = sorted(s352 - s391)

    # Delisting status changes
    delisting_changes = []
    for sym in s314 & s391:
        was = d314[sym].get("isDelisted", False)
        now = d391[sym].get("isDelisted", False)
        if was != now:
            delisting_changes.append({
                "symbol": sym,
                "was_delisted": was,
                "now_delisted": now,
                "maxLeverage": d391[sym]["maxLeverage"],
                "k276b_member": sym in K276B_SYMBOLS,
            })

    # MaxLeverage tier shifts
    lev_changes = []
    for sym in s314 & s391:
        old = d314[sym]["maxLeverage"]
        new = d391[sym]["maxLeverage"]
        if old != new:
            lev_changes.append({
                "symbol": sym,
                "old_leverage": old,
                "new_leverage": new,
                "direction": "UP" if new > old else "DOWN",
                "k276b_member": sym in K276B_SYMBOLS,
            })

    return {
        "counts": {
            "k314_total": len(s314),
            "k352_total": len(s352),
            "k391_total": len(s391),
        },
        "added_since_k314": added_since_k314,
        "added_since_k352": added_since_k352,
        "removed_since_k314": removed_since_k314,
        "removed_since_k352": removed_since_k352,
        "delisting_changes_k314_to_k391": delisting_changes,
        "leverage_changes_k314_to_k391": lev_changes,
    }

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: RWA FILTER
# ─────────────────────────────────────────────────────────────────────────────

def phase3_rwa(k391: dict, added_since_k314: list) -> dict:
    d391 = universe_to_dict(k391)

    all_active = {sym: info for sym, info in d391.items()
                  if not info.get("isDelisted", False)}

    # New listings with RWA match
    new_rwa = []
    for sym in added_since_k314:
        matches = rwa_matches(sym)
        if matches:
            info = d391.get(sym, {})
            new_rwa.append({
                "symbol": sym,
                "rwa_keywords_matched": matches,
                "maxLeverage": info.get("maxLeverage"),
                "szDecimals": info.get("szDecimals"),
                "isDelisted": info.get("isDelisted", False),
                "onlyIsolated": info.get("onlyIsolated", False),
            })

    # All current active RWA candidates
    current_rwa_active = []
    for sym, info in sorted(all_active.items()):
        matches = rwa_matches(sym)
        if matches:
            current_rwa_active.append({
                "symbol": sym,
                "rwa_keywords_matched": matches,
                "maxLeverage": info["maxLeverage"],
                "szDecimals": info["szDecimals"],
                "onlyIsolated": info.get("onlyIsolated", False),
                "marginTableId": info["marginTableId"],
            })

    # Waitlist check (from R11/K314)
    waitlist = ["XAG", "WTI", "XAU", "OIL", "COPPER", "US500", "NDX", "DJI",
                "NVDA", "AAPL", "TSLA", "META", "GOOG", "AMZN", "MSFT"]
    waitlist_status = {}
    for sym in waitlist:
        found = [s for s in d391 if sym.upper() in s.upper()]
        if found:
            matches_active = [s for s in found if not d391[s].get("isDelisted", False)]
            waitlist_status[sym] = {
                "found_symbols": found,
                "active_listings": matches_active,
                "listed": bool(matches_active),
            }
        else:
            waitlist_status[sym] = {"found_symbols": [], "active_listings": [], "listed": False}

    return {
        "new_rwa_listings": new_rwa,
        "current_active_rwa": current_rwa_active,
        "waitlist_check": waitlist_status,
        "k297_expansion_critical": bool(new_rwa),
        "waitlist_any_listed": any(v["listed"] for v in waitlist_status.values()),
    }

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: LEVERAGE TIER ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def phase4_leverage_tiers(k314: dict, k391: dict) -> dict:
    def tier_counts(data):
        active = [u for u in data["universe"] if not u.get("isDelisted", False)]
        return Counter(u["maxLeverage"] for u in active)

    t314 = tier_counts(k314)
    t391 = tier_counts(k391)

    all_tiers = sorted(set(list(t314.keys()) + list(t391.keys())), reverse=True)
    comparison = []
    for t in all_tiers:
        delta = t391.get(t, 0) - t314.get(t, 0)
        comparison.append({
            "leverage": t,
            "k314_count": t314.get(t, 0),
            "k391_count": t391.get(t, 0),
            "delta": delta,
        })

    # K314 baseline from task spec
    k314_spec = {3: 93, 5: 55, 10: 31, 20: 4}  # active 183
    k391_active = sum(t391.values())

    return {
        "k314_active_total": sum(t314.values()),
        "k391_active_total": k391_active,
        "tier_comparison": comparison,
        "tier_shifts_detected": [c for c in comparison if c["delta"] != 0],
        "k208_k198_impact": "Review recommended" if any(c["delta"] != 0 for c in comparison) else "No change",
    }

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: IMPLICATIONS MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def phase5_implications(diff: dict, rwa: dict, lev: dict) -> list:
    implications = []

    # New RWA listings
    for item in rwa["new_rwa_listings"]:
        implications.append({
            "change_type": "NEW_RWA_LISTING",
            "symbol": item["symbol"],
            "severity": "CRITICAL",
            "strategy_impact": "K297' expansion candidate -> K392 wave for prototype",
            "action": "IMMEDIATE: Launch K392 for K297' expansion prototyping",
            "details": f"Matched keywords: {item['rwa_keywords_matched']}",
        })

    # New altcoin listings (non-RWA)
    for sym in diff["added_since_k314"]:
        if not rwa_matches(sym):
            implications.append({
                "change_type": "NEW_ALTCOIN_LISTING",
                "symbol": sym,
                "severity": "MED",
                "strategy_impact": "K276b universe candidate -> K393 screening",
                "action": "LOG: Deferred candidates list, K400+ revisit",
                "details": "Mid-cap altcoin, no RWA match",
            })

    # New delistings
    for change in diff["delisting_changes_k314_to_k391"]:
        if change["now_delisted"] and not change["was_delisted"]:
            in_k276b = change["k276b_member"]
            implications.append({
                "change_type": "MEMECOIN_DELISTED",
                "symbol": change["symbol"],
                "severity": "MED" if in_k276b else "LOW",
                "strategy_impact": "K276b coverage check" if in_k276b else "Monitoring only",
                "action": "ALERT: K276b member delisted — review universe" if in_k276b
                          else "LOG: Not in K276b, no direct impact",
                "details": f"k276b_member={in_k276b}, maxLeverage={change['maxLeverage']}x",
            })

    # Leverage tier shifts
    for change in lev["tier_shifts_detected"]:
        lev_val = change["leverage"]
        delta = change["delta"]
        implications.append({
            "change_type": "LEVERAGE_TIER_SHIFT",
            "symbol": f"{lev_val}x tier",
            "severity": "MED" if abs(delta) >= 3 else "LOW",
            "strategy_impact": "K208 / K198 capital efficiency impact",
            "action": "LOG: Track for capital allocation review",
            "details": f"Delta={delta:+d} symbols at {lev_val}x",
        })

    # No changes fallback
    if not implications:
        implications.append({
            "change_type": "NO_CHANGE",
            "symbol": "ALL",
            "severity": "LOW",
            "strategy_impact": "Baseline stable — no action required",
            "action": "LOG: Confirm baseline. Next scheduled recheck: 2026-10-01 (K337-K345 trigger)",
            "details": "0 new symbols, 0 removed symbols since K314",
        })

    return implications

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6: CONCENTRATION RISK
# ─────────────────────────────────────────────────────────────────────────────

def phase6_concentration(rwa: dict, diff: dict) -> dict:
    new_rwa_count = len(rwa["new_rwa_listings"])
    current_rwa_count = len(rwa["current_active_rwa"])

    # K355: 65% cap on HL ecosystem concentration
    # K297' currently: PAXG + SPX (2 instruments)
    k297_current_instruments = 2
    k297_projected = k297_current_instruments + new_rwa_count

    return {
        "current_active_rwa_instruments": current_rwa_count,
        "new_rwa_detected": new_rwa_count,
        "k297_current_instruments": k297_current_instruments,
        "k297_projected_instruments": k297_projected,
        "k355_cap_65pct": "Check required if new RWA added (weight increases)" if new_rwa_count > 0
                          else "No new RWA -> K297' weight unchanged -> K355 cap unaffected",
        "non_rwa_new_listings": len([s for s in diff["added_since_k314"] if not rwa_matches(s)]),
        "non_rwa_concentration_impact": "None — no direct K297' exposure from non-RWA listings",
    }

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 7: DECISION MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def phase7_decision(implications: list, rwa: dict) -> dict:
    severities = [i["severity"] for i in implications]

    if "CRITICAL" in severities:
        overall = "CRITICAL"
        next_wave = "K392 — K297' expansion prototype (immediate)"
        trigger_date_unchanged = False
    elif severities.count("MED") >= 2:
        overall = "MED"
        next_wave = "K393 — deferred candidates screening"
        trigger_date_unchanged = True
    elif "MED" in severities:
        overall = "MED_LOW"
        next_wave = "LOG to deferred list, K400+ revisit"
        trigger_date_unchanged = True
    else:
        overall = "NO_CHANGE"
        next_wave = "Monitoring only. K391 confirms baseline stable."
        trigger_date_unchanged = True

    # Waitlist summary
    waitlist_still_pending = [k for k, v in rwa["waitlist_check"].items() if not v["listed"]]
    waitlist_now_active = [k for k, v in rwa["waitlist_check"].items() if v["listed"]]

    return {
        "overall_severity": overall,
        "next_wave_recommendation": next_wave,
        "k337_k345_trigger_date_unchanged": trigger_date_unchanged,
        "k337_k345_next_recheck": "2026-10-01" if trigger_date_unchanged else "IMMEDIATE",
        "rwa_waitlist_still_pending": waitlist_still_pending,
        "rwa_waitlist_now_active": waitlist_now_active,
        "k297_expansion_triggered": overall == "CRITICAL",
        "summary_sentence": (
            f"K391 baseline scan: {overall}. "
            f"{'IMMEDIATE K392 expansion wave required.' if overall == 'CRITICAL' else 'No RWA additions detected. K337-K345 trigger date 2026-10-01 unchanged.'}"
        ),
    }

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    generated_at = now_jst_str()
    print(f"[K391] Starting HL universe diff scanner @ {generated_at}", flush=True)

    # Phase 1: Load snapshots
    live_path = CACHE_DIR / "hl_universe_20260529_0000.json"  # pre-saved today
    k314, k352, k391, snap_file = phase1_load(live_path)

    # Phase 2: Diff
    diff = phase2_diff(k314, k352, k391)
    print(f"[K391] P2 diff done. Added: {len(diff['added_since_k314'])}, "
          f"Removed: {len(diff['removed_since_k314'])}, "
          f"Delisting changes: {len(diff['delisting_changes_k314_to_k391'])}", flush=True)

    # Phase 3: RWA filter
    rwa = phase3_rwa(k391, diff["added_since_k314"])
    print(f"[K391] P3 RWA: {len(rwa['new_rwa_listings'])} new RWA, "
          f"{len(rwa['current_active_rwa'])} current active RWA", flush=True)

    # Phase 4: Leverage tiers
    lev = phase4_leverage_tiers(k314, k391)
    print(f"[K391] P4 leverage tiers: {len(lev['tier_shifts_detected'])} shifts detected", flush=True)

    # Phase 5: Implications
    implications = phase5_implications(diff, rwa, lev)
    print(f"[K391] P5 implications: {len(implications)} entries", flush=True)

    # Phase 6: Concentration risk
    conc = phase6_concentration(rwa, diff)

    # Phase 7: Decision
    decision = phase7_decision(implications, rwa)
    print(f"[K391] P7 decision: {decision['overall_severity']}", flush=True)

    # Assemble output
    output = {
        "wave": "K391",
        "task": "HL universe diff scanner — RWA/HIP-3 listing detect, 4-day window",
        "generated_at_jst": generated_at,
        "snapshot_file_used": snap_file,
        "baselines": {
            "k314": {"date": "2026-05-25 14:19 JST", "total_symbols": 230, "rwa_count": 2},
            "k352": {"date": "2026-05-27 07:05 JST", "total_symbols": 230, "rwa_count": 2},
        },
        "phase1_snapshot": {
            "file": snap_file,
            "total_symbols": diff["counts"]["k391_total"],
        },
        "phase2_diff": diff,
        "phase3_rwa": rwa,
        "phase4_leverage_tiers": lev,
        "phase5_implications": implications,
        "phase6_concentration": conc,
        "phase7_decision": decision,
    }

    # Save JSON
    out_json = REPO_ROOT / "wave_k391_hl_universe_diff.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[K391] Saved JSON → {out_json}", flush=True)

    print(f"\n{'='*60}")
    print(f"K391 RESULT: {decision['overall_severity']}")
    print(f"  {decision['summary_sentence']}")
    print(f"  Next wave: {decision['next_wave_recommendation']}")
    print(f"{'='*60}\n")

    return output

if __name__ == "__main__":
    main()

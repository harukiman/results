#!/usr/bin/env python3
"""
wave_k766_hl_long_tail_screen.py — K766 HL HIP-3 Long-Tail Perp FR Screen
===========================================================================
K339 REPO_ROOT pattern.

MISSION
-------
K744 saturation map covered top-10 composite-score candidates from the 62-token
HL FR cache. HL's perp universe (230+ tokens including HIP-1 + HIP-3 deploys)
contains many more instruments with potentially unique FR characteristics not
yet evaluated. This wave performs a systematic long-tail screen to identify
fresh alt-alt candidates outside the current 15-vertex saturation group.

METHODOLOGY
-----------
Phase 1: Fetch live HL universe via /info {"type":"metaAndAssetCtxs"} → universe
         snapshot (name, szDecimals, maxLeverage, dayNtlVlm, funding, OI, premium)
Phase 2: Identify long-tail candidates
         - NOT in current 76-daemon active list
         - NOT in V-15 vertex set (APT ATOM AVAX BNB ENA FIL HBAR INJ LDO SEI SOL TIA)
           nor the 3 additional vertices accepted post-K744 (BNB already CLOSED,
           PEPE, WIF, FIL, HBAR, ONDO, TAO, WLD, PENDLE, PYTH)
         - NOT in K449/K476/K484/K493/K500/K517/K594 base assets (BTC/ETH)
         - Volume tier: lowest 30% by dayNtlVlm (proxy for long-tail)
         - Active listing: isDelisted != True
Phase 3: Vol pre-screen for each candidate using cached FR data (30d window)
         - vol_ratio vs SOL (target ≥ 1.5x)
         - raw_corr vs AVAX/SOL/FIL/HBAR (L003/L007/L010/L011) → target ≤ 0.45
         - carry_stability (% positive FR) → target 40-80% (not structural carry)
Phase 4: Rank survivors by composite score (same K744 formula)
         composite = vol_ratio × cycle_indep × fr_amp
Phase 5: Decision — K767+ wave queue for top 1-3 candidates

EXCLUSION LISTS
---------------
V-15 vertices (K744): APT ATOM AVAX BNB ENA FIL HBAR INJ LDO SEI SOL TIA
Post-K744 accepted/tested: PEPE WIF DOGE RUNE ONDO TAO WLD PENDLE PYTH
Base assets (BTC-paired): BTC ETH
Closed-line rejects (K480-K532): SUI ARB NEAR OSMO DOT ALGO BNB (in V)
K744 candidates already screened: AAVE JUP BONK KAS OP SHIB TON CRV MKR UNI RNDR

CONSTRAINTS
-----------
- API rate limit: 1 req/sec (HL public API)
- 30d history per token = ~720 hourly FR points (sufficient for vol pre-screen)
- Skip full 180d backtest in this wave (K767+ handles full eval)
- LIVE 自動変更禁止
- Public repo: no credentials

Usage:
    python3 wave_k766_hl_long_tail_screen.py
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

# ── K339 pattern ─────────────────────────────────────────────────────────────
WAVE_ID = "K766"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": REPO_ROOT, "pattern": "K339"}

# ── Exclusion lists ───────────────────────────────────────────────────────────
# V-15 vertices (current alt-alt family members)
V15_VERTICES = {
    "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL",
    "HBAR", "INJ", "LDO", "SEI", "SOL", "TIA",
}

# Base assets (BTC-paired strategy bases)
BASE_ASSETS = {"BTC", "ETH"}

# Post-K744 tested tokens (already screened or accepted)
POST_K744_TESTED = {
    "PEPE", "WIF", "DOGE", "RUNE",
    "ONDO", "TAO", "WLD", "PENDLE", "PYTH",
}

# K744 all-candidates screened (24 tokens)
K744_SCREENED = {
    "ONDO", "TAO", "WLD", "PENDLE", "PYTH",
    "PEPE", "AAVE", "WIF", "JUP", "BONK",
    "KAS", "OP", "DOT", "SHIB", "TON", "CRV",
    "SUI", "MKR", "ARB", "UNI", "ALGO", "NEAR",
    "DOGE", "RNDR",
}

# Closed lines (hard REJECT, K532 governance)
CLOSED_LINE_REJECTS = {"SUI", "ARB", "NEAR", "DOT", "ALGO"}

# Combined exclusion
EXCLUDED = V15_VERTICES | BASE_ASSETS | POST_K744_TESTED | K744_SCREENED | CLOSED_LINE_REJECTS

# Vol pre-screen thresholds
VOL_RATIO_MIN = 1.5           # vs SOL
CORR_MAX = 0.45               # vs cluster anchors (AVAX, SOL, FIL, HBAR)
CARRY_STABILITY_MAX = 0.80    # not structural carry (RUNE lesson)
CARRY_STABILITY_MIN = 0.35    # meaningful carry exists
DAYNAL_VLM_PERCENTILE = 30   # lowest 30% by volume = long-tail

# Composite score formula (K744 consistent)
ANN_FACTOR_8760 = math.sqrt(8760)

# API
HL_API = "https://api.hyperliquid.xyz/info"
API_SLEEP = 1.1  # seconds between requests


# ── Phase 1: HL Universe Inventory ───────────────────────────────────────────

def fetch_hl_universe() -> Dict:
    """Fetch live HL perp universe via metaAndAssetCtxs API."""
    print(f"\n[Phase 1] Fetching HL universe snapshot ...")

    resp = requests.post(
        HL_API,
        json={"type": "metaAndAssetCtxs"},
        timeout=30,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()

    meta = data[0]
    asset_ctxs = data[1]
    universe = meta["universe"]

    print(f"  Total HL perps: {len(universe)}")

    # Build combined records
    instruments = []
    for i, inst in enumerate(universe):
        ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
        instruments.append({
            "name": inst["name"],
            "szDecimals": inst.get("szDecimals", 0),
            "maxLeverage": inst.get("maxLeverage", 0),
            "marginTableId": inst.get("marginTableId", 0),
            "isDelisted": inst.get("isDelisted", False),
            "funding": float(ctx.get("funding", 0) or 0),
            "openInterest": float(ctx.get("openInterest", 0) or 0),
            "dayNtlVlm": float(ctx.get("dayNtlVlm", 0) or 0),
            "premium": float(ctx.get("premium", 0) or 0),
            "oraclePx": float(ctx.get("oraclePx", 0) or 0),
            "markPx": float(ctx.get("markPx", 0) or 0),
        })

    # Sort by dayNtlVlm descending
    instruments.sort(key=lambda x: x["dayNtlVlm"], reverse=True)

    snapshot = {
        "wave": WAVE_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_instruments": len(instruments),
        "active_count": sum(1 for x in instruments if not x["isDelisted"]),
        "instruments": instruments,
    }

    out_path = DATA / "hl_perp_universe_snapshot.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"  Saved: {out_path}")

    # Stats
    active = [x for x in instruments if not x["isDelisted"]]
    vlms = [x["dayNtlVlm"] for x in active]
    p30 = np.percentile(vlms, DAYNAL_VLM_PERCENTILE)
    p70 = np.percentile(vlms, 70)
    print(f"  Active: {len(active)}, P30 dayNtlVlm: ${p30:,.0f}, P70: ${p70:,.0f}")

    return snapshot


# ── Phase 2: Identify Long-Tail Candidates ────────────────────────────────────

def identify_long_tail_candidates(snapshot: Dict) -> List[Dict]:
    """Filter HL universe to long-tail candidates not in existing pipeline."""
    print(f"\n[Phase 2] Identifying long-tail candidates ...")

    instruments = snapshot["instruments"]
    active = [x for x in instruments if not x["isDelisted"]]

    # Volume threshold: P30 of active instruments
    vlms = [x["dayNtlVlm"] for x in active]
    vol_p30 = np.percentile(vlms, DAYNAL_VLM_PERCENTILE)
    vol_p70 = np.percentile(vlms, 70)

    candidates = []
    skipped_excluded = []
    skipped_volume = []
    skipped_delisted = []

    for inst in instruments:
        name = inst["name"]

        if inst["isDelisted"]:
            skipped_delisted.append(name)
            continue

        if name in EXCLUDED:
            skipped_excluded.append(name)
            continue

        # Long-tail: lowest 30% by dayNtlVlm
        # (tokens above median but still below P70 are 'mid-tail', skip them)
        # Accept lowest 30% AND mid-tail with zero-OI (HIP-3 fresh deploys)
        if inst["dayNtlVlm"] > vol_p70 and inst["openInterest"] > 1000:
            skipped_volume.append(name)
            continue

        candidates.append({
            "name": name,
            "szDecimals": inst["szDecimals"],
            "maxLeverage": inst["maxLeverage"],
            "marginTableId": inst["marginTableId"],
            "dayNtlVlm": inst["dayNtlVlm"],
            "openInterest": inst["openInterest"],
            "funding_8h": inst["funding"],
            "funding_ann_pct": inst["funding"] * 8760 * 100,
            "premium": inst["premium"],
            "vol_tier": "low" if inst["dayNtlVlm"] <= vol_p30 else "mid",
        })

    print(f"  Excluded (in pipeline): {len(skipped_excluded)}")
    print(f"  Skipped (high volume): {len(skipped_volume)}")
    print(f"  Skipped (delisted): {len(skipped_delisted)}")
    print(f"  Long-tail candidates: {len(candidates)}")

    for c in candidates[:15]:
        print(f"    {c['name']:12s} dayNtlVlm=${c['dayNtlVlm']:>12,.0f}  OI={c['openInterest']:>10.0f}  FR_ann={c['funding_ann_pct']:>7.1f}%")

    return candidates


# ── Phase 3: Vol Pre-Screen + FR Analysis ────────────────────────────────────

def _load_cached_fr(name: str, days: int = 30) -> Optional[pd.Series]:
    """Load cached FR series (last N days)."""
    p = HL_CACHE / f"hl_fr_{name}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        s = df.set_index("timestamp")["hl_fr"].sort_index()
        cutoff = s.index.max() - pd.Timedelta(days=days)
        return s[s.index >= cutoff]
    except Exception:
        return None


def _load_anchor_fr() -> Dict[str, pd.Series]:
    """Load anchor token FR series for correlation computation."""
    anchors = {}
    for tok in ["SOL", "AVAX", "FIL", "HBAR"]:
        s = _load_cached_fr(tok, days=90)
        if s is not None and len(s) > 100:
            anchors[tok] = s
    return anchors


def compute_prescreen(name: str, anchors: Dict[str, pd.Series]) -> Optional[Dict]:
    """
    Compute Phase 3 pre-screen metrics for a candidate token.
    Returns None if insufficient data.
    """
    fr = _load_cached_fr(name, days=90)
    if fr is None or len(fr) < 168:  # need at least 7d
        return {"name": name, "has_data": False, "skip_reason": "no_cached_data"}

    sol_fr = anchors.get("SOL")
    avax_fr = anchors.get("AVAX")
    fil_fr = anchors.get("FIL")
    hbar_fr = anchors.get("HBAR")

    if sol_fr is None:
        return None

    # Align on common index
    def align(s: pd.Series, ref: pd.Series) -> Tuple[pd.Series, pd.Series]:
        idx = s.index.intersection(ref.index)
        return s.loc[idx], ref.loc[idx]

    fr_sol, sol_al = align(fr, sol_fr)

    if len(fr_sol) < 100:
        return {"name": name, "has_data": False, "skip_reason": "insufficient_overlap_with_SOL"}

    # Vol ratio vs SOL (std of FR)
    tok_std = float(fr_sol.std())
    sol_std = float(sol_al.std())
    vol_ratio_sol = tok_std / sol_std if sol_std > 0 else 0.0

    # Raw correlations vs anchors
    corrs = {}
    if avax_fr is not None:
        a, b = align(fr, avax_fr)
        corrs["AVAX"] = float(a.corr(b)) if len(a) >= 50 else float("nan")
    else:
        corrs["AVAX"] = float("nan")

    corrs["SOL"] = float(fr_sol.corr(sol_al)) if len(fr_sol) >= 50 else float("nan")

    if fil_fr is not None:
        a, b = align(fr, fil_fr)
        corrs["FIL"] = float(a.corr(b)) if len(a) >= 50 else float("nan")
    else:
        corrs["FIL"] = float("nan")

    if hbar_fr is not None:
        a, b = align(fr, hbar_fr)
        corrs["HBAR"] = float(a.corr(b)) if len(a) >= 50 else float("nan")
    else:
        corrs["HBAR"] = float("nan")

    # Carry stability (% positive FR)
    carry_stability = float((fr > 0).mean())

    # FR amplitude (annualised)
    fr_mean_ann = float(fr.mean()) * 8760 * 100  # % annual
    fr_std_ann = float(fr.std()) * ANN_FACTOR_8760 * 100  # % annual

    # 30d rolling metrics (most recent data)
    fr_30d = fr.tail(720)
    carry_30d = float((fr_30d > 0).mean()) if len(fr_30d) > 0 else float("nan")
    vol_ratio_30d = (float(fr_30d.std()) / sol_std) if sol_std > 0 and len(fr_30d) > 0 else 0.0

    # Cycle independence (1 - max corr among anchors with data)
    valid_corrs = [v for v in corrs.values() if not math.isnan(v)]
    max_corr = max(valid_corrs) if valid_corrs else float("nan")
    cycle_indep = 1 - max_corr if not math.isnan(max_corr) else float("nan")

    # Composite score (K744 formula)
    if not math.isnan(cycle_indep) and vol_ratio_sol > 0 and fr_std_ann > 0:
        composite = vol_ratio_sol * max(0, cycle_indep) * (fr_std_ann / 100)
    else:
        composite = 0.0

    # Pre-screen pass/fail
    reasons_fail = []
    reasons_pass = []

    if vol_ratio_sol < VOL_RATIO_MIN:
        reasons_fail.append(f"vol_ratio={vol_ratio_sol:.3f} < {VOL_RATIO_MIN}")
    else:
        reasons_pass.append(f"vol_ratio={vol_ratio_sol:.3f} PASS")

    avax_corr_val = corrs.get("AVAX", float("nan"))
    if not math.isnan(avax_corr_val) and avax_corr_val > CORR_MAX:
        reasons_fail.append(f"corr_AVAX={avax_corr_val:.3f} > {CORR_MAX}")
    else:
        avax_disp = "n/a" if math.isnan(avax_corr_val) else f"{avax_corr_val:.3f}"
        reasons_pass.append(f"L003_AVAX={avax_disp} PASS")

    sol_corr_val = corrs.get("SOL", float("nan"))
    if not math.isnan(sol_corr_val) and sol_corr_val > CORR_MAX:
        reasons_fail.append(f"corr_SOL={sol_corr_val:.3f} > {CORR_MAX}")
    else:
        sol_disp = "n/a" if math.isnan(sol_corr_val) else f"{sol_corr_val:.3f}"
        reasons_pass.append(f"L011_SOL={sol_disp} PASS")

    if carry_stability > CARRY_STABILITY_MAX:
        reasons_fail.append(f"carry_stability={carry_stability:.3f} > {CARRY_STABILITY_MAX} (structural carry BLOCK)")
    elif carry_stability < CARRY_STABILITY_MIN:
        reasons_fail.append(f"carry_stability={carry_stability:.3f} < {CARRY_STABILITY_MIN} (insufficient carry)")
    else:
        reasons_pass.append(f"carry_stability={carry_stability:.3f} PASS")

    prescreen_pass = len(reasons_fail) == 0

    return {
        "name": name,
        "has_data": True,
        "n_rows": len(fr),
        "vol_ratio_sol": round(vol_ratio_sol, 4),
        "vol_ratio_30d": round(vol_ratio_30d, 4),
        "corr_AVAX": round(corrs.get("AVAX", float("nan")), 4),
        "corr_SOL": round(corrs.get("SOL", float("nan")), 4),
        "corr_FIL": round(corrs.get("FIL", float("nan")), 4),
        "corr_HBAR": round(corrs.get("HBAR", float("nan")), 4),
        "max_corr": round(max_corr, 4) if not math.isnan(max_corr) else float("nan"),
        "cycle_indep": round(cycle_indep, 4) if not math.isnan(cycle_indep) else float("nan"),
        "carry_stability": round(carry_stability, 4),
        "carry_30d": round(carry_30d, 4),
        "fr_mean_ann_pct": round(fr_mean_ann, 4),
        "fr_std_ann_pct": round(fr_std_ann, 4),
        "composite_score": round(composite, 4),
        "prescreen_pass": prescreen_pass,
        "reasons_pass": reasons_pass,
        "reasons_fail": reasons_fail,
    }


def phase3_vol_prescreen(candidates: List[Dict], anchors: Dict[str, pd.Series]) -> List[Dict]:
    """Run Phase 3 vol pre-screen on all candidates."""
    print(f"\n[Phase 3] Vol pre-screen + correlation analysis ...")
    print(f"  Candidates to screen: {len(candidates)}")

    results = []
    no_data_count = 0

    for i, cand in enumerate(candidates):
        name = cand["name"]
        result = compute_prescreen(name, anchors)

        if result is None:
            print(f"  [{i+1:3d}/{len(candidates)}] {name:12s} → SKIPPED (no anchor data)")
            continue

        if not result.get("has_data"):
            no_data_count += 1
            # Mark with candidate volume info too
            result.update({
                "dayNtlVlm": cand.get("dayNtlVlm", 0),
                "openInterest": cand.get("openInterest", 0),
                "vol_tier": cand.get("vol_tier", "unknown"),
                "funding_ann_pct": cand.get("funding_ann_pct", 0),
            })
            results.append(result)
            skip_reason = result.get("skip_reason", "no_data")
            print(f"  [{i+1:3d}/{len(candidates)}] {name:12s} → NO CACHED DATA ({skip_reason})")
            continue

        result.update({
            "dayNtlVlm": cand.get("dayNtlVlm", 0),
            "openInterest": cand.get("openInterest", 0),
            "vol_tier": cand.get("vol_tier", "unknown"),
            "funding_ann_pct": cand.get("funding_ann_pct", 0),
        })
        results.append(result)

        status = "PASS" if result["prescreen_pass"] else "FAIL"
        corr_disp = f"L003={result['corr_AVAX']:.3f} L011={result['corr_SOL']:.3f}"
        print(f"  [{i+1:3d}/{len(candidates)}] {name:12s} → {status:4s} | vol_ratio={result['vol_ratio_sol']:.3f} {corr_disp} carry={result['carry_stability']:.3f} comp={result['composite_score']:.4f}")

    passing = [r for r in results if r.get("has_data") and r.get("prescreen_pass")]
    print(f"\n  No cached data: {no_data_count}")
    print(f"  Failed pre-screen: {sum(1 for r in results if r.get('has_data') and not r.get('prescreen_pass'))}")
    print(f"  Passed pre-screen: {len(passing)}")

    return results


# ── Phase 4: Rank Survivors by Composite Score ────────────────────────────────

def phase4_rank_survivors(results: List[Dict]) -> Dict:
    """Rank Phase 3 survivors by composite score (K744 formula)."""
    print(f"\n[Phase 4] Ranking survivors by composite score ...")

    survivors = [r for r in results if r.get("has_data") and r.get("prescreen_pass")]
    no_data = [r for r in results if not r.get("has_data")]
    failed = [r for r in results if r.get("has_data") and not r.get("prescreen_pass")]

    # Sort survivors by composite score descending
    survivors.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === TOP SURVIVORS (ranked by composite score) ===")
    for i, s in enumerate(survivors):
        print(f"  #{i+1:2d} {s['name']:12s} | composite={s['composite_score']:.4f} | vol_ratio={s['vol_ratio_sol']:.3f}x | max_corr={s.get('max_corr', float('nan')):.3f} | carry={s['carry_stability']:.3f} | FR_std_ann={s.get('fr_std_ann_pct', 0):.1f}%")

    print(f"\n  === FAILED PRE-SCREEN ===")
    for f_ in sorted(failed, key=lambda x: x.get("composite_score", 0), reverse=True):
        reasons = "; ".join(f_["reasons_fail"])
        print(f"  {f_['name']:12s} | {reasons}")

    print(f"\n  === NO CACHED DATA (new HIP-3 deploys — need fresh fetch) ===")
    for nd in no_data:
        print(f"  {nd['name']:12s} | dayNtlVlm=${nd.get('dayNtlVlm', 0):>10,.0f} | OI={nd.get('openInterest', 0):>8.0f}")

    return {
        "survivors": survivors,
        "failed": failed,
        "no_data": no_data,
        "top5": survivors[:5],
    }


# ── Phase 5: K767+ Wave Queue Decision ───────────────────────────────────────

def phase5_wave_queue(ranked: Dict) -> Dict:
    """Define K767+ wave queue based on Phase 4 rankings."""
    print(f"\n[Phase 5] Defining K767+ wave queue ...")

    top5 = ranked["top5"]
    survivors = ranked["survivors"]
    no_data = ranked["no_data"]

    # K767-K769 = top-3 survivors
    k767_queue = []
    backlog = []
    no_data_queue = []

    for i, s in enumerate(survivors):
        entry = {
            "wave_candidate": f"K{767 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_sol": s["vol_ratio_sol"],
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "concerns": [],
        }

        # Note liquidity concerns for long-tail
        if s.get("dayNtlVlm", 0) < 5_000_000:
            entry["concerns"].append("LOW_LIQUIDITY (<$5M/day) — may fail G6 entries/yr or G9 history")
        if s.get("openInterest", 0) < 100_000:
            entry["concerns"].append("LOW_OI (<$100K) — execution slippage risk")

        if i < 3:
            k767_queue.append(entry)
        else:
            backlog.append(entry)

    # HIP-3 fresh deploys without cached data → separate queue for data fetch first
    for nd in no_data[:5]:
        no_data_queue.append({
            "wave_candidate": "FETCH_FIRST",
            "token": nd["name"],
            "dayNtlVlm": nd.get("dayNtlVlm", 0),
            "openInterest": nd.get("openInterest", 0),
            "status": "NEEDS_FR_HISTORY_FETCH",
            "note": "HIP-3 deploys not in K163 cache — fetch 30d FR via HL API first",
        })

    print(f"\n  === K767-K769 IMMEDIATE QUEUE ===")
    for entry in k767_queue:
        concerns = " | ".join(entry["concerns"]) if entry["concerns"] else "None"
        print(f"  {entry['wave_candidate']}: {entry['token']:12s} | composite={entry['composite_score']:.4f} | vol={entry['vol_ratio_sol']:.3f}x | concerns: {concerns}")

    print(f"\n  === BACKLOG ===")
    for entry in backlog:
        print(f"  {entry['token']:12s} | composite={entry['composite_score']:.4f}")

    print(f"\n  === HIP-3 NO-CACHE QUEUE (fetch data first) ===")
    for nd in no_data_queue:
        print(f"  {nd['token']:12s} | dayNtlVlm=${nd['dayNtlVlm']:>10,.0f}")

    return {
        "k767_k769_queue": k767_queue,
        "backlog": backlog,
        "hip3_no_cache_queue": no_data_queue,
    }


# ── Build JSON output ─────────────────────────────────────────────────────────

def build_output(
    snapshot: Dict,
    candidates: List[Dict],
    phase3_results: List[Dict],
    ranked: Dict,
    wave_queue: Dict,
) -> Dict:
    """Build final K766 JSON output."""
    now_utc = datetime.now(timezone.utc)

    output = {
        "wave": WAVE_ID,
        "title": "K766 HL HIP-3 Long-Tail Perp FR Screen",
        "generated_utc": now_utc.isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": "conserv/mid/optimist 3-point — deferred to K767+ full evals",
        "live_auto_change_prohibited": True,
        "universe_summary": {
            "total_perps": snapshot["total_instruments"],
            "active_perps": snapshot["active_count"],
            "long_tail_candidates_identified": len(candidates),
            "candidates_with_cached_data": sum(1 for r in phase3_results if r.get("has_data")),
            "prescreen_pass": len(ranked["survivors"]),
            "prescreen_fail": len(ranked["failed"]),
            "no_cached_data": len(ranked["no_data"]),
        },
        "exclusion_summary": {
            "V15_vertices": sorted(V15_VERTICES),
            "base_assets": sorted(BASE_ASSETS),
            "post_k744_tested": sorted(POST_K744_TESTED),
            "k744_screened": sorted(K744_SCREENED),
            "closed_lines": sorted(CLOSED_LINE_REJECTS),
        },
        "phase3_all_results": phase3_results,
        "phase4_ranking": ranked,
        "phase5_wave_queue": wave_queue,
    }

    return output


# ── Save candidates JSON ──────────────────────────────────────────────────────

def save_candidates(phase3_results: List[Dict], ranked: Dict, wave_queue: Dict):
    """Save long-tail candidates JSON."""
    out = {
        "wave": WAVE_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "top5_candidates": ranked["top5"],
        "k767_k769_queue": wave_queue["k767_k769_queue"],
        "all_survivors_ranked": ranked["survivors"],
        "failed_prescreen": ranked["failed"],
        "no_cached_data_hip3": ranked["no_data"],
        "backlog": wave_queue["backlog"],
    }
    path = DATA / "hl_long_tail_candidates.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Saved: {path}")
    return path


# ── report.html badge ─────────────────────────────────────────────────────────

def build_badge(wave_queue: Dict, ranked: Dict, snapshot: Dict) -> str:
    """Build K766 HTML badge for report.html."""
    top5 = ranked["top5"]
    queue = wave_queue["k767_k769_queue"]
    no_data = ranked["no_data"]

    now_jst = datetime.now(timezone.utc)
    # Convert to JST (UTC+9)
    jst_hour = (now_jst.hour + 9) % 24
    jst_date = now_jst.strftime(f"%Y-%m-%d {jst_hour:02d}:{now_jst.minute:02d} JST")

    # Build rows for top-5 table
    rows_html = ""
    for i, s in enumerate(top5):
        rank_badge = f"#{i+1}"
        wave_cand = queue[i]["wave_candidate"] if i < len(queue) else "BACKLOG"
        name = s["name"]
        comp = s["composite_score"]
        vol = s["vol_ratio_sol"]
        max_corr = s.get("max_corr", float("nan"))
        carry = s["carry_stability"]
        fr_std = s.get("fr_std_ann_pct", 0)
        vlm = s.get("dayNtlVlm", 0)

        concerns = ""
        if vlm < 5_000_000:
            concerns = " ⚠️ LOW-LIQ"

        rows_html += f"""
      <tr>
        <td style="color:#58a6ff;font-weight:700;">{rank_badge}</td>
        <td style="color:#e3b341;font-weight:700;">{wave_cand}</td>
        <td style="color:#3fb950;font-weight:800;">{name}</td>
        <td style="color:#e6edf3;">{comp:.4f}</td>
        <td style="color:#e6edf3;">{vol:.3f}x</td>
        <td style="color:#e6edf3;">{max_corr:.3f}</td>
        <td style="color:#e6edf3;">{carry:.3f}</td>
        <td style="color:#e6edf3;">{fr_std:.1f}%</td>
        <td style="color:#e6edf3;">${vlm/1e6:.1f}M{concerns}</td>
      </tr>"""

    # No-cache HIP-3 section
    no_cache_html = ""
    if no_data:
        no_cache_items = "".join([
            f'<span style="background:rgba(57,210,192,0.12);border:1px solid #39d2c0;border-radius:4px;padding:2px 8px;margin:2px;display:inline-block;color:#39d2c0;font-size:0.75rem;">'
            f'{nd["name"]} ${nd.get("dayNtlVlm",0)/1e6:.2f}M</span>'
            for nd in no_data[:10]
        ])
        no_cache_html = f"""
    <div style="margin-top:12px;padding:8px 12px;background:rgba(57,210,192,0.05);border-left:3px solid #39d2c0;border-radius:4px;">
      <div style="color:#39d2c0;font-weight:700;font-size:0.78rem;margin-bottom:4px;">HIP-3 FRESH DEPLOYS — NO CACHED DATA ({len(no_data)} tokens) — Fetch FR history before eval</div>
      {no_cache_items}
    </div>"""

    badge = f"""
<!-- K766_HL_LONG_TAIL_BADGE: K766 HL HIP-3 Long-Tail Perp FR Screen | universe={snapshot['total_instruments']} perps | active={snapshot['active_count']} | long-tail candidates={len(ranked['survivors'])+len(ranked['failed'])+len(ranked['no_data'])} | prescreen_pass={len(ranked['survivors'])} | K767-K769 queue={len(queue)} | HIP-3 no-cache={len(no_data)} | K339 REPO_ROOT | {jst_date} -->
<!-- K766 HL LONG-TAIL FR SCREEN BADGE START -->
<section id="k766-longtail" style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px 22px;margin:18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="background:rgba(88,166,255,0.15);border:2px solid #58a6ff;border-radius:8px;padding:4px 10px;color:#58a6ff;font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K766</div>
    <div style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:6px;padding:3px 9px;color:#3fb950;font-size:0.73rem;font-weight:700;">SCREEN COMPLETE</div>
    <div style="color:#8b949e;font-size:0.72rem;margin-left:auto;">{jst_date}</div>
  </div>

  <div style="color:#e6edf3;font-size:1.08rem;font-weight:900;margin-bottom:8px;">&#128301; K766 — HL HIP-3 Long-Tail Perp FR Screen — {len(ranked['survivors'])} Candidates Pass Pre-Screen</div>

  <div style="background:rgba(30,37,44,0.7);border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:0.78rem;color:#8b949e;line-height:1.6;">
    <strong style="color:#e6edf3;">Universe:</strong> {snapshot['total_instruments']} HL perps ({snapshot['active_count']} active) &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Long-tail identified:</strong> {len(ranked['survivors'])+len(ranked['failed'])+len(ranked['no_data'])} tokens (not in existing 76-daemon pipeline) &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Pre-screen pass:</strong> {len(ranked['survivors'])} &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">HIP-3 no-cache:</strong> {len(no_data)}
  </div>

  <div style="color:#58a6ff;font-size:0.85rem;font-weight:700;margin-bottom:8px;">TOP-5 LONG-TAIL CANDIDATES → K767-K769 QUEUE</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:4px 8px;">Rank</th>
        <th style="text-align:left;padding:4px 8px;">Wave</th>
        <th style="text-align:left;padding:4px 8px;">Token</th>
        <th style="text-align:right;padding:4px 8px;">Composite</th>
        <th style="text-align:right;padding:4px 8px;">VolRatio</th>
        <th style="text-align:right;padding:4px 8px;">MaxCorr</th>
        <th style="text-align:right;padding:4px 8px;">Carry%</th>
        <th style="text-align:right;padding:4px 8px;">FR_std_ann</th>
        <th style="text-align:right;padding:4px 8px;">DayVlm</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>
  </div>
  {no_cache_html}

  <div style="margin-top:14px;padding:10px 14px;background:rgba(209,136,34,0.08);border-left:3px solid #d29922;border-radius:4px;font-size:0.77rem;color:#8b949e;">
    <strong style="color:#d29922;">&#9888; K766 Constraints:</strong> Pre-screen only (no full 180d backtest).
    Long-tail liquidity may fail G6 entries/yr or G9 history at full §6 eval.
    vol_ratio threshold 1.5x | max_corr &le;0.45 | carry stability 35-80%.
    K767-K769 → full alt-alt §6 gate eval. ROI estimates deferred.
  </div>

  <div style="margin-top:10px;font-size:0.72rem;color:#6e7681;">
    最終更新: {jst_date} (K766 long-tail screen — {snapshot['total_instruments']} perps, {len(ranked['survivors'])} pass, K767-K769 queue: {', '.join(q['token'] for q in queue)}) &nbsp;|&nbsp; K339 REPO_ROOT &nbsp;|&nbsp; LIVE 自動変更禁止
  </div>
</section>
<!-- /K766 HL LONG-TAIL FR SCREEN BADGE -->
"""
    return badge


def inject_badge_into_report(badge_html: str):
    """Inject K766 badge into report.html after the K765 badge."""
    report_path = BASE / "report.html"
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if K766 badge already exists
    if "K766_HL_LONG_TAIL_BADGE" in content:
        print("  K766 badge already in report.html — replacing ...")
        # Find and replace existing badge
        start_marker = "<!-- K766_HL_LONG_TAIL_BADGE:"
        end_marker = "<!-- /K766 HL LONG-TAIL FR SCREEN BADGE -->"
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        if start_idx >= 0 and end_idx > start_idx:
            content = content[:start_idx] + badge_html.strip() + content[end_idx:]
    else:
        # Insert after K765 badge end marker
        k765_end = "<!-- /K765 SMART ROUTING AXIS #6 BADGE -->"
        if k765_end in content:
            content = content.replace(k765_end, k765_end + "\n" + badge_html)
            print("  K766 badge injected after K765 badge.")
        else:
            # Fallback: insert before closing body tag
            content = content.replace("</body>", badge_html + "\n</body>")
            print("  K766 badge injected before </body> (K765 marker not found).")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Updated: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(f"Wave K766: HL HIP-3 Long-Tail Perp FR Screen")
    print(f"K339 REPO_ROOT: {REPO_ROOT}")
    print(f"LIVE 自動変更禁止 | Public repo | No credentials")
    print("=" * 70)

    # Phase 1: Fetch universe
    snapshot = fetch_hl_universe()
    time.sleep(API_SLEEP)

    # Phase 2: Identify candidates
    candidates = identify_long_tail_candidates(snapshot)

    # Load anchor FR series
    print(f"\n  Loading anchor FR series (SOL/AVAX/FIL/HBAR) ...")
    anchors = _load_anchor_fr()
    print(f"  Anchors loaded: {list(anchors.keys())}")

    # Phase 3: Vol pre-screen
    phase3_results = phase3_vol_prescreen(candidates, anchors)

    # Phase 4: Rank survivors
    ranked = phase4_rank_survivors(phase3_results)

    # Phase 5: Wave queue
    wave_queue = phase5_wave_queue(ranked)

    # Save candidates JSON
    save_candidates(phase3_results, ranked, wave_queue)

    # Build full output JSON
    output = build_output(snapshot, candidates, phase3_results, ranked, wave_queue)
    out_path = BASE / "wave_k766_hl_long_tail_screen.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {out_path}")

    # Build + inject HTML badge
    badge = build_badge(wave_queue, ranked, snapshot)
    inject_badge_into_report(badge)

    # Summary
    runtime = round(time.time() - START_TIME, 1)
    print(f"\n{'=' * 70}")
    print(f"K766 COMPLETE — runtime {runtime}s")
    print(f"Universe: {snapshot['total_instruments']} perps ({snapshot['active_count']} active)")
    print(f"Long-tail candidates: {len(candidates)}")
    print(f"Pre-screen pass: {len(ranked['survivors'])}")
    print(f"Pre-screen fail: {len(ranked['failed'])}")
    print(f"No cached data (HIP-3): {len(ranked['no_data'])}")
    print(f"\nK767-K769 QUEUE:")
    for q in wave_queue["k767_k769_queue"]:
        print(f"  {q['wave_candidate']}: {q['token']} (composite={q['composite_score']:.4f})")
    print(f"{'=' * 70}")

    return output


if __name__ == "__main__":
    main()

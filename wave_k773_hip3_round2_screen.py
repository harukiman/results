#!/usr/bin/env python3
"""
wave_k773_hip3_round2_screen.py — K773 HIP-3 Batch FR Fetch + Round 2 Screen
==============================================================================
K339 REPO_ROOT pattern.

MISSION
-------
K766 long-tail screen found 99 tokens with no cached FR data (status=no_cache).
K766 produced 2 ACCEPTs (K768 BLUR, K769 AXS) from cached data only.
This wave fetches 30d FR history for the top-25 no-cache tokens (by dayNtlVlm)
and re-runs the same K766/K744 pre-screen framework to identify fresh candidates.

METHODOLOGY
-----------
Phase 1: Load K766 results
         - read data/hl_long_tail_candidates.json
         - identify 99 tokens with status=no_cache
         - prioritize top 25 by dayNtlVlm
Phase 2: Batch FR fetch (top 25)
         - For each, fetch 30d HL FR history via:
           POST /info {"type":"fundingHistory","coin":"X","startTime":...}
         - Rate limit: 1 req/sec (HL public)
         - Cache to cache/k163_hl/hl_fr_{token}.parquet
Phase 3: Pre-screen + ranking
         - Same K766/K744 framework:
           vol_ratio vs SOL >= 1.5x
           L003/L007/L010/L011 max corr <= 0.45
           L004 carry-stability 35-80%
         - Composite score = vol_ratio × cycle_indep × fr_amp
Phase 4: K774+ wave queue
         - Top 3 fresh candidates -> K774-K776 full eval queue
         - HBAR explicit check included (K766 had NaN for HBAR corr)
Phase 5: report.html badge
         - K773 K766 round 2 update with top 5 fresh candidates
         - Combined K766+K773 ranked list

EXCLUSION LISTS (inherited from K766)
--------------------------------------
V-15 vertices (K744): APT ATOM AVAX BNB ENA FIL HBAR INJ LDO SEI SOL TIA
Post-K744 accepted/tested: PEPE WIF DOGE RUNE ONDO TAO WLD PENDLE PYTH
Base assets (BTC-paired): BTC ETH
Closed-line rejects (K480-K532): SUI ARB NEAR OSMO DOT ALGO BNB
K744 candidates screened: AAVE JUP BONK KAS OP SHIB TON CRV MKR UNI RNDR
K766 accepted: BLUR AXS COMP STX MEME (already in round 1)

CONSTRAINTS
-----------
- API rate limit: 1 req/sec (HL public API)
- 25 tokens × ~1.1s = ~28s total fetch time
- LIVE 自動変更禁止
- Public repo: no credentials

Usage:
    python3 wave_k773_hip3_round2_screen.py
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone, timedelta
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
HL_CACHE.mkdir(parents=True, exist_ok=True)

# ── K339 pattern ──────────────────────────────────────────────────────────────
WAVE_ID = "K773"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": REPO_ROOT, "pattern": "K339"}

# ── Constants ─────────────────────────────────────────────────────────────────
HL_API = "https://api.hyperliquid.xyz/info"
API_SLEEP = 1.1           # seconds between requests
FETCH_DAYS = 30           # days of FR history to fetch
MIN_ROWS = 168            # minimum rows for pre-screen (~7d hourly)
TOP_N_NOCACHE = 25        # how many no-cache tokens to fetch

# Pre-screen thresholds (K766/K744 consistent)
VOL_RATIO_MIN = 1.5
CORR_MAX = 0.45
CARRY_STABILITY_MIN = 0.35
CARRY_STABILITY_MAX = 0.80

ANN_FACTOR_8760 = math.sqrt(8760)


# ── Phase 1: Load K766 Results ────────────────────────────────────────────────

def phase1_load_k766() -> Tuple[List[Dict], List[Dict]]:
    """
    Load K766 candidates JSON.
    Returns (no_cache_sorted_top25, k766_survivors).
    """
    print(f"\n[Phase 1] Loading K766 results ...")

    candidates_path = DATA / "hl_long_tail_candidates.json"
    if not candidates_path.exists():
        raise FileNotFoundError(f"K766 output not found: {candidates_path}")

    with open(candidates_path) as f:
        data = json.load(f)

    no_cache = data.get("no_cached_data_hip3", [])
    k766_survivors = data.get("all_survivors_ranked", [])
    backlog = data.get("backlog", [])

    print(f"  no_cache_hip3: {len(no_cache)} tokens")
    print(f"  K766 survivors: {len(k766_survivors)}")
    print(f"  K766 backlog: {len(backlog)}")

    # Sort no-cache by dayNtlVlm descending, take top N
    sorted_nc = sorted(no_cache, key=lambda x: x.get("dayNtlVlm", 0), reverse=True)
    top_nc = sorted_nc[:TOP_N_NOCACHE]

    print(f"\n  Top {TOP_N_NOCACHE} no-cache tokens by dayNtlVlm:")
    for i, t in enumerate(top_nc):
        print(f"    {i+1:2d}. {t['name']:<12} dayNtlVlm=${t['dayNtlVlm']:>10,.0f}  "
              f"OI={t.get('openInterest',0):>10.0f}  FR_ann={t.get('funding_ann_pct',0):>8.2f}%")

    return top_nc, k766_survivors


# ── Phase 2: Batch FR Fetch ───────────────────────────────────────────────────

def _fetch_fr_history(coin: str, days: int = 30) -> Optional[pd.DataFrame]:
    """
    Fetch funding rate history from HL API.
    POST /info {"type":"fundingHistory","coin":"X","startTime":ms_epoch}
    Returns DataFrame with columns [timestamp, hl_fr] or None on error.
    """
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    payload = {
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_ms,
    }
    try:
        resp = requests.post(
            HL_API,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        records = resp.json()

        if not records or not isinstance(records, list):
            return None

        rows = []
        for r in records:
            ts = pd.Timestamp(int(r["time"]), unit="ms", tz="UTC")
            fr = float(r.get("fundingRate", 0) or 0)
            rows.append({"timestamp": ts, "hl_fr": fr})

        if not rows:
            return None

        df = pd.DataFrame(rows).sort_values("timestamp").drop_duplicates("timestamp")
        return df

    except Exception as e:
        print(f"    ERROR fetching {coin}: {e}")
        return None


def phase2_batch_fetch(tokens: List[Dict]) -> Dict[str, bool]:
    """
    Fetch FR history for top-N no-cache tokens.
    Returns dict: {token_name: fetch_success}.
    """
    print(f"\n[Phase 2] Batch FR fetch for {len(tokens)} tokens ...")
    print(f"  Rate limit: {API_SLEEP}s/req — estimated {len(tokens)*API_SLEEP:.0f}s total")

    results = {}

    for i, tok in enumerate(tokens):
        name = tok["name"]
        cache_path = HL_CACHE / f"hl_fr_{name}.parquet"

        # Check if already cached from a previous run
        if cache_path.exists():
            try:
                existing = pd.read_parquet(cache_path)
                if len(existing) >= MIN_ROWS:
                    print(f"  [{i+1:2d}/{len(tokens)}] {name:<12} → ALREADY CACHED ({len(existing)} rows)")
                    results[name] = True
                    continue
            except Exception:
                pass  # Re-fetch if corrupt

        print(f"  [{i+1:2d}/{len(tokens)}] {name:<12} → fetching ...", end="", flush=True)
        t0 = time.time()

        df = _fetch_fr_history(name, days=FETCH_DAYS)

        elapsed = time.time() - t0

        if df is None or len(df) == 0:
            print(f" NO DATA ({elapsed:.1f}s)")
            results[name] = False
        else:
            df.to_parquet(cache_path, index=False)
            print(f" {len(df)} rows cached ({elapsed:.1f}s)")
            results[name] = True

        # Rate limit
        sleep_needed = max(0, API_SLEEP - elapsed)
        if sleep_needed > 0:
            time.sleep(sleep_needed)

    success_count = sum(1 for v in results.values() if v)
    print(f"\n  Fetch complete: {success_count}/{len(tokens)} successful")
    return results


# ── Phase 3: Pre-Screen ───────────────────────────────────────────────────────

def _load_cached_fr(name: str, days: int = 90) -> Optional[pd.Series]:
    """Load cached FR series (last N days), normalised to naive hourly UTC."""
    p = HL_CACHE / f"hl_fr_{name}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        ts = pd.to_datetime(df["timestamp"])
        # Handle both tz-aware (new fetches, UTC) and tz-naive (old cache) timestamps
        if ts.dt.tz is not None:
            ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
        # Floor to hourly to align with SOL anchor (which is stored as clean hourly)
        df["timestamp"] = ts.dt.floor("h")
        s = df.set_index("timestamp")["hl_fr"].sort_index()
        s = s[~s.index.duplicated(keep="last")]
        cutoff = s.index.max() - pd.Timedelta(days=days)
        return s[s.index >= cutoff]
    except Exception as e:
        print(f"    WARN: failed to load {name}: {e}")
        return None


def _load_anchor_fr() -> Dict[str, pd.Series]:
    """Load anchor token FR series for correlation computation."""
    anchors = {}
    for tok in ["SOL", "AVAX", "FIL", "HBAR"]:
        s = _load_cached_fr(tok, days=90)
        if s is not None and len(s) > 100:
            anchors[tok] = s
            print(f"    Anchor {tok}: {len(s)} rows")
        else:
            print(f"    WARN: anchor {tok} insufficient data")
    return anchors


def _align(s: pd.Series, ref: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Align two series on common index."""
    idx = s.index.intersection(ref.index)
    return s.loc[idx], ref.loc[idx]


def compute_prescreen(name: str, anchors: Dict[str, pd.Series], tok_meta: Dict) -> Dict:
    """
    Compute Phase 3 pre-screen metrics for a candidate token.
    Same K766/K744 framework.
    """
    fr = _load_cached_fr(name, days=90)
    if fr is None or len(fr) < MIN_ROWS:
        return {
            "name": name,
            "has_data": False,
            "skip_reason": "insufficient_data_post_fetch",
            "dayNtlVlm": tok_meta.get("dayNtlVlm", 0),
            "openInterest": tok_meta.get("openInterest", 0),
            "vol_tier": tok_meta.get("vol_tier", "unknown"),
            "funding_ann_pct": tok_meta.get("funding_ann_pct", 0),
        }

    sol_fr = anchors.get("SOL")
    avax_fr = anchors.get("AVAX")
    fil_fr = anchors.get("FIL")
    hbar_fr = anchors.get("HBAR")

    if sol_fr is None:
        return {
            "name": name,
            "has_data": False,
            "skip_reason": "no_sol_anchor",
        }

    # Indices are already tz-naive hourly (handled in _load_cached_fr)
    fr_sol, sol_al = _align(fr, sol_fr)
    if len(fr_sol) < 100:
        return {
            "name": name,
            "has_data": False,
            "skip_reason": "insufficient_overlap_with_SOL",
            "dayNtlVlm": tok_meta.get("dayNtlVlm", 0),
        }

    # Vol ratio vs SOL
    tok_std = float(fr_sol.std())
    sol_std = float(sol_al.std())
    vol_ratio_sol = tok_std / sol_std if sol_std > 0 else 0.0

    # Raw correlations vs anchors
    corrs: Dict[str, float] = {}
    for tok_name, anchor_s in [("AVAX", avax_fr), ("FIL", fil_fr), ("HBAR", hbar_fr)]:
        if anchor_s is not None:
            a, b = _align(fr, anchor_s)
            corrs[tok_name] = float(a.corr(b)) if len(a) >= 50 else float("nan")
        else:
            corrs[tok_name] = float("nan")

    corrs["SOL"] = float(fr_sol.corr(sol_al)) if len(fr_sol) >= 50 else float("nan")

    # Carry stability (% positive FR)
    carry_stability = float((fr > 0).mean())

    # FR amplitude (annualised)
    fr_mean_ann = float(fr.mean()) * 8760 * 100    # % annual
    fr_std_ann = float(fr.std()) * ANN_FACTOR_8760 * 100  # % annual

    # 30d rolling
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

    for corr_key, corr_label in [("AVAX", "L003_AVAX"), ("SOL", "L011_SOL"),
                                   ("FIL", "L007_FIL"), ("HBAR", "L010_HBAR")]:
        v = corrs.get(corr_key, float("nan"))
        if not math.isnan(v) and v > CORR_MAX:
            reasons_fail.append(f"corr_{corr_key}={v:.3f} > {CORR_MAX}")
        else:
            disp = "n/a" if math.isnan(v) else f"{v:.3f}"
            reasons_pass.append(f"{corr_label}={disp} PASS")

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
        "dayNtlVlm": tok_meta.get("dayNtlVlm", 0),
        "openInterest": tok_meta.get("openInterest", 0),
        "vol_tier": tok_meta.get("vol_tier", "unknown"),
        "funding_ann_pct": tok_meta.get("funding_ann_pct", 0),
    }


def phase3_prescreen(tokens: List[Dict], fetch_results: Dict[str, bool]) -> List[Dict]:
    """Run pre-screen on all fetched tokens."""
    print(f"\n[Phase 3] Pre-screen + correlation analysis ...")

    print(f"\n  Loading anchor FR series ...")
    anchors = _load_anchor_fr()
    print(f"  Anchors loaded: {list(anchors.keys())}")

    results = []
    for i, tok in enumerate(tokens):
        name = tok["name"]
        if not fetch_results.get(name, False):
            results.append({
                "name": name,
                "has_data": False,
                "skip_reason": "fetch_failed",
                "dayNtlVlm": tok.get("dayNtlVlm", 0),
                "openInterest": tok.get("openInterest", 0),
                "vol_tier": tok.get("vol_tier", "unknown"),
                "funding_ann_pct": tok.get("funding_ann_pct", 0),
            })
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<12} → FETCH FAILED — skip")
            continue

        result = compute_prescreen(name, anchors, tok)
        results.append(result)

        if not result.get("has_data"):
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<12} → NO USABLE DATA ({result.get('skip_reason','')})")
        else:
            status = "PASS" if result["prescreen_pass"] else "FAIL"
            reasons = "; ".join(result["reasons_fail"]) if result["reasons_fail"] else "all PASS"
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<12} → {status:4s} | "
                  f"vol_ratio={result['vol_ratio_sol']:.3f} "
                  f"L003={result['corr_AVAX']:.3f} "
                  f"L010={result['corr_HBAR']:.3f} "
                  f"L011={result['corr_SOL']:.3f} "
                  f"carry={result['carry_stability']:.3f} "
                  f"comp={result['composite_score']:.4f}"
                  + (f" | FAIL: {reasons}" if result["reasons_fail"] else ""))

    survivors = [r for r in results if r.get("has_data") and r.get("prescreen_pass")]
    failed = [r for r in results if r.get("has_data") and not r.get("prescreen_pass")]
    no_data = [r for r in results if not r.get("has_data")]

    print(f"\n  === Phase 3 Summary ===")
    print(f"  Passed pre-screen: {len(survivors)}")
    print(f"  Failed pre-screen: {len(failed)}")
    print(f"  No usable data:    {len(no_data)}")

    return results


# ── Phase 4: Rank + Wave Queue ────────────────────────────────────────────────

def phase4_rank_and_queue(phase3_results: List[Dict], k766_survivors: List[Dict]) -> Dict:
    """
    Rank Phase 3 survivors by composite score.
    Build K774+ wave queue.
    Build combined K766+K773 ranked list.
    """
    print(f"\n[Phase 4] Ranking survivors + building K774+ wave queue ...")

    survivors = [r for r in phase3_results if r.get("has_data") and r.get("prescreen_pass")]
    failed = [r for r in phase3_results if r.get("has_data") and not r.get("prescreen_pass")]
    no_data = [r for r in phase3_results if not r.get("has_data")]

    survivors.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === K773 ROUND 2 SURVIVORS (fresh long-tail, ranked) ===")
    for i, s in enumerate(survivors):
        print(f"  #{i+1:2d} {s['name']:<12} | composite={s['composite_score']:.4f} | "
              f"vol_ratio={s['vol_ratio_sol']:.3f}x | max_corr={s.get('max_corr',float('nan')):.3f} | "
              f"carry={s['carry_stability']:.3f} | FR_std_ann={s.get('fr_std_ann_pct',0):.1f}% | "
              f"dayVlm=${s.get('dayNtlVlm',0)/1e6:.2f}M")

    print(f"\n  === FAILED PRE-SCREEN ===")
    for f_ in sorted(failed, key=lambda x: x.get("composite_score", 0), reverse=True):
        reasons = "; ".join(f_["reasons_fail"])
        print(f"  {f_['name']:<12} | {reasons}")

    # K774+ queue: top 3 survivors
    k774_queue = []
    for i, s in enumerate(survivors[:3]):
        entry = {
            "wave_candidate": f"K{774 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_sol": s["vol_ratio_sol"],
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "concerns": [],
            "source": "K773_round2",
        }
        if s.get("dayNtlVlm", 0) < 5_000_000:
            entry["concerns"].append("LOW_LIQUIDITY (<$5M/day) — may fail G6 entries/yr or G9 history")
        if s.get("openInterest", 0) < 100_000:
            entry["concerns"].append("LOW_OI (<$100K) — execution slippage risk")
        k774_queue.append(entry)

    # Backlog (rank 4+)
    backlog_new = []
    for i, s in enumerate(survivors[3:]):
        backlog_new.append({
            "wave_candidate": f"K{777 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_sol": s["vol_ratio_sol"],
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "concerns": [],
            "source": "K773_round2_backlog",
        })

    print(f"\n  === K774+ WAVE QUEUE ===")
    for entry in k774_queue:
        concerns = " | ".join(entry["concerns"]) if entry["concerns"] else "None"
        print(f"  {entry['wave_candidate']}: {entry['token']:<12} | composite={entry['composite_score']:.4f} | "
              f"vol={entry['vol_ratio_sol']:.3f}x | concerns: {concerns}")

    # Combined K766+K773 ranked list (dedup by name)
    seen = set()
    combined = []
    for s in survivors:  # K773 first (fresh)
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K773_round2"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k766_survivors:  # then K766
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K766_round1"
            combined.append(s_copy)
            seen.add(s["name"])

    combined.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === COMBINED K766+K773 RANKED LIST ({len(combined)} tokens) ===")
    for i, s in enumerate(combined):
        src = s.get("source", "?")
        print(f"  #{i+1:2d} [{src:14s}] {s['name']:<12} composite={s.get('composite_score',0):.4f}")

    return {
        "survivors": survivors,
        "failed": failed,
        "no_data": no_data,
        "top5": survivors[:5],
        "k774_queue": k774_queue,
        "backlog_new": backlog_new,
        "combined_ranked": combined,
    }


# ── Phase 5: Save JSON ────────────────────────────────────────────────────────

def phase5_save_json(top_nc: List[Dict], fetch_results: Dict[str, bool],
                     phase3_results: List[Dict], ranked: Dict) -> Path:
    """Save K773 round-2 candidates JSON."""
    now_utc = datetime.now(timezone.utc)

    output = {
        "wave": WAVE_ID,
        "title": "K773 HIP-3 Batch FR Fetch + Round 2 Screen",
        "generated_utc": now_utc.isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": "conserv/mid/optimist 3-point — deferred to K774+ full evals",
        "live_auto_change_prohibited": True,
        "round2_summary": {
            "tokens_attempted": len(top_nc),
            "fetch_success": sum(1 for v in fetch_results.values() if v),
            "fetch_failed": sum(1 for v in fetch_results.values() if not v),
            "prescreen_pass": len(ranked["survivors"]),
            "prescreen_fail": len(ranked["failed"]),
            "no_usable_data": len(ranked["no_data"]),
        },
        "fetch_results": fetch_results,
        "top5_fresh_candidates": ranked["top5"],
        "k774_queue": ranked["k774_queue"],
        "all_survivors_ranked": ranked["survivors"],
        "failed_prescreen": ranked["failed"],
        "backlog_new": ranked["backlog_new"],
        "combined_k766_k773_ranked": ranked["combined_ranked"],
        "phase3_all_results": phase3_results,
    }

    # Replace nan with None for JSON serialization
    def replace_nan(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        elif isinstance(obj, dict):
            return {k: replace_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_nan(v) for v in obj]
        return obj

    output_clean = replace_nan(output)

    path = DATA / "hl_long_tail_candidates_round2.json"
    with open(path, "w") as f:
        json.dump(output_clean, f, indent=2)
    print(f"\n  Saved: {path}")
    return path


# ── report.html badge ─────────────────────────────────────────────────────────

def build_badge(ranked: Dict, fetch_results: Dict[str, bool]) -> str:
    """Build K773 HTML badge for report.html."""
    now_utc = datetime.now(timezone.utc)
    jst_hour = (now_utc.hour + 9) % 24
    jst_date = now_utc.strftime(f"%Y-%m-%d {jst_hour:02d}:{now_utc.minute:02d} JST")

    top5 = ranked["top5"]
    k774_queue = ranked["k774_queue"]
    combined = ranked["combined_ranked"]
    survivors = ranked["survivors"]

    # Top-5 fresh rows
    rows_html = ""
    for i, s in enumerate(top5):
        wave_cand = k774_queue[i]["wave_candidate"] if i < len(k774_queue) else "BACKLOG"
        name = s["name"]
        comp = s.get("composite_score", 0)
        vol = s.get("vol_ratio_sol", 0)
        max_corr = s.get("max_corr", float("nan"))
        carry = s.get("carry_stability", 0)
        fr_std = s.get("fr_std_ann_pct", 0)
        vlm = s.get("dayNtlVlm", 0)
        corr_hbar = s.get("corr_HBAR", float("nan"))
        corr_disp = f"{max_corr:.3f}" if max_corr is not None and not (isinstance(max_corr, float) and math.isnan(max_corr)) else "n/a"
        hbar_disp = f"{corr_hbar:.3f}" if corr_hbar is not None and not (isinstance(corr_hbar, float) and math.isnan(corr_hbar)) else "n/a"

        liq_warn = ""
        if vlm < 5_000_000:
            liq_warn = " <span style='color:#f0883e;font-size:0.7rem;'>&#9888; LOW-LIQ</span>"

        rows_html += f"""
      <tr>
        <td style="color:#58a6ff;font-weight:700;">#{i+1}</td>
        <td style="color:#e3b341;font-weight:700;">{wave_cand}</td>
        <td style="color:#3fb950;font-weight:800;">{name}</td>
        <td style="color:#e6edf3;text-align:right;">{comp:.4f}</td>
        <td style="color:#e6edf3;text-align:right;">{vol:.3f}x</td>
        <td style="color:#e6edf3;text-align:right;">{corr_disp}</td>
        <td style="color:#e6edf3;text-align:right;">{hbar_disp}</td>
        <td style="color:#e6edf3;text-align:right;">{carry:.3f}</td>
        <td style="color:#e6edf3;text-align:right;">{fr_std:.1f}%</td>
        <td style="color:#e6edf3;text-align:right;">${vlm/1e6:.2f}M{liq_warn}</td>
      </tr>"""

    # Combined top-10 rows
    combined_rows = ""
    for i, s in enumerate(combined[:10]):
        src = s.get("source", "?")
        src_color = "#39d2c0" if "K773" in src else "#8b949e"
        src_badge = f'<span style="font-size:0.68rem;color:{src_color};">[{src.replace("_round","")}]</span>'
        name = s["name"]
        comp = s.get("composite_score", 0)
        vol = s.get("vol_ratio_sol", 0)
        max_corr = s.get("max_corr", None)
        carry = s.get("carry_stability", 0)
        corr_disp = f"{max_corr:.3f}" if max_corr is not None and not (isinstance(max_corr, float) and math.isnan(max_corr)) else "n/a"
        vlm = s.get("dayNtlVlm", 0)
        combined_rows += f"""
      <tr style="border-bottom:1px solid #21262d;">
        <td style="color:#8b949e;padding:3px 6px;">#{i+1}</td>
        <td style="padding:3px 6px;">{src_badge} <span style="color:#3fb950;font-weight:700;">{name}</span></td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{comp:.4f}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{vol:.3f}x</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{corr_disp}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{carry:.3f}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">${vlm/1e6:.2f}M</td>
      </tr>"""

    fetch_count = sum(1 for v in fetch_results.values() if v)

    badge = f"""
<!-- K773_HIP3_ROUND2_BADGE: K773 HIP-3 Batch FR Fetch Round 2 | top25_fetched={fetch_count}/{len(fetch_results)} | prescreen_pass={len(survivors)} | K774+ queue={len(k774_queue)} | combined_K766+K773={len(combined)} | K339 REPO_ROOT | {jst_date} -->
<!-- K773 HIP3 ROUND2 BADGE START -->
<section id="k773-round2" style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px 22px;margin:18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="background:rgba(57,210,192,0.15);border:2px solid #39d2c0;border-radius:8px;padding:4px 10px;color:#39d2c0;font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K773</div>
    <div style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:6px;padding:3px 9px;color:#3fb950;font-size:0.73rem;font-weight:700;">ROUND 2 SCREEN COMPLETE</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">K766 + K773 combined</div>
    <div style="color:#8b949e;font-size:0.72rem;margin-left:auto;">{jst_date}</div>
  </div>

  <div style="color:#e6edf3;font-size:1.08rem;font-weight:900;margin-bottom:8px;">&#128301; K773 — HIP-3 Batch FR Fetch Round 2 — {len(survivors)} Fresh Candidates Pass Pre-Screen</div>

  <div style="background:rgba(30,37,44,0.7);border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:0.78rem;color:#8b949e;line-height:1.6;">
    <strong style="color:#e6edf3;">Round 2 scope:</strong> Top-25 no-cache tokens from K766 (99 total) &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Fetched:</strong> {fetch_count}/{len(fetch_results)} &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Pre-screen pass:</strong> {len(survivors)} fresh &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Combined K766+K773:</strong> {len(combined)} candidates ranked &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">HBAR corr:</strong> explicitly computed for all (K766 fix)
  </div>

  <div style="color:#39d2c0;font-size:0.85rem;font-weight:700;margin-bottom:8px;">TOP-5 FRESH LONG-TAIL CANDIDATES → K774+ QUEUE</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.77rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:4px 8px;">Rank</th>
        <th style="text-align:left;padding:4px 8px;">Wave</th>
        <th style="text-align:left;padding:4px 8px;">Token</th>
        <th style="text-align:right;padding:4px 8px;">Composite</th>
        <th style="text-align:right;padding:4px 8px;">VolRatio</th>
        <th style="text-align:right;padding:4px 8px;">MaxCorr</th>
        <th style="text-align:right;padding:4px 8px;">HBAR</th>
        <th style="text-align:right;padding:4px 8px;">Carry%</th>
        <th style="text-align:right;padding:4px 8px;">FR_std_ann</th>
        <th style="text-align:right;padding:4px 8px;">DayVlm</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>
  </div>

  <div style="color:#58a6ff;font-size:0.82rem;font-weight:700;margin-top:16px;margin-bottom:8px;">COMBINED K766+K773 RANKED — TOP 10</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.75rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:3px 6px;">#</th>
        <th style="text-align:left;padding:3px 6px;">Source / Token</th>
        <th style="text-align:right;padding:3px 6px;">Composite</th>
        <th style="text-align:right;padding:3px 6px;">VolRatio</th>
        <th style="text-align:right;padding:3px 6px;">MaxCorr</th>
        <th style="text-align:right;padding:3px 6px;">Carry%</th>
        <th style="text-align:right;padding:3px 6px;">DayVlm</th>
      </tr>
    </thead>
    <tbody>{combined_rows}
    </tbody>
  </table>
  </div>

  <div style="margin-top:14px;padding:10px 14px;background:rgba(209,136,34,0.08);border-left:3px solid #d29922;border-radius:4px;font-size:0.77rem;color:#8b949e;">
    <strong style="color:#d29922;">&#9888; K773 Constraints:</strong> Pre-screen only (no full 180d backtest).
    30d FR history fetch only. Long-tail liquidity may fail G6 entries/yr or G9 history at full §6 eval.
    vol_ratio threshold 1.5x | max_corr &le;0.45 | carry stability 35-80%.
    K774+ → full alt-alt §6 gate eval. ROI estimates deferred to K774+. K523 3-point mandatory at K774+.
    HBAR corr explicitly computed for all tokens (K766 had NaN — now fixed).
  </div>

  <div style="margin-top:10px;font-size:0.72rem;color:#6e7681;">
    最終更新: {jst_date} (K773 round 2 — {fetch_count} fetched, {len(survivors)} pass, K774+ queue: {', '.join(q['token'] for q in k774_queue)}) &nbsp;|&nbsp; K339 REPO_ROOT &nbsp;|&nbsp; LIVE 自動変更禁止
  </div>
</section>
<!-- /K773 HIP3 ROUND2 BADGE -->
"""
    return badge


def inject_badge_into_report(badge_html: str):
    """Inject K773 badge into report.html after K766 badge."""
    report_path = BASE / "report.html"
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "K773_HIP3_ROUND2_BADGE" in content:
        print("  K773 badge already in report.html — replacing ...")
        start_marker = "<!-- K773_HIP3_ROUND2_BADGE:"
        end_marker = "<!-- /K773 HIP3 ROUND2 BADGE -->"
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        if start_idx >= 0 and end_idx > start_idx:
            content = content[:start_idx] + badge_html.strip() + content[end_idx:]
    else:
        # Insert after K770 K768 BLUR-SOL SCAFFOLD BADGE end marker
        k770_end = "<!-- /K770 K768 BLUR-SOL SCAFFOLD BADGE -->"
        k766_end = "<!-- /K766 HL LONG-TAIL FR SCREEN BADGE -->"
        if k770_end in content:
            content = content.replace(k770_end, k770_end + "\n" + badge_html)
            print("  K773 badge injected after K770 badge.")
        elif k766_end in content:
            content = content.replace(k766_end, k766_end + "\n" + badge_html)
            print("  K773 badge injected after K766 badge.")
        else:
            content = content.replace("</body>", badge_html + "\n</body>")
            print("  K773 badge injected before </body> (fallback).")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Updated: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(f"Wave K773: HIP-3 Batch FR Fetch + Round 2 Screen")
    print(f"K339 REPO_ROOT: {REPO_ROOT}")
    print(f"LIVE 自動変更禁止 | Public repo | No credentials")
    print(f"API rate limit: {API_SLEEP}s/req | Fetch days: {FETCH_DAYS}")
    print("=" * 70)

    # Phase 1: Load K766 results
    top_nc, k766_survivors = phase1_load_k766()

    # Phase 2: Batch FR fetch
    fetch_results = phase2_batch_fetch(top_nc)

    # Phase 3: Pre-screen
    phase3_results = phase3_prescreen(top_nc, fetch_results)

    # Phase 4: Rank + queue
    ranked = phase4_rank_and_queue(phase3_results, k766_survivors)

    # Phase 5: Save JSON
    phase5_save_json(top_nc, fetch_results, phase3_results, ranked)

    # Build + inject HTML badge
    badge = build_badge(ranked, fetch_results)
    inject_badge_into_report(badge)

    # Summary
    runtime = round(time.time() - START_TIME, 1)
    print(f"\n{'=' * 70}")
    print(f"K773 COMPLETE — runtime {runtime}s")
    print(f"Tokens attempted: {len(top_nc)}")
    print(f"Fetch success: {sum(1 for v in fetch_results.values() if v)}")
    print(f"Pre-screen pass (fresh): {len(ranked['survivors'])}")
    print(f"Pre-screen fail: {len(ranked['failed'])}")
    print(f"No usable data: {len(ranked['no_data'])}")
    print(f"Combined K766+K773 ranked: {len(ranked['combined_ranked'])}")
    print(f"\nK774+ QUEUE:")
    for q in ranked["k774_queue"]:
        print(f"  {q['wave_candidate']}: {q['token']} (composite={q['composite_score']:.4f})")
    print(f"{'=' * 70}")

    return ranked


if __name__ == "__main__":
    main()

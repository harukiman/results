#!/usr/bin/env python3
"""
wave_k781_hip3_round2c_screen.py — K781 HIP-3 Batch FR Fetch Round 2c
=======================================================================
K339 REPO_ROOT pattern.

MISSION
-------
K766 long-tail screen found 99 tokens with no cached FR data.
K773 fetched the top 25 by dayNtlVlm (round 2).  74 remain uncached.
This wave fetches 30d FR history for the next 25 (rank 26-50 by dayNtlVlm,
i.e. round 2c) and runs the same K766/K744/K773 pre-screen framework.

K775 LESSON APPLIED
-------------------
FULL history vol_ratio is used for final ranking (not 30d snapshot).
30d artifact can dramatically over-state vol_ratio for newly listed tokens.
carry_stability is evaluated on both full history AND 30d rolling.

METHODOLOGY
-----------
Phase 1: Load K773 results (data/hl_long_tail_candidates_round2.json)
         + K766 results (data/hl_long_tail_candidates.json)
         - identify 74 still-uncached tokens
         - sort by dayNtlVlm descending, take next 25 (rank 26-50)
Phase 2: Batch FR fetch (next 25)
         - POST /info {"type":"fundingHistory","coin":"X","startTime":ms}
         - 30d window per token
         - Rate limit: 1 req/sec
         - Cache to cache/k163_hl/hl_fr_{token}.parquet
Phase 3: Pre-screen + K775 vol verification
         - vol_ratio vs SOL >= 1.5x — FULL history (≥120d where available)
         - L003/L007/L010/L011 max corr <= 0.45
         - L004 carry-stability 35-80% (both full + 30d rolling)
         - Composite = vol_ratio_full × cycle_indep × fr_std_ann
Phase 4: Rank + K782+ wave queue
         - Top 5 fresh long-tail candidates from round 2c
         - Combine with K766+K773 ranked list → updated master ranking
         - Output top 3 for K782-K784 eval queue
Phase 5: report.html badge
         - K781 round 2c update with top 5 fresh candidates
         - Combined K766+K773+K781 ranked list

EXCLUSION LISTS (inherited from K766/K773)
------------------------------------------
V-15 vertices (K744): APT ATOM AVAX BNB ENA FIL HBAR INJ LDO SEI SOL TIA
Post-K744 accepted/tested: PEPE WIF DOGE RUNE ONDO TAO WLD PENDLE PYTH
Base assets (BTC-paired): BTC ETH
Closed-line rejects (K480-K532): SUI ARB NEAR OSMO DOT ALGO BNB
K744 candidates screened: AAVE JUP BONK KAS OP SHIB TON CRV MKR UNI RNDR
K766 round1 screened: BLUR AXS COMP STX MEME IMX GALA SAND ICP BOME STRK ARK SUSHI
K773 round2 screened: IO ZK SPX MORPHO WLFI EIGEN MEGA AVNT HEMI DYDX AR SYRUP
                      APE kSHIB CHIP AZTEC kBONK STABLE IP DASH IOTA SKY STBL NXPC VINE

CONSTRAINTS
-----------
- API rate limit: 1 req/sec (HL public API)
- 25 tokens × ~1.1s = ~28s total fetch time
- K775 lesson: use FULL history vol_ratio, not 30d snapshot
- LIVE 自動変更禁止
- Public repo: no credentials

Usage:
    python3 wave_k781_hip3_round2c_screen.py
"""
from __future__ import annotations

import json
import math
import os
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
WAVE_ID = "K781"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": REPO_ROOT, "pattern": "K339"}

# ── Constants ─────────────────────────────────────────────────────────────────
HL_API = "https://api.hyperliquid.xyz/info"
API_SLEEP = 1.1           # seconds between requests
FETCH_DAYS = 30           # days of FR history to fetch per token
MIN_ROWS = 168            # minimum rows for pre-screen (~7d hourly)
TOP_N_ROUND2C = 25        # next 25 from remaining 74 uncached

# Pre-screen thresholds (K766/K744/K773 consistent)
VOL_RATIO_MIN = 1.5
CORR_MAX = 0.45
CARRY_STABILITY_MIN = 0.35
CARRY_STABILITY_MAX = 0.80

# K775 lesson: FULL history evaluation window (use all available data ≥120d)
FULL_HIST_DAYS = 360      # load full history up to 1 year for vol_ratio_full

ANN_FACTOR_8760 = math.sqrt(8760)


# ── Phase 1: Identify next 25 uncached tokens ─────────────────────────────────

def phase1_load_uncached() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Load K766 + K773 results, identify 74 still-uncached tokens.
    Returns (next_25_for_fetch, k766_survivors, k773_survivors).
    """
    print(f"\n[Phase 1] Loading K766 + K773 results, identifying uncached tokens ...")

    # Load K766 no-cache list
    k766_path = DATA / "hl_long_tail_candidates.json"
    if not k766_path.exists():
        raise FileNotFoundError(f"K766 output not found: {k766_path}")

    with open(k766_path) as f:
        k766_data = json.load(f)

    no_cache_all = k766_data.get("no_cached_data_hip3", [])
    k766_survivors = k766_data.get("all_survivors_ranked", [])
    print(f"  K766 no_cache_hip3: {len(no_cache_all)} tokens")
    print(f"  K766 survivors: {len(k766_survivors)}")

    # Load K773 survivors
    k773_path = DATA / "hl_long_tail_candidates_round2.json"
    k773_survivors = []
    if k773_path.exists():
        with open(k773_path) as f:
            k773_data = json.load(f)
        k773_survivors = k773_data.get("all_survivors_ranked", [])
        print(f"  K773 survivors: {len(k773_survivors)}")
    else:
        print(f"  WARN: K773 output not found at {k773_path}")

    # Get set of currently cached token names
    cached_names: set = set()
    for fname in os.listdir(HL_CACHE):
        if fname.startswith("hl_fr_") and fname.endswith(".parquet") and "_full" not in fname:
            name = fname.replace("hl_fr_", "").replace(".parquet", "")
            cached_names.add(name)
    print(f"  Currently cached tokens: {len(cached_names)}")

    # Sort all no-cache tokens by dayNtlVlm descending
    no_cache_sorted = sorted(no_cache_all, key=lambda x: x.get("dayNtlVlm", 0), reverse=True)

    # Split into: already fetched (K773 round2 = top 25) vs still uncached
    still_uncached = [t for t in no_cache_sorted if t["name"] not in cached_names]
    already_fetched = [t for t in no_cache_sorted if t["name"] in cached_names]

    print(f"  Already fetched (cached): {len(already_fetched)}")
    print(f"  Still uncached: {len(still_uncached)}")

    # Take next 25 (round 2c)
    next_25 = still_uncached[:TOP_N_ROUND2C]
    remaining_after = still_uncached[TOP_N_ROUND2C:]

    print(f"\n  Round 2c batch (next {TOP_N_ROUND2C} by dayNtlVlm):")
    for i, t in enumerate(next_25):
        print(f"    {i+1:2d}. {t['name']:<15} dayNtlVlm=${t['dayNtlVlm']:>10,.0f}  "
              f"OI={t.get('openInterest',0):>10.0f}  FR_ann={t.get('funding_ann_pct',0):>8.2f}%")

    print(f"\n  Remaining uncached after round 2c: {len(remaining_after)} tokens")

    return next_25, k766_survivors, k773_survivors


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
    Fetch FR history for the next-25 tokens (round 2c).
    Returns dict: {token_name: fetch_success}.
    """
    print(f"\n[Phase 2] Batch FR fetch for {len(tokens)} tokens (round 2c) ...")
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
                    print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → ALREADY CACHED ({len(existing)} rows)")
                    results[name] = True
                    continue
            except Exception:
                pass  # Re-fetch if corrupt

        print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → fetching ...", end="", flush=True)
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


# ── Phase 3: Pre-Screen with K775 FULL history vol_ratio ─────────────────────

def _load_cached_fr(name: str, days: int = 90) -> Optional[pd.Series]:
    """
    Load cached FR series (last N days), normalised to naive hourly UTC.
    K775 lesson: caller passes FULL_HIST_DAYS for vol_ratio computation.
    """
    p = HL_CACHE / f"hl_fr_{name}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        ts = pd.to_datetime(df["timestamp"])
        # Handle both tz-aware (UTC) and tz-naive timestamps
        if ts.dt.tz is not None:
            ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
        df["timestamp"] = ts.dt.floor("h")
        s = df.set_index("timestamp")["hl_fr"].sort_index()
        s = s[~s.index.duplicated(keep="last")]
        if days > 0:
            cutoff = s.index.max() - pd.Timedelta(days=days)
            return s[s.index >= cutoff]
        return s
    except Exception as e:
        print(f"    WARN: failed to load {name}: {e}")
        return None


def _load_anchor_fr() -> Dict[str, pd.Series]:
    """Load anchor token FR series for correlation + vol_ratio computation."""
    anchors = {}
    for tok in ["SOL", "AVAX", "FIL", "HBAR"]:
        # K775 lesson: load full history for anchors
        s = _load_cached_fr(tok, days=FULL_HIST_DAYS)
        if s is not None and len(s) > 100:
            anchors[tok] = s
            print(f"    Anchor {tok}: {len(s)} rows")
        else:
            print(f"    WARN: anchor {tok} insufficient data ({len(s) if s is not None else 0} rows)")
    return anchors


def _align(s: pd.Series, ref: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Align two series on common index."""
    idx = s.index.intersection(ref.index)
    return s.loc[idx], ref.loc[idx]


def compute_prescreen(name: str, anchors: Dict[str, pd.Series], tok_meta: Dict) -> Dict:
    """
    Compute Phase 3 pre-screen metrics for a candidate token.
    K775 lesson: vol_ratio uses FULL history (FULL_HIST_DAYS), not just 30d.
    """
    # FULL history for vol_ratio_full (K775 lesson)
    fr_full = _load_cached_fr(name, days=FULL_HIST_DAYS)
    if fr_full is None or len(fr_full) < MIN_ROWS:
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

    # Align on FULL history intersection (K775: not just 30d)
    fr_full_al, sol_full_al = _align(fr_full, sol_fr)
    if len(fr_full_al) < 100:
        return {
            "name": name,
            "has_data": False,
            "skip_reason": "insufficient_overlap_with_SOL_full",
            "dayNtlVlm": tok_meta.get("dayNtlVlm", 0),
        }

    # vol_ratio FULL (K775 lesson — primary metric)
    tok_std_full = float(fr_full_al.std())
    sol_std_full = float(sol_full_al.std())
    vol_ratio_full = tok_std_full / sol_std_full if sol_std_full > 0 else 0.0

    # Also compute 30d rolling vol_ratio for comparison (K775 lesson: show both)
    fr_30d = _load_cached_fr(name, days=30)
    sol_30d = _load_cached_fr("SOL", days=30)
    vol_ratio_30d = 0.0
    if fr_30d is not None and sol_30d is not None and len(fr_30d) > 0 and len(sol_30d) > 0:
        fr_30d_al, sol_30d_al = _align(fr_30d, sol_30d)
        if len(fr_30d_al) > 50:
            sol_std_30d = float(sol_30d_al.std())
            vol_ratio_30d = float(fr_30d_al.std()) / sol_std_30d if sol_std_30d > 0 else 0.0

    # Detect 30d artifact: warn if 30d >> full
    vol_ratio_artifact_warn = False
    if vol_ratio_30d > 2 * vol_ratio_full and vol_ratio_full > 0:
        vol_ratio_artifact_warn = True

    # Raw correlations vs anchors (use full history overlap)
    corrs: Dict[str, float] = {}
    for tok_name, anchor_s in [("AVAX", avax_fr), ("FIL", fil_fr), ("HBAR", hbar_fr)]:
        if anchor_s is not None:
            a, b = _align(fr_full, anchor_s)
            corrs[tok_name] = float(a.corr(b)) if len(a) >= 50 else float("nan")
        else:
            corrs[tok_name] = float("nan")
    corrs["SOL"] = float(fr_full_al.corr(sol_full_al)) if len(fr_full_al) >= 50 else float("nan")

    # Carry stability: FULL history
    carry_stability_full = float((fr_full > 0).mean())

    # Carry stability: 30d rolling (K775: both)
    carry_30d = float("nan")
    if fr_30d is not None and len(fr_30d) > 0:
        carry_30d = float((fr_30d > 0).mean())

    # FR amplitude (annualised, full history)
    fr_mean_ann = float(fr_full.mean()) * 8760 * 100      # % annual
    fr_std_ann = float(fr_full.std()) * ANN_FACTOR_8760 * 100  # % annual

    # Cycle independence (1 - max corr)
    valid_corrs = [v for v in corrs.values() if not math.isnan(v)]
    max_corr = max(valid_corrs) if valid_corrs else float("nan")
    cycle_indep = 1 - max_corr if not math.isnan(max_corr) else float("nan")

    # Composite score (K744 formula, using vol_ratio_full per K775)
    if not math.isnan(cycle_indep) and vol_ratio_full > 0 and fr_std_ann > 0:
        composite = vol_ratio_full * max(0, cycle_indep) * (fr_std_ann / 100)
    else:
        composite = 0.0

    # Pre-screen pass/fail
    reasons_fail = []
    reasons_pass = []

    # vol_ratio: use FULL history (K775 lesson)
    if vol_ratio_full < VOL_RATIO_MIN:
        reasons_fail.append(f"vol_ratio_full={vol_ratio_full:.3f} < {VOL_RATIO_MIN}")
    else:
        reasons_pass.append(f"vol_ratio_full={vol_ratio_full:.3f} PASS")
        if vol_ratio_artifact_warn:
            reasons_pass.append(f"  [K775_WARN] 30d={vol_ratio_30d:.3f} >> full={vol_ratio_full:.3f} (30d artifact detected)")

    for corr_key, corr_label in [("AVAX", "L003_AVAX"), ("SOL", "L011_SOL"),
                                   ("FIL", "L007_FIL"), ("HBAR", "L010_HBAR")]:
        v = corrs.get(corr_key, float("nan"))
        if not math.isnan(v) and v > CORR_MAX:
            reasons_fail.append(f"corr_{corr_key}={v:.3f} > {CORR_MAX}")
        else:
            disp = "n/a" if math.isnan(v) else f"{v:.3f}"
            reasons_pass.append(f"{corr_label}={disp} PASS")

    # Carry stability: use full history for block decision, show 30d too
    if carry_stability_full > CARRY_STABILITY_MAX:
        reasons_fail.append(
            f"carry_stability_full={carry_stability_full:.3f} > {CARRY_STABILITY_MAX} (structural carry BLOCK)"
        )
    elif carry_stability_full < CARRY_STABILITY_MIN:
        reasons_fail.append(
            f"carry_stability_full={carry_stability_full:.3f} < {CARRY_STABILITY_MIN} (insufficient carry)"
        )
    else:
        reasons_pass.append(f"carry_stability_full={carry_stability_full:.3f} PASS")
        if not math.isnan(carry_30d):
            if carry_30d > CARRY_STABILITY_MAX or carry_30d < CARRY_STABILITY_MIN:
                reasons_pass.append(
                    f"  [K775_NOTE] carry_30d={carry_30d:.3f} out of range (check OOS stability)"
                )

    prescreen_pass = len(reasons_fail) == 0

    return {
        "name": name,
        "has_data": True,
        "n_rows": len(fr_full),
        # K775: both FULL and 30d vol ratios
        "vol_ratio_full": round(vol_ratio_full, 4),
        "vol_ratio_30d": round(vol_ratio_30d, 4),
        "vol_ratio_artifact_warn": vol_ratio_artifact_warn,
        # Use FULL for composite (K775 lesson)
        "vol_ratio_sol": round(vol_ratio_full, 4),   # main metric = FULL
        "corr_AVAX": round(corrs.get("AVAX", float("nan")), 4),
        "corr_SOL": round(corrs.get("SOL", float("nan")), 4),
        "corr_FIL": round(corrs.get("FIL", float("nan")), 4),
        "corr_HBAR": round(corrs.get("HBAR", float("nan")), 4),
        "max_corr": round(max_corr, 4) if not math.isnan(max_corr) else float("nan"),
        "cycle_indep": round(cycle_indep, 4) if not math.isnan(cycle_indep) else float("nan"),
        "carry_stability": round(carry_stability_full, 4),   # FULL
        "carry_stability_full": round(carry_stability_full, 4),
        "carry_30d": round(carry_30d, 4) if not math.isnan(carry_30d) else float("nan"),
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
        "k775_full_hist_days_loaded": len(fr_full),
    }


def phase3_prescreen(tokens: List[Dict], fetch_results: Dict[str, bool]) -> List[Dict]:
    """Run K775-aware pre-screen on all fetched tokens."""
    print(f"\n[Phase 3] Pre-screen + K775 FULL history vol verification ...")

    print(f"\n  Loading anchor FR series (FULL history, up to {FULL_HIST_DAYS}d) ...")
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
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → FETCH FAILED — skip")
            continue

        result = compute_prescreen(name, anchors, tok)
        results.append(result)

        if not result.get("has_data"):
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → NO USABLE DATA ({result.get('skip_reason','')})")
        else:
            status = "PASS" if result["prescreen_pass"] else "FAIL"
            artifact_flag = " [K775_ARTIFACT]" if result.get("vol_ratio_artifact_warn") else ""
            reasons = "; ".join(result["reasons_fail"]) if result["reasons_fail"] else "all PASS"
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → {status:4s} | "
                  f"vol_full={result['vol_ratio_full']:.3f} vol_30d={result['vol_ratio_30d']:.3f}{artifact_flag} | "
                  f"L003={result['corr_AVAX']:.3f} "
                  f"L010={result['corr_HBAR']:.3f} "
                  f"L011={result['corr_SOL']:.3f} | "
                  f"carry_full={result['carry_stability_full']:.3f} carry_30d={result['carry_30d']:.3f} | "
                  f"comp={result['composite_score']:.4f}"
                  + (f" | FAIL: {reasons}" if result["reasons_fail"] else ""))

    survivors = [r for r in results if r.get("has_data") and r.get("prescreen_pass")]
    failed = [r for r in results if r.get("has_data") and not r.get("prescreen_pass")]
    no_data = [r for r in results if not r.get("has_data")]

    print(f"\n  === Phase 3 Summary ===")
    print(f"  Passed pre-screen: {len(survivors)}")
    print(f"  Failed pre-screen: {len(failed)}")
    print(f"  No usable data:    {len(no_data)}")
    print(f"  K775 FULL history: vol_ratio_full used for all decisions")

    return results


# ── Phase 4: Rank + Wave Queue ────────────────────────────────────────────────

def phase4_rank_and_queue(
    phase3_results: List[Dict],
    k766_survivors: List[Dict],
    k773_survivors: List[Dict],
) -> Dict:
    """
    Rank Phase 3 survivors by composite score.
    Build K782+ wave queue (top 3).
    Build combined K766+K773+K781 ranked list.
    """
    print(f"\n[Phase 4] Ranking survivors + building K782+ wave queue ...")

    survivors = [r for r in phase3_results if r.get("has_data") and r.get("prescreen_pass")]
    failed = [r for r in phase3_results if r.get("has_data") and not r.get("prescreen_pass")]
    no_data = [r for r in phase3_results if not r.get("has_data")]

    survivors.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === K781 ROUND 2c SURVIVORS (fresh long-tail, ranked) ===")
    for i, s in enumerate(survivors):
        artifact = " [K775_ART]" if s.get("vol_ratio_artifact_warn") else ""
        print(f"  #{i+1:2d} {s['name']:<15} | composite={s['composite_score']:.4f} | "
              f"vol_full={s['vol_ratio_full']:.3f}x vol_30d={s['vol_ratio_30d']:.3f}x{artifact} | "
              f"max_corr={s.get('max_corr',float('nan')):.3f} | "
              f"carry_full={s['carry_stability']:.3f} | FR_std_ann={s.get('fr_std_ann_pct',0):.1f}% | "
              f"dayVlm=${s.get('dayNtlVlm',0)/1e6:.3f}M")

    print(f"\n  === FAILED PRE-SCREEN ===")
    for f_ in sorted(failed, key=lambda x: x.get("composite_score", 0), reverse=True):
        reasons = "; ".join(f_["reasons_fail"])
        print(f"  {f_['name']:<15} | {reasons}")

    # K782+ queue: top 3 survivors
    k782_queue = []
    for i, s in enumerate(survivors[:3]):
        entry = {
            "wave_candidate": f"K{782 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_full": s["vol_ratio_full"],
            "vol_ratio_30d": s["vol_ratio_30d"],
            "vol_ratio_artifact_warn": s.get("vol_ratio_artifact_warn", False),
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "carry_30d": s.get("carry_30d", float("nan")),
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "concerns": [],
            "source": "K781_round2c",
        }
        if s.get("dayNtlVlm", 0) < 5_000_000:
            entry["concerns"].append("LOW_LIQUIDITY (<$5M/day) — may fail G6 entries/yr or G9 history")
        if s.get("openInterest", 0) < 100_000:
            entry["concerns"].append("LOW_OI (<$100K) — execution slippage risk")
        if s.get("vol_ratio_artifact_warn"):
            entry["concerns"].append(f"K775_ARTIFACT: 30d vol={s['vol_ratio_30d']:.2f}x >> full={s['vol_ratio_full']:.2f}x — use FULL")
        k782_queue.append(entry)

    # Backlog (rank 4+)
    backlog_new = []
    for i, s in enumerate(survivors[3:]):
        backlog_new.append({
            "wave_candidate": f"K{785 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_full": s["vol_ratio_full"],
            "vol_ratio_30d": s["vol_ratio_30d"],
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "source": "K781_round2c_backlog",
        })

    print(f"\n  === K782+ WAVE QUEUE ===")
    for entry in k782_queue:
        concerns = " | ".join(entry["concerns"]) if entry["concerns"] else "None"
        print(f"  {entry['wave_candidate']}: {entry['token']:<15} | composite={entry['composite_score']:.4f} | "
              f"vol_full={entry['vol_ratio_full']:.3f}x | concerns: {concerns}")

    # Combined K766+K773+K781 ranked list (dedup by name)
    seen: set = set()
    combined = []

    for s in survivors:           # K781 round2c first (freshest)
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K781_round2c"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k773_survivors:     # K773 round2
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K773_round2"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k766_survivors:     # K766 round1
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K766_round1"
            combined.append(s_copy)
            seen.add(s["name"])

    combined.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === COMBINED K766+K773+K781 RANKED LIST ({len(combined)} tokens) ===")
    for i, s in enumerate(combined):
        src = s.get("source", "?")
        artifact = " [K775_ART]" if s.get("vol_ratio_artifact_warn") else ""
        print(f"  #{i+1:2d} [{src:15s}] {s['name']:<15} composite={s.get('composite_score',0):.4f}{artifact}")

    return {
        "survivors": survivors,
        "failed": failed,
        "no_data": no_data,
        "top5": survivors[:5],
        "k782_queue": k782_queue,
        "backlog_new": backlog_new,
        "combined_ranked": combined,
    }


# ── Phase 5: Save JSON ────────────────────────────────────────────────────────

def _replace_nan(obj):
    """Recursively replace NaN float with None for JSON serialization."""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: _replace_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_nan(v) for v in obj]
    return obj


def phase5_save_json(
    next_25: List[Dict],
    fetch_results: Dict[str, bool],
    phase3_results: List[Dict],
    ranked: Dict,
) -> Path:
    """Save K781 round-2c candidates JSON."""
    now_utc = datetime.now(timezone.utc)

    output = {
        "wave": WAVE_ID,
        "title": "K781 HIP-3 Batch FR Fetch Round 2c",
        "generated_utc": now_utc.isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": "conserv/mid/optimist 3-point — deferred to K782+ full evals",
        "live_auto_change_prohibited": True,
        "k775_lesson": {
            "description": "FULL history vol_ratio used for all pre-screen decisions (not 30d snapshot)",
            "full_hist_days": FULL_HIST_DAYS,
            "vol_ratio_metric": "vol_ratio_full (primary) + vol_ratio_30d (diagnostic)",
            "artifact_detection": "30d artifact flagged when vol_ratio_30d > 2x vol_ratio_full",
        },
        "round2c_summary": {
            "tokens_attempted": len(next_25),
            "fetch_success": sum(1 for v in fetch_results.values() if v),
            "fetch_failed": sum(1 for v in fetch_results.values() if not v),
            "prescreen_pass": len(ranked["survivors"]),
            "prescreen_fail": len(ranked["failed"]),
            "no_usable_data": len(ranked["no_data"]),
            "k775_artifact_flagged": sum(
                1 for r in phase3_results if r.get("vol_ratio_artifact_warn")
            ),
        },
        "fetch_results": fetch_results,
        "top5_fresh_candidates": ranked["top5"],
        "k782_queue": ranked["k782_queue"],
        "all_survivors_ranked": ranked["survivors"],
        "failed_prescreen": ranked["failed"],
        "backlog_new": ranked["backlog_new"],
        "combined_k766_k773_k781_ranked": ranked["combined_ranked"],
        "phase3_all_results": phase3_results,
    }

    output_clean = _replace_nan(output)

    path = DATA / "hl_long_tail_candidates_round2c.json"
    with open(path, "w") as f:
        json.dump(output_clean, f, indent=2)
    print(f"\n  Saved: {path}")
    return path


# ── Phase 6: report.html badge ────────────────────────────────────────────────

def build_badge(ranked: Dict, fetch_results: Dict[str, bool]) -> str:
    """Build K781 HTML badge for report.html."""
    now_utc = datetime.now(timezone.utc)
    jst_hour = (now_utc.hour + 9) % 24
    jst_date = now_utc.strftime(f"%Y-%m-%d {jst_hour:02d}:{now_utc.minute:02d} JST")

    top5 = ranked["top5"]
    k782_queue = ranked["k782_queue"]
    combined = ranked["combined_ranked"]
    survivors = ranked["survivors"]

    # Top-5 fresh rows
    rows_html = ""
    for i, s in enumerate(top5):
        wave_cand = k782_queue[i]["wave_candidate"] if i < len(k782_queue) else "BACKLOG"
        name = s["name"]
        comp = s.get("composite_score", 0)
        vol_full = s.get("vol_ratio_full", 0)
        vol_30d = s.get("vol_ratio_30d", 0)
        max_corr = s.get("max_corr", float("nan"))
        carry = s.get("carry_stability", 0)
        fr_std = s.get("fr_std_ann_pct", 0)
        vlm = s.get("dayNtlVlm", 0)
        artifact = s.get("vol_ratio_artifact_warn", False)

        corr_disp = (
            f"{max_corr:.3f}" if max_corr is not None
            and not (isinstance(max_corr, float) and math.isnan(max_corr))
            else "n/a"
        )
        artifact_badge = (
            " <span style='color:#f0883e;font-size:0.68rem;'>&#9888;K775</span>"
            if artifact else ""
        )
        liq_warn = (
            " <span style='color:#f0883e;font-size:0.68rem;'>&#9888;LIQ</span>"
            if vlm < 5_000_000 else ""
        )

        rows_html += f"""
      <tr>
        <td style="color:#58a6ff;font-weight:700;">#{i+1}</td>
        <td style="color:#e3b341;font-weight:700;">{wave_cand}</td>
        <td style="color:#3fb950;font-weight:800;">{name}</td>
        <td style="color:#e6edf3;text-align:right;">{comp:.4f}</td>
        <td style="color:#e6edf3;text-align:right;">{vol_full:.3f}x{artifact_badge}</td>
        <td style="color:#8b949e;text-align:right;font-size:0.72rem;">{vol_30d:.3f}x</td>
        <td style="color:#e6edf3;text-align:right;">{corr_disp}</td>
        <td style="color:#e6edf3;text-align:right;">{carry:.3f}</td>
        <td style="color:#e6edf3;text-align:right;">{fr_std:.1f}%</td>
        <td style="color:#e6edf3;text-align:right;">${vlm/1e6:.3f}M{liq_warn}</td>
      </tr>"""

    # Combined top-10 rows
    combined_rows = ""
    for i, s in enumerate(combined[:10]):
        src = s.get("source", "?")
        if "K781" in src:
            src_color = "#f0883e"
        elif "K773" in src:
            src_color = "#39d2c0"
        else:
            src_color = "#8b949e"
        src_short = src.replace("_round", "").replace("round", "")
        src_badge = f'<span style="font-size:0.67rem;color:{src_color};">[{src_short}]</span>'
        name = s["name"]
        comp = s.get("composite_score", 0)
        vol_full = s.get("vol_ratio_full", s.get("vol_ratio_sol", 0))
        max_corr = s.get("max_corr", None)
        carry = s.get("carry_stability", 0)
        vlm = s.get("dayNtlVlm", 0)
        corr_disp = (
            f"{max_corr:.3f}" if max_corr is not None
            and not (isinstance(max_corr, float) and math.isnan(max_corr))
            else "n/a"
        )
        combined_rows += f"""
      <tr style="border-bottom:1px solid #21262d;">
        <td style="color:#8b949e;padding:3px 6px;">#{i+1}</td>
        <td style="padding:3px 6px;">{src_badge} <span style="color:#3fb950;font-weight:700;">{name}</span></td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{comp:.4f}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{vol_full:.3f}x</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{corr_disp}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{carry:.3f}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">${vlm/1e6:.3f}M</td>
      </tr>"""

    fetch_count = sum(1 for v in fetch_results.values() if v)
    artifact_count = sum(
        1 for s in survivors if s.get("vol_ratio_artifact_warn")
    )

    badge = f"""
<!-- K781_HIP3_ROUND2C_BADGE: K781 HIP-3 Batch FR Fetch Round 2c | top25_fetched={fetch_count}/{len(fetch_results)} | prescreen_pass={len(survivors)} | K782+ queue={len(k782_queue)} | combined_K766+K773+K781={len(combined)} | K775_artifacts={artifact_count} | K339 REPO_ROOT | {jst_date} -->
<!-- K781 HIP3 ROUND2C BADGE START -->
<section id="k781-round2c" style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px 22px;margin:18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="background:rgba(240,136,62,0.15);border:2px solid #f0883e;border-radius:8px;padding:4px 10px;color:#f0883e;font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K781</div>
    <div style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:6px;padding:3px 9px;color:#3fb950;font-size:0.73rem;font-weight:700;">ROUND 2c SCREEN COMPLETE</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">K766 + K773 + K781 combined</div>
    <div style="background:rgba(240,136,62,0.10);border:1px solid #f0883e;border-radius:6px;padding:3px 9px;color:#f0883e;font-size:0.70rem;">K775 vol-FULL verify</div>
    <div style="color:#8b949e;font-size:0.72rem;margin-left:auto;">{jst_date}</div>
  </div>

  <div style="color:#e6edf3;font-size:1.08rem;font-weight:900;margin-bottom:8px;">&#128301; K781 — HIP-3 Batch FR Fetch Round 2c — {len(survivors)} Fresh Candidates Pass Pre-Screen</div>

  <div style="background:rgba(30,37,44,0.7);border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:0.78rem;color:#8b949e;line-height:1.6;">
    <strong style="color:#e6edf3;">Round 2c scope:</strong> Next-25 uncached tokens (rank 26-50 of 99 by dayNtlVlm) &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Fetched:</strong> {fetch_count}/{len(fetch_results)} &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Pre-screen pass:</strong> {len(survivors)} fresh &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">K775 FULL vol:</strong> vol_ratio_full (not 30d) used for all decisions &nbsp;|&nbsp;
    <strong style="color:#f0883e;">30d artifacts detected:</strong> {artifact_count} &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Combined K766+K773+K781:</strong> {len(combined)} candidates ranked
  </div>

  <div style="color:#f0883e;font-size:0.85rem;font-weight:700;margin-bottom:8px;">TOP-5 FRESH LONG-TAIL CANDIDATES → K782+ QUEUE</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.77rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:4px 8px;">Rank</th>
        <th style="text-align:left;padding:4px 8px;">Wave</th>
        <th style="text-align:left;padding:4px 8px;">Token</th>
        <th style="text-align:right;padding:4px 8px;">Composite</th>
        <th style="text-align:right;padding:4px 8px;">VolFull</th>
        <th style="text-align:right;padding:4px 8px;">Vol30d</th>
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

  <div style="color:#58a6ff;font-size:0.82rem;font-weight:700;margin-top:16px;margin-bottom:8px;">COMBINED K766+K773+K781 RANKED — TOP 10</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.75rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:3px 6px;">#</th>
        <th style="text-align:left;padding:3px 6px;">Source / Token</th>
        <th style="text-align:right;padding:3px 6px;">Composite</th>
        <th style="text-align:right;padding:3px 6px;">VolFull</th>
        <th style="text-align:right;padding:3px 6px;">MaxCorr</th>
        <th style="text-align:right;padding:3px 6px;">Carry%</th>
        <th style="text-align:right;padding:3px 6px;">DayVlm</th>
      </tr>
    </thead>
    <tbody>{combined_rows}
    </tbody>
  </table>
  </div>

  <div style="margin-top:14px;padding:10px 14px;background:rgba(240,136,62,0.08);border-left:3px solid #f0883e;border-radius:4px;font-size:0.77rem;color:#8b949e;">
    <strong style="color:#f0883e;">&#9888; K775 Vol-FULL Lesson Applied:</strong>
    vol_ratio uses FULL cache history (up to {FULL_HIST_DAYS}d), NOT 30d snapshot.
    30d artifacts flagged when vol_30d &gt; 2x vol_full.
    Newly listed tokens can have extreme 30d vol from listing-day spikes;
    FULL history normalises this.
    Pre-screen thresholds: vol_ratio_full &ge;1.5x | max_corr &le;0.45 | carry_stability_full 35-80%.
    K782+ &rarr; full alt-alt &sect;6 gate eval. ROI estimates deferred to K782+. K523 3-point mandatory at K782+.
    LIVE 自動変更禁止.
  </div>

  <div style="margin-top:10px;font-size:0.72rem;color:#6e7681;">
    最終更新: {jst_date} (K781 round 2c — {fetch_count} fetched, {len(survivors)} pass, K782+ queue: {', '.join(q['token'] for q in k782_queue) if k782_queue else 'none'}) &nbsp;|&nbsp; K339 REPO_ROOT &nbsp;|&nbsp; LIVE 自動変更禁止
  </div>
</section>
<!-- /K781 HIP3 ROUND2C BADGE -->
"""
    return badge


def inject_badge_into_report(badge_html: str):
    """Inject K781 badge into report.html after K773 badge."""
    report_path = BASE / "report.html"
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "K781_HIP3_ROUND2C_BADGE" in content:
        print("  K781 badge already in report.html — replacing ...")
        start_marker = "<!-- K781_HIP3_ROUND2C_BADGE:"
        end_marker = "<!-- /K781 HIP3 ROUND2C BADGE -->"
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        if start_idx >= 0 and end_idx > start_idx:
            content = content[:start_idx] + badge_html.strip() + content[end_idx:]
    else:
        # Insert after K773 badge end marker
        k773_end = "<!-- /K773 HIP3 ROUND2 BADGE -->"
        k766_end = "<!-- /K766 HL LONG-TAIL FR SCREEN BADGE -->"
        if k773_end in content:
            content = content.replace(k773_end, k773_end + "\n" + badge_html)
            print("  K781 badge injected after K773 badge.")
        elif k766_end in content:
            content = content.replace(k766_end, k766_end + "\n" + badge_html)
            print("  K781 badge injected after K766 badge (fallback).")
        else:
            content = content.replace("</body>", badge_html + "\n</body>")
            print("  K781 badge injected before </body> (fallback).")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Updated: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(f"Wave K781: HIP-3 Batch FR Fetch Round 2c")
    print(f"K339 REPO_ROOT: {REPO_ROOT}")
    print(f"LIVE 自動変更禁止 | Public repo | No credentials")
    print(f"API rate limit: {API_SLEEP}s/req | Fetch days: {FETCH_DAYS}")
    print(f"K775 lesson: FULL history vol_ratio (up to {FULL_HIST_DAYS}d) — not 30d snapshot")
    print("=" * 70)

    # Phase 1: Identify next 25 uncached tokens
    next_25, k766_survivors, k773_survivors = phase1_load_uncached()

    # Phase 2: Batch FR fetch
    fetch_results = phase2_batch_fetch(next_25)

    # Phase 3: Pre-screen with K775 full history vol verification
    phase3_results = phase3_prescreen(next_25, fetch_results)

    # Phase 4: Rank + K782+ queue
    ranked = phase4_rank_and_queue(phase3_results, k766_survivors, k773_survivors)

    # Phase 5: Save JSON
    phase5_save_json(next_25, fetch_results, phase3_results, ranked)

    # Build + inject HTML badge
    badge = build_badge(ranked, fetch_results)
    inject_badge_into_report(badge)

    # Summary
    runtime = round(time.time() - START_TIME, 1)
    print(f"\n{'=' * 70}")
    print(f"K781 COMPLETE — runtime {runtime}s")
    print(f"Tokens attempted: {len(next_25)}")
    print(f"Fetch success: {sum(1 for v in fetch_results.values() if v)}")
    print(f"Pre-screen pass (fresh): {len(ranked['survivors'])}")
    print(f"Pre-screen fail: {len(ranked['failed'])}")
    print(f"No usable data: {len(ranked['no_data'])}")
    print(f"K775 artifacts flagged: {sum(1 for s in ranked['survivors'] if s.get('vol_ratio_artifact_warn'))}")
    print(f"Combined K766+K773+K781 ranked: {len(ranked['combined_ranked'])}")
    print(f"\nK782+ QUEUE:")
    for q in ranked["k782_queue"]:
        concerns = " | ".join(q["concerns"]) if q["concerns"] else "None"
        print(f"  {q['wave_candidate']}: {q['token']} (composite={q['composite_score']:.4f}) | concerns: {concerns}")
    print(f"\nTOP 3 FOR K782-K784 EVAL QUEUE:")
    for i, q in enumerate(ranked["k782_queue"][:3]):
        print(f"  {i+1}. {q['wave_candidate']}: {q['token']}")
    print(f"{'=' * 70}")

    return ranked


if __name__ == "__main__":
    main()

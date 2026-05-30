#!/usr/bin/env python3
"""
wave_k793_hip3_round2e_screen.py — K793 HIP-3 Batch FR Fetch Round 2e (Final)
===============================================================================
K339 REPO_ROOT pattern.

MISSION
-------
K766 long-tail screen found 99 tokens with no cached FR data.
K773 (round 2)  fetched rank 1-25   by dayNtlVlm: 25 tokens.
K781 (round 2c) fetched rank 26-50  by dayNtlVlm: 25 tokens.
K785 (round 2d) fetched rank 51-75  by dayNtlVlm: 25 tokens.
K793 (round 2e) fetches rank 76-99  by dayNtlVlm: FINAL 24 tokens.
Total coverage after this wave: 99/99 = EXHAUSTED.

K775 LESSON APPLIED (mandatory)
--------------------------------
FULL history vol_ratio is used for final ranking (not 30d snapshot).
30d artifact can dramatically over-state vol_ratio for newly listed tokens.
carry_stability is evaluated on both full history AND 30d rolling.

K782 LESSON APPLIED — L004_DIFF
---------------------------------------
L004_DIFF: (X_FR - SOL_FR > 0).mean() must be in [0.30, 0.70] for BOTH:
  - FULL history (all available data)
  - OOS proxy (last 1/8 of FULL history, or last 30d if insufficient)
K788 REFINEMENT: if borderline 0.28-0.30 BUT G2 p<0.05 historical evidence
  → allow (borderline PASS) to avoid missing genuine opportunities.

METHODOLOGY
-----------
Phase 1: Load K785 (round 2d) results + K766 no_cache list
         - identify final 24 uncached tokens (rank 76-99 by dayNtlVlm)
Phase 2: Batch FR fetch (24 tokens)
         - POST /info {"type":"fundingHistory","coin":"X","startTime":ms}
         - FULL available history from 2020-01-01 via pagination
         - Rate limit: 1 req/sec
         - Cache to cache/k163_hl/
Phase 3: Enhanced pre-screen (K775 + K782 + K788 lessons)
         - vol_ratio FULL history >= 1.5x (K775)
         - L003/L007/L010/L011 max_corr <= 0.45
         - L004 carry_stability_full 35-80%
         - L004_DIFF (K782): (X_FR - SOL_FR > 0).mean() in [0.30, 0.70] FULL + OOS
         - K788 borderline: [0.28, 0.30) + needs_g2_check flag (soft PASS)
         - Composite score = vol_ratio_full × cycle_indep × fr_std_ann
Phase 4: Rank + K794+ wave queue
         - Top 5 fresh long-tail candidates from round 2e
         - Combined K766+K773+K781+K785+K793 master ranking
         - Top 3 for K794-K796 eval queue
Phase 5: Save JSON + report.html badge
         - Long-tail saturation analysis across all rounds
         - Stop criterion recommendation

SATURATION ANALYSIS (across all rounds)
-----------------------------------------
Round 1  (K766): 10/16  processed (115 checked, 16 with cache, 99 no-cache)
Round 2  (K773): 7/25   pass pre-screen
Round 2c (K781): 10/25  pass pre-screen
Round 2d (K785): 2/25   pass pre-screen (strict L004_DIFF)
Round 2e (K793): X/24   pass pre-screen ← THIS WAVE
Exhaustion: 99/99 fetched, stop criterion evaluated.

EXCLUSION LISTS (inherited from K766/K773/K781/K785)
------------------------------------------------------
V-15 vertices (K744): APT ATOM AVAX BNB ENA FIL HBAR INJ LDO SEI SOL TIA
Post-K744 accepted/tested: PEPE WIF DOGE RUNE ONDO TAO WLD PENDLE PYTH
Base assets (BTC-paired): BTC ETH
Closed-line rejects (K480-K532): SUI ARB NEAR OSMO DOT ALGO BNB
K744 candidates screened: AAVE JUP BONK KAS OP SHIB TON CRV MKR UNI RNDR
K766 round1 screened: BLUR AXS COMP STX MEME IMX GALA SAND ICP BOME STRK ARK SUSHI
K773 round2 screened: IO ZK SPX MORPHO WLFI EIGEN MEGA AVNT HEMI DYDX AR SYRUP
                      APE kSHIB CHIP AZTEC kBONK STABLE IP DASH IOTA SKY STBL NXPC VINE
K781 round2c screened: AERO BIO ORDI ETC HMSTR BERA INIT kLUNC ZEN AIXBT POPCAT
                       2Z MOODENG MELANIA SAGA PROVE ALT ZORA CELO CAKE kNEIRO YGG POLYX PNUT S
K785 round2d screened: CC W GRIFFAIN DYM ANIME GMX BIGTIME ENS LINEA LAYER MOVE
                       KAITO GOAT MET kFLOKI TURBO BRETT RESOLV MERL MINA SUPER ZETA DOOD NEO HYPER
K793 round2e (this):   APEX BSV FOGO BABY USUAL PEOPLE SOPH ME MANTA GMT BANANA
                       ACE TRB WCT REZ CFX GAS 0G SKR UMA TNSR RSR XAI NOT

CONSTRAINTS
-----------
- API rate limit: 1 req/sec (HL public API)
- 24 tokens × ~1.1s = ~27s fetch time (many already cached)
- K775 lesson: FULL history vol_ratio (not 30d snapshot)
- K782 lesson: L004_DIFF block mandatory
- K788 lesson: borderline [0.28, 0.30) soft PASS if G2 likely OK
- LIVE 自動変更禁止
- Public repo: no credentials

Usage:
    python3 wave_k793_hip3_round2e_screen.py
"""
from __future__ import annotations

import json
import math
import os
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
HL_CACHE.mkdir(parents=True, exist_ok=True)

# ── K339 pattern ──────────────────────────────────────────────────────────────
WAVE_ID = "K793"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": REPO_ROOT, "pattern": "K339"}

# ── Constants ─────────────────────────────────────────────────────────────────
HL_API = "https://api.hyperliquid.xyz/info"
API_SLEEP = 1.1            # seconds between requests
MIN_ROWS = 168             # minimum rows for pre-screen (~7d hourly)
TOP_N_ROUND2E = 24         # final 24 from remaining uncached

# Pre-screen thresholds (K766/K744/K773/K781/K785 consistent)
VOL_RATIO_MIN = 1.5
CORR_MAX = 0.45
CARRY_STABILITY_MIN = 0.35
CARRY_STABILITY_MAX = 0.80

# K782 L004_DIFF thresholds
L004_DIFF_MIN = 0.30
L004_DIFF_MAX = 0.70

# K788 borderline refinement: [0.28, 0.30) = soft pass (flag for G2 check)
L004_DIFF_BORDERLINE_LOW = 0.28

# K775 lesson: FULL history evaluation (use all available data)
FULL_HIST_DAYS = 500       # load full history up to ~1.4 years

ANN_FACTOR_8760 = math.sqrt(8760)

# Fetch from 2020-01-01 for maximum history
FULL_HISTORY_START_MS = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

# Round 2e explicit batch (rank 76-99 of original 99 no-cache tokens by dayNtlVlm)
ROUND_2E_EXPLICIT = [
    "APEX", "BSV", "FOGO", "BABY", "USUAL", "PEOPLE", "SOPH", "ME", "MANTA",
    "GMT", "BANANA", "ACE", "TRB", "WCT", "REZ", "CFX", "GAS", "0G",
    "SKR", "UMA", "TNSR", "RSR", "XAI", "NOT",
]


# ── Phase 1: Identify final 24 uncached tokens ────────────────────────────────

def phase1_load_uncached() -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Load K766 + K773 + K781 + K785 results, identify final 24 uncached tokens.
    Returns (final_24_for_fetch, k766_survivors, k773_survivors, k781_survivors, k785_survivors).
    """
    print(f"\n[Phase 1] Loading K766/K773/K781/K785 results, identifying final 24 uncached ...")

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

    # Load K781 survivors
    k781_path = DATA / "hl_long_tail_candidates_round2c.json"
    k781_survivors = []
    if k781_path.exists():
        with open(k781_path) as f:
            k781_data = json.load(f)
        k781_survivors = k781_data.get("all_survivors_ranked", [])
        print(f"  K781 survivors: {len(k781_survivors)}")
    else:
        print(f"  WARN: K781 output not found at {k781_path}")

    # Load K785 survivors
    k785_path = DATA / "hl_long_tail_candidates_round2d.json"
    k785_survivors = []
    if k785_path.exists():
        with open(k785_path) as f:
            k785_data = json.load(f)
        k785_survivors = k785_data.get("all_survivors_ranked", [])
        print(f"  K785 survivors: {len(k785_survivors)}")
    else:
        print(f"  WARN: K785 output not found at {k785_path}")

    # Build final_24 from no_cache_all metadata filtered to round-2e names
    round2e_lookup = {t["name"]: t for t in no_cache_all}
    final_24 = [round2e_lookup[n] for n in ROUND_2E_EXPLICIT if n in round2e_lookup]

    # Remaining (should be 0 after this wave)
    covered_all = set()
    for fname, rnd in [
        ("hl_long_tail_candidates_round2.json", "r2"),
        ("hl_long_tail_candidates_round2c.json", "r2c"),
        ("hl_long_tail_candidates_round2d.json", "r2d"),
    ]:
        p = DATA / fname
        if p.exists():
            with open(p) as f:
                d = json.load(f)
            for sym in d.get("fetch_results", {}).keys():
                covered_all.add(sym)
    for sym in ROUND_2E_EXPLICIT:
        covered_all.add(sym)

    remaining_after = [
        t for t in no_cache_all
        if t["name"] not in covered_all
    ]

    print(f"\n  Round 2e batch: {len(final_24)} tokens (rank 76-99 by dayNtlVlm)")
    for i, t in enumerate(final_24):
        print(f"    {i+1:2d}. {t['name']:<15} dayNtlVlm=${t['dayNtlVlm']:>10,.0f}  "
              f"OI={t.get('openInterest', 0):>10.0f}  FR_ann={t.get('funding_ann_pct', 0):>8.2f}%")

    print(f"\n  Remaining uncached after round 2e: {len(remaining_after)} tokens")
    if remaining_after:
        print(f"  Remaining: {[t['name'] for t in remaining_after]}")
    else:
        print("  *** LONG-TAIL AXIS EXHAUSTED: 99/99 fetched ***")

    return final_24, k766_survivors, k773_survivors, k781_survivors, k785_survivors


# ── Phase 2: Batch FR Fetch (FULL history) ────────────────────────────────────

def _fetch_fr_history_full(coin: str) -> Optional[pd.DataFrame]:
    """
    Fetch FULL available funding rate history from HL API using pagination.
    HL API returns max 500 rows per call starting from startTime.
    We paginate from FULL_HISTORY_START_MS until no more data returned.

    POST /info {"type":"fundingHistory","coin":"X","startTime":ms_epoch}
    Returns DataFrame with columns [timestamp, hl_fr] or None on error.
    """
    all_rows: List[Dict] = []
    start_ms = FULL_HISTORY_START_MS
    PAGE_SIZE = 500

    while True:
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_ms,
        }
        try:
            resp = requests.post(
                HL_API,
                json=payload,
                timeout=60,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            records = resp.json()

            if not records or not isinstance(records, list):
                break

            for r in records:
                ts = pd.Timestamp(int(r["time"]), unit="ms", tz="UTC")
                fr = float(r.get("fundingRate", 0) or 0)
                all_rows.append({"timestamp": ts, "hl_fr": fr})

            if len(records) < PAGE_SIZE:
                break  # Last page: fewer than 500 rows = no more data

            # Next page: start from last record's time + 1ms
            start_ms = int(records[-1]["time"]) + 1
            time.sleep(0.3)  # Brief pause between pages

        except Exception as e:
            print(f"    ERROR fetching {coin} (page start={start_ms}): {e}")
            break

    if not all_rows:
        return None

    df = pd.DataFrame(all_rows).sort_values("timestamp").drop_duplicates("timestamp")
    return df


def phase2_batch_fetch(tokens: List[Dict]) -> Dict[str, bool]:
    """
    Fetch FULL FR history for the final 24 tokens (round 2e) using pagination.
    K775 lesson: fetch FULL history (paginated from 2020-01-01) not just 30d.

    Stale cache detection: if cached max timestamp < 60d ago, re-fetch.

    Returns dict: {token_name: fetch_success}.
    """
    print(f"\n[Phase 2] Batch FR fetch (paginated FULL history) for {len(tokens)} tokens (round 2e) ...")
    print(f"  Rate limit: {API_SLEEP}s/req base — paginated fetches may take longer")
    print(f"  K775 lesson: fetching from 2020-01-01 with pagination for complete history")

    # Stale cutoff: caches older than 60d must be re-fetched
    stale_cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=60)

    results = {}

    for i, tok in enumerate(tokens):
        name = tok["name"]
        cache_path = HL_CACHE / f"hl_fr_{name}.parquet"

        # Check if already cached and fresh
        if cache_path.exists():
            try:
                existing = pd.read_parquet(cache_path)
                if len(existing) >= MIN_ROWS:
                    ts = pd.to_datetime(existing["timestamp"])
                    if ts.dt.tz is None:
                        ts = ts.dt.tz_localize("UTC")
                    max_ts = ts.max()
                    if max_ts >= stale_cutoff:
                        n_days = (ts.max() - ts.min()).days
                        print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → CACHED+FRESH ({len(existing)} rows / {n_days}d)")
                        results[name] = True
                        continue
                    else:
                        print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → STALE (max={max_ts.date()}) — re-fetching ...")
            except Exception:
                pass  # Re-fetch if corrupt

        print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → paginated FULL fetch ...", end="", flush=True)
        t0 = time.time()

        df = _fetch_fr_history_full(name)

        elapsed = time.time() - t0

        if df is None or len(df) == 0:
            print(f" NO DATA ({elapsed:.1f}s)")
            results[name] = False
        else:
            df.to_parquet(cache_path, index=False)
            n_days = (df["timestamp"].max() - df["timestamp"].min()).days if len(df) > 1 else 0
            print(f" {len(df)} rows / {n_days}d ({elapsed:.1f}s)")
            results[name] = True

        # Rate limit between tokens
        sleep_needed = max(0, API_SLEEP - elapsed % API_SLEEP) if elapsed < API_SLEEP else 0
        if sleep_needed > 0.1:
            time.sleep(sleep_needed)

    success_count = sum(1 for v in results.values() if v)
    print(f"\n  Fetch complete: {success_count}/{len(tokens)} successful")
    return results


# ── Phase 3: Pre-Screen (K775 + K782 + K788 lessons applied) ─────────────────

def _load_cached_fr(name: str, days: int = 0) -> Optional[pd.Series]:
    """
    Load cached FR series, normalised to naive hourly UTC.
    days=0 means load ALL available data (FULL history).
    K775 lesson: default to full history (days=0).
    """
    p = HL_CACHE / f"hl_fr_{name}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        ts = pd.to_datetime(df["timestamp"])
        if ts.dt.tz is not None:
            ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
        df["timestamp"] = ts.dt.floor("h")
        s = df.set_index("timestamp")["hl_fr"].sort_index()
        s = s[~s.index.duplicated(keep="last")]
        if days > 0:
            cutoff = s.index.max() - pd.Timedelta(days=days)
            return s[s.index >= cutoff]
        return s  # full history
    except Exception as e:
        print(f"    WARN: failed to load {name}: {e}")
        return None


def _load_anchor_fr() -> Dict[str, pd.Series]:
    """Load anchor token FR series for correlation + vol_ratio computation (FULL history)."""
    anchors = {}
    for tok in ["SOL", "AVAX", "FIL", "HBAR"]:
        s = _load_cached_fr(tok, days=0)  # FULL history
        if s is not None and len(s) > 100:
            anchors[tok] = s
            n_days = (s.index.max() - s.index.min()).days if len(s) > 1 else 0
            print(f"    Anchor {tok}: {len(s)} rows / {n_days}d")
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
    K775: vol_ratio uses FULL history.
    K782: L004_DIFF = (X_FR - SOL_FR > 0).mean() must be in [0.30, 0.70] FULL + OOS.
    K788: borderline [0.28, 0.30) → soft PASS with needs_g2_check flag.
    """
    # FULL history
    fr_full = _load_cached_fr(name, days=0)
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

    # Align on FULL history intersection (K775)
    fr_full_al, sol_full_al = _align(fr_full, sol_fr)
    if len(fr_full_al) < 100:
        return {
            "name": name,
            "has_data": False,
            "skip_reason": "insufficient_overlap_with_SOL_full",
            "dayNtlVlm": tok_meta.get("dayNtlVlm", 0),
        }

    n_days_full = (fr_full_al.index.max() - fr_full_al.index.min()).days if len(fr_full_al) > 1 else 0

    # vol_ratio FULL (K775 lesson — primary metric)
    tok_std_full = float(fr_full_al.std())
    sol_std_full = float(sol_full_al.std())
    vol_ratio_full = tok_std_full / sol_std_full if sol_std_full > 0 else 0.0

    # Also compute 30d rolling vol_ratio (K775: show both)
    fr_30d = _load_cached_fr(name, days=30)
    sol_30d = _load_cached_fr("SOL", days=30)
    vol_ratio_30d = 0.0
    if fr_30d is not None and sol_30d is not None and len(fr_30d) > 0 and len(sol_30d) > 0:
        fr_30d_al, sol_30d_al = _align(fr_30d, sol_30d)
        if len(fr_30d_al) > 50:
            sol_std_30d = float(sol_30d_al.std())
            vol_ratio_30d = float(fr_30d_al.std()) / sol_std_30d if sol_std_30d > 0 else 0.0

    # Detect 30d artifact
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

    # Carry stability: FULL history (absolute sign)
    carry_stability_full = float((fr_full > 0).mean())

    # Carry stability: 30d rolling (K775: both)
    carry_30d = float("nan")
    if fr_30d is not None and len(fr_30d) > 0:
        carry_30d = float((fr_30d > 0).mean())

    # ── K782 + K788: L004_DIFF — differential carry vs SOL ──────────────────
    diff_full = fr_full_al - sol_full_al
    l004_diff_full = float((diff_full > 0).mean()) if len(diff_full) > 0 else float("nan")

    # OOS proxy: last 1/8 of FULL history
    oos_cutoff_idx = len(fr_full_al) * 7 // 8
    if oos_cutoff_idx < len(fr_full_al) - 100:
        diff_oos = diff_full.iloc[oos_cutoff_idx:]
        l004_diff_oos = float((diff_oos > 0).mean()) if len(diff_oos) > 0 else float("nan")
    elif fr_30d is not None and sol_30d is not None:
        fr_30d_al2, sol_30d_al2 = _align(fr_30d, sol_30d)
        if len(fr_30d_al2) > 50:
            diff_oos_30d = fr_30d_al2 - sol_30d_al2
            l004_diff_oos = float((diff_oos_30d > 0).mean())
        else:
            l004_diff_oos = float("nan")
    else:
        l004_diff_oos = float("nan")

    # FR amplitude (annualised, full history)
    fr_mean_ann = float(fr_full.mean()) * 8760 * 100
    fr_std_ann = float(fr_full.std()) * ANN_FACTOR_8760 * 100

    # Cycle independence (1 - max corr)
    valid_corrs = [v for v in corrs.values() if not math.isnan(v)]
    max_corr = max(valid_corrs) if valid_corrs else float("nan")
    cycle_indep = 1 - max_corr if not math.isnan(max_corr) else float("nan")

    # Composite score (K744 formula, using vol_ratio_full per K775)
    if not math.isnan(cycle_indep) and vol_ratio_full > 0 and fr_std_ann > 0:
        composite = vol_ratio_full * max(0, cycle_indep) * (fr_std_ann / 100)
    else:
        composite = 0.0

    # ── Pre-screen pass/fail ──────────────────────────────────────────────────
    reasons_fail = []
    reasons_pass = []

    # vol_ratio: FULL history (K775 lesson)
    if vol_ratio_full < VOL_RATIO_MIN:
        reasons_fail.append(f"vol_ratio_full={vol_ratio_full:.3f} < {VOL_RATIO_MIN}")
    else:
        reasons_pass.append(f"vol_ratio_full={vol_ratio_full:.3f} PASS")
        if vol_ratio_artifact_warn:
            reasons_pass.append(
                f"  [K775_WARN] 30d={vol_ratio_30d:.3f} >> full={vol_ratio_full:.3f} (30d artifact detected)"
            )

    # Correlations
    for corr_key, corr_label in [("AVAX", "L003_AVAX"), ("SOL", "L011_SOL"),
                                   ("FIL", "L007_FIL"), ("HBAR", "L010_HBAR")]:
        v = corrs.get(corr_key, float("nan"))
        if not math.isnan(v) and v > CORR_MAX:
            reasons_fail.append(f"corr_{corr_key}={v:.3f} > {CORR_MAX}")
        else:
            disp = "n/a" if math.isnan(v) else f"{v:.3f}"
            reasons_pass.append(f"{corr_label}={disp} PASS")

    # L004 absolute carry stability
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

    # L004_DIFF (K782 + K788 lessons)
    l004_diff_full_valid = not math.isnan(l004_diff_full)
    l004_diff_oos_valid = not math.isnan(l004_diff_oos)
    k788_borderline_flag = False  # Flag for borderline case needing G2 check

    if l004_diff_full_valid:
        # Check full L004_DIFF
        full_in_range = L004_DIFF_MIN <= l004_diff_full <= L004_DIFF_MAX
        full_borderline = L004_DIFF_BORDERLINE_LOW <= l004_diff_full < L004_DIFF_MIN

        if full_in_range:
            reasons_pass.append(f"L004_DIFF_full={l004_diff_full:.3f} PASS")
            # Check OOS
            if l004_diff_oos_valid:
                oos_in_range = L004_DIFF_MIN <= l004_diff_oos <= L004_DIFF_MAX
                oos_borderline = L004_DIFF_BORDERLINE_LOW <= l004_diff_oos < L004_DIFF_MIN
                if oos_in_range:
                    reasons_pass.append(f"L004_DIFF_oos={l004_diff_oos:.3f} PASS")
                elif oos_borderline:
                    # K788: OOS borderline → soft pass, needs G2 check
                    reasons_pass.append(
                        f"L004_DIFF_oos={l004_diff_oos:.3f} BORDERLINE (K788: needs G2 check)"
                    )
                    k788_borderline_flag = True
                else:
                    reasons_fail.append(
                        f"L004_DIFF_oos={l004_diff_oos:.3f} OUTSIDE [{L004_DIFF_MIN},{L004_DIFF_MAX}] "
                        f"(K782 OOS diff-carry BLOCK)"
                    )
        elif full_borderline:
            # K788: FULL borderline → soft pass, needs G2 check
            reasons_pass.append(
                f"L004_DIFF_full={l004_diff_full:.3f} BORDERLINE [{L004_DIFF_BORDERLINE_LOW},{L004_DIFF_MIN}] "
                f"(K788: soft PASS — needs G2 p-value check before deploy)"
            )
            k788_borderline_flag = True
        else:
            reasons_fail.append(
                f"L004_DIFF_full={l004_diff_full:.3f} OUTSIDE [{L004_DIFF_MIN},{L004_DIFF_MAX}] "
                f"(K782 diff-carry BLOCK)"
            )
    else:
        # If we can't compute, soft-pass with warning
        reasons_pass.append("L004_DIFF=n/a (insufficient aligned data — soft PASS)")

    prescreen_pass = len(reasons_fail) == 0

    return {
        "name": name,
        "has_data": True,
        "n_rows": len(fr_full),
        "n_days_full": n_days_full,
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
        # K782 + K788 L004_DIFF
        "l004_diff_full": round(l004_diff_full, 4) if not math.isnan(l004_diff_full) else None,
        "l004_diff_oos": round(l004_diff_oos, 4) if not math.isnan(l004_diff_oos) else None,
        "l004_diff_pass": (
            l004_diff_full_valid
            and L004_DIFF_MIN <= l004_diff_full <= L004_DIFF_MAX
            and (not l004_diff_oos_valid or L004_DIFF_MIN <= l004_diff_oos <= L004_DIFF_MAX)
        ),
        "k788_borderline": k788_borderline_flag,
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
        "k775_full_hist_rows": len(fr_full),
        "k775_full_hist_days": n_days_full,
    }


def phase3_prescreen(tokens: List[Dict], fetch_results: Dict[str, bool]) -> List[Dict]:
    """Run K775+K782+K788-aware pre-screen on all fetched tokens."""
    print(f"\n[Phase 3] Pre-screen + K775 FULL history + K782 L004_DIFF + K788 borderline ...")

    print(f"\n  Loading anchor FR series (FULL history) ...")
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
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → NO USABLE DATA ({result.get('skip_reason', '')})")
        else:
            status = "PASS" if result["prescreen_pass"] else "FAIL"
            if result["prescreen_pass"] and result.get("k788_borderline"):
                status = "PASS*"  # Borderline pass
            artifact_flag = " [K775_ART]" if result.get("vol_ratio_artifact_warn") else ""
            border_flag = " [K788_BORDER]" if result.get("k788_borderline") else ""
            l004d_full = result.get("l004_diff_full")
            l004d_oos = result.get("l004_diff_oos")
            l004d_str = (
                f"L004D_f={l004d_full:.3f}" if l004d_full is not None else "L004D_f=n/a"
            )
            l004d_oos_str = (
                f"oos={l004d_oos:.3f}" if l004d_oos is not None else "oos=n/a"
            )
            reasons = "; ".join(result["reasons_fail"]) if result["reasons_fail"] else "all PASS"
            print(f"  [{i+1:2d}/{len(tokens)}] {name:<15} → {status:5s} | "
                  f"vol_full={result['vol_ratio_full']:.3f}x vol_30d={result['vol_ratio_30d']:.3f}x{artifact_flag} | "
                  f"L003={result['corr_AVAX']:.3f} "
                  f"L010={result['corr_HBAR']:.3f} "
                  f"L011={result['corr_SOL']:.3f} | "
                  f"carry_full={result['carry_stability_full']:.3f} | "
                  f"{l004d_str} {l004d_oos_str}{border_flag} | "
                  f"comp={result['composite_score']:.4f}"
                  + (f" | FAIL: {reasons}" if result["reasons_fail"] else ""))

    survivors = [r for r in results if r.get("has_data") and r.get("prescreen_pass")]
    failed = [r for r in results if r.get("has_data") and not r.get("prescreen_pass")]
    no_data = [r for r in results if not r.get("has_data")]

    print(f"\n  === Phase 3 Summary ===")
    print(f"  Passed pre-screen: {len(survivors)} (includes K788 borderline PASS*)")
    print(f"  Failed pre-screen: {len(failed)}")
    print(f"  No usable data:    {len(no_data)}")
    print(f"  K775 FULL history: vol_ratio_full used for all decisions")
    print(f"  K782 L004_DIFF:    differential carry [0.30, 0.70] mandatory")
    print(f"  K788 borderline:   [0.28, 0.30) soft PASS flagged for G2 check")

    return results


# ── Phase 4: Rank + Wave Queue ────────────────────────────────────────────────

def _saturation_analysis(survivors_2e: List[Dict]) -> Dict:
    """
    Compute long-tail axis saturation analysis across all 5 rounds.
    Returns dict with pass rates and stop criterion recommendation.
    """
    pass_rates = {
        "round1_K766":  {"attempted": 16, "pass": 10, "rate": 10/16},
        "round2_K773":  {"attempted": 25, "pass": 7,  "rate": 7/25},
        "round2c_K781": {"attempted": 25, "pass": 10, "rate": 10/25},
        "round2d_K785": {"attempted": 25, "pass": 2,  "rate": 2/25},
        "round2e_K793": {"attempted": 24, "pass": len(survivors_2e), "rate": len(survivors_2e)/24},
    }

    # Stop criterion: < 1/25 = 4% ≈ exhausted
    STOP_THRESHOLD = 1/25
    round2e_rate = pass_rates["round2e_K793"]["rate"]
    exhausted = (round2e_rate < STOP_THRESHOLD) and (len(survivors_2e) <= 1)

    total_attempted = sum(v["attempted"] for v in pass_rates.values())
    total_pass = sum(v["pass"] for v in pass_rates.values())

    recommendation = (
        "STOP — long-tail axis exhausted: 99/99 tokens screened, pass rate collapsed"
        if exhausted else
        "CONTINUE — residual candidates remain above threshold"
    )

    return {
        "pass_rates_by_round": pass_rates,
        "total_attempted": total_attempted,
        "total_pass": total_pass,
        "overall_pass_rate": total_pass / total_attempted if total_attempted > 0 else 0,
        "stop_threshold": STOP_THRESHOLD,
        "round2e_rate": round2e_rate,
        "long_tail_exhausted": exhausted,
        "recommendation": recommendation,
        "note": "99/99 tokens from K766 no-cache list have now been fetched and screened",
    }


def phase4_rank_and_queue(
    phase3_results: List[Dict],
    k766_survivors: List[Dict],
    k773_survivors: List[Dict],
    k781_survivors: List[Dict],
    k785_survivors: List[Dict],
) -> Dict:
    """
    Rank Phase 3 survivors by composite score.
    Build K794+ wave queue (top 3).
    Build combined K766+K773+K781+K785+K793 ranked list.
    """
    print(f"\n[Phase 4] Ranking survivors + building K794+ wave queue ...")

    survivors = [r for r in phase3_results if r.get("has_data") and r.get("prescreen_pass")]
    failed = [r for r in phase3_results if r.get("has_data") and not r.get("prescreen_pass")]
    no_data = [r for r in phase3_results if not r.get("has_data")]

    survivors.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === K793 ROUND 2e SURVIVORS (fresh long-tail, ranked) ===")
    if survivors:
        for i, s in enumerate(survivors):
            artifact = " [K775_ART]" if s.get("vol_ratio_artifact_warn") else ""
            border = " [K788*]" if s.get("k788_borderline") else ""
            l004d = s.get("l004_diff_full")
            l004d_str = f"L004D={l004d:.3f}" if l004d is not None else "L004D=n/a"
            print(f"  #{i+1:2d} {s['name']:<15} | composite={s['composite_score']:.4f} | "
                  f"vol_full={s['vol_ratio_full']:.3f}x{artifact} | "
                  f"max_corr={s.get('max_corr', float('nan')):.3f} | "
                  f"carry_full={s['carry_stability']:.3f} | "
                  f"{l004d_str}{border} | "
                  f"FR_std_ann={s.get('fr_std_ann_pct', 0):.1f}% | "
                  f"dayVlm=${s.get('dayNtlVlm', 0)/1e6:.3f}M")
    else:
        print("  (no survivors — round 2e fully exhausted)")

    print(f"\n  === FAILED PRE-SCREEN ===")
    for f_ in sorted(failed, key=lambda x: x.get("composite_score", 0), reverse=True):
        reasons = "; ".join(f_["reasons_fail"])
        print(f"  {f_['name']:<15} | {reasons}")

    # K794+ queue: top 3 survivors
    k794_queue = []
    for i, s in enumerate(survivors[:3]):
        entry = {
            "wave_candidate": f"K{794 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_full": s["vol_ratio_full"],
            "vol_ratio_30d": s["vol_ratio_30d"],
            "vol_ratio_artifact_warn": s.get("vol_ratio_artifact_warn", False),
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "carry_30d": s.get("carry_30d", float("nan")),
            "l004_diff_full": s.get("l004_diff_full"),
            "l004_diff_oos": s.get("l004_diff_oos"),
            "k788_borderline": s.get("k788_borderline", False),
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "concerns": [],
            "source": "K793_round2e",
        }
        if s.get("dayNtlVlm", 0) < 5_000_000:
            entry["concerns"].append("LOW_LIQUIDITY (<$5M/day) — may fail G6 entries/yr or G9 history")
        if s.get("openInterest", 0) < 100_000:
            entry["concerns"].append("LOW_OI (<$100K) — execution slippage risk")
        if s.get("vol_ratio_artifact_warn"):
            entry["concerns"].append(
                f"K775_ARTIFACT: 30d vol={s['vol_ratio_30d']:.2f}x >> full={s['vol_ratio_full']:.2f}x — use FULL"
            )
        if s.get("k788_borderline"):
            l004d = s.get("l004_diff_full")
            entry["concerns"].append(
                f"K788_BORDERLINE: L004_DIFF={l004d:.3f} [{L004_DIFF_BORDERLINE_LOW},{L004_DIFF_MIN}) "
                f"— requires G2 permutation p<0.05 before deploy"
            )
        l004d = s.get("l004_diff_full")
        if l004d is not None and not s.get("k788_borderline") and (l004d < 0.40 or l004d > 0.60):
            entry["concerns"].append(
                f"L004_DIFF borderline: {l004d:.3f} — verify OOS stability before G5"
            )
        k794_queue.append(entry)

    # Backlog (rank 4+)
    backlog_new = []
    for i, s in enumerate(survivors[3:]):
        backlog_new.append({
            "wave_candidate": f"K{797 + i}",
            "token": s["name"],
            "composite_score": s["composite_score"],
            "vol_ratio_full": s["vol_ratio_full"],
            "vol_ratio_30d": s["vol_ratio_30d"],
            "max_corr": s.get("max_corr", float("nan")),
            "carry_stability": s["carry_stability"],
            "l004_diff_full": s.get("l004_diff_full"),
            "k788_borderline": s.get("k788_borderline", False),
            "fr_std_ann_pct": s.get("fr_std_ann_pct", 0),
            "dayNtlVlm": s.get("dayNtlVlm", 0),
            "source": "K793_round2e_backlog",
        })

    print(f"\n  === K794+ WAVE QUEUE ===")
    if k794_queue:
        for entry in k794_queue:
            concerns = " | ".join(entry["concerns"]) if entry["concerns"] else "None"
            print(f"  {entry['wave_candidate']}: {entry['token']:<15} | composite={entry['composite_score']:.4f} | "
                  f"vol_full={entry['vol_ratio_full']:.3f}x | concerns: {concerns}")
    else:
        print("  (empty — no survivors from round 2e)")

    # Combined K766+K773+K781+K785+K793 ranked list (dedup by name)
    seen: set = set()
    combined = []

    for s in survivors:            # K793 round2e first (freshest)
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K793_round2e"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k785_survivors:       # K785 round2d
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K785_round2d"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k781_survivors:       # K781 round2c
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K781_round2c"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k773_survivors:       # K773 round2
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K773_round2"
            combined.append(s_copy)
            seen.add(s["name"])
    for s in k766_survivors:       # K766 round1
        if s["name"] not in seen:
            s_copy = dict(s)
            s_copy["source"] = "K766_round1"
            combined.append(s_copy)
            seen.add(s["name"])

    combined.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    print(f"\n  === COMBINED K766+K773+K781+K785+K793 RANKED LIST ({len(combined)} tokens) ===")
    for i, s in enumerate(combined):
        src = s.get("source", "?")
        artifact = " [K775_ART]" if s.get("vol_ratio_artifact_warn") else ""
        border = " [K788*]" if s.get("k788_borderline") else ""
        print(f"  #{i+1:2d} [{src:15s}] {s['name']:<15} composite={s.get('composite_score', 0):.4f}{artifact}{border}")

    # Saturation analysis
    saturation = _saturation_analysis(survivors)
    print(f"\n  === LONG-TAIL SATURATION ANALYSIS ===")
    for rnd, info in saturation["pass_rates_by_round"].items():
        print(f"  {rnd:<20}: {info['pass']:2d}/{info['attempted']:2d} = {info['rate']*100:.1f}%")
    print(f"  Total: {saturation['total_pass']}/{saturation['total_attempted']} = "
          f"{saturation['overall_pass_rate']*100:.1f}%")
    print(f"  Round 2e rate: {saturation['round2e_rate']*100:.1f}% (stop threshold: {saturation['stop_threshold']*100:.1f}%)")
    print(f"  Long-tail exhausted: {saturation['long_tail_exhausted']}")
    print(f"  Recommendation: {saturation['recommendation']}")

    return {
        "survivors": survivors,
        "failed": failed,
        "no_data": no_data,
        "top5": survivors[:5],
        "k794_queue": k794_queue,
        "backlog_new": backlog_new,
        "combined_ranked": combined,
        "saturation": saturation,
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
    final_24: List[Dict],
    fetch_results: Dict[str, bool],
    phase3_results: List[Dict],
    ranked: Dict,
) -> Path:
    """Save K793 round-2e candidates JSON."""
    now_utc = datetime.now(timezone.utc)

    output = {
        "wave": WAVE_ID,
        "title": "K793 HIP-3 Batch FR Fetch Round 2e (Final — Long-Tail Exhaust)",
        "generated_utc": now_utc.isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": "conserv/mid/optimist 3-point — deferred to K794+ full evals",
        "live_auto_change_prohibited": True,
        "k775_lesson": {
            "description": "FULL history vol_ratio used for all pre-screen decisions (not 30d snapshot)",
            "fetch_strategy": "startTime=2020-01-01 for maximum history",
            "vol_ratio_metric": "vol_ratio_full (primary) + vol_ratio_30d (diagnostic)",
            "artifact_detection": "30d artifact flagged when vol_ratio_30d > 2x vol_ratio_full",
        },
        "k782_lesson": {
            "description": "L004_DIFF (X_FR - SOL_FR > 0).mean() must be in [0.30, 0.70] FULL + OOS",
            "thresholds": {"min": L004_DIFF_MIN, "max": L004_DIFF_MAX},
            "rationale": "K782 PROVE rejected for diff_carry=27.7% — structural SOL-FR dominance in aligned window",
        },
        "k788_lesson": {
            "description": "K788 borderline refinement: [0.28, 0.30) soft PASS if G2 p<0.05 likely",
            "borderline_low": L004_DIFF_BORDERLINE_LOW,
            "borderline_high": L004_DIFF_MIN,
            "rationale": "Avoid missing genuine opportunities at slight boundary cases; requires G2 verification",
        },
        "round2e_summary": {
            "tokens_attempted": len(final_24),
            "fetch_success": sum(1 for v in fetch_results.values() if v),
            "fetch_failed": sum(1 for v in fetch_results.values() if not v),
            "prescreen_pass": len(ranked["survivors"]),
            "prescreen_fail": len(ranked["failed"]),
            "no_usable_data": len(ranked["no_data"]),
            "k788_borderline_count": sum(1 for r in phase3_results if r.get("k788_borderline")),
            "k775_artifact_flagged": sum(1 for r in phase3_results if r.get("vol_ratio_artifact_warn")),
            "l004_diff_blocked": sum(
                1 for r in phase3_results
                if r.get("has_data") and not r.get("prescreen_pass")
                and any("L004_DIFF" in rf for rf in r.get("reasons_fail", []))
            ),
        },
        "fetch_results": fetch_results,
        "top5_fresh_candidates": ranked["top5"],
        "k794_queue": ranked["k794_queue"],
        "all_survivors_ranked": ranked["survivors"],
        "failed_prescreen": ranked["failed"],
        "backlog_new": ranked["backlog_new"],
        "combined_k766_k773_k781_k785_k793_ranked": ranked["combined_ranked"],
        "saturation_analysis": ranked["saturation"],
        "phase3_all_results": phase3_results,
    }

    output_clean = _replace_nan(output)

    path = DATA / "hl_long_tail_candidates_round2e.json"
    with open(path, "w") as f:
        json.dump(output_clean, f, indent=2)
    print(f"\n  Saved: {path}")
    return path


# ── Phase 6: report.html badge ────────────────────────────────────────────────

def build_badge(ranked: Dict, fetch_results: Dict[str, bool], final_24: List[Dict]) -> str:
    """Build K793 HTML badge for report.html."""
    now_utc = datetime.now(timezone.utc)
    jst_hour = (now_utc.hour + 9) % 24
    jst_date = now_utc.strftime(f"%Y-%m-%d {jst_hour:02d}:{now_utc.minute:02d} JST")

    top5 = ranked["top5"]
    k794_queue = ranked["k794_queue"]
    combined = ranked["combined_ranked"]
    survivors = ranked["survivors"]
    failed = ranked["failed"]
    saturation = ranked["saturation"]

    # Top-5 fresh rows
    rows_html = ""
    if not top5:
        rows_html = """
      <tr><td colspan="12" style="color:#8b949e;text-align:center;padding:10px;">
        No survivors from round 2e — long-tail axis fully exhausted
      </td></tr>"""
    for i, s in enumerate(top5):
        wave_cand = k794_queue[i]["wave_candidate"] if i < len(k794_queue) else "BACKLOG"
        name = s["name"]
        comp = s.get("composite_score", 0)
        vol_full = s.get("vol_ratio_full", 0)
        vol_30d = s.get("vol_ratio_30d", 0)
        max_corr = s.get("max_corr", float("nan"))
        carry = s.get("carry_stability", 0)
        fr_std = s.get("fr_std_ann_pct", 0)
        vlm = s.get("dayNtlVlm", 0)
        artifact = s.get("vol_ratio_artifact_warn", False)
        border = s.get("k788_borderline", False)
        l004d = s.get("l004_diff_full")
        n_days = s.get("n_days_full", s.get("k775_full_hist_days", 0))

        corr_disp = (
            f"{max_corr:.3f}" if max_corr is not None
            and not (isinstance(max_corr, float) and math.isnan(max_corr))
            else "n/a"
        )
        l004d_disp = f"{l004d:.3f}" if l004d is not None else "n/a"
        artifact_badge = (
            " <span style='color:#f0883e;font-size:0.68rem;'>&#9888;K775</span>"
            if artifact else ""
        )
        border_badge = (
            " <span style='color:#d29922;font-size:0.68rem;'>&#9889;K788</span>"
            if border else ""
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
        <td style="color:#e3b341;text-align:right;">{l004d_disp}{border_badge}</td>
        <td style="color:#e6edf3;text-align:right;">{fr_std:.1f}%</td>
        <td style="color:#e6edf3;text-align:right;">${vlm/1e6:.3f}M{liq_warn}</td>
        <td style="color:#8b949e;text-align:right;font-size:0.72rem;">{n_days}d</td>
      </tr>"""

    # Failed pre-screen rows
    fail_rows_html = ""
    for f_ in sorted(failed, key=lambda x: x.get("composite_score", 0), reverse=True):
        name = f_["name"]
        reasons = "; ".join(f_.get("reasons_fail", []))
        l004d = f_.get("l004_diff_full")
        l004d_disp = f"{l004d:.3f}" if l004d is not None else "n/a"
        l004d_block = any("L004_DIFF" in r for r in f_.get("reasons_fail", []))
        l004d_color = "#f85149" if l004d_block else "#8b949e"
        fail_rows_html += f"""
      <tr style="border-bottom:1px solid #21262d;opacity:0.75;">
        <td style="color:#f85149;padding:3px 6px;">FAIL</td>
        <td style="color:#e6edf3;padding:3px 6px;font-weight:700;">{name}</td>
        <td style="color:{l004d_color};padding:3px 6px;text-align:right;">{l004d_disp}</td>
        <td style="color:#8b949e;padding:3px 6px;font-size:0.70rem;">{reasons[:80]}{'...' if len(reasons) > 80 else ''}</td>
      </tr>"""

    # Combined top-10 rows
    combined_rows = ""
    for i, s in enumerate(combined[:10]):
        src = s.get("source", "?")
        if "K793" in src:
            src_color = "#bc8cff"
        elif "K785" in src:
            src_color = "#f0883e"
        elif "K781" in src:
            src_color = "#e3b341"
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
        l004d = s.get("l004_diff_full")
        corr_disp = (
            f"{max_corr:.3f}" if max_corr is not None
            and not (isinstance(max_corr, float) and math.isnan(max_corr))
            else "n/a"
        )
        l004d_disp = f"{l004d:.3f}" if l004d is not None else "n/a"
        combined_rows += f"""
      <tr style="border-bottom:1px solid #21262d;">
        <td style="color:#8b949e;padding:3px 6px;">#{i+1}</td>
        <td style="padding:3px 6px;">{src_badge} <span style="color:#3fb950;font-weight:700;">{name}</span></td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{comp:.4f}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{vol_full:.3f}x</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{corr_disp}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">{carry:.3f}</td>
        <td style="color:#e3b341;text-align:right;padding:3px 6px;">{l004d_disp}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 6px;">${vlm/1e6:.3f}M</td>
      </tr>"""

    # Saturation table rows
    sat_rows = ""
    round_labels = {
        "round1_K766":  "Round 1 (K766)",
        "round2_K773":  "Round 2 (K773)",
        "round2c_K781": "Round 2c (K781)",
        "round2d_K785": "Round 2d (K785)",
        "round2e_K793": "Round 2e (K793) ★",
    }
    for rnd_key, info in saturation["pass_rates_by_round"].items():
        lbl = round_labels.get(rnd_key, rnd_key)
        rate_pct = info["rate"] * 100
        bar_w = int(rate_pct * 2)  # max 100px for 50%
        if "K793" in rnd_key:
            row_color = "#bc8cff"
            star = " &#9733;"
        elif rate_pct < 10:
            row_color = "#f85149"
            star = ""
        else:
            row_color = "#3fb950"
            star = ""
        sat_rows += f"""
      <tr style="border-bottom:1px solid #21262d;">
        <td style="color:{row_color};padding:3px 8px;font-weight:{'700' if 'K793' in rnd_key else '400'};">{lbl}</td>
        <td style="color:#e6edf3;text-align:right;padding:3px 8px;">{info['pass']}/{info['attempted']}</td>
        <td style="color:{row_color};text-align:right;padding:3px 8px;">{rate_pct:.1f}%</td>
        <td style="padding:3px 8px;">
          <div style="background:rgba(255,255,255,0.08);border-radius:3px;height:8px;width:120px;">
            <div style="background:{row_color};border-radius:3px;height:8px;width:{min(bar_w*1.2, 120):.0f}px;"></div>
          </div>
        </td>
      </tr>"""

    fetch_count = sum(1 for v in fetch_results.values() if v)
    artifact_count = sum(1 for s in survivors if s.get("vol_ratio_artifact_warn"))
    l004d_blocked = sum(
        1 for r in ranked.get("failed", [])
        if any("L004_DIFF" in rf for rf in r.get("reasons_fail", []))
    )
    k788_count = sum(1 for r in ranked.get("survivors", []) if r.get("k788_borderline"))
    exhausted = saturation["long_tail_exhausted"]
    exhaust_label = "EXHAUSTED" if exhausted else "CONTINUE"
    exhaust_color = "#f85149" if exhausted else "#3fb950"

    badge = f"""
<!-- K793_HIP3_ROUND2E_BADGE: K793 HIP-3 Batch FR Fetch Round 2e Final | top24_fetched={fetch_count}/{len(fetch_results)} | prescreen_pass={len(survivors)} | K794+ queue={len(k794_queue)} | combined_K766+K773+K781+K785+K793={len(combined)} | K775_artifacts={artifact_count} | K782_L004_DIFF_blocked={l004d_blocked} | long_tail={exhaust_label} | K339 REPO_ROOT | {jst_date} -->
<!-- K793 HIP3 ROUND2E BADGE START -->
<section id="k793-round2e" style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:18px 22px;margin:18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="background:rgba(188,140,255,0.15);border:2px solid #bc8cff;border-radius:8px;padding:4px 10px;color:#bc8cff;font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K793</div>
    <div style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:6px;padding:3px 9px;color:#3fb950;font-size:0.73rem;font-weight:700;">ROUND 2e SCREEN COMPLETE</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">K766+K773+K781+K785+K793 combined</div>
    <div style="background:rgba({248 if exhausted else 63},{81 if exhausted else 185},{73 if exhausted else 80},0.15);border:1px solid {exhaust_color};border-radius:6px;padding:3px 9px;color:{exhaust_color};font-size:0.70rem;font-weight:800;">LONG-TAIL {exhaust_label}</div>
    <div style="color:#8b949e;font-size:0.72rem;margin-left:auto;">{jst_date}</div>
  </div>

  <div style="color:#e6edf3;font-size:1.08rem;font-weight:900;margin-bottom:8px;">&#128301; K793 — HIP-3 Batch FR Fetch Round 2e (Final) — {len(survivors)} Fresh Candidates Pass Pre-Screen</div>

  <div style="background:rgba(30,37,44,0.7);border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:0.78rem;color:#8b949e;line-height:1.6;">
    <strong style="color:#e6edf3;">Round 2e scope:</strong> Final 24 uncached tokens (rank 76-99 of 99 by dayNtlVlm) &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Fetched:</strong> {fetch_count}/{len(fetch_results)} (FULL history from 2020-01-01) &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Pre-screen pass:</strong> {len(survivors)} fresh &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">K775 vol-FULL:</strong> vol_ratio_full for all decisions &nbsp;|&nbsp;
    <strong style="color:#f0883e;">K782 L004_DIFF:</strong> diff-carry [{L004_DIFF_MIN},{L004_DIFF_MAX}] block — {l004d_blocked} blocked &nbsp;|&nbsp;
    <strong style="color:#d29922;">K788 borderline:</strong> [{L004_DIFF_BORDERLINE_LOW},{L004_DIFF_MIN}) soft PASS — {k788_count} flagged &nbsp;|&nbsp;
    <strong style="color:#e6edf3;">Combined K766–K793:</strong> {len(combined)} candidates total
  </div>

  <div style="color:#f0883e;font-size:0.85rem;font-weight:700;margin-bottom:8px;">TOP-5 FRESH LONG-TAIL CANDIDATES → K794+ QUEUE</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.76rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:4px 6px;">Rank</th>
        <th style="text-align:left;padding:4px 6px;">Wave</th>
        <th style="text-align:left;padding:4px 6px;">Token</th>
        <th style="text-align:right;padding:4px 6px;">Composite</th>
        <th style="text-align:right;padding:4px 6px;">VolFull</th>
        <th style="text-align:right;padding:4px 6px;">Vol30d</th>
        <th style="text-align:right;padding:4px 6px;">MaxCorr</th>
        <th style="text-align:right;padding:4px 6px;">Carry%</th>
        <th style="text-align:right;padding:4px 6px;">L004_DIFF</th>
        <th style="text-align:right;padding:4px 6px;">FR_std_ann</th>
        <th style="text-align:right;padding:4px 6px;">DayVlm</th>
        <th style="text-align:right;padding:4px 6px;">Hist</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>
  </div>

  <div style="color:#f85149;font-size:0.82rem;font-weight:700;margin-top:16px;margin-bottom:8px;">FAILED PRE-SCREEN ({len(failed)} tokens)</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.74rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:3px 6px;">Status</th>
        <th style="text-align:left;padding:3px 6px;">Token</th>
        <th style="text-align:right;padding:3px 6px;">L004_DIFF</th>
        <th style="text-align:left;padding:3px 6px;">Reason</th>
      </tr>
    </thead>
    <tbody>{fail_rows_html}
    </tbody>
  </table>
  </div>

  <div style="color:#58a6ff;font-size:0.82rem;font-weight:700;margin-top:16px;margin-bottom:8px;">COMBINED K766+K773+K781+K785+K793 RANKED — TOP 10</div>
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
        <th style="text-align:right;padding:3px 6px;">L004_DIFF</th>
        <th style="text-align:right;padding:3px 6px;">DayVlm</th>
      </tr>
    </thead>
    <tbody>{combined_rows}
    </tbody>
  </table>
  </div>

  <div style="color:#bc8cff;font-size:0.82rem;font-weight:700;margin-top:16px;margin-bottom:8px;">LONG-TAIL SATURATION ANALYSIS — ALL 5 ROUNDS</div>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:0.76rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:3px 8px;">Round</th>
        <th style="text-align:right;padding:3px 8px;">Pass/Attempted</th>
        <th style="text-align:right;padding:3px 8px;">Pass Rate</th>
        <th style="text-align:left;padding:3px 8px;">Bar</th>
      </tr>
    </thead>
    <tbody>{sat_rows}
    </tbody>
  </table>
  </div>
  <div style="margin-top:8px;padding:8px 12px;background:rgba({248 if exhausted else 63},{81 if exhausted else 185},{73 if exhausted else 80},0.08);border-left:3px solid {exhaust_color};border-radius:4px;font-size:0.78rem;color:#e6edf3;">
    <strong style="color:{exhaust_color};">&#9654; Stop Criterion:</strong> {saturation['recommendation']}
    &nbsp;|&nbsp;
    <strong style="color:#8b949e;">Total screened:</strong> {saturation['total_pass']}/{saturation['total_attempted']} pass ({saturation['overall_pass_rate']*100:.1f}%)
    &nbsp;|&nbsp;
    <strong style="color:#8b949e;">99/99 tokens fetched</strong>
  </div>

  <div style="margin-top:14px;padding:10px 14px;background:rgba(188,140,255,0.08);border-left:3px solid #bc8cff;border-radius:4px;font-size:0.77rem;color:#8b949e;">
    <strong style="color:#f0883e;">&#9888; K775 Vol-FULL Applied:</strong>
    vol_ratio uses FULL history (from 2020-01-01), NOT 30d snapshot.
    30d artifacts flagged when vol_30d &gt; 2&times; vol_full.
    &nbsp;|&nbsp;
    <strong style="color:#e3b341;">&#9889; K782 L004_DIFF Applied:</strong>
    (X_FR &minus; SOL_FR &gt; 0).mean() must be in [{L004_DIFF_MIN}, {L004_DIFF_MAX}] for FULL + OOS.
    &nbsp;|&nbsp;
    <strong style="color:#d29922;">&#9889; K788 Borderline:</strong>
    [{L004_DIFF_BORDERLINE_LOW}, {L004_DIFF_MIN}) soft PASS — requires G2 p&lt;0.05 verification.
    Pre-screen: vol_ratio_full &ge;1.5x | max_corr &le;0.45 | carry_full 35-80% | L004_DIFF 30-70%.
    K794+ &rarr; full alt-alt &sect;6 gate eval. ROI estimates deferred to K794+. K523 3-point mandatory.
    LIVE 自動変更禁止.
  </div>

  <div style="color:#6e7681;font-size:0.72rem;border-top:1px solid rgba(188,140,255,0.15);padding-top:8px;margin-top:10px;">
    最終更新: {jst_date} (K793 round 2e — {fetch_count} fetched, {len(survivors)} pass, K794+ queue: {', '.join(e['token'] for e in k794_queue) if k794_queue else 'none'}) &nbsp;|&nbsp; K339 REPO_ROOT &nbsp;|&nbsp; LIVE 自動変更禁止 &nbsp;|&nbsp; Long-tail: {exhaust_label}
  </div>
</section>
<!-- /K793 HIP3 ROUND2E BADGE -->
"""
    return badge


def phase6_update_report_html(badge: str) -> None:
    """Insert or replace K793 badge in report.html after the K785 badge."""
    report_path = BASE / "report.html"
    if not report_path.exists():
        print(f"  WARN: report.html not found at {report_path} — skipping")
        return

    with open(report_path, "r") as f:
        html = f.read()

    START_MARKER = "<!-- K793 HIP3 ROUND2E BADGE START -->"
    END_MARKER = "<!-- /K793 HIP3 ROUND2E BADGE -->"

    if START_MARKER in html and END_MARKER in html:
        # Replace existing badge
        start_idx = html.index(START_MARKER)
        meta_marker = "<!-- K793_HIP3_ROUND2E_BADGE:"
        if meta_marker in html:
            meta_idx = html.rindex(meta_marker, 0, start_idx)
            html = html[:meta_idx] + badge.strip() + "\n" + html[html.index(END_MARKER) + len(END_MARKER):]
        else:
            html = html[:start_idx] + badge.strip() + "\n" + html[html.index(END_MARKER) + len(END_MARKER):]
        print(f"  Replaced existing K793 badge in report.html")
    else:
        # Insert after K785 badge end
        k785_end = "<!-- /K785 HIP3 ROUND2D BADGE -->"
        if k785_end in html:
            insert_pos = html.index(k785_end) + len(k785_end)
            html = html[:insert_pos] + "\n\n" + badge.strip() + "\n" + html[insert_pos:]
            print(f"  Inserted K793 badge after K785 badge in report.html")
        else:
            # Fallback: insert before </body>
            html = html.replace("</body>", badge.strip() + "\n\n</body>")
            print(f"  Inserted K793 badge before </body> in report.html (fallback)")

    with open(report_path, "w") as f:
        f.write(html)
    print(f"  report.html updated: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"{'='*70}")
    print(f"  Wave {WAVE_ID} — HIP-3 Batch FR Fetch Round 2e (Final)")
    print(f"  K339 REPO_ROOT: {REPO_ROOT}")
    print(f"  K775: FULL history vol_ratio (startTime=2020-01-01)")
    print(f"  K782: L004_DIFF block [0.30, 0.70] mandatory")
    print(f"  K788: borderline [{L004_DIFF_BORDERLINE_LOW}, {L004_DIFF_MIN}) soft PASS")
    print(f"  Round 2e: final 24 tokens (rank 76-99 of 99)")
    print(f"  LONG-TAIL EXHAUST CHECK: 99/99 total coverage after this wave")
    print(f"{'='*70}")

    # Phase 1
    final_24, k766_survivors, k773_survivors, k781_survivors, k785_survivors = phase1_load_uncached()

    # Phase 2
    fetch_results = phase2_batch_fetch(final_24)

    # Phase 3
    phase3_results = phase3_prescreen(final_24, fetch_results)

    # Phase 4
    ranked = phase4_rank_and_queue(
        phase3_results, k766_survivors, k773_survivors, k781_survivors, k785_survivors
    )

    # Phase 5: Save JSON
    json_path = phase5_save_json(final_24, fetch_results, phase3_results, ranked)

    # Phase 6: report.html badge
    badge = build_badge(ranked, fetch_results, final_24)
    phase6_update_report_html(badge)

    print(f"\n{'='*70}")
    print(f"  K793 COMPLETE")
    print(f"  Runtime: {time.time() - START_TIME:.1f}s")
    print(f"  Fetched: {sum(1 for v in fetch_results.values() if v)}/{len(fetch_results)}")
    print(f"  Pre-screen pass: {len(ranked['survivors'])}")
    print(f"  K794+ queue: {[e['token'] for e in ranked['k794_queue']]}")
    print(f"  Combined pool: {len(ranked['combined_ranked'])} tokens")
    print(f"  Long-tail exhausted: {ranked['saturation']['long_tail_exhausted']}")
    print(f"  Saturation rec: {ranked['saturation']['recommendation']}")
    print(f"  JSON: {json_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

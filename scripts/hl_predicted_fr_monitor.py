"""
HL predictedFundings Live Monitor — K304 Scaffold
==================================================
Purpose:
    Poll https://api.hyperliquid.xyz/info (type=predictedFundings) every 5 min.
    Save per-snapshot parquet to cache/hl_predicted_fr_YYYYMMDDHHMM.parquet.
    Purge snapshots older than 24h (rolling cache).
    Emit dashboard JSON at data/hl_predicted_fr_dashboard.json.

Alert logic:
    K208 universe (SOL/XRP/SUI etc):  extreme |pred_bybit_fr - pred_hl_fr| deviation.
    K265/K276b universe (HL alts):    predicted FR ranking change vs prior 24h.
    K297 RWA (XAG/XAU/SPX etc):      FR sign tracking (positive = short carry live).

Rate limit note:
    288 calls/day at 5-min polling = light load.
    Single POST per call, ~3-10 KB response.
    HL API: no documented rate limit for public info endpoints; 1 req/5s nominal.

Usage:
    python3 scripts/hl_predicted_fr_monitor.py            # single-shot (default)
    python3 scripts/hl_predicted_fr_monitor.py --loop     # continuous loop (60s overlap)
    python3 scripts/hl_predicted_fr_monitor.py --dry-run  # fetch + print, skip writes
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"
DATA  = BASE / "data"
LOGS  = BASE / "logs"

CACHE_GLOB      = "hl_predicted_fr_*.parquet"
DASHBOARD_JSON  = DATA / "hl_predicted_fr_dashboard.json"
LOG_FILE        = LOGS / "hl_predicted_fr_monitor.log"

CACHE_HOURS     = 24          # rolling window to keep
POLL_INTERVAL_S = 300         # 5 minutes (used in --loop mode)

# ---------------------------------------------------------------------------
# Universe definitions (from K208 / K265 / K276b / K297 analyses)
# ---------------------------------------------------------------------------

# K208 reverse-carry panel (DAR(2,1) whipsaw filter on Bybit-HL spread)
K208_COINS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# K265 full longtail FR carry (35 symbols)
K265_COINS = [
    "AAVE", "ARB", "ATOM", "AVAX", "BNB", "BONK", "BTC", "CRV", "DOGE", "DOT",
    "ETH", "FET", "INJ", "LDO", "MKR", "NEAR", "PEPE", "RNDR", "SHIB", "SUSHI",
    "TAO", "UNI", "WIF", "TIA", "JUP", "BOME", "ENA", "STRK", "PYTH", "MEME",
    "WLD", "SEI", "ONDO", "ARK", "BLUR",
]

# K276b top-20 trimmed variant (highest Sharpe contributors from K265)
K276B_COINS = [
    "ENA", "ONDO", "ATOM", "TIA", "SEI", "WLD", "RNDR", "TAO", "MEME", "AAVE",
    "PYTH", "LDO", "FET", "PEPE", "MKR", "JUP", "UNI", "BOME", "DOT", "BONK",
]

# K297 RWA (HIP-3 real-world asset perps on HL) — FR sign tracking
K297_RWA_COINS = ["XAG", "XAU", "SPX", "PAXG", "NQ"]

# Alert thresholds
K208_ALERT_BPS   = 2.0    # |pred_bybit - pred_hl| above this triggers alert
K265_RANK_DELTA  = 3      # rank shift in top-quartile position triggers alert
K297_SIGN_CHANGE = True   # always track sign changes

# ---------------------------------------------------------------------------
# HL API helpers
# ---------------------------------------------------------------------------
HL_API = "https://api.hyperliquid.xyz/info"


def hl_post(payload: dict, retries: int = 3, delay: float = 6.0) -> Any:
    """POST to HL info API with retry and exponential back-off."""
    for attempt in range(retries):
        try:
            body = json.dumps(payload).encode()
            req  = urllib.request.Request(
                HL_API, data=body,
                headers={"Content-Type": "application/json", "User-Agent": "ct-monitor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            if attempt < retries - 1:
                wait = delay * (2 ** attempt)
                log(f"  [WARN] hl_post attempt {attempt+1} failed: {exc} — retry in {wait:.0f}s")
                time.sleep(wait)
            else:
                raise


def fetch_predicted_fundings() -> Tuple[Dict[str, Dict], int]:
    """
    Fetch predictedFundings from HL.
    Returns (parsed_dict, fetch_timestamp_ms).

    Parsed dict structure:
        {
          "BTC": {
            "HlPerp":    {"fundingRate": 0.000125, "nextFundingTime": 1234567890000},
            "BinPerp":   {"fundingRate": 0.000100, "nextFundingTime": ...},
            "BybitPerp": {"fundingRate": 0.000130, "nextFundingTime": ...},
          },
          ...
        }
    Missing venues are None.
    """
    ts  = int(time.time() * 1000)
    raw = hl_post({"type": "predictedFundings"})
    parsed: Dict[str, Dict] = {}
    for item in raw:
        coin   = item[0]
        venues = {}
        for ve in item[1]:
            vname = ve[0]
            vdata = ve[1]
            if vdata is not None:
                venues[vname] = {
                    "fundingRate":     float(vdata.get("fundingRate", 0.0)),
                    "nextFundingTime": vdata.get("nextFundingTime"),
                }
            else:
                venues[vname] = None
        parsed[coin] = venues
    return parsed, ts


# ---------------------------------------------------------------------------
# Parquet snapshot
# ---------------------------------------------------------------------------

def snapshot_to_rows(parsed: Dict[str, Dict], ts_ms: int) -> List[Dict]:
    """Flatten parsed predictedFundings dict into tabular rows."""
    rows = []
    for coin, venues in parsed.items():
        hl    = venues.get("HlPerp")    or {}
        binp  = venues.get("BinPerp")   or {}
        bybit = venues.get("BybitPerp") or {}
        rows.append({
            "ts_ms":              ts_ms,
            "coin":               coin,
            "hl_fr":              hl.get("fundingRate"),
            "hl_next_settle_ms":  hl.get("nextFundingTime"),
            "bin_fr":             binp.get("fundingRate"),
            "bin_next_settle_ms": binp.get("nextFundingTime"),
            "bybit_fr":           bybit.get("fundingRate"),
            "bybit_next_settle_ms": bybit.get("nextFundingTime"),
        })
    return rows


def save_snapshot(rows: List[Dict], ts_ms: int, dry_run: bool = False) -> Optional[Path]:
    """Save rows to parquet. Returns path or None if dry_run."""
    dt  = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    fn  = f"hl_predicted_fr_{dt.strftime('%Y%m%d%H%M')}.parquet"
    out = CACHE / fn
    if dry_run:
        log(f"  [DRY-RUN] Would write {len(rows)} rows → {out}")
        return None
    df = pd.DataFrame(rows)
    df["ts_ms"] = df["ts_ms"].astype("int64")
    df.to_parquet(out, index=False, compression="snappy")
    log(f"  Snapshot saved: {out} ({len(rows)} coins, {os.path.getsize(out)//1024}KB)")
    return out


def purge_old_snapshots(dry_run: bool = False) -> int:
    """Remove parquet snapshots older than CACHE_HOURS. Returns count purged."""
    cutoff_ms = (time.time() - CACHE_HOURS * 3600) * 1000
    pattern   = str(CACHE / CACHE_GLOB)
    purged    = 0
    for fp in glob.glob(pattern):
        p  = Path(fp)
        # Extract timestamp from filename: hl_predicted_fr_YYYYMMDDHHMM.parquet
        stem = p.stem  # e.g. "hl_predicted_fr_202605251330"
        try:
            ts_part = stem.split("_")[-1]          # "202605251330"
            dt_file = datetime.strptime(ts_part, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            ts_file = dt_file.timestamp() * 1000
        except Exception:
            continue
        if ts_file < cutoff_ms:
            if dry_run:
                log(f"  [DRY-RUN] Would purge {p.name}")
            else:
                p.unlink()
                log(f"  Purged old snapshot: {p.name}")
            purged += 1
    return purged


# ---------------------------------------------------------------------------
# Alert logic
# ---------------------------------------------------------------------------

def compute_k208_alerts(parsed: Dict[str, Dict]) -> List[Dict]:
    """
    K208: alert when |pred_bybit_fr - pred_hl_fr| > threshold for any K208 coin.
    Strategy monitors spread sign for reverse carry entry decisions.
    """
    alerts = []
    for coin in K208_COINS:
        v     = parsed.get(coin, {})
        hl    = v.get("HlPerp")
        bybit = v.get("BybitPerp")
        if not hl or not bybit:
            continue
        hl_fr    = hl["fundingRate"]
        bybit_fr = bybit["fundingRate"]
        spread   = bybit_fr - hl_fr
        spread_bps = spread * 1e4
        alert_level = (
            "EXTREME" if abs(spread_bps) > K208_ALERT_BPS * 3 else
            "HIGH"    if abs(spread_bps) > K208_ALERT_BPS * 1.5 else
            "NORMAL"  if abs(spread_bps) > K208_ALERT_BPS else
            None
        )
        alerts.append({
            "coin":        coin,
            "hl_fr_bps":    round(hl_fr * 1e4, 5),
            "bybit_fr_bps": round(bybit_fr * 1e4, 5),
            "spread_bps":   round(spread_bps, 5),
            "spread_sign":  "positive" if spread > 0 else "negative",
            "k208_signal":  "LONG_SPREAD" if spread > 0 else "NO_ENTRY",
            "alert":        alert_level,
        })
    return alerts


def compute_k265_k276b_alerts(parsed: Dict[str, Dict],
                               prior_ranks: Optional[Dict[str, int]] = None) -> Tuple[List[Dict], Dict[str, int]]:
    """
    K265/K276b: rank HL predicted FR cross-sectionally.
    Alert if rank shifts > K265_RANK_DELTA for any symbol in K276b universe.
    Returns (alert_list, current_ranks_dict).
    """
    # Build rank table for K265 universe (all 35)
    entries = []
    for coin in K265_COINS:
        v  = parsed.get(coin, {})
        hl = v.get("HlPerp")
        if hl:
            entries.append((coin, hl["fundingRate"]))

    # Sort descending by FR (highest = most expensive to be long)
    entries.sort(key=lambda x: x[1], reverse=True)
    current_ranks = {coin: i + 1 for i, (coin, _) in enumerate(entries)}

    alerts = []
    if prior_ranks:
        for coin in K276B_COINS:
            cur  = current_ranks.get(coin)
            prev = prior_ranks.get(coin)
            if cur is None or prev is None:
                continue
            delta = abs(cur - prev)
            if delta >= K265_RANK_DELTA:
                v  = parsed.get(coin, {})
                hl = v.get("HlPerp") or {}
                alerts.append({
                    "coin":       coin,
                    "prev_rank":  prev,
                    "cur_rank":   cur,
                    "rank_delta": delta,
                    "hl_fr_bps":  round(hl.get("fundingRate", 0) * 1e4, 5),
                    "alert":      "RANK_SHIFT",
                })

    return alerts, current_ranks


def compute_k297_rwa_tracking(parsed: Dict[str, Dict]) -> List[Dict]:
    """
    K297 RWA: track FR sign for real-world asset perps.
    Positive HL FR = long-side pays = short carry opportunity.
    """
    tracking = []
    for coin in K297_RWA_COINS:
        v  = parsed.get(coin, {})
        hl = v.get("HlPerp")
        if hl is None:
            tracking.append({
                "coin":     coin,
                "status":   "NOT_LISTED",
                "hl_fr_bps": None,
                "sign":     None,
            })
            continue
        fr   = hl["fundingRate"]
        sign = "positive" if fr > 0 else ("negative" if fr < 0 else "zero")
        tracking.append({
            "coin":         coin,
            "hl_fr_bps":    round(fr * 1e4, 5),
            "sign":         sign,
            "carry_signal": "SHORT_CARRY_LIVE" if fr > 0 else ("FLAT_OR_REVERSE" if fr < 0 else "ZERO"),
            "next_settle_ms": hl.get("nextFundingTime"),
        })
    return tracking


# ---------------------------------------------------------------------------
# Dashboard JSON
# ---------------------------------------------------------------------------

def build_dashboard(
    parsed:     Dict[str, Dict],
    ts_ms:      int,
    k208_alerts:   List[Dict],
    k265_alerts:   List[Dict],
    k265_ranks:    Dict[str, int],
    k297_tracking: List[Dict],
    all_alerts_firing: List[str],
) -> Dict:
    """Build the dashboard JSON payload."""

    now_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()

    # Top 10 highest predicted HL FR (long carry opportunity — receive if short)
    hl_frs = []
    for coin, venues in parsed.items():
        hl = venues.get("HlPerp")
        if hl and hl.get("fundingRate") is not None:
            hl_frs.append((coin, hl["fundingRate"]))
    hl_frs.sort(key=lambda x: x[1], reverse=True)

    top10_highest = [
        {"rank": i + 1, "coin": c, "hl_fr_bps": round(fr * 1e4, 5)}
        for i, (c, fr) in enumerate(hl_frs[:10])
    ]
    top10_lowest = [
        {"rank": i + 1, "coin": c, "hl_fr_bps": round(fr * 1e4, 5)}
        for i, (c, fr) in enumerate(reversed(hl_frs[-10:]))
    ]

    # K208 spread snapshot
    k208_spreads = {
        a["coin"]: {
            "hl_fr_bps":    a["hl_fr_bps"],
            "bybit_fr_bps": a["bybit_fr_bps"],
            "spread_bps":   a["spread_bps"],
            "signal":       a["k208_signal"],
        }
        for a in k208_alerts
    }

    # K265/K276b rank snapshot (top 20 + bottom 5 by FR)
    k265_rank_snapshot = [
        {
            "coin": coin,
            "rank": rank,
            "hl_fr_bps": round(
                (parsed.get(coin, {}).get("HlPerp") or {}).get("fundingRate", 0) * 1e4, 5
            ),
        }
        for coin, rank in sorted(k265_ranks.items(), key=lambda x: x[1])
        if coin in K265_COINS
    ]

    # Next settlement awareness
    hl_next_times = set()
    for venues in parsed.values():
        hl = venues.get("HlPerp")
        if hl and hl.get("nextFundingTime"):
            hl_next_times.add(hl["nextFundingTime"])
    next_settle_ms  = min(hl_next_times) if hl_next_times else None
    mins_to_settle  = round((next_settle_ms - ts_ms) / 60000, 1) if next_settle_ms else None

    return {
        "generated_at_utc":         now_utc,
        "snapshot_ts_ms":           ts_ms,
        "total_coins":              len(parsed),
        "mins_to_next_hl_settle":   mins_to_settle,
        "alerts_firing":            all_alerts_firing,
        "top10_highest_hl_fr":      top10_highest,
        "top10_lowest_hl_fr":       top10_lowest,
        "k208_spread_snapshot":     k208_spreads,
        "k208_extreme_alerts":      [a for a in k208_alerts if a.get("alert") in ("EXTREME", "HIGH")],
        "k265_k276b_rank_snapshot": k265_rank_snapshot,
        "k265_k276b_rank_alerts":   k265_alerts,
        "k297_rwa_tracking":        k297_tracking,
        "config": {
            "k208_alert_threshold_bps":  K208_ALERT_BPS,
            "k265_rank_alert_delta":     K265_RANK_DELTA,
            "k208_coins":                K208_COINS,
            "k265_coins":                K265_COINS,
            "k276b_coins":               K276B_COINS,
            "k297_rwa_coins":            K297_RWA_COINS,
            "cache_hours":               CACHE_HOURS,
            "poll_interval_s":           POLL_INTERVAL_S,
        },
    }


# ---------------------------------------------------------------------------
# Load prior ranks from most-recent cached snapshot
# ---------------------------------------------------------------------------

def load_prior_ranks() -> Optional[Dict[str, int]]:
    """
    Load HL FR ranks from the most recent parquet snapshot (prior to current).
    Returns dict {coin: rank} or None if no prior snapshot found.
    """
    pattern = str(CACHE / CACHE_GLOB)
    files   = sorted(glob.glob(pattern))
    if len(files) < 2:
        # Need at least 2 snapshots to compute rank delta; skip on first run
        return None
    target = files[-2]   # second-to-last = prior snapshot (last = just-written current)

    try:
        df = pd.read_parquet(target, columns=["coin", "hl_fr"])
        df = df.dropna(subset=["hl_fr"])
        # Filter to K265 universe only — must match compute_k265_k276b_alerts ranking scope
        df = df[df["coin"].isin(K265_COINS)]
        df = df.sort_values("hl_fr", ascending=False).reset_index(drop=True)
        return {row["coin"]: i + 1 for i, row in df.iterrows()}
    except Exception as exc:
        log(f"  [WARN] Could not load prior ranks from {target}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Write timestamped log message to stdout and log file."""
    ts  = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = f"[{ts}] {msg}"
    print(out, flush=True)
    try:
        with open(LOG_FILE, "a") as fh:
            fh.write(out + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main single-shot run
# ---------------------------------------------------------------------------

def run_once(dry_run: bool = False) -> Dict:
    """
    Execute one polling cycle:
      1. Fetch predictedFundings
      2. Save parquet snapshot
      3. Purge old snapshots
      4. Compute alerts
      5. Write dashboard JSON
    Returns dashboard dict.
    """
    log("=" * 60)
    log("HL predictedFundings Monitor — poll cycle start")

    # 1. Fetch
    log("[1] Fetching predictedFundings...")
    parsed, ts_ms = fetch_predicted_fundings()
    dt_str = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    log(f"    OK: {len(parsed)} coins at {dt_str}")

    # 2. Save snapshot
    log("[2] Saving parquet snapshot...")
    rows = snapshot_to_rows(parsed, ts_ms)
    save_snapshot(rows, ts_ms, dry_run=dry_run)

    # 3. Purge old
    log("[3] Purging old snapshots (>24h)...")
    n_purged = purge_old_snapshots(dry_run=dry_run)
    log(f"    Purged {n_purged} old file(s)")

    # 4. Alerts
    log("[4] Computing alerts...")

    # K208
    k208_alerts = compute_k208_alerts(parsed)
    k208_extreme = [a for a in k208_alerts if a.get("alert") in ("EXTREME", "HIGH")]
    log(f"    K208: {len(k208_alerts)} coins, {len(k208_extreme)} extreme/high spread alerts")
    for a in k208_alerts:
        flag = f" *** {a['alert']}" if a.get("alert") else ""
        log(f"      {a['coin']:<6} spread={a['spread_bps']:+.4f}bps  {a['k208_signal']}{flag}")

    # K265/K276b
    prior_ranks           = load_prior_ranks()
    k265_alerts, k265_cur_ranks = compute_k265_k276b_alerts(parsed, prior_ranks)
    log(f"    K265/K276b: {len(k265_cur_ranks)} coins ranked, {len(k265_alerts)} rank shift alerts")
    for a in k265_alerts:
        log(f"      {a['coin']:<8} rank {a['prev_rank']} → {a['cur_rank']} (Δ{a['rank_delta']}) *** RANK_SHIFT")

    # K297 RWA
    k297_tracking = compute_k297_rwa_tracking(parsed)
    log(f"    K297 RWA: {len(k297_tracking)} tracked")
    for t in k297_tracking:
        if t["status"] == "NOT_LISTED" if "status" in t else False:
            log(f"      {t['coin']:<6} NOT_LISTED on HL")
        else:
            log(f"      {t['coin']:<6} FR={t.get('hl_fr_bps', 'N/A'):+.4f}bps  {t.get('carry_signal','?')}")

    # Build unified alert list
    all_alerts: List[str] = []
    for a in k208_extreme:
        all_alerts.append(f"K208_SPREAD_ALERT:{a['coin']}:{a['alert']}:{a['spread_bps']:+.4f}bps")
    for a in k265_alerts:
        all_alerts.append(f"K265_RANK_SHIFT:{a['coin']}:{a['prev_rank']}→{a['cur_rank']}")
    for t in k297_tracking:
        if t.get("carry_signal") == "SHORT_CARRY_LIVE":
            all_alerts.append(f"K297_RWA_CARRY:{t['coin']}:{t['hl_fr_bps']:+.4f}bps")

    # 5. Dashboard
    log("[5] Writing dashboard JSON...")
    dashboard = build_dashboard(
        parsed, ts_ms,
        k208_alerts, k265_alerts, k265_cur_ranks,
        k297_tracking, all_alerts
    )
    if not dry_run:
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_JSON, "w") as fh:
            json.dump(dashboard, fh, indent=2)
        log(f"    Dashboard written: {DASHBOARD_JSON}")
    else:
        log(f"    [DRY-RUN] Would write dashboard to {DASHBOARD_JSON}")

    log("Poll cycle complete.")
    log("=" * 60)
    return dashboard


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HL predictedFundings live monitor (K304 scaffold)"
    )
    parser.add_argument(
        "--loop",     action="store_true",
        help="Run continuously every POLL_INTERVAL_S seconds (use launchctl instead)"
    )
    parser.add_argument(
        "--dry-run",  action="store_true",
        help="Fetch and compute alerts but do not write any files"
    )
    args = parser.parse_args()

    # Ensure directories exist
    CACHE.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    if args.loop:
        log(f"Starting continuous loop (interval={POLL_INTERVAL_S}s). Ctrl-C to stop.")
        while True:
            try:
                run_once(dry_run=args.dry_run)
            except KeyboardInterrupt:
                log("Interrupted by user. Exiting.")
                break
            except Exception as exc:
                log(f"[ERROR] Poll cycle failed: {exc}")
            log(f"Sleeping {POLL_INTERVAL_S}s until next poll...")
            time.sleep(POLL_INTERVAL_S)
    else:
        run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

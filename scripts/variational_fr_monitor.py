"""
Variational RWA Funding Rate Monitor — K363/K365 Scaffold
==========================================================
Purpose:
    Poll https://api.variational.io/metadata/stats every 4 hours (via launchd).
    Single-shot execution model. Accumulates FR data for RWA instruments until
    Variational trading API goes live (Q3-Q4 2026 target → K366 production integration).

    Each call:
      1. GET https://api.variational.io/metadata/stats — public read API, no auth, 10 req/10s per IP
      2. Parse JSON response: list of instruments with FR, OI, mark price, spread
      3. Filter RWA instruments (XAUT, XAU, PAXG, CL, XAG, COPPER, plus any newly listed)
      4. Save snapshot to cache/variational_fr_snapshots/var_<YYYYMMDD_HHMM>.parquet
      5. Update data/variational_fr_dashboard.json with current state (for HTML widget)

On error: write to logs/variational_fr_monitor.err, exit 0 (don't break launchd schedule)
Stdout: brief summary (timestamp, # instruments, RWA highlights)

K363 context: SCAFFOLD phase. Accumulate FR data for RWA instruments.
K365 confirmed: public read API live, trading API not yet available (Q3-Q4 2026).
K365 baseline snapshot (2026-05-27):
  XAUT: OI $26.6M, FR -71.1% ann
  XAU:  OI $21.9M, FR +560% ann (likely spike)
  PAXG: OI $15.0M, FR +239.8% ann
  CL:   OI $4.9M,  FR -247% ann (inverted)
  XAG:  OI $4.1M,  FR 0% (no signal)
  COPPER: OI $1.6M, FR 0%

Trigger conditions (documented per K363):
  A: Variational announces trading API → K366 wave (integration scaffold)
  B: XAG/Silver FR sustained >5% ann for 7 days → K297'' satellite candidate evaluation
  C: HL CFTC enforcement → consider K297' partial migration (Scenario B)
  D: Any RWA listing OI > $50M → check competitive significance

Settlement cadence: 4h (vs HL 1h/8h)

Security (K339):
    REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals in paths
"""
from __future__ import annotations

import json
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Paths — K339 security: relative to REPO_ROOT, no hardcoded /Users/ literals
# ---------------------------------------------------------------------------
REPO_ROOT      = Path(__file__).resolve().parent.parent
CACHE_DIR      = REPO_ROOT / "cache" / "variational_fr_snapshots"
DATA_DIR       = REPO_ROOT / "data"
LOGS_DIR       = REPO_ROOT / "logs"
ERR_FILE       = LOGS_DIR / "variational_fr_monitor.err"
DASHBOARD_FILE = DATA_DIR / "variational_fr_dashboard.json"

JST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# Variational API
# ---------------------------------------------------------------------------
VAR_API_URL = "https://api.variational.io/metadata/stats"

# RWA instrument filter — core set + detect newly listed via keyword scan
RWA_SYMBOLS = {"XAUT", "XAU", "PAXG", "CL", "XAG", "COPPER"}

# Keywords for auto-detecting newly listed RWA instruments (case-insensitive)
RWA_KEYWORDS = {"gold", "silver", "crude", "oil", "copper", "platinum", "pax", "tether", "xau", "xag"}

# K365 baseline snapshot (2026-05-27) for delta comparison
K365_BASELINE: Dict[str, Dict] = {
    "XAUT":   {"fr_ann_pct": -71.1,  "oi_usd": 26_600_000, "date": "2026-05-27"},
    "XAU":    {"fr_ann_pct": 560.0,  "oi_usd": 21_900_000, "date": "2026-05-27"},
    "PAXG":   {"fr_ann_pct": 239.8,  "oi_usd": 15_000_000, "date": "2026-05-27"},
    "CL":     {"fr_ann_pct": -247.0, "oi_usd":  4_900_000, "date": "2026-05-27"},
    "XAG":    {"fr_ann_pct": 0.0,    "oi_usd":  4_100_000, "date": "2026-05-27"},
    "COPPER": {"fr_ann_pct": 0.0,    "oi_usd":  1_600_000, "date": "2026-05-27"},
}


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def fetch_variational_stats(retries: int = 3, delay: float = 5.0) -> Any:
    """GET Variational /metadata/stats with retry and exponential back-off."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                VAR_API_URL,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ct-variational-fr-monitor/1.0",
                }
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            if attempt < retries - 1:
                wait = delay * (2 ** attempt)
                print(f"  [WARN] fetch attempt {attempt+1} failed: {exc} — retry in {wait:.0f}s",
                      flush=True)
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Parse + filter
# ---------------------------------------------------------------------------

def parse_instrument(raw: Dict) -> Optional[Dict]:
    """
    Parse a single instrument entry from Variational /metadata/stats response.
    Handles both nested and flat response shapes defensively.

    Expected fields (best-effort, may vary with API evolution):
      symbol / ticker / name
      funding_rate / fundingRate / fr / funding_rate_annualized
      open_interest / openInterest / oi
      mark_price / markPrice
      spread / bid_ask_spread
    Returns None if symbol cannot be determined.
    """
    # Symbol extraction — try common key variants
    symbol = (
        raw.get("symbol") or raw.get("ticker") or raw.get("name") or
        raw.get("coin") or raw.get("asset") or ""
    ).upper().strip()

    if not symbol:
        return None

    # Funding rate (annualized %) — try several key names
    fr_raw = (
        raw.get("funding_rate_annualized") or
        raw.get("fundingRateAnnualized") or
        raw.get("fr_ann") or
        raw.get("fr_annualized") or
        None
    )
    if fr_raw is None:
        # Try non-annualized (4h settlement = 6 periods/day = 2190/year)
        fr_period = (
            raw.get("funding_rate") or
            raw.get("fundingRate") or
            raw.get("fr") or
            None
        )
        if fr_period is not None:
            try:
                fr_raw = float(fr_period) * 2190 * 100  # convert to ann %
            except (TypeError, ValueError):
                fr_raw = None
    else:
        try:
            fr_raw = float(fr_raw) * 100  # assume decimal → %
        except (TypeError, ValueError):
            fr_raw = None

    # OI in USD
    oi_raw = (
        raw.get("open_interest_usd") or
        raw.get("openInterestUsd") or
        raw.get("oi_usd") or
        raw.get("open_interest") or
        raw.get("openInterest") or
        raw.get("oi") or
        None
    )
    try:
        oi_usd = float(oi_raw) if oi_raw is not None else None
    except (TypeError, ValueError):
        oi_usd = None

    # Mark price
    mark_raw = (
        raw.get("mark_price") or raw.get("markPrice") or
        raw.get("price") or raw.get("last_price") or None
    )
    try:
        mark_price = float(mark_raw) if mark_raw is not None else None
    except (TypeError, ValueError):
        mark_price = None

    # Spread
    spread_raw = (
        raw.get("spread") or raw.get("bid_ask_spread") or
        raw.get("bidAskSpread") or None
    )
    try:
        spread = float(spread_raw) if spread_raw is not None else None
    except (TypeError, ValueError):
        spread = None

    return {
        "symbol":      symbol,
        "fr_ann_pct":  fr_raw,
        "oi_usd":      oi_usd,
        "mark_price":  mark_price,
        "spread":      spread,
        "raw":         raw,  # preserve original for future parsing evolution
    }


def is_rwa_instrument(parsed: Dict) -> bool:
    """
    Return True if this instrument is an RWA / TradFi asset:
    - Exact match in RWA_SYMBOLS set, OR
    - Contains an RWA keyword in the symbol (auto-detect newly listed)
    """
    sym = parsed["symbol"]
    if sym in RWA_SYMBOLS:
        return True
    sym_lower = sym.lower()
    return any(kw in sym_lower for kw in RWA_KEYWORDS)


def filter_rwa(instruments: List[Dict]) -> List[Dict]:
    """Return parsed instruments that are RWA assets."""
    return [p for p in instruments if is_rwa_instrument(p)]


# ---------------------------------------------------------------------------
# Snapshot save
# ---------------------------------------------------------------------------

def build_snapshot_rows(instruments: List[Dict], ts_ms: int) -> List[Dict]:
    """Flatten parsed instrument list to tabular rows."""
    rows = []
    for inst in instruments:
        sym = inst["symbol"]
        baseline = K365_BASELINE.get(sym, {})
        fr_curr = inst.get("fr_ann_pct")
        fr_base = baseline.get("fr_ann_pct")
        fr_delta = None
        if fr_curr is not None and fr_base is not None:
            try:
                fr_delta = float(fr_curr) - float(fr_base)
            except (TypeError, ValueError):
                pass

        oi_curr = inst.get("oi_usd")
        oi_base = baseline.get("oi_usd")
        oi_delta = None
        if oi_curr is not None and oi_base is not None:
            try:
                oi_delta = float(oi_curr) - float(oi_base)
            except (TypeError, ValueError):
                pass

        rows.append({
            "ts_ms":          ts_ms,
            "symbol":         sym,
            "fr_ann_pct":     fr_curr,
            "oi_usd":         oi_curr,
            "mark_price":     inst.get("mark_price"),
            "spread":         inst.get("spread"),
            "is_rwa":         is_rwa_instrument(inst),
            "fr_delta_vs_k365": fr_delta,
            "oi_delta_vs_k365": oi_delta,
        })
    return rows


def save_snapshot(rows: List[Dict], ts_ms: int) -> Path:
    """
    Save rows to parquet at cache/variational_fr_snapshots/var_<YYYYMMDD_HHMM>.parquet.
    """
    dt  = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    fn  = f"var_{dt.strftime('%Y%m%d_%H%M')}.parquet"
    out = CACHE_DIR / fn

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)

    # Enforce stable dtypes for consistent parquet schema
    if "ts_ms" in df.columns:
        df["ts_ms"] = df["ts_ms"].astype("int64")
    for float_col in ["fr_ann_pct", "oi_usd", "mark_price", "spread",
                       "fr_delta_vs_k365", "oi_delta_vs_k365"]:
        if float_col in df.columns:
            df[float_col] = pd.to_numeric(df[float_col], errors="coerce").astype("float64")
    if "is_rwa" in df.columns:
        df["is_rwa"] = df["is_rwa"].astype(bool)

    df.to_parquet(out, index=False, compression="snappy")
    return out


# ---------------------------------------------------------------------------
# Dashboard JSON update
# ---------------------------------------------------------------------------

def update_dashboard(rwa_instruments: List[Dict], all_count: int, ts_ms: int) -> None:
    """
    Write/update data/variational_fr_dashboard.json for HTML widget consumption.
    Structure:
      {
        "updated_at_jst": "...",
        "updated_ts_ms": 1234567890000,
        "api_url": "...",
        "total_instruments": N,
        "rwa_instruments": [ { symbol, fr_ann_pct, oi_usd, mark_price, spread,
                                fr_delta_vs_k365, oi_delta_vs_k365 } ],
        "k365_baseline": { ... },
        "trigger_conditions": { ... }
      }
    """
    dt_jst = datetime.fromtimestamp(ts_ms / 1000, tz=JST).strftime("%Y-%m-%d %H:%M JST")

    rwa_out = []
    for inst in rwa_instruments:
        sym = inst["symbol"]
        baseline = K365_BASELINE.get(sym, {})
        fr_curr = inst.get("fr_ann_pct")
        fr_base = baseline.get("fr_ann_pct")
        oi_curr = inst.get("oi_usd")
        oi_base = baseline.get("oi_usd")

        fr_delta = None
        if fr_curr is not None and fr_base is not None:
            try:
                fr_delta = round(float(fr_curr) - float(fr_base), 2)
            except (TypeError, ValueError):
                pass

        oi_delta = None
        if oi_curr is not None and oi_base is not None:
            try:
                oi_delta = round(float(oi_curr) - float(oi_base), 0)
            except (TypeError, ValueError):
                pass

        rwa_out.append({
            "symbol":         sym,
            "fr_ann_pct":     round(float(fr_curr), 2) if fr_curr is not None else None,
            "oi_usd":         round(float(oi_curr), 0) if oi_curr is not None else None,
            "mark_price":     round(float(inst["mark_price"]), 4) if inst.get("mark_price") is not None else None,
            "spread":         round(float(inst["spread"]), 6) if inst.get("spread") is not None else None,
            "fr_delta_vs_k365": fr_delta,
            "oi_delta_vs_k365": oi_delta,
        })

    # Sort by OI descending
    rwa_out.sort(key=lambda x: (x["oi_usd"] or 0), reverse=True)

    payload = {
        "updated_at_jst":     dt_jst,
        "updated_ts_ms":      ts_ms,
        "api_url":            VAR_API_URL,
        "total_instruments":  all_count,
        "rwa_count":          len(rwa_out),
        "rwa_instruments":    rwa_out,
        "k365_baseline":      K365_BASELINE,
        "trigger_conditions": {
            "A": "Variational announces trading API → K366 wave (integration scaffold)",
            "B": "XAG/Silver FR sustained >5% ann for 7 days → K297'' satellite candidate evaluation",
            "C": "HL CFTC enforcement → consider K297' partial migration (Scenario B)",
            "D": "Any RWA listing OI > $50M → check competitive significance",
        },
        "trading_api_note": "Trading API public release will trigger K366 production integration (Q3-Q4 2026 expected)",
        "settlement_cadence": "4h (vs HL 1h/8h)",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Main single-shot run
# ---------------------------------------------------------------------------

def run_once() -> None:
    ts_ms  = int(time.time() * 1000)
    dt_str = datetime.fromtimestamp(ts_ms / 1000, tz=JST).strftime("%Y-%m-%dT%H:%M JST")

    print(f"[{dt_str}] Variational FR Monitor — poll cycle start", flush=True)

    # Step 1: Fetch
    print(f"  [1] GET {VAR_API_URL} ...", flush=True)
    raw_response = fetch_variational_stats()

    # Step 2: Parse — handle list or dict response
    raw_list: List[Dict] = []
    if isinstance(raw_response, list):
        raw_list = raw_response
    elif isinstance(raw_response, dict):
        # Try common wrapper keys
        for key in ("data", "instruments", "markets", "stats", "results"):
            if key in raw_response and isinstance(raw_response[key], list):
                raw_list = raw_response[key]
                break
        if not raw_list:
            # Flat dict of symbol → data
            for k, v in raw_response.items():
                if isinstance(v, dict):
                    v["symbol"] = v.get("symbol") or k
                    raw_list.append(v)
                elif isinstance(v, (int, float, str)):
                    # Skip top-level scalar values
                    pass

    print(f"      Raw response: {len(raw_list)} instrument entries", flush=True)

    parsed_all = [parse_instrument(item) for item in raw_list if isinstance(item, dict)]
    parsed_all = [p for p in parsed_all if p is not None]

    # Step 3: Filter RWA
    rwa_instruments = filter_rwa(parsed_all)
    print(f"      Total parsed: {len(parsed_all)} | RWA filtered: {len(rwa_instruments)}", flush=True)

    # Print RWA highlights
    for inst in sorted(rwa_instruments, key=lambda x: (x.get("oi_usd") or 0), reverse=True):
        sym = inst["symbol"]
        fr  = inst.get("fr_ann_pct")
        oi  = inst.get("oi_usd")
        base_fr = K365_BASELINE.get(sym, {}).get("fr_ann_pct")
        delta_str = ""
        if fr is not None and base_fr is not None:
            delta = fr - base_fr
            sign  = "+" if delta >= 0 else ""
            delta_str = f" [Δvs K365: {sign}{delta:.1f}%]"
        oi_m = f"${oi/1e6:.1f}M" if oi is not None else "OI=?"
        fr_s = f"{fr:.1f}%" if fr is not None else "FR=?"
        print(f"      {sym:8s} FR={fr_s:>10s} ann  OI={oi_m}{delta_str}", flush=True)

    # Step 4: Save parquet snapshot
    print("  [4] Saving parquet snapshot...", flush=True)
    rows = build_snapshot_rows(parsed_all, ts_ms)
    out  = save_snapshot(rows, ts_ms)
    size_kb = out.stat().st_size // 1024
    print(f"      Saved: {out.name} ({size_kb}KB, {len(rows)} rows)", flush=True)

    # Step 5: Update dashboard JSON
    print("  [5] Updating dashboard JSON...", flush=True)
    update_dashboard(rwa_instruments, len(parsed_all), ts_ms)
    print(f"      Dashboard: {DASHBOARD_FILE.name} updated", flush=True)

    # Summary line
    rwa_summary = ", ".join(
        f"{inst['symbol']}={inst.get('fr_ann_pct', '?'):.1f}%" if inst.get("fr_ann_pct") is not None
        else f"{inst['symbol']}=?"
        for inst in sorted(rwa_instruments, key=lambda x: (x.get("oi_usd") or 0), reverse=True)[:3]
    )
    print(
        f"[SUMMARY] {dt_str} | total={len(parsed_all)} | rwa={len(rwa_instruments)} "
        f"| top3_FR: {rwa_summary}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Ensure directories exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        run_once()
    except Exception:
        # On any unhandled error: write to err file and exit 0 (don't break launchd)
        err_msg  = traceback.format_exc()
        ts_str   = datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST")
        err_line = f"[{ts_str}] FATAL ERROR:\n{err_msg}\n"
        print(err_line, file=sys.stderr, flush=True)
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(ERR_FILE, "a") as fh:
                fh.write(err_line)
        except Exception:
            pass
        sys.exit(0)  # exit 0 to avoid launchd throttling


if __name__ == "__main__":
    main()

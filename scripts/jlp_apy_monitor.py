#!/usr/bin/env python3
"""K468 JLP APY trigger monitor — Jupiter Perpetuals LP yield tracking.

K467 CONDITIONAL → K468 trigger-based activation.
K467 found JLP APY currently 1.68%, break-even 21%.
Entry trigger: gross APY >= 25% (K468 detects + alerts this trigger).

Single-shot execution, weekly cron via launchd (StartInterval=604800, 7 days).
Tracks JLP APY from DefiLlama yields API, computes 7d/30d means and slope,
detects APY trigger thresholds for entry/reduce/exit decisions.

K468 requirements:
- K467 analysis: JLP currently 1.68% gross APY, break-even ~21%, IL+hedge cost ~14-17%/yr
- REPO_ROOT via K339 pattern (no /Users/ literals in paths)
- DefiLlama free API: https://api.llama.fi/yields (filtered for Jupiter Perpetuals)
- Stdlib only (no new packages)
- Cache files: cache/jlp_apy_alerts.jsonl
- Dashboard: data/jlp_apy_dashboard.json
- Logs: logs/jlp_apy_monitor.log/.err
- Error handling: catch all -> exit 0 (no crash notifications)
- Optional: ntfy.sh integration for critical alerts

Trigger thresholds (K468 design):
  TRIGGER_ENTRY (>= 25% gross APY): "JLP entry threshold reached"
  TRIGGER_REDUCE (< 15% gross APY after entry): "JLP unprofitable, exit half"
  TRIGGER_EXIT (< 10% sustained 14d): "JLP exit — below minimum viable"

JLP pool identifiers (DefiLlama):
  - Jupiter Perpetuals JLP: search for "JLP" on Solana in /yields
  - Pool ID may vary; we search by project=jupiter and chain=Solana
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR  = REPO_ROOT / "cache"
DATA_DIR   = REPO_ROOT / "data"
LOGS_DIR   = REPO_ROOT / "logs"

ALERTS_JSONL   = CACHE_DIR / "jlp_apy_alerts.jsonl"
DASHBOARD_JSON = DATA_DIR  / "jlp_apy_dashboard.json"
LOG_FILE       = LOGS_DIR  / "jlp_apy_monitor.log"
ERR_FILE       = LOGS_DIR  / "jlp_apy_monitor.err"

JST = timezone(timedelta(hours=9))

# ── K467 analysis constants ──────────────────────────────────────────────────
BREAK_EVEN_APY       = 21.0   # % gross APY (IL + hedge cost + basis risk ~14-17%/yr -> ~21% break-even)
ENTRY_TRIGGER_APY    = 25.0   # % >= 25% gross APY -> TRIGGER_ENTRY
REDUCE_TRIGGER_APY   = 15.0   # % < 15% gross APY -> TRIGGER_REDUCE (exit half)
EXIT_TRIGGER_APY     = 10.0   # % < 10% sustained 14d -> TRIGGER_EXIT
SUSTAINED_EXIT_DAYS  = 14     # days below EXIT_TRIGGER required for EXIT signal
K467_CURRENT_APY     = 1.68   # % as of K467 analysis (2026-05-25)

# ── Optional ntfy.sh notification ────────────────────────────────────────────
NTFY_TOPIC = "cryptolab-jlp-apy"   # set to None to disable

# ── DefiLlama yields API ──────────────────────────────────────────────────────
DEFILLAMA_YIELDS_URL = "https://api.llama.fi/yields"


# ─────────────────────────────────────────────────────────────────────────────
# Logging helpers
# ─────────────────────────────────────────────────────────────────────────────

def log_msg(msg: str) -> None:
    """Write to log file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
            f.write(f"[{ts}] {msg}\n")
    except Exception as e:
        print(f"[log_msg error] {e}", file=sys.stderr)


def log_err(msg: str) -> None:
    """Write to stderr log file."""
    try:
        ERR_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ERR_FILE, "a") as f:
            ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
            f.write(f"[{ts}] {msg}\n")
    except Exception as e:
        print(f"[log_err error] {e}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# DefiLlama fetch
# ─────────────────────────────────────────────────────────────────────────────

def fetch_jlp_pool_id() -> Optional[str]:
    """Find Jupiter Perpetuals JLP pool ID from DefiLlama /yields.

    Returns pool ID string or None if not found.
    """
    try:
        with urllib.request.urlopen(DEFILLAMA_YIELDS_URL, timeout=20) as resp:
            if resp.status != 200:
                log_err(f"fetch_jlp_pool_id: HTTP {resp.status}")
                return None
            data = json.loads(resp.read().decode("utf-8"))
            pools = data.get("data", [])
            # Search for Jupiter JLP pool on Solana
            candidates = []
            for pool in pools:
                project = (pool.get("project") or "").lower()
                symbol  = (pool.get("symbol")  or "").upper()
                chain   = (pool.get("chain")   or "").lower()
                if "jupiter" in project and "solana" in chain:
                    candidates.append(pool)
            if candidates:
                # Prefer JLP symbol
                for p in candidates:
                    sym = (p.get("symbol") or "").upper()
                    if "JLP" in sym:
                        log_msg(f"JLP pool found: {p.get('pool')} symbol={p.get('symbol')} apy={p.get('apy')}")
                        return p.get("pool")
                # fallback: return first Jupiter/Solana pool
                return candidates[0].get("pool")
            log_err("fetch_jlp_pool_id: No Jupiter Perpetuals JLP pool found in DefiLlama yields")
            return None
    except urllib.error.URLError as e:
        log_err(f"fetch_jlp_pool_id: URLError {e}")
        return None
    except Exception as e:
        log_err(f"fetch_jlp_pool_id: {type(e).__name__} {e}")
        return None


def fetch_jlp_apy_current() -> Optional[float]:
    """Fetch current JLP APY directly from DefiLlama /yields pool list.

    Returns current gross APY (%) or None on error.
    Also returns pool metadata for logging.
    """
    try:
        with urllib.request.urlopen(DEFILLAMA_YIELDS_URL, timeout=20) as resp:
            if resp.status != 200:
                log_err(f"fetch_jlp_apy_current: HTTP {resp.status}")
                return None
            data = json.loads(resp.read().decode("utf-8"))
            pools = data.get("data", [])
            # Search candidates
            jlp_pools = []
            for pool in pools:
                project = (pool.get("project") or "").lower()
                symbol  = (pool.get("symbol")  or "").upper()
                chain   = (pool.get("chain")   or "").lower()
                if "jupiter" in project and "solana" in chain:
                    jlp_pools.append(pool)

            if jlp_pools:
                # Prefer JLP symbol match
                for p in jlp_pools:
                    sym = (p.get("symbol") or "").upper()
                    if "JLP" in sym:
                        apy = p.get("apy")
                        if apy is not None:
                            return float(apy)
                # fallback: first candidate
                apy = jlp_pools[0].get("apy")
                if apy is not None:
                    return float(apy)

            log_err("fetch_jlp_apy_current: JLP pool not found")
            return None
    except Exception as e:
        log_err(f"fetch_jlp_apy_current: {type(e).__name__} {e}")
        return None


def fetch_jlp_apy_history(pool_id: str) -> Optional[list[dict]]:
    """Fetch JLP APY historical chart from DefiLlama /chart/{pool_id}.

    Returns list of {timestamp, apy} dicts or None on error.
    """
    url = f"https://yields.llama.fi/chart/{pool_id}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            if resp.status != 200:
                log_err(f"fetch_jlp_apy_history: HTTP {resp.status}")
                return None
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except Exception as e:
        log_err(f"fetch_jlp_apy_history: {type(e).__name__} {e}")
        return None


def load_dashboard_fallback() -> Optional[float]:
    """Load last known APY from dashboard JSON as fallback."""
    try:
        if DASHBOARD_JSON.exists():
            with open(DASHBOARD_JSON) as f:
                dash = json.load(f)
                return dash.get("current_apy")
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────────────────────────────────────

def extract_apy_series(raw_data: list[dict]) -> list[tuple[int, float]]:
    """Extract [(unix_sec, apy_pct), ...] sorted ascending.

    DefiLlama chart format: timestamp is ISO string or unix seconds, apy is float.
    """
    result = []
    for point in raw_data:
        if not isinstance(point, dict):
            continue
        ts_raw = point.get("timestamp")
        apy    = point.get("apy")
        if ts_raw is None or apy is None:
            continue
        try:
            if isinstance(ts_raw, str):
                dt_obj = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_sec = int(dt_obj.timestamp())
            else:
                ts_sec = int(ts_raw)
            result.append((ts_sec, float(apy)))
        except (ValueError, TypeError):
            continue
    result.sort(key=lambda x: x[0])
    return result


def compute_metrics(apy_series: list[tuple[int, float]], current_apy: Optional[float]) -> dict:
    """Compute 7d/30d mean, slope, and trend from historical APY series.

    Uses simple linear regression for slope (no numpy required).
    Returns:
        current_apy, apy_7d_mean, apy_30d_mean, apy_30d_slope, point_count
    """
    now_sec = datetime.now(JST).timestamp()
    day_sec = 86400.0

    # Filter windows
    apy_7d  = [(ts, apy) for ts, apy in apy_series if (now_sec - ts) / day_sec <= 7]
    apy_30d = [(ts, apy) for ts, apy in apy_series if (now_sec - ts) / day_sec <= 30]
    apy_14d = [(ts, apy) for ts, apy in apy_series if (now_sec - ts) / day_sec <= 14]

    def mean(vals):
        apys = [a for _, a in vals]
        return sum(apys) / len(apys) if apys else None

    def linear_slope(vals):
        """Slope in %/day via least-squares (pure stdlib)."""
        if len(vals) < 2:
            return None
        n = len(vals)
        t0 = vals[0][0]
        xs = [(ts - t0) / day_sec for ts, _ in vals]
        ys = [a for _, a in vals]
        sx  = sum(xs)
        sy  = sum(ys)
        sxy = sum(x * y for x, y in zip(xs, ys))
        sxx = sum(x * x for x in xs)
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-12:
            return None
        return (n * sxy - sx * sy) / denom

    mean_7d  = mean(apy_7d)
    mean_30d = mean(apy_30d)
    mean_14d = mean(apy_14d)
    slope_30d = linear_slope(apy_30d)

    # Use historical 7d mean as current_apy fallback if direct fetch failed
    effective_current = current_apy if current_apy is not None else (
        apy_series[-1][1] if apy_series else None
    )

    return {
        "current_apy":    effective_current,
        "apy_7d_mean":    mean_7d,
        "apy_30d_mean":   mean_30d,
        "apy_14d_mean":   mean_14d,
        "apy_30d_slope":  slope_30d,   # %/day; positive = trending up
        "point_count":    len(apy_series),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Alert detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_triggers(metrics: dict) -> dict:
    """Detect JLP APY entry/reduce/exit triggers.

    Returns:
        alert_status: BELOW_BREAK_EVEN | ENTRY_READY | ACTIVE | REDUCE_WARNING | EXIT
        recommended_action: human-readable string
        estimated_net_apy_if_entered: current - break_even
        vector_to_break_even: pp required to reach break_even
        vector_to_entry: pp required to reach entry trigger
    """
    current  = metrics.get("current_apy")
    mean_14d = metrics.get("apy_14d_mean")
    mean_7d  = metrics.get("apy_7d_mean")
    slope    = metrics.get("apy_30d_slope")

    # Use best available APY for threshold checks
    apy_check = current if current is not None else mean_7d

    if apy_check is None:
        return {
            "alert_status":             "UNKNOWN",
            "recommended_action":       "Cannot determine APY — API fetch failed. Check logs.",
            "estimated_net_apy_if_entered": None,
            "vector_to_break_even":     None,
            "vector_to_entry":          None,
        }

    net_apy = apy_check - BREAK_EVEN_APY
    vector_to_breakeven = BREAK_EVEN_APY - apy_check
    vector_to_entry     = ENTRY_TRIGGER_APY - apy_check

    # Slope annotation
    trend_note = ""
    if slope is not None:
        if slope > 0.1:
            trend_note = f" (trending UP +{slope:.2f}%/day)"
        elif slope < -0.1:
            trend_note = f" (trending DOWN {slope:.2f}%/day)"
        else:
            trend_note = " (flat)"

    # Entry trigger: >= 25% — highest priority check
    if apy_check >= ENTRY_TRIGGER_APY:
        return {
            "alert_status": "ENTRY_READY",
            "recommended_action": (
                f"TRIGGER_ENTRY: JLP gross APY {apy_check:.2f}% >= {ENTRY_TRIGGER_APY}% threshold. "
                f"Net APY if entered: +{net_apy:.2f}pp (vs {BREAK_EVEN_APY}% break-even). "
                f"Action: Review JLP entry — set up Solana wallet, hedge on HL, size position.{trend_note}"
            ),
            "estimated_net_apy_if_entered": round(net_apy, 2),
            "vector_to_break_even":         f"ABOVE break-even by {-vector_to_breakeven:.2f}pp",
            "vector_to_entry":              f"THRESHOLD MET (+{-vector_to_entry:.2f}pp above entry)",
        }

    # Between break-even and entry trigger: monitoring zone (active position OK)
    if apy_check >= BREAK_EVEN_APY:
        return {
            "alert_status": "ACTIVE",
            "recommended_action": (
                f"JLP gross APY {apy_check:.2f}% is above break-even ({BREAK_EVEN_APY}%) "
                f"but below entry trigger ({ENTRY_TRIGGER_APY}%). "
                f"If position active: hold. No new entry recommended. Monitor weekly.{trend_note}"
            ),
            "estimated_net_apy_if_entered": round(net_apy, 2),
            "vector_to_break_even":         f"ABOVE break-even by {-vector_to_breakeven:.2f}pp",
            "vector_to_entry":              f"+{vector_to_entry:.2f}pp required to reach {ENTRY_TRIGGER_APY}% entry",
        }

    # Reduce trigger: < 15% (only actionable if position is active)
    # Per K467: currently at 1.68%, no position — treat as BELOW_BREAK_EVEN not REDUCE
    # REDUCE_WARNING is only meaningful once ENTRY_READY has fired and position opened
    if apy_check < REDUCE_TRIGGER_APY and apy_check >= EXIT_TRIGGER_APY:
        return {
            "alert_status": "REDUCE_WARNING",
            "recommended_action": (
                f"TRIGGER_REDUCE: JLP gross APY {apy_check:.2f}% < {REDUCE_TRIGGER_APY}% reduce threshold. "
                f"If JLP position active: exit half immediately. "
                f"If no position: remain in cash — far below {ENTRY_TRIGGER_APY}% entry trigger.{trend_note}"
            ),
            "estimated_net_apy_if_entered": round(net_apy, 2),
            "vector_to_break_even":         f"+{vector_to_breakeven:.2f}pp required",
            "vector_to_entry":              f"+{vector_to_entry:.2f}pp required to reach {ENTRY_TRIGGER_APY}% entry",
        }

    # Exit trigger: < 10% SUSTAINED 14d (per K468 spec: "sustained 14d")
    # Requires 14d mean to be below EXIT_TRIGGER_APY — not triggered on sparse/single data.
    # When data_points < 14d worth of history (no historical data), default to BELOW_BREAK_EVEN.
    if mean_14d is not None and mean_14d < EXIT_TRIGGER_APY:
        return {
            "alert_status": "EXIT",
            "recommended_action": (
                f"TRIGGER_EXIT: JLP 14d mean APY {mean_14d:.2f}% < {EXIT_TRIGGER_APY}% sustained ({SUSTAINED_EXIT_DAYS}d) exit threshold. "
                f"If JLP position active: exit ALL. No new entry until APY recovers above {ENTRY_TRIGGER_APY}%.{trend_note}"
            ),
            "estimated_net_apy_if_entered": round(net_apy, 2),
            "vector_to_break_even":         f"+{vector_to_breakeven:.2f}pp required",
            "vector_to_entry":              f"+{vector_to_entry:.2f}pp required to reach {ENTRY_TRIGGER_APY}% entry",
        }

    # Below break-even (including when current < EXIT_TRIGGER but 14d data unavailable):
    # Hold cash. Wait for >= ENTRY_TRIGGER_APY.
    action = (
        f"Hold cash. JLP currently {apy_check:.2f}% < break-even {BREAK_EVEN_APY}%. "
        f"Wait for >= {ENTRY_TRIGGER_APY}% trigger.{trend_note}"
    )
    return {
        "alert_status":             "BELOW_BREAK_EVEN",
        "recommended_action":       action,
        "estimated_net_apy_if_entered": round(net_apy, 2),
        "vector_to_break_even":     f"+{vector_to_breakeven:.2f}pp required",
        "vector_to_entry":          f"+{vector_to_entry:.2f}pp required to reach {ENTRY_TRIGGER_APY}% entry",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Alert persistence
# ─────────────────────────────────────────────────────────────────────────────

def write_alert(alert_status: str, message: str, metrics: dict) -> None:
    """Append alert entry to JSONL file."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "alert_status":  alert_status,
            "message":       message,
            "current_apy":   metrics.get("current_apy"),
            "apy_7d_mean":   metrics.get("apy_7d_mean"),
            "apy_30d_mean":  metrics.get("apy_30d_mean"),
        }
        with open(ALERTS_JSONL, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log_msg(f"Alert written: {alert_status}")
    except Exception as e:
        log_err(f"write_alert: {e}")


def send_ntfy(message: str, title: str = "JLP APY Alert", priority: str = "default") -> None:
    """Send ntfy.sh notification (best-effort, no crash on failure)."""
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title":    title,
                "Priority": priority,
                "Tags":     "moneybag,chart_with_upwards_trend",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        log_msg(f"ntfy sent: {title}")
    except Exception as e:
        log_err(f"ntfy send failed (non-fatal): {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard JSON writer
# ─────────────────────────────────────────────────────────────────────────────

def write_dashboard(metrics: dict, trigger_info: dict) -> None:
    """Write dashboard JSON in K468 schema."""
    now_jst = datetime.now(JST)
    current = metrics.get("current_apy")
    breakeven_gap = (current - BREAK_EVEN_APY) if current is not None else None

    dashboard = {
        "last_poll_jst":              now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
        "last_poll_utc":              datetime.now(timezone.utc).isoformat(),
        "current_apy":                round(current, 4) if current is not None else K467_CURRENT_APY,
        "apy_7d_mean":                round(metrics["apy_7d_mean"],  4) if metrics.get("apy_7d_mean")  is not None else None,
        "apy_30d_mean":               round(metrics["apy_30d_mean"], 4) if metrics.get("apy_30d_mean") is not None else None,
        "apy_30d_slope":              round(metrics["apy_30d_slope"], 6) if metrics.get("apy_30d_slope") is not None else None,
        "break_even_apy":             BREAK_EVEN_APY,
        "entry_trigger_threshold":    ENTRY_TRIGGER_APY,
        "reduce_trigger_threshold":   REDUCE_TRIGGER_APY,
        "exit_trigger_threshold":     EXIT_TRIGGER_APY,
        "alert_status":               trigger_info.get("alert_status", "UNKNOWN"),
        "recommended_action":         trigger_info.get("recommended_action", ""),
        "estimated_net_apy_if_entered": trigger_info.get("estimated_net_apy_if_entered"),
        "vector_to_break_even":       trigger_info.get("vector_to_break_even"),
        "vector_to_entry":            trigger_info.get("vector_to_entry"),
        "data_points":                metrics.get("point_count", 0),
        "k467_baseline_apy":          K467_CURRENT_APY,
        "source":                     "DefiLlama yields API (api.llama.fi/yields)",
        "wave":                       "K468",
    }

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_JSON, "w") as f:
            json.dump(dashboard, f, indent=2)
        log_msg(f"Dashboard written: {DASHBOARD_JSON}")
    except Exception as e:
        log_err(f"write_dashboard: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run single-shot JLP APY monitor (K468)."""
    try:
        log_msg("K468 JLP APY monitor started")

        # 1. Fetch current APY from DefiLlama
        log_msg("Fetching JLP APY from DefiLlama yields API...")
        current_apy = fetch_jlp_apy_current()

        if current_apy is None:
            log_err("Could not fetch current JLP APY — using K467 baseline fallback")
            current_apy = load_dashboard_fallback()
            if current_apy is None:
                current_apy = K467_CURRENT_APY
                log_msg(f"Using K467 baseline APY: {K467_CURRENT_APY}%")

        log_msg(f"Current JLP APY: {current_apy:.4f}%")

        # 2. Fetch historical series for 7d/30d metrics
        apy_series: list[tuple[int, float]] = []
        pool_id = fetch_jlp_pool_id()
        if pool_id:
            log_msg(f"Fetching JLP APY history for pool {pool_id}...")
            raw_history = fetch_jlp_apy_history(pool_id)
            if raw_history:
                apy_series = extract_apy_series(raw_history)
                log_msg(f"APY history: {len(apy_series)} data points")
            else:
                log_err("No APY history returned for JLP pool")
        else:
            log_err("JLP pool ID not found — 7d/30d metrics will be None")

        # 3. Compute metrics
        metrics = compute_metrics(apy_series, current_apy)

        # 4. Detect triggers
        trigger_info = detect_triggers(metrics)
        alert_status = trigger_info.get("alert_status", "UNKNOWN")

        # 5. Write alert to JSONL
        write_alert(alert_status, trigger_info.get("recommended_action", ""), metrics)

        # 6. Write dashboard JSON
        write_dashboard(metrics, trigger_info)

        # 7. Send ntfy notification for actionable triggers
        if alert_status == "ENTRY_READY":
            send_ntfy(
                message=trigger_info.get("recommended_action", "JLP entry trigger fired"),
                title=f"JLP ENTRY TRIGGER: {current_apy:.2f}% >= {ENTRY_TRIGGER_APY}%",
                priority="high",
            )
        elif alert_status in ("REDUCE_WARNING", "EXIT"):
            send_ntfy(
                message=trigger_info.get("recommended_action", f"JLP {alert_status}"),
                title=f"JLP {alert_status}: {current_apy:.2f}%",
                priority="urgent",
            )

        # 8. Summary log
        log_msg(
            f"K468 complete: current={current_apy:.2f}% "
            f"7d={metrics.get('apy_7d_mean') or 'N/A'} "
            f"30d={metrics.get('apy_30d_mean') or 'N/A'} "
            f"status={alert_status} "
            f"break_even={BREAK_EVEN_APY}% entry_trigger={ENTRY_TRIGGER_APY}%"
        )

        return 0

    except Exception as e:
        log_err(f"Unhandled exception: {type(e).__name__} {e}")
        return 0   # always exit cleanly — weekly cron must not crash launchd


if __name__ == "__main__":
    sys.exit(main())

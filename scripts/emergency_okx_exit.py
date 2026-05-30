#!/usr/bin/env python3
"""
emergency_okx_exit.py — K745 OKX Emergency Exit Script (Skeleton)
===================================================================
SCAFFOLD: Dry-run safe by default. Live execution requires:
  1. OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE in environment
  2. OKX_LIVE_ENABLED=true in .env.local
  3. Explicit --EXECUTE flag (cannot be passed accidentally)

Mirrors emergency_hl_exit.py (K357) pattern for OKX venue.

Context (K745):
  After K498 OKX activation, OKX will hold up to 40% of AUM ($4M at $10M).
  Emergency scenarios triggering OKX exit:
    - OKX regulatory enforcement or API shutdown signal
    - OKX trading halt or withdrawal freeze
    - OKX-specific exploit or insolvency signal
    - Operator discretion (override)

  Default response: market-close all OKX perp positions.
  Fallback: re-route to HL/Bybit (if cap headroom exists).

Usage:
  python3 scripts/emergency_okx_exit.py --dry-run              # safe, no orders
  python3 scripts/emergency_okx_exit.py --status               # show OKX position state
  python3 scripts/emergency_okx_exit.py --EXECUTE --confirm    # LIVE — real orders

Trigger conditions (§66 runbook):
  - OKX API returns repeated 5xx errors (>10 in 5min)
  - OKX-specific regulatory notice
  - OKX withdrawal freeze signal
  - OKX mark price deviation >5% from CEX consensus
  - Operator emergency trigger (EMERGENCY_OKX_FLAG file)

Security (K339):
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals
  Private keys: env vars only (OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE)
  API keys NEVER logged

WARNING: --EXECUTE flag triggers REAL OKX ORDERS.
         Default mode (--dry-run) is safe. Always verify dry-run output first.
         This script is a SKELETON — verify against live OKX API before production use.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR  = REPO_ROOT / "logs"
DATA_DIR  = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / "cache"

LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── OKX API endpoints ─────────────────────────────────────────────────────────
OKX_BASE_URL    = "https://www.okx.com"
OKX_POSITIONS_EP = "/api/v5/account/positions"
OKX_CLOSE_EP     = "/api/v5/trade/close-position"
OKX_CANCEL_EP    = "/api/v5/trade/cancel-order"
OKX_ORDERS_EP    = "/api/v5/trade/orders-pending"
OKX_BALANCE_EP   = "/api/v5/account/balance"

# ── Emergency flag files ──────────────────────────────────────────────────────
EMERGENCY_OKX_FLAG   = REPO_ROOT / "EMERGENCY_OKX_EXIT_TRIGGERED.flag"
EMERGENCY_STATUS_JSON = DATA_DIR  / "emergency_okx_exit_status.json"
EMERGENCY_LOG_FILE   = LOGS_DIR  / "emergency_okx_exit.log"

# ── Constants ─────────────────────────────────────────────────────────────────
SLIPPAGE_ESTIMATE_PCT  = 0.20   # 20 bps estimated slippage per market-close (OKX conservative)
CANCEL_WAIT_SECONDS    = 1.5
CLOSE_WAIT_SECONDS     = 2.0
POST_CLOSE_VERIFY_WAIT = 5.0
POSITION_NOISE_USD     = 10.0   # positions < $10 notional considered closed

# ntfy.sh alert topic (optional push notification)
NTFY_EMERGENCY_TOPIC = "cryptolab-emergency-okx-exit"

# ── Logging ───────────────────────────────────────────────────────────────────
def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("emergency_okx_exit")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(EMERGENCY_LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("[emergency_okx_exit] %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

log = _setup_logger()


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers (HMAC-SHA256 — same as okx_client.py)
# ─────────────────────────────────────────────────────────────────────────────

def _timestamp_okx() -> str:
    """OKX requires ISO 8601 UTC timestamp with ms precision."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _sign_okx(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    """HMAC-SHA256 signature: base64(hmac(secret, timestamp+METHOD+path+body))."""
    import base64, hashlib, hmac as _hmac
    prehash = timestamp + method.upper() + path + body
    sig = _hmac.new(secret.encode("utf-8"), prehash.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("utf-8")


def _okx_get(path: str, api_key: str, secret: str, passphrase: str) -> Optional[dict]:
    """Authenticated GET request to OKX API."""
    import urllib.request, urllib.error
    ts  = _timestamp_okx()
    sig = _sign_okx(secret, ts, "GET", path)
    url = OKX_BASE_URL + path
    headers = {
        "OK-ACCESS-KEY":       api_key,
        "OK-ACCESS-SIGN":      sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type":        "application/json",
        "User-Agent":          "crypto-lab-emergency-okx-exit/1.0",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        log.error("GET %s HTTP %d", path, exc.code)
        return None
    except Exception as exc:
        log.error("GET %s error: %s", path, exc)
        return None


def _okx_post(path: str, body: dict, api_key: str, secret: str, passphrase: str) -> Optional[dict]:
    """Authenticated POST request to OKX API."""
    import urllib.request, urllib.error
    body_str = json.dumps(body, separators=(",", ":"))
    ts  = _timestamp_okx()
    sig = _sign_okx(secret, ts, "POST", path, body_str)
    url = OKX_BASE_URL + path
    headers = {
        "OK-ACCESS-KEY":       api_key,
        "OK-ACCESS-SIGN":      sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type":        "application/json",
        "User-Agent":          "crypto-lab-emergency-okx-exit/1.0",
    }
    try:
        req = urllib.request.Request(url, data=body_str.encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_bytes = exc.read() if hasattr(exc, "read") else b""
        log.error("POST %s HTTP %d: %s", path, exc.code, body_bytes[:200])
        return None
    except Exception as exc:
        log.error("POST %s error: %s", path, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core exit logic
# ─────────────────────────────────────────────────────────────────────────────

def _load_credentials() -> Tuple[str, str, str]:
    """
    Load OKX credentials from environment.
    K339: credentials NEVER hardcoded. Never log credential values.
    """
    api_key    = os.environ.get("OKX_API_KEY", "")
    api_secret = os.environ.get("OKX_API_SECRET", "")
    passphrase = os.environ.get("OKX_PASSPHRASE", "")
    return api_key, api_secret, passphrase


def _check_live_gate() -> bool:
    """Check OKX_LIVE_ENABLED=true in environment."""
    return os.environ.get("OKX_LIVE_ENABLED", "false").lower().strip() == "true"


def fetch_okx_positions(
    api_key: str,
    secret:  str,
    passphrase: str,
    dry_run: bool = True,
) -> List[dict]:
    """
    Fetch all open OKX perpetual positions.
    Returns list of position dicts (OKX format).
    In dry-run: returns dummy positions for plan generation.
    """
    if dry_run:
        log.info("DRY-RUN: skipping live OKX position fetch")
        return [
            {
                "instId": "INJ-USDT-SWAP", "posSide": "short",
                "pos": "10.0", "avgPx": "25.50", "notionalUsd": "255.00",
                "_dry_run": True,
            },
        ]

    raw = _okx_get(OKX_POSITIONS_EP + "?instType=SWAP", api_key, secret, passphrase)
    if raw is None or raw.get("code") != "0":
        log.error("Failed to fetch positions: %s", raw)
        return []
    return raw.get("data", [])


def fetch_okx_pending_orders(
    api_key: str, secret: str, passphrase: str, dry_run: bool = True,
) -> List[dict]:
    """Fetch all pending (unfilled) OKX orders."""
    if dry_run:
        return []
    raw = _okx_get(OKX_ORDERS_EP + "?instType=SWAP", api_key, secret, passphrase)
    if raw is None or raw.get("code") != "0":
        return []
    return raw.get("data", [])


def cancel_okx_order(
    inst_id:    str,
    order_id:   str,
    api_key:    str, secret: str, passphrase: str,
    dry_run:    bool = True,
) -> bool:
    """Cancel a single OKX order. Returns True if successful."""
    if dry_run:
        log.info("DRY-RUN: would cancel %s ordId=%s", inst_id, order_id)
        return True
    body = {"instId": inst_id, "ordId": order_id}
    raw = _okx_post(OKX_CANCEL_EP, body, api_key, secret, passphrase)
    ok = raw is not None and raw.get("code") == "0"
    if not ok:
        log.error("Cancel failed: %s ordId=%s: %s", inst_id, order_id, raw)
    return ok


def close_okx_position(
    inst_id:    str,
    pos_side:   str,   # "net" | "long" | "short"
    mgn_mode:   str,   # "cross" | "isolated"
    api_key:    str, secret: str, passphrase: str,
    dry_run:    bool = True,
) -> dict:
    """
    Close an OKX position via market order.
    Uses POST /api/v5/trade/close-position (market ordType).
    Returns OKX response dict or dry-run mock.
    """
    if dry_run:
        log.info("DRY-RUN: would close %s posSide=%s mgnMode=%s (MARKET)", inst_id, pos_side, mgn_mode)
        return {
            "ok": True, "dry_run": True,
            "inst_id": inst_id, "pos_side": pos_side,
            "order_type": "market",
        }

    body = {
        "instId":  inst_id,
        "mgnMode": mgn_mode,
        "posSide": pos_side,
        "ordType": "market",   # emergency: market to guarantee fill
    }
    log.warning("LIVE CLOSE: %s posSide=%s mgnMode=%s MARKET", inst_id, pos_side, mgn_mode)
    raw = _okx_post(OKX_CLOSE_EP, body, api_key, secret, passphrase)
    if raw is None:
        return {"ok": False, "error": "HTTP request failed"}
    if raw.get("code") != "0":
        return {"ok": False, "error": f"OKX error {raw.get('code')}: {raw.get('msg')}", "raw": raw}
    data = raw.get("data", [{}])
    return {"ok": True, "raw": raw, "order_id": data[0].get("ordId", "") if data else ""}


def send_ntfy_alert(message: str, priority: str = "urgent") -> None:
    """
    Send push notification via ntfy.sh.
    Non-blocking: failure doesn't interrupt exit procedure.
    """
    try:
        import urllib.request
        data = message.encode("utf-8")
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_EMERGENCY_TOPIC}",
            data=data,
            headers={"Priority": priority, "Title": "EMERGENCY OKX EXIT"},
        )
        urllib.request.urlopen(req, timeout=5)
        log.info("Alert sent to ntfy.sh/%s", NTFY_EMERGENCY_TOPIC)
    except Exception as exc:
        log.warning("ntfy alert failed (non-critical): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Exit orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run_emergency_exit(
    dry_run:    bool = True,
    confirm:    bool = False,
    api_key:    str  = "",
    secret:     str  = "",
    passphrase: str  = "",
) -> dict:
    """
    Full emergency OKX exit procedure:
      Phase 1: Raise emergency flag file
      Phase 2: Cancel all pending OKX orders
      Phase 3: Close all OKX positions (market orders)
      Phase 4: Verify positions closed
      Phase 5: Update risk_positions.json
      Phase 6: Write status JSON + send alert

    Returns status dict with per-position results.
    """
    now_jst = datetime.now(JST)
    ts      = datetime.now(timezone.utc).isoformat()

    log.warning("=" * 70)
    log.warning("EMERGENCY OKX EXIT %s", "DRY-RUN" if dry_run else "LIVE")
    log.warning("Started: %s JST", now_jst.strftime("%Y-%m-%d %H:%M:%S"))
    log.warning("=" * 70)

    if not dry_run:
        if not confirm:
            log.error("LIVE mode requires --confirm flag. Aborting.")
            return {"ok": False, "error": "confirm required for LIVE mode"}
        if not _check_live_gate():
            log.error("OKX_LIVE_ENABLED != true. Aborting live exit.")
            return {"ok": False, "error": "OKX_LIVE_ENABLED must be true"}
        if not api_key:
            log.error("No OKX_API_KEY found. Aborting live exit.")
            return {"ok": False, "error": "OKX credentials required"}

    status = {
        "mode":            "dry_run" if dry_run else "LIVE",
        "started_jst":     now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "started_utc":     ts,
        "cancel_results":  [],
        "close_results":   [],
        "positions_before": [],
        "final_status":    "PENDING",
        "elapsed_s":       0.0,
    }

    t0 = time.time()

    # Phase 1: Set emergency flag
    try:
        EMERGENCY_OKX_FLAG.write_text(
            f"EMERGENCY OKX EXIT TRIGGERED\n"
            f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}\n"
            f"Time (JST): {now_jst.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"User: {os.environ.get('USER', 'unknown')}\n"
        )
        log.info("Phase 1: Emergency flag set: %s", EMERGENCY_OKX_FLAG.name)
    except Exception as exc:
        log.warning("Flag write failed (non-critical): %s", exc)

    # Phase 2: Fetch + cancel pending orders
    log.info("Phase 2: Fetching pending OKX orders ...")
    pending = fetch_okx_pending_orders(api_key, secret, passphrase, dry_run)
    log.info("  Found %d pending orders", len(pending))
    for order in pending:
        inst_id  = order.get("instId", "")
        order_id = order.get("ordId", "")
        ok = cancel_okx_order(inst_id, order_id, api_key, secret, passphrase, dry_run)
        status["cancel_results"].append({"inst_id": inst_id, "order_id": order_id, "cancelled": ok})
        time.sleep(CANCEL_WAIT_SECONDS)

    # Phase 3: Fetch positions + close
    log.info("Phase 3: Fetching open OKX positions ...")
    positions = fetch_okx_positions(api_key, secret, passphrase, dry_run)
    status["positions_before"] = positions
    log.info("  Found %d open positions", len(positions))

    if not positions:
        log.info("  No positions to close.")
        status["final_status"] = "COMPLETE_NOTHING_TO_CLOSE"
    else:
        for pos in positions:
            inst_id  = pos.get("instId", "")
            pos_side = pos.get("posSide", "net")
            mgn_mode = pos.get("mgnMode", "cross")
            notional = float(pos.get("notionalUsd", 0.0) or 0.0)

            if abs(notional) < POSITION_NOISE_USD:
                log.info("  Skipping dust position: %s (notional=$%.2f)", inst_id, notional)
                continue

            slippage_est = abs(notional) * SLIPPAGE_ESTIMATE_PCT / 100
            log.warning(
                "  CLOSING: %s posSide=%s notional=$%.2f (slip_est=$%.2f)",
                inst_id, pos_side, notional, slippage_est,
            )

            result = close_okx_position(inst_id, pos_side, mgn_mode, api_key, secret, passphrase, dry_run)
            status["close_results"].append({
                "inst_id":       inst_id,
                "pos_side":      pos_side,
                "notional_usd":  notional,
                "slippage_est":  round(slippage_est, 2),
                "result":        result,
            })
            time.sleep(CLOSE_WAIT_SECONDS)

        # Phase 4: Post-close verification
        log.info("Phase 4: Verifying positions closed ...")
        time.sleep(POST_CLOSE_VERIFY_WAIT)
        positions_after = fetch_okx_positions(api_key, secret, passphrase, dry_run)
        open_count = len([p for p in positions_after if abs(float(p.get("notionalUsd", 0) or 0)) > POSITION_NOISE_USD])
        status["positions_after_count"] = open_count
        if open_count == 0:
            status["final_status"] = "COMPLETE_ALL_CLOSED"
            log.info("  All OKX positions closed successfully.")
        else:
            status["final_status"] = f"PARTIAL_CLOSE: {open_count} positions remain"
            log.error("  %d positions still open! Manual intervention required.", open_count)

    status["elapsed_s"] = round(time.time() - t0, 1)

    # Phase 5: Update risk manager
    _update_risk_manager_okx_cleared()

    # Phase 6: Write status JSON
    status_payload = {
        "_wave":  "K745",
        "source": "emergency_okx_exit.py",
        **status,
    }
    try:
        tmp = EMERGENCY_STATUS_JSON.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(status_payload, f, indent=2)
        tmp.replace(EMERGENCY_STATUS_JSON)
        log.info("Status: %s", EMERGENCY_STATUS_JSON.name)
    except Exception as exc:
        log.warning("Status write failed: %s", exc)

    # Alert
    alert_msg = (
        f"EMERGENCY OKX EXIT {'DRY-RUN' if dry_run else 'LIVE'} | "
        f"status={status['final_status']} | "
        f"closed={len(status['close_results'])} positions | "
        f"{now_jst.strftime('%Y-%m-%d %H:%M JST')}"
    )
    send_ntfy_alert(alert_msg)
    log.warning("EMERGENCY OKX EXIT COMPLETE: %s", status["final_status"])
    return status_payload


def _update_risk_manager_okx_cleared() -> None:
    """Update risk_positions.json to zero out all OKX positions."""
    if not (DATA_DIR / "risk_positions.json").exists():
        return
    try:
        with open(DATA_DIR / "risk_positions.json") as f:
            data = json.load(f)
        positions = [p for p in data.get("positions", []) if p.get("venue") != "OKX"]
        data["positions"] = positions
        data["_emergency_okx_cleared_utc"] = datetime.now(timezone.utc).isoformat()
        tmp = (DATA_DIR / "risk_positions.json").with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(DATA_DIR / "risk_positions.json")
        log.info("risk_positions.json: OKX positions cleared")
    except Exception as exc:
        log.warning("risk_positions update failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Status check
# ─────────────────────────────────────────────────────────────────────────────

def check_status(api_key: str, secret: str, passphrase: str) -> dict:
    """Show current OKX position state and concentration (dry-run-safe)."""
    has_creds = bool(api_key and secret and passphrase)

    status = {
        "timestamp_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "has_credentials": has_creds,
        "live_enabled": _check_live_gate(),
        "emergency_flag_exists": EMERGENCY_OKX_FLAG.exists(),
    }

    if has_creds and _check_live_gate():
        positions = fetch_okx_positions(api_key, secret, passphrase, dry_run=False)
        status["positions"] = positions
        status["total_notional_usd"] = sum(
            abs(float(p.get("notionalUsd", 0) or 0)) for p in positions
        )
    else:
        status["note"] = "Credentials/live gate not set — position state unknown (dry-run mode)"
        status["positions"] = []

    # Check risk_positions.json for OKX-tracked positions
    if (DATA_DIR / "risk_positions.json").exists():
        try:
            with open(DATA_DIR / "risk_positions.json") as f:
                rm_data = json.load(f)
            okx_pos = [p for p in rm_data.get("positions", []) if p.get("venue") == "OKX"]
            status["risk_manager_okx_positions"] = okx_pos
            status["risk_manager_okx_notional"] = sum(p.get("notional_usd", 0) for p in okx_pos)
        except Exception:
            pass

    return status


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="K745 OKX Emergency Exit (K357 mirror — SCAFFOLD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  --dry-run (DEFAULT): Fetch positions + generate exit plan. NO orders sent.
  --EXECUTE --confirm: Live execution. Sends REAL OKX market orders.

CREDENTIALS (env vars, set in .env.local):
  OKX_API_KEY       — API key (trade scope required)
  OKX_API_SECRET    — API secret
  OKX_PASSPHRASE    — API passphrase
  OKX_LIVE_ENABLED  — must be "true" for live execution

TRIGGER CONDITIONS (§66 runbook):
  - OKX API repeated 5xx (>10 in 5min)
  - OKX regulatory notice / trading halt
  - OKX withdrawal freeze signal
  - OKX mark price deviation >5% from CEX consensus
  - Operator emergency trigger

SAFETY CHECKLIST:
  1. Run --status to see current OKX positions
  2. Run --dry-run to review exit plan
  3. Set OKX_LIVE_ENABLED=true in .env.local
  4. Run --EXECUTE --confirm to execute
  5. Verify via --status after execution

K339: credentials from env vars only. Never hardcode keys.
LIVE modification禁止 unless --EXECUTE --confirm supplied.
        """,
    )
    p.add_argument("--dry-run",  action="store_true", default=True,  help="Dry run (no orders)")
    p.add_argument("--EXECUTE",  action="store_true", default=False, help="LIVE execution mode")
    p.add_argument("--confirm",  action="store_true", default=False, help="Required for --EXECUTE")
    p.add_argument("--status",   action="store_true", help="Show current OKX position state")
    p.add_argument("--json",     action="store_true", help="Output as JSON")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    api_key, secret, passphrase = _load_credentials()

    # Mode determination: --EXECUTE overrides --dry-run
    is_live = args.EXECUTE and not args.dry_run

    if args.status:
        status = check_status(api_key, secret, passphrase)
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"\n=== OKX Emergency Exit Status ===")
            print(f"  Credentials loaded:  {status['has_credentials']}")
            print(f"  Live enabled:        {status['live_enabled']}")
            print(f"  Emergency flag:      {status['emergency_flag_exists']}")
            print(f"  Positions (risk_mgr):{status.get('risk_manager_okx_positions', [])}")
            if "total_notional_usd" in status:
                print(f"  OKX notional:       ${status['total_notional_usd']:,.2f}")
        return 0

    # Confirm live mode safety
    if is_live:
        print(
            "\n⚠  WARNING: --EXECUTE mode — LIVE OKX MARKET ORDERS WILL BE SUBMITTED  ⚠",
            file=sys.stderr,
        )
        if not args.confirm:
            print("  Add --confirm to proceed with live execution.", file=sys.stderr)
            return 1
        if not _check_live_gate():
            print("  OKX_LIVE_ENABLED != 'true'. Set in .env.local.", file=sys.stderr)
            return 1

    dry_run = not is_live
    print(
        f"\n=== Emergency OKX Exit: {'DRY-RUN' if dry_run else 'LIVE'} ===",
        file=sys.stderr,
    )

    result = run_emergency_exit(
        dry_run=dry_run,
        confirm=args.confirm,
        api_key=api_key,
        secret=secret,
        passphrase=passphrase,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n  Mode:   {result.get('mode')}")
        print(f"  Status: {result.get('final_status')}")
        print(f"  Elapsed: {result.get('elapsed_s')}s")
        if result.get("close_results"):
            print(f"  Closed: {len(result['close_results'])} positions")
        if result.get("cancel_results"):
            print(f"  Cancelled: {len(result['cancel_results'])} orders")

    return 0 if result.get("final_status", "").startswith("COMPLETE") else 1


if __name__ == "__main__":
    sys.exit(main())

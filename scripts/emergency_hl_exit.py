"""
emergency_hl_exit.py — K357 Emergency HyperLiquid Exit Script
=============================================================
SCAFFOLD: Design + dry-run only. Live trading requires user-supplied credentials.

Context (K355):
  v6.13d production allocates 57.5% of capital to HyperLiquid infrastructure:
    K280 main     75% × ~50% HL leg    = 37.5% on HL
    K297' satellite  20% (PAXG/SPX, HL-only) = 20% on HL
    sUSDe         5% (Ethena, ETH-based) =  0% on HL
  Worst-case scenario (HL platform shutdown, P=3-7%/12mo) = 1.7-4.0% expected loss.
  K355 identified: NO emergency exit script existed. This K357 scaffold closes that gap.

Usage:
  python3 scripts/emergency_hl_exit.py --dry-run --user 0x...
  python3 scripts/emergency_hl_exit.py --dry-run                   # uses HL_USER_ADDRESS env
  python3 scripts/emergency_hl_exit.py --EXECUTE --user 0x...      # LIVE — requires confirm

Trigger conditions (per §14 runbook):
  - CFTC/regulatory enforcement action against HL
  - HL platform alert (exploit, insolvency signal, ADL cascade)
  - HYPE token -40% in 7 days (platform stress indicator)
  - Custom user trigger (operator discretion)

Security (K339):
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals in paths
  Private key: read from HL_PRIVATE_KEY env var ONLY at execution moment — NEVER logged
  User address: read from HL_USER_ADDRESS env var or --user CLI arg

WARNING: This script performs REAL TRADING when run with --EXECUTE.
         Default mode is --dry-run (safe). Always verify dry-run output first.

Dependencies: requests, json, os, sys, time, argparse, hashlib, hmac (stdlib only + requests)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import json
import logging
import os
import struct
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR  = REPO_ROOT / "logs"
CACHE_DIR = REPO_ROOT / "cache"
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ── HL API endpoints ──────────────────────────────────────────────────────────
HL_INFO_URL     = "https://api.hyperliquid.xyz/info"
HL_EXCHANGE_URL = "https://api.hyperliquid.xyz/exchange"

# ── Constants ─────────────────────────────────────────────────────────────────
SLIPPAGE_ESTIMATE_PCT  = 0.15   # 15 bps estimated slippage per market-close
CANCEL_WAIT_SECONDS    = 2.0    # wait between cancel requests
CLOSE_WAIT_SECONDS     = 3.0    # wait between position-close requests
POST_CLOSE_VERIFY_WAIT = 5.0    # wait before verifying position is zero
ESTIMATED_TIME_PER_POS = 30     # seconds (per plan spec)
POSITION_NOISE_USD     = 10.0   # positions < $10 notional considered closed

# ── ntfy.sh topic for emergency alerts ───────────────────────────────────────
NTFY_EMERGENCY_TOPIC = "cryptolab-emergency-hl-exit"

# ── Flag file (K302a daemons check this; refuse to trade if present) ─────────
EMERGENCY_FLAG_FILE     = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
EMERGENCY_STATUS_JSON   = CACHE_DIR / "emergency_exit_status.json"
EMERGENCY_LOG_FILE      = LOGS_DIR  / "emergency_hl_exit.log"

# ── Logging setup ─────────────────────────────────────────────────────────────
def setup_logging(to_file: bool = True) -> logging.Logger:
    logger = logging.getLogger("emergency_hl_exit")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S UTC")
    sh  = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    if to_file:
        fh = logging.FileHandler(EMERGENCY_LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# 1. HL Info API (read-only, no auth required)
# ─────────────────────────────────────────────────────────────────────────────

def _hl_post_info(payload: dict, dry_run: bool = False, retries: int = 3) -> Any:
    """POST to HL info endpoint. In dry-run: returns mock data instead of calling API."""
    if dry_run:
        return None  # callers handle None as mock
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library required. Install with: pip install requests")

    body = json.dumps(payload).encode()
    for attempt in range(retries):
        try:
            resp = requests.post(
                HL_INFO_URL,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "ct-emergency-exit/1.0"},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt < retries - 1:
                wait = 5 * (2 ** attempt)
                print(f"  [WARN] hl_post_info attempt {attempt+1} failed: {exc} — retry in {wait}s")
                time.sleep(wait)
            else:
                raise


def fetch_positions(user: str, dry_run: bool = False) -> List[Dict]:
    """
    GET clearinghouseState for user. Returns list of position dicts:
      {coin, size, value_usd, side}  (side = 'long' | 'short')

    HL API response structure:
      assetPositions: [{position: {coin, szi (size, + long / - short), positionValue, ...}}]
    """
    if dry_run:
        print("  [DRY-RUN] fetch_positions — returning empty mock (no API call made)")
        return []

    raw = _hl_post_info({"type": "clearinghouseState", "user": user})
    if raw is None:
        return []

    positions = []
    for item in raw.get("assetPositions", []):
        pos = item.get("position", {})
        coin = pos.get("coin", "")
        szi  = float(pos.get("szi", "0") or "0")    # signed: + = long, - = short
        pval = float(pos.get("positionValue", "0") or "0")

        if abs(szi) < 1e-9:
            continue  # skip zero positions

        positions.append({
            "coin":      coin,
            "size":      abs(szi),
            "value_usd": abs(pval),
            "side":      "long" if szi > 0 else "short",
            "raw_szi":   szi,
        })

    return positions


def fetch_orders(user: str, dry_run: bool = False) -> List[Dict]:
    """
    GET openOrders for user. Returns list of order dicts:
      {coin, oid, side, size, px}
    """
    if dry_run:
        print("  [DRY-RUN] fetch_orders — returning empty mock (no API call made)")
        return []

    raw = _hl_post_info({"type": "openOrders", "user": user})
    if raw is None:
        return []

    orders = []
    for o in (raw or []):
        orders.append({
            "coin":  o.get("coin", ""),
            "oid":   o.get("oid", 0),
            "side":  o.get("side", ""),
            "size":  float(o.get("sz", "0") or "0"),
            "px":    float(o.get("limitPx", "0") or "0"),
        })
    return orders


def fetch_balance(user: str, dry_run: bool = False) -> Dict:
    """Fetch USDC margin balance and HLP/vault exposure summary."""
    if dry_run:
        print("  [DRY-RUN] fetch_balance — returning mock $0 (no API call made)")
        return {"usdc_balance": 0.0, "unrealized_pnl": 0.0, "withdrawable": 0.0}

    raw = _hl_post_info({"type": "clearinghouseState", "user": user})
    if raw is None:
        return {}

    margin = raw.get("crossMarginSummary", {})
    return {
        "usdc_balance":    float(margin.get("accountValue", "0") or "0"),
        "unrealized_pnl":  float(margin.get("totalNtlPos", "0") or "0"),
        "withdrawable":    float(raw.get("withdrawable", "0") or "0"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exit Plan Builder
# ─────────────────────────────────────────────────────────────────────────────

def _detect_k457_basket_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K459 Phase 6: Detect K457 multi-asset basket positions (BTC/ETH/SOL on HL + Bybit).

    K457 basket = up to 6 legs: BTC long+short, ETH long+short, SOL long+short
    across HL and Bybit venues simultaneously.

    Returns a dict describing detected basket legs if found, or None.
    Used to ensure short legs are closed first (avoid uncovered short window).

    Sequential close: short legs first, then long legs (per K459 Phase 6 protocol).
    """
    K457_SYMBOLS = {"BTC", "ETH", "SOL"}
    basket_positions = [p for p in positions if p.get("coin", "").upper() in K457_SYMBOLS]

    if not basket_positions:
        return None

    longs  = [p for p in basket_positions if p.get("side") == "long"]
    shorts = [p for p in basket_positions if p.get("side") == "short"]

    if not (longs and shorts):
        return None  # need at least one long and one short to be a basket

    return {
        "detected":         True,
        "strategy":         "K457 BTC+ETH+SOL multi-asset basket",
        "long_legs":        [{"coin": p["coin"], "value_usd": p["value_usd"], "size": p["size"]}
                             for p in longs],
        "short_legs":       [{"coin": p["coin"], "value_usd": p["value_usd"], "size": p["size"]}
                             for p in shorts],
        "long_count":       len(longs),
        "short_count":      len(shorts),
        "total_notional":   sum(p["value_usd"] for p in basket_positions),
        "close_protocol":   "SHORT LEGS FIRST (avoid uncovered short), then LONG LEGS",
        "note":             "K457 basket — close all short legs before long legs per K459 Phase 6",
    }


def _detect_k476_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K478 Phase 5: Detect K476 paired positions (SOL long + BTC short, or reverse).

    K476 SOL-BTC = 2 legs on HL: SOL and BTC (one long, one short).
    Sequential close: short leg first (avoid uncovered short), then long leg.

    A K476 pair is identified by:
      - One long leg: SOL or BTC
      - One short leg: the other of SOL/BTC
      - Both on HL (HL-only strategy, K434 smart router)

    Note: SOL also appears in K457 basket — disambiguation is by position count.
    K476 will be detected when we see exactly SOL+BTC in a paired long/short.
    """
    K476_SYMBOLS = {"SOL", "BTC"}
    sol_btc = [p for p in positions if p.get("coin", "").upper() in K476_SYMBOLS]
    if len(sol_btc) < 2:
        return None

    longs  = [p for p in sol_btc if p.get("side") == "long"]
    shorts = [p for p in sol_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K476_SYMBOLS or short_sym not in K476_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "venue":           "HL",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            "K476 SOL-BTC paired position — cover short first, then sell long (HL-only, K434)",
    }


def close_k476_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K478 Phase 5: Close K476 SOL-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k476_detail = plan.get("k476_pair_detail")

    if not k476_detail or not k476_detail.get("detected"):
        logger.info("  [K476] No K476 SOL-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym  = k476_detail["short_symbol"]
    long_sym   = k476_detail["long_symbol"]
    short_val  = k476_detail.get("short_value_usd", 0.0)
    long_val   = k476_detail.get("long_value_usd", 0.0)

    logger.info(f"  [K476] SOL-BTC paired close — {k476_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  (HL IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  (HL IOC reduce-only)")

    if dry_run:
        logger.info("    [DRY-RUN] K476 SOL-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on HL (sequential)
    # Step 1: cover short (buy SOL or BTC)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ HL")
    # Step 2: sell long (after short covered)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ HL")
    logger.info("    SCAFFOLD: K476 close wired but not executed (HL auth required at live activation)")
    return True


def _detect_k484_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K489 Phase 4: Detect K484 paired positions (AVAX long + BTC short, or reverse).

    K484 AVAX-BTC = 2 legs on HL: AVAX and BTC (one long, one short).
    Sequential close: short leg first (avoid uncovered short), then long leg.

    A K484 pair is identified by:
      - One long leg: AVAX or BTC
      - One short leg: the other of AVAX/BTC
      - Both on HL (HL-only strategy, K434 smart router)

    Note: AVAX also appears in K376 momentum strategy — disambiguation is by paired
    long/short detection (K376 is directional, K484 is delta-neutral paired).
    K484 will be detected when we see exactly AVAX+BTC in a paired long/short.

    OOS Sharpe 43.89 (#1 paired-trade family): AVAX-BTC differential is structurally
    persistent, creating larger FR spread than ETH-BTC or SOL-BTC.
    """
    K484_SYMBOLS = {"AVAX", "BTC"}
    avax_btc = [p for p in positions if p.get("coin", "").upper() in K484_SYMBOLS]
    if len(avax_btc) < 2:
        return None

    longs  = [p for p in avax_btc if p.get("side") == "long"]
    shorts = [p for p in avax_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K484_SYMBOLS or short_sym not in K484_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "venue":           "HL",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            "K484 AVAX-BTC paired position — cover short first, then sell long (HL-only, K434)",
    }


def close_k484_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K489 Phase 4: Close K484 AVAX-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k484_detail = plan.get("k484_pair_detail")

    if not k484_detail or not k484_detail.get("detected"):
        logger.info("  [K484] No K484 AVAX-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym  = k484_detail["short_symbol"]
    long_sym   = k484_detail["long_symbol"]
    short_val  = k484_detail.get("short_value_usd", 0.0)
    long_val   = k484_detail.get("long_value_usd", 0.0)

    logger.info(f"  [K484] AVAX-BTC paired close — {k484_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  (HL IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  (HL IOC reduce-only)")

    if dry_run:
        logger.info("    [DRY-RUN] K484 AVAX-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on HL (sequential)
    # Step 1: cover short (buy AVAX or BTC)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ HL")
    # Step 2: sell long (after short covered)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ HL")
    logger.info("    SCAFFOLD: K484 close wired but not executed (HL auth required at live activation)")
    return True


def _detect_k493_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K499 Phase 4: Detect K493 paired positions (ATOM long + BTC short, or reverse).

    K493 ATOM-BTC = 2 legs on HL: ATOM and BTC (one long, one short).
    Sequential close: short leg first (avoid uncovered short), then long leg.

    A K493 pair is identified by:
      - One long leg: ATOM or BTC
      - One short leg: the other of ATOM/BTC
      - Both on HL (HL-only strategy, K434 smart router)

    Note: ATOM disambiguation — ATOM is Cosmos Hub native token, not present in K457 basket.
    K493 is identified by ATOM+BTC in a paired long/short.
    OOS Sharpe 50.79 (#1 paired-trade family). G5a 0.1763 (most orthogonal).
    Cosmos hypothesis CONFIRMED.
    """
    K493_SYMBOLS = {"ATOM", "BTC"}
    atom_btc = [p for p in positions if p.get("coin", "").upper() in K493_SYMBOLS]
    if len(atom_btc) < 2:
        return None

    longs  = [p for p in atom_btc if p.get("side") == "long"]
    shorts = [p for p in atom_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K493_SYMBOLS or short_sym not in K493_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "venue":           "HL",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            "K493 ATOM-BTC paired position — cover short first, then sell long (HL-only, K434)",
    }


def close_k493_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K499 Phase 4: Close K493 ATOM-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k493_detail = plan.get("k493_pair_detail")

    if not k493_detail or not k493_detail.get("detected"):
        logger.info("  [K493] No K493 ATOM-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym  = k493_detail["short_symbol"]
    long_sym   = k493_detail["long_symbol"]
    short_val  = k493_detail.get("short_value_usd", 0.0)
    long_val   = k493_detail.get("long_value_usd", 0.0)

    logger.info(f"  [K493] ATOM-BTC paired close — {k493_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  (HL IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  (HL IOC reduce-only)")

    if dry_run:
        logger.info("    [DRY-RUN] K493 ATOM-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on HL (sequential)
    # Step 1: cover short (buy ATOM or BTC)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ HL")
    # Step 2: sell long (after short covered)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ HL")
    logger.info("    SCAFFOLD: K493 close wired but not executed (HL auth required at live activation)")
    return True


def _detect_k500_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K506 Phase 4: Detect K500 paired positions (INJ long + BTC short, or reverse).

    K500 INJ-BTC = 2 legs on HL: INJ and BTC (one long, one short).
    Sequential close: short leg first (avoid uncovered short), then long leg.

    A K500 pair is identified by:
      - One long leg: INJ or BTC
      - One short leg: the other of INJ/BTC
      - Both on HL (HL-only strategy, K434 smart router)

    Note: INJ is the Injective DeFi-perp chain token (Cosmos SDK).
    K500 is identified by INJ+BTC in a paired long/short.
    OOS Sharpe 11.23 (family rank #4). G5d 0.2893 PASS (Cosmos 2nd CONFIRMED).
    INJ DeFi-perp mechanics distinct from ATOM IBC/staking.
    """
    K500_SYMBOLS = {"INJ", "BTC"}
    inj_btc = [p for p in positions if p.get("coin", "").upper() in K500_SYMBOLS]
    if len(inj_btc) < 2:
        return None

    longs  = [p for p in inj_btc if p.get("side") == "long"]
    shorts = [p for p in inj_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K500_SYMBOLS or short_sym not in K500_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "venue":           "HL",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            "K500 INJ-BTC paired position — cover short first, then sell long (HL-only, K434)",
    }


def close_k500_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K506 Phase 4: Close K500 INJ-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k500_detail = plan.get("k500_pair_detail")

    if not k500_detail or not k500_detail.get("detected"):
        logger.info("  [K500] No K500 INJ-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym  = k500_detail["short_symbol"]
    long_sym   = k500_detail["long_symbol"]
    short_val  = k500_detail.get("short_value_usd", 0.0)
    long_val   = k500_detail.get("long_value_usd", 0.0)

    logger.info(f"  [K500] INJ-BTC paired close — {k500_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  (HL IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  (HL IOC reduce-only)")

    if dry_run:
        logger.info("    [DRY-RUN] K500 INJ-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on HL (sequential)
    # Step 1: cover short (buy INJ or BTC)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ HL")
    # Step 2: sell long (after short covered)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ HL")
    logger.info("    SCAFFOLD: K500 close wired but not executed (HL auth required at live activation)")
    return True


def _detect_k507_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K514 Phase 4: Detect K507 paired positions (SEI long + BTC short, or reverse).

    K507 SEI-BTC = 2 legs split across HL + Bybit:
      - One leg on HL (SEI leg)
      - One leg on Bybit (BTC leg)
    Sequential close: short leg first (avoid uncovered short), then long leg.
    HL portion closes on HL; Bybit portion closes on Bybit.

    A K507 pair is identified by:
      - One long leg: SEI or BTC
      - One short leg: the other of SEI/BTC
      - HL+Bybit split: SEI on HL, BTC on Bybit (or reverse based on direction)

    Note: SEI is the native token of Sei Network (parallelized EVM + Cosmos SDK).
    K507 is the Cosmos 3rd ACCEPT. OOS Sharpe 48.10 (family rank #2).
    HL+Bybit split: 1.5% HL + 1.5% Bybit → HL 63.5% (1.5pp headroom vs 65% cap).
    SEI EVM-compat creates orthogonal FR dynamics vs ATOM IBC/staking + INJ DeFi-perp.
    """
    K507_SYMBOLS = {"SEI", "BTC"}
    sei_btc = [p for p in positions if p.get("coin", "").upper() in K507_SYMBOLS]
    if len(sei_btc) < 2:
        return None

    longs  = [p for p in sei_btc if p.get("side") == "long"]
    shorts = [p for p in sei_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K507_SYMBOLS or short_sym not in K507_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    # Determine venue split: SEI on HL, BTC on Bybit (or reverse)
    long_venue  = "HL"    if long_sym == "SEI"  else "Bybit"
    short_venue = "HL"    if short_sym == "SEI" else "Bybit"

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "split_protocol":  "HL_1.5PCT_BYBIT_1.5PCT",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            (
            f"K507 SEI-BTC paired position — cover {short_sym}@{short_venue} first, "
            f"then sell {long_sym}@{long_venue}. "
            "HL+Bybit split: SEI leg on HL, BTC leg on Bybit (K514)."
        ),
    }


def close_k507_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K514 Phase 4: Close K507 SEI-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.
    HL portion closes on HL; Bybit portion closes on Bybit.

    K507 HL+Bybit split:
      SEI leg → HL (1.5% of AUM)
      BTC leg → Bybit (1.5% of AUM)
    Close: cover short (SEI@HL or BTC@Bybit) first → sell long second.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k507_detail = plan.get("k507_pair_detail")

    if not k507_detail or not k507_detail.get("detected"):
        logger.info("  [K507] No K507 SEI-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym   = k507_detail["short_symbol"]
    long_sym    = k507_detail["long_symbol"]
    short_val   = k507_detail.get("short_value_usd", 0.0)
    long_val    = k507_detail.get("long_value_usd", 0.0)
    short_venue = k507_detail.get("short_venue", "Bybit")
    long_venue  = k507_detail.get("long_venue", "HL")

    logger.info(f"  [K507] SEI-BTC paired close — {k507_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  "
                f"({short_venue} IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  "
                f"({long_venue} IOC reduce-only)")
    logger.info(f"    Split: HL 1.5% + Bybit 1.5% — close each leg on its venue")

    if dry_run:
        logger.info("    [DRY-RUN] K507 SEI-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on respective venues (sequential)
    # Step 1: cover short on its venue (HL or Bybit)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ {short_venue}")
    # Step 2: sell long on its venue (HL or Bybit)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ {long_venue}")
    logger.info("    SCAFFOLD: K507 close wired but not executed "
                "(HL+Bybit auth required at live activation)")
    return True


def _detect_k512_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K520 Phase 4: Detect K512 paired positions (APT long + BTC short, or reverse).

    K512 APT-BTC = 2 legs split across HL + Bybit:
      - One leg on HL (APT leg)
      - One leg on Bybit (BTC leg)
    Sequential close: short leg first (avoid uncovered short), then long leg.
    HL portion closes on HL; Bybit portion closes on Bybit.

    A K512 pair is identified by:
      - One long leg: APT or BTC
      - One short leg: the other of APT/BTC
      - HL+Bybit split: APT on HL, BTC on Bybit (or reverse based on direction)

    Note: APT is the native token of Aptos (Move-VM, Block-STM parallel execution).
    K512 is the Move-VM 5th ecosystem ACCEPT. OOS Sharpe 51.10 (family rank #1).
    HL+Bybit split: 1% HL + 1% Bybit → HL 64% (1pp headroom vs 65% cap).
    Move-VM Block-STM + Move resource model creates orthogonal FR dynamics vs all other VMs.
    OU half-life 0.27d: APT-BTC differential mean-reverts extremely quickly.
    """
    K512_SYMBOLS = {"APT", "BTC"}
    apt_btc = [p for p in positions if p.get("coin", "").upper() in K512_SYMBOLS]
    if len(apt_btc) < 2:
        return None

    longs  = [p for p in apt_btc if p.get("side") == "long"]
    shorts = [p for p in apt_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K512_SYMBOLS or short_sym not in K512_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    # Determine venue split: APT on HL, BTC on Bybit (or reverse)
    long_venue  = "HL"    if long_sym == "APT"  else "Bybit"
    short_venue = "HL"    if short_sym == "APT" else "Bybit"

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "split_protocol":  "HL_1PCT_BYBIT_1PCT",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            (
            f"K512 APT-BTC paired position — cover {short_sym}@{short_venue} first, "
            f"then sell {long_sym}@{long_venue}. "
            "HL+Bybit split: APT leg on HL (1%), BTC leg on Bybit (1%) (K520)."
        ),
    }


def close_k512_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K520 Phase 4: Close K512 APT-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.
    HL portion closes on HL; Bybit portion closes on Bybit.

    K512 HL+Bybit split:
      APT leg → HL (1% of AUM)
      BTC leg → Bybit (1% of AUM)
    Close: cover short (APT@HL or BTC@Bybit) first → sell long second.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k512_detail = plan.get("k512_pair_detail")

    if not k512_detail or not k512_detail.get("detected"):
        logger.info("  [K512] No K512 APT-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym   = k512_detail["short_symbol"]
    long_sym    = k512_detail["long_symbol"]
    short_val   = k512_detail.get("short_value_usd", 0.0)
    long_val    = k512_detail.get("long_value_usd", 0.0)
    short_venue = k512_detail.get("short_venue", "Bybit")
    long_venue  = k512_detail.get("long_venue", "HL")

    logger.info(f"  [K512] APT-BTC paired close — {k512_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  "
                f"({short_venue} IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  "
                f"({long_venue} IOC reduce-only)")
    logger.info(f"    Split: HL 1% + Bybit 1% — close each leg on its venue")

    if dry_run:
        logger.info("    [DRY-RUN] K512 APT-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on respective venues (sequential)
    # Step 1: cover short on its venue (HL or Bybit)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ {short_venue}")
    # Step 2: sell long on its venue (HL or Bybit)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ {long_venue}")
    logger.info("    SCAFFOLD: K512 close wired but not executed "
                "(HL+Bybit auth required at live activation)")
    return True


def _detect_k587_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K678 Phase 4: Detect K587 paired positions (ICP long + BTC short, or reverse).

    K587 ICP-BTC = 2 legs split across HL + Bybit:
      - ICP leg on HL (0.5% of AUM, 4x leverage — HL maxLev=5x for ICP)
      - BTC leg on Bybit (0.5% of AUM, 4x leverage)
    Sequential close: short leg first (avoid uncovered short), then long leg.
    HL portion (ICP) closes on HL; Bybit portion (BTC) closes on Bybit.

    A K587 pair is identified by:
      - One long leg: ICP or BTC
      - One short leg: the other of ICP/BTC
      - HL+Bybit split: ICP on HL, BTC on Bybit (or reverse based on direction)

    Note: ICP is Internet Computer Protocol (Dfinity) — decentralised cloud compute.
    K587 is the Compute/Cloud cluster ACCEPT CONDITIONAL. OOS Sharpe 12.53.
    HL+Bybit split: 0.5% HL + 0.5% Bybit (high vol — ICP vol 8.40x vs BTC).
    HL maxLev ICP = 5x; strategy uses 4x (margin of safety below HL cap).
    """
    K587_SYMBOLS = {"ICP", "BTC"}
    icp_btc = [p for p in positions if p.get("coin", "").upper() in K587_SYMBOLS]
    if len(icp_btc) < 2:
        return None

    longs  = [p for p in icp_btc if p.get("side") == "long"]
    shorts = [p for p in icp_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K587_SYMBOLS or short_sym not in K587_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    # Determine venue split: ICP on HL, BTC on Bybit (or reverse)
    long_venue  = "HL"    if long_sym == "ICP"  else "Bybit"
    short_venue = "HL"    if short_sym == "ICP" else "Bybit"

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "split_protocol":  "HL_05PCT_BYBIT_05PCT",
        "close_protocol":  "short_leg_first_then_long_leg",
        "hl_max_lev_note": "ICP HL maxLev=5x; strategy uses 4x (margin of safety)",
        "note":            (
            f"K587 ICP-BTC paired position — cover {short_sym}@{short_venue} first, "
            f"then sell {long_sym}@{long_venue}. "
            "HL+Bybit split: ICP leg on HL (0.5%), BTC leg on Bybit (0.5%) (K678). "
            "ICP vol 8.40x vs BTC = highest in BTC-base family."
        ),
    }


def close_k587_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K678 Phase 4: Close K587 ICP-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.
    ICP leg closes on HL; BTC leg closes on Bybit.

    K587 HL+Bybit split:
      ICP leg → HL (0.5% of AUM, HL maxLev=5x, using 4x)
      BTC leg → Bybit (0.5% of AUM)
    Close: cover short (ICP@HL or BTC@Bybit) first → sell long second.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k587_detail = plan.get("k587_pair_detail")

    if not k587_detail or not k587_detail.get("detected"):
        logger.info("  [K587] No K587 ICP-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym   = k587_detail["short_symbol"]
    long_sym    = k587_detail["long_symbol"]
    short_val   = k587_detail.get("short_value_usd", 0.0)
    long_val    = k587_detail.get("long_value_usd", 0.0)
    short_venue = k587_detail.get("short_venue", "HL")
    long_venue  = k587_detail.get("long_venue", "Bybit")

    logger.info(f"  [K587] ICP-BTC paired close — {k587_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  "
                f"({short_venue} IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  "
                f"({long_venue} IOC reduce-only)")
    logger.info(f"    Split: HL 0.5% (ICP) + Bybit 0.5% (BTC) — close each leg on its venue")
    logger.info(f"    HL maxLev note: ICP HL maxLev=5x; strategy at 4x (margin of safety)")

    if dry_run:
        logger.info("    [DRY-RUN] K587 ICP-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on respective venues (sequential)
    # Step 1: cover short on its venue (HL or Bybit)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ {short_venue}")
    # Step 2: sell long on its venue (HL or Bybit)
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ {long_venue}")
    logger.info("    SCAFFOLD: K587 close wired but not executed "
                "(HL+Bybit auth required at live activation)")
    return True


def _detect_k541_position(positions: List[Dict]) -> Optional[Dict]:
    """
    K550 Phase 4: Detect K541 stablecoin supply growth signal positions.

    K541 = LONG BTC + LONG ETH + LONG SOL on HL (directional, not paired).
    Signal: 7d stablecoin supply z-score 2nd derivative (acceleration) > 0.5.
    Universe: BTC, ETH, SOL (3 long legs, equal weight, HL-only).
    Close protocol: IOC reduce-only BTC → ETH → SOL (all longs, HL-only).

    Note: K541 is NOT a paired trade — all 3 legs are LONG.
    Disambiguation from K495 DEX-CEX: K541 uses z-score acceleration signal
    vs K495 DEX vol ratio signal. Both target BTC+ETH+SOL LONG but via different
    independent signals. If both are open simultaneously, both are closed.

    K541 ACCEPT CONDITIONAL (K550 scaffold):
      OOS Sharpe 1.498, $294K/yr @$10M, 7-axis Sh 6.872 +0.165 lift
      G5 max corr 0.074 — highly orthogonal to FR-carry family
      90d paper-trade gate (longer than 60d for lower Sharpe)
      DefiLlama free public API (stablecoins.llama.fi)
    """
    K541_SYMBOLS = {"BTC", "ETH", "SOL"}
    k541_longs = [p for p in positions
                  if p.get("coin", "").upper() in K541_SYMBOLS
                  and p.get("side") == "long"]

    if len(k541_longs) < 2:
        return None  # need at least 2 of 3 symbols long

    btc_long = next((p for p in k541_longs if p["coin"].upper() == "BTC"), None)
    eth_long = next((p for p in k541_longs if p["coin"].upper() == "ETH"), None)
    sol_long = next((p for p in k541_longs if p["coin"].upper() == "SOL"), None)

    detected_legs = [p for p in [btc_long, eth_long, sol_long] if p is not None]
    total_val = sum(p["value_usd"] for p in detected_legs)

    return {
        "detected":           True,
        "strategy":           "K541 Stablecoin Supply Growth (V3 acceleration)",
        "signal":             "7d USDT+USDC supply z-score 2nd derivative > 0.5",
        "universe":           ["BTC", "ETH", "SOL"],
        "legs_detected":      len(detected_legs),
        "btc_long":           {"coin": "BTC", "value_usd": btc_long["value_usd"], "size": btc_long["size"]} if btc_long else None,
        "eth_long":           {"coin": "ETH", "value_usd": eth_long["value_usd"], "size": eth_long["size"]} if eth_long else None,
        "sol_long":           {"coin": "SOL", "value_usd": sol_long["value_usd"], "size": sol_long["size"]} if sol_long else None,
        "total_notional":     total_val,
        "venue":              "HL",
        "close_protocol":     "IOC_SEQUENTIAL: LONG BTC → ETH → SOL (all reduce-only on HL)",
        "note":               "K541 directional LONG (not paired) — all 3 legs on HL, close all simultaneously on emergency",
    }


def close_k541_position(
    plan:    dict,
    logger:  "logging.Logger",
    dry_run: bool = False,
) -> bool:
    """
    K550 Phase 4: Close K541 stablecoin supply growth signal positions.

    Close protocol:
      1. IOC reduce-only BTC long on HL (largest notional first)
      2. IOC reduce-only ETH long on HL
      3. IOC reduce-only SOL long on HL
    All legs on HL (directional signal, HL-only).

    Returns True if close completed (or no position detected).
    """
    k541_detail = plan.get("k541_detail")

    if not k541_detail or not k541_detail.get("detected"):
        logger.info("  K541: no stablecoin supply signal position detected — skipping.")
        return True

    total_val     = k541_detail.get("total_notional", 0.0)
    legs_detected = k541_detail.get("legs_detected", 0)

    logger.info(f"  [K541] Stablecoin supply signal close — {legs_detected} legs, ${total_val:,.0f} total notional (HL-only)")
    logger.info(f"  [K541] Close protocol: IOC sequential BTC → ETH → SOL (all LONG reduce-only)")

    for sym in ["BTC", "ETH", "SOL"]:
        leg_key = f"{sym.lower()}_long"
        leg = k541_detail.get(leg_key)
        if not leg:
            continue
        val = leg.get("value_usd", 0.0)
        if dry_run:
            logger.info(f"    [K541] DRY-RUN: SELL {sym}@HL ${val:,.0f} (IOC reduce-only)")
        else:
            logger.info(f"    [K541] SCAFFOLD: IOC reduce LONG {sym}@HL ${val:,.0f} (K541 stablecoin signal)")
            logger.info(f"    SCAFFOLD: K541 close wired but not executed "
                        "(HL auth required at live activation)")
    return True


def _detect_k521_position(positions: List[Dict]) -> Optional[Dict]:
    """
    K565 Phase 4: Detect K521 Options 25d Skew signal positions.

    K521 = LONG BTC on HL (directional, not paired).
    Signal: Deribit DVOL z-score + ETH-BTC 25d skew spread composite > 1.0 (V4).
    Universe: BTC primary (1 long leg, HL-only, 3% sleeve).
    Close protocol: IOC reduce-only LONG BTC (single leg, HL-only).

    Note: K521 is NOT a paired trade — single BTC LONG on DVOL spike.
    Disambiguation from K495/K541: K521 targets BTC only (not BTC+ETH+SOL).
    K521 CONDITIONAL ACCEPT (K565 scaffold):
      OOS Sharpe 1.019, $494K/yr @$10M, 5-axis Sh 6.386 +0.082 lift
      Max corr 0.199 — orthogonal confirmed (institutional axis distinct from retail F&G)
      90d paper-trade gate (G3 DSR CONDITIONAL)
      Deribit free public API (DVOL index + options 25d skew, no auth)
    """
    K521_SYMBOLS = {"BTC"}
    k521_longs = [p for p in positions
                  if p.get("coin", "").upper() in K521_SYMBOLS
                  and p.get("side") == "long"]

    if not k521_longs:
        return None

    btc_long  = k521_longs[0]
    total_val = btc_long.get("value_usd", 0.0)

    return {
        "detected":       True,
        "strategy":       "K521 Options 25d Skew (V4 DVOL + skew composite)",
        "signal":         "Deribit DVOL z-score (60%) + ETH-BTC 25d skew spread z-score (40%) composite > 1.0",
        "universe":       ["BTC"],
        "btc_long":       {
            "coin":      "BTC",
            "value_usd": btc_long.get("value_usd", 0.0),
            "size":      btc_long.get("size", 0.0),
        },
        "total_notional": total_val,
        "venue":          "HL",
        "close_protocol": "IOC_SINGLE: LONG BTC reduce-only on HL",
        "note":           (
            "K521 directional LONG BTC (not paired) — single leg on HL. "
            "Close IOC reduce-only. Mean-reversion on DVOL spike. "
            "Deribit free API: DVOL index + 25d skew (no auth)."
        ),
    }


def close_k521_position(
    plan:    dict,
    logger:  "logging.Logger",
    dry_run: bool = False,
) -> bool:
    """
    K565 Phase 4: Close K521 Options 25d Skew signal position (LONG BTC).

    Close protocol:
      1. Detect K521 BTC LONG from plan
      2. IOC reduce-only LONG BTC on HL
    Single leg (BTC only, HL-only, 3% sleeve, 2x leverage).

    Returns True if close completed (or no position detected).
    """
    k521_detail = plan.get("k521_detail")

    if not k521_detail or not k521_detail.get("detected"):
        logger.info("  K521: no options skew signal position detected — skipping.")
        return True

    total_val = k521_detail.get("total_notional", 0.0)
    btc_leg   = k521_detail.get("btc_long", {})
    btc_val   = btc_leg.get("value_usd", total_val)

    logger.info(f"  [K521] Options skew signal close — LONG BTC ${btc_val:,.0f} (HL-only)")
    logger.info(f"  [K521] Close protocol: IOC reduce-only LONG BTC @ HL (single leg)")

    if dry_run:
        logger.info(f"    [K521] DRY-RUN: SELL BTC@HL ${btc_val:,.0f} (IOC reduce-only)")
    else:
        logger.info(f"    [K521] SCAFFOLD: IOC reduce LONG BTC@HL ${btc_val:,.0f} (K521 options skew signal)")
        logger.info("    SCAFFOLD: K521 close wired but not executed "
                    "(HL auth required at live activation)")
    return True


def _detect_k628_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K637 Phase 4: Detect K628 JTO-BTC orthogonalized paired positions.

    K628 JTO-BTC = 2 legs, BOTH on Bybit (Bybit primary — JTO maxLev high):
      - JTO leg on Bybit
      - BTC leg on Bybit
      - No HL exposure (Bybit-only; HL concentration unchanged at 65%)
    Sequential close: short leg first, then long leg (K439 close pattern).

    A K628 pair is identified by:
      - One long leg: JTO or BTC
      - One short leg: the other of JTO/BTC
      - Both legs on Bybit (Bybit-only strategy, K637 scaffold)

    Note: JTO = Jito Network (jitoSOL LST + MEV block engine, Solana)
    K628 ACCEPT CONDITIONAL. OOS Sharpe 18.30 (residual, K628 orthog).
    Orthogonalization: residual = JTO_diff − 0.164×SEI_diff − 0.302×DOGE_diff
    β_SEI=0.164, β_DOGE=0.302 (K628 OLS, IS R²=0.075).
    Bybit-only: HL concentration UNCHANGED at 65%.
    Profit @$10M 4x: 2% sleeve=$7.14M/yr | 3% sleeve=$10.7M/yr | best case $17.85M/yr.
    60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<20%.
    """
    K628_SYMBOLS = {"JTO", "BTC"}
    jto_btc = [p for p in positions if p.get("coin", "").upper() in K628_SYMBOLS]
    if len(jto_btc) < 2:
        return None

    longs  = [p for p in jto_btc if p.get("side") == "long"]
    shorts = [p for p in jto_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K628_SYMBOLS or short_sym not in K628_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    # Both legs on Bybit (Bybit primary spec)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "split_protocol":  "BYBIT_PRIMARY_2PCT",
        "close_protocol":  "short_leg_first_then_long_leg",
        "orthog_note":     "residual = JTO_diff - 0.164*SEI_diff - 0.302*DOGE_diff (K628 OLS)",
        "note":            (
            f"K628 JTO-BTC orthogonalized paired position — cover {short_sym}@{short_venue} first, "
            f"then sell {long_sym}@{long_venue}. "
            "Bybit-only: both JTO and BTC legs on Bybit (2% sleeve, K637). "
            "HL concentration UNCHANGED at 65% (Bybit-only strategy). "
            "Close via Bybit API IOC reduce-only (NOT HL API)."
        ),
    }


def close_k628_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K637 Phase 4: Close K628 JTO-BTC orthogonalized paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.
    Both legs close on Bybit (Bybit primary — NOT HL API).

    K628 JTO Bybit-only:
      - JTO and BTC both on Bybit (JTO maxLev high on Bybit)
      - Close via Bybit API IOC reduce-only (not HL exchange API)
      - HL concentration UNCHANGED — no HL action needed for K628

    Note: This function closes K628 Bybit positions. In a full HL emergency,
    K628 positions are UNAFFECTED by HL shutdown (Bybit-only). However,
    if closing all positions across all venues, Bybit close-all handles K628.

    Returns True on success (or dry-run), False on error.
    """
    k628_detail = plan.get("k628_pair_detail")

    if not k628_detail or not k628_detail.get("detected"):
        logger.info("  [K628] No K628 JTO-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym  = k628_detail["short_symbol"]
    long_sym   = k628_detail["long_symbol"]
    short_val  = k628_detail.get("short_value_usd", 0.0)
    long_val   = k628_detail.get("long_value_usd", 0.0)
    short_venue = k628_detail.get("short_venue", "Bybit")
    long_venue  = k628_detail.get("long_venue", "Bybit")

    logger.info(f"  [K628] JTO-BTC orthog paired close — {k628_detail['state']}")
    logger.info(f"  [K628] Orthog: residual = JTO_diff − 0.164×SEI_diff − 0.302×DOGE_diff (K628 OLS)")
    logger.info(f"  [K628] Venue: Bybit-only (HL concentration UNCHANGED at 65%)")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  ({short_venue} IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  ({long_venue} IOC reduce-only)")

    if dry_run:
        logger.info("    [DRY-RUN] K628 JTO-BTC orthog close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on Bybit (sequential)
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ {short_venue}")
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ {long_venue}")
    logger.info("    SCAFFOLD: K628 close wired but not executed "
                "(Bybit auth required at live activation). "
                "Note: HL is NOT affected — K628 is Bybit-only.")
    return True


def _detect_k507_tia_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K524 Phase 4: Detect K507 TIA paired positions (TIA long + BTC short, or reverse).

    K507 TIA-BTC = 2 legs, both on HL (HL-only spec):
      - TIA leg on HL
      - BTC leg on HL
      - No Bybit split (smaller 1% weight, HL-only per K524 spec)
    Sequential close: short leg first (avoid uncovered short), then long leg.
    Both legs close on HL (IOC reduce-only).

    A K507 TIA pair is identified by:
      - One long leg: TIA or BTC
      - One short leg: the other of TIA/BTC
      - Both legs on HL (HL-only)

    Note: TIA is the native token of Celestia (modular data availability layer).
    K507 TIA ACCEPT. OOS Sharpe 14.44 (family rank #6).
    Celestia DA: rollup adoption + blob fee market drives FR dynamics orthogonal to BTC.
    G5d vs ATOM: 0.05 = LOWEST in family (TIA modular DA distinct from Cosmos hub).
    HL concentration: 64% post-K512 + 1% TIA = 65% (exactly at cap).
    """
    K507_TIA_SYMBOLS = {"TIA", "BTC"}
    tia_btc = [p for p in positions if p.get("coin", "").upper() in K507_TIA_SYMBOLS]
    if len(tia_btc) < 2:
        return None

    longs  = [p for p in tia_btc if p.get("side") == "long"]
    shorts = [p for p in tia_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    if long_sym not in K507_TIA_SYMBOLS or short_sym not in K507_TIA_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    # Both legs on HL (HL-only spec)
    long_venue  = "HL"
    short_venue = "HL"

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "split_protocol":  "HL_ONLY_1PCT",
        "close_protocol":  "short_leg_first_then_long_leg",
        "note":            (
            f"K507 TIA-BTC paired position — cover {short_sym}@{short_venue} first, "
            f"then sell {long_sym}@{long_venue}. "
            "HL-only: both TIA and BTC legs on HL (1% sleeve, K524)."
        ),
    }


def close_k507_tia_paired_positions(
    plan:    Dict,
    logger:  "logging.Logger",
    dry_run: bool = True,
) -> bool:
    """
    K524 Phase 4: Close K507 TIA-BTC paired positions.
    Sequential: short leg first (avoid uncovered short), then long leg.
    Both legs close on HL (HL-only spec — no Bybit split).

    K507 TIA HL-only:
      TIA leg → HL (1% of AUM, full sleeve on HL)
      BTC leg → HL (both legs on same venue)
    Close: cover short (TIA@HL or BTC@HL) first → sell long second.

    Args:
      plan:    exit plan dict (from plan_exit())
      logger:  logger instance
      dry_run: True = paper-trade simulation

    Returns True on success (or dry-run), False on error.
    """
    k507_tia_detail = plan.get("k507_tia_pair_detail")

    if not k507_tia_detail or not k507_tia_detail.get("detected"):
        logger.info("  [K507-TIA] No K507 TIA-BTC paired position detected (NEUTRAL or 60d paper-trade).")
        return True

    short_sym   = k507_tia_detail["short_symbol"]
    long_sym    = k507_tia_detail["long_symbol"]
    short_val   = k507_tia_detail.get("short_value_usd", 0.0)
    long_val    = k507_tia_detail.get("long_value_usd", 0.0)
    short_venue = k507_tia_detail.get("short_venue", "HL")
    long_venue  = k507_tia_detail.get("long_venue", "HL")

    logger.info(f"  [K507-TIA] TIA-BTC paired close — {k507_tia_detail['state']}")
    logger.info(f"    Step 1 (SHORT first): BUY-COVER {short_sym} ${short_val:,.0f}  "
                f"({short_venue} IOC reduce-only)")
    logger.info(f"    Step 2 (LONG second): SELL      {long_sym} ${long_val:,.0f}  "
                f"({long_venue} IOC reduce-only)")
    logger.info(f"    Venue: HL-only (both legs on HL, 1% sleeve)")

    if dry_run:
        logger.info("    [DRY-RUN] K507 TIA-BTC close simulated — no actual orders submitted")
        return True

    # LIVE scaffold: IOC close on HL (sequential)
    # Step 1: cover short on HL
    logger.info(f"    SCAFFOLD: IOC reduce {short_sym} (cover short) @ {short_venue}")
    # Step 2: sell long on HL
    logger.info(f"    SCAFFOLD: IOC reduce {long_sym} (sell long) @ {long_venue}")
    logger.info("    SCAFFOLD: K507 TIA close wired but not executed "
                "(HL auth required at live activation)")
    return True


def _detect_k449_paired_positions(positions: List[Dict]) -> Optional[Dict]:
    """
    K450 Phase 11: Detect K449 paired positions (ETH long + BTC short, or reverse).

    Returns a dict describing the paired position if found, or None.
    Used to ensure both legs are closed together (avoid uncovered short).

    A K449 pair is identified by:
      - One long leg: ETH or BTC
      - One short leg: the other of ETH/BTC
    """
    K449_SYMBOLS = {"ETH", "BTC"}
    eth_btc = [p for p in positions if p.get("coin", "").upper() in K449_SYMBOLS]
    if len(eth_btc) < 2:
        return None

    # Check if we have one long and one short in ETH/BTC
    longs  = [p for p in eth_btc if p.get("side") == "long"]
    shorts = [p for p in eth_btc if p.get("side") == "short"]

    if not (longs and shorts):
        return None

    long_pos  = longs[0]
    short_pos = shorts[0]
    long_sym  = long_pos["coin"].upper()
    short_sym = short_pos["coin"].upper()

    # Both must be in K449_SYMBOLS and be different symbols
    if long_sym not in K449_SYMBOLS or short_sym not in K449_SYMBOLS:
        return None
    if long_sym == short_sym:
        return None

    return {
        "detected":        True,
        "long_symbol":     long_sym,
        "short_symbol":    short_sym,
        "long_value_usd":  long_pos.get("value_usd", 0.0),
        "short_value_usd": short_pos.get("value_usd", 0.0),
        "long_size":       long_pos.get("size", 0.0),
        "short_size":      short_pos.get("size", 0.0),
        "state":           f"LONG_{long_sym}_SHORT_{short_sym}",
        "note":            "K449 paired position — must close both legs simultaneously to avoid uncovered short",
    }


def _detect_k495_position(positions: List[Dict]) -> Optional[Dict]:
    """
    K502 Phase 4: Detect K495 DEX-CEX flow divergence positions (LONG BTC+ETH+SOL).

    K495 is bear-conditional LONG-only (no short legs):
      - LONG BTC (HL)
      - LONG ETH (HL)
      - LONG SOL (HL)

    Identification: 2+ of BTC/ETH/SOL are LONG simultaneously (not short).
    Note: BTC/ETH may appear in other strategies (K449/K476/K484 short legs).
    K495 detection uses LONG-only criterion for all 3 symbols together.
    If the position set has LONG BTC + LONG ETH + LONG SOL simultaneously,
    this is almost certainly a K495 position (no other strategy holds all 3 LONG).

    Returns dict describing the K495 position, or None if not found.
    """
    K495_SYMBOLS = {"BTC", "ETH", "SOL"}
    k495_longs   = [p for p in positions
                    if p.get("coin", "").upper() in K495_SYMBOLS
                    and p.get("side") == "long"]

    if len(k495_longs) < 2:
        return None

    # Require at least 2 of the 3 assets to be long (partial position is valid)
    long_syms = {p["coin"].upper() for p in k495_longs}
    if not long_syms.intersection(K495_SYMBOLS):
        return None

    total_value = sum(float(p.get("value_usd", 0.0)) for p in k495_longs)
    legs = [
        {
            "symbol":    p["coin"].upper(),
            "side":      "long",
            "size":      p.get("size", 0.0),
            "value_usd": p.get("value_usd", 0.0),
        }
        for p in k495_longs
    ]

    return {
        "detected":       True,
        "assets":         sorted(list(long_syms)),
        "legs":           legs,
        "total_value_usd": round(total_value, 2),
        "state":          "LONG_" + "_".join(sorted(long_syms)),
        "close_protocol": "IOC reduce-only BTC → ETH → SOL (largest notional first)",
        "note":           "K495 DEX-CEX flow divergence position — bear-conditional LONG BTC+ETH+SOL; close all 3 legs IOC reduce-only",
    }


def close_k495_position(
    logger:  "logging.Logger",
    plan:    Dict,
    dry_run: bool = True,
) -> None:
    """
    K502 Phase 4: Close K495 DEX-CEX flow divergence positions (LONG BTC+ETH+SOL).

    Close protocol:
      Step 1: IOC reduce-only SELL BTC   (largest notional)
      Step 2: IOC reduce-only SELL ETH
      Step 3: IOC reduce-only SELL SOL   (smallest of the three)

    K495 is LONG-only: no short-leg risk. Sequential IOC is sufficient.
    Bear-regime gate flip (BULL) triggers auto-close in k495_dex_cex_flow_run.py
    daily cron — this function handles emergency forced close.

    Args:
      logger:  logging.Logger instance
      plan:    exit plan dict (from plan_exit())
      dry_run: True = paper-trade simulation
    """
    k495_detail = plan.get("k495_detail")

    if not k495_detail or not k495_detail.get("detected"):
        logger.info("  [K495] No K495 DEX-CEX flow position detected (NEUTRAL or 60d paper-trade).")
        return

    assets     = k495_detail.get("assets", [])
    total_val  = k495_detail.get("total_value_usd", 0.0)

    logger.info(f"  [K495] DEX-CEX flow divergence close — {k495_detail['state']}")
    logger.info(f"    Assets: {', '.join(assets)}  total=${total_val:,.0f}")
    logger.info(f"    Protocol: {k495_detail['close_protocol']}")

    if dry_run:
        logger.info("    [DRY-RUN] K495 BTC+ETH+SOL close simulated — no actual orders submitted")
        return

    # LIVE scaffold: submit IOC reduce-only per asset (BTC → ETH → SOL order)
    close_order = ["BTC", "ETH", "SOL"]
    for sym in close_order:
        leg = next((l for l in k495_detail.get("legs", []) if l["symbol"] == sym), None)
        if leg:
            logger.info(f"    SCAFFOLD: IOC reduce-only SELL {sym} ${leg['value_usd']:,.0f} (HL)")
    logger.info("    SCAFFOLD: K495 close wired but not executed (HL auth required at live activation)")


def plan_exit(positions: List[Dict], orders: List[Dict]) -> Dict:
    """
    Produce a structured exit plan:
      cancel_orders:    [(coin, oid), ...]     — cancel ALL open orders first
      close_positions:  [{coin, size, side_to_close, value_usd}, ...] — market close
      total_notional:   float (USD)
      estimated_time:   int (seconds)
      slippage_estimate_usd: float

    K450 Phase 11: Detects K449 paired positions (ETH/BTC) and marks them
    for simultaneous closure to avoid creating an uncovered short exposure.
    Short leg is closed first, then long (safer sequencing).
    """
    cancel_list = [(o["coin"], o["oid"]) for o in orders]

    # K450: detect K449 paired positions (ETH/BTC)
    k449_pair = _detect_k449_paired_positions(positions)
    k449_coins = set()
    if k449_pair:
        k449_coins = {k449_pair["long_symbol"], k449_pair["short_symbol"]}

    # K478: detect K476 paired positions (SOL/BTC — HL-only)
    k476_pair = _detect_k476_paired_positions(positions)
    k476_coins: set = set()
    if k476_pair:
        k476_coins = {k476_pair["long_symbol"], k476_pair["short_symbol"]}

    # K489: detect K484 paired positions (AVAX/BTC — HL-only)
    k484_pair = _detect_k484_paired_positions(positions)
    k484_coins: set = set()
    if k484_pair:
        k484_coins = {k484_pair["long_symbol"], k484_pair["short_symbol"]}

    # K499: detect K493 paired positions (ATOM/BTC — HL-only)
    k493_pair = _detect_k493_paired_positions(positions)
    k493_coins: set = set()
    if k493_pair:
        k493_coins = {k493_pair["long_symbol"], k493_pair["short_symbol"]}

    # K506: detect K500 paired positions (INJ/BTC — HL-only)
    k500_pair = _detect_k500_paired_positions(positions)
    k500_coins: set = set()
    if k500_pair:
        k500_coins = {k500_pair["long_symbol"], k500_pair["short_symbol"]}

    # K514: detect K507 paired positions (SEI/BTC — HL+Bybit split)
    k507_pair = _detect_k507_paired_positions(positions)
    k507_coins: set = set()
    if k507_pair:
        k507_coins = {k507_pair["long_symbol"], k507_pair["short_symbol"]}

    # K520: detect K512 paired positions (APT/BTC — HL+Bybit split)
    k512_pair = _detect_k512_paired_positions(positions)
    k512_coins: set = set()
    if k512_pair:
        k512_coins = {k512_pair["long_symbol"], k512_pair["short_symbol"]}

    # K524: detect K507 TIA paired positions (TIA/BTC — HL-only)
    k507_tia_pair = _detect_k507_tia_paired_positions(positions)
    k507_tia_coins: set = set()
    if k507_tia_pair:
        k507_tia_coins = {k507_tia_pair["long_symbol"], k507_tia_pair["short_symbol"]}

    # K637: detect K628 JTO-BTC orthog paired positions (JTO/BTC — Bybit-only)
    # Note: K628 is Bybit-only — HL positions are NOT affected; HL concentration stays 65%
    k628_pair = _detect_k628_paired_positions(positions)
    k628_coins: set = set()
    if k628_pair:
        k628_coins = {k628_pair["long_symbol"], k628_pair["short_symbol"]}

    # K550: detect K541 stablecoin supply growth signal positions (LONG BTC+ETH+SOL)
    k541_pos = _detect_k541_position(positions)
    k541_coins: set = set()
    if k541_pos:
        k541_coins = set(k541_pos.get("universe", []))

    # K565: detect K521 options 25d skew signal positions (LONG BTC, HL-only)
    k521_pos = _detect_k521_position(positions)
    k521_coins: set = set()
    if k521_pos:
        k521_coins = set(k521_pos.get("universe", []))

    # K502: detect K495 DEX-CEX flow divergence positions (LONG BTC+ETH+SOL)
    k495_pos = _detect_k495_position(positions)
    k495_coins: set = set()
    if k495_pos:
        k495_coins = set(k495_pos.get("assets", []))

    # K459: detect K457 basket positions (BTC/ETH/SOL)
    k457_basket = _detect_k457_basket_positions(positions)
    k457_coins: set = set()
    if k457_basket:
        k457_coins = {"BTC", "ETH", "SOL"}

    close_list = []
    total_notional = 0.0

    # K459 basket positions: close ALL short legs first, then long legs
    if k457_basket:
        close_order = 0
        # Phase 1: close all shorts (buy-to-cover)
        for leg in k457_basket.get("short_legs", []):
            coin = leg["coin"]
            short_pos = next((p for p in positions if p["coin"].upper() == coin.upper()
                              and p["side"] == "short"), None)
            if short_pos:
                close_order += 1
                close_list.append({
                    "coin":             short_pos["coin"],
                    "size":             short_pos["size"],
                    "side_to_close":    "buy",   # covering short
                    "value_usd":        short_pos["value_usd"],
                    "current_side":     "short",
                    "k457_basket":      True,
                    "k457_close_order": close_order,
                    "close_phase":      "SHORTS_FIRST",
                    "note":             f"K457 basket short leg {coin} — cover first (avoid uncovered short)",
                })
                total_notional += short_pos["value_usd"]

        # Phase 2: close all longs (sell)
        for leg in k457_basket.get("long_legs", []):
            coin = leg["coin"]
            long_pos = next((p for p in positions if p["coin"].upper() == coin.upper()
                             and p["side"] == "long"), None)
            if long_pos:
                close_order += 1
                close_list.append({
                    "coin":             long_pos["coin"],
                    "size":             long_pos["size"],
                    "side_to_close":    "sell",
                    "value_usd":        long_pos["value_usd"],
                    "current_side":     "long",
                    "k457_basket":      True,
                    "k457_close_order": close_order,
                    "close_phase":      "LONGS_SECOND",
                    "note":             f"K457 basket long leg {coin} — sell second",
                })
                total_notional += long_pos["value_usd"]

    # K449 paired positions: close short first (avoid uncovered short window)
    if k449_pair:
        # Short leg first
        short_coin = k449_pair["short_symbol"]
        short_pos  = next((p for p in positions if p["coin"].upper() == short_coin
                           and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":           short_pos["coin"],
                "size":           short_pos["size"],
                "side_to_close":  "buy",   # covering short
                "value_usd":      short_pos["value_usd"],
                "current_side":   "short",
                "k449_paired":    True,
                "k449_close_order": 1,      # close short first
                "note":           "K449 paired short leg — cover first",
            })
            total_notional += short_pos["value_usd"]

        # Long leg second
        long_coin = k449_pair["long_symbol"]
        long_pos  = next((p for p in positions if p["coin"].upper() == long_coin
                          and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":           long_pos["coin"],
                "size":           long_pos["size"],
                "side_to_close":  "sell",
                "value_usd":      long_pos["value_usd"],
                "current_side":   "long",
                "k449_paired":    True,
                "k449_close_order": 2,      # close long second
                "note":           "K449 paired long leg — sell second",
            })
            total_notional += long_pos["value_usd"]

    # K476 SOL-BTC paired positions: short leg first, then long leg
    if k476_pair:
        # Short leg first (avoid uncovered short)
        short_coin = k476_pair["short_symbol"]
        short_pos  = next((p for p in positions if p["coin"].upper() == short_coin
                           and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":            short_pos["coin"],
                "size":            short_pos["size"],
                "side_to_close":   "buy",   # covering short
                "value_usd":       short_pos["value_usd"],
                "current_side":    "short",
                "k476_paired":     True,
                "k476_close_order": 1,       # close short first
                "venue":           "HL",
                "note":            f"K476 SOL-BTC short leg {short_coin} — cover first (HL-only)",
            })
            total_notional += short_pos["value_usd"]

        # Long leg second
        long_coin = k476_pair["long_symbol"]
        long_pos  = next((p for p in positions if p["coin"].upper() == long_coin
                          and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":            long_pos["coin"],
                "size":            long_pos["size"],
                "side_to_close":   "sell",
                "value_usd":       long_pos["value_usd"],
                "current_side":    "long",
                "k476_paired":     True,
                "k476_close_order": 2,       # close long second
                "venue":           "HL",
                "note":            f"K476 SOL-BTC long leg {long_coin} — sell second (HL-only)",
            })
            total_notional += long_pos["value_usd"]

    # K484 AVAX-BTC paired positions: short leg first, then long leg (K489 Phase 4)
    if k484_pair:
        # Short leg first (avoid uncovered short)
        short_coin = k484_pair["short_symbol"]
        short_pos  = next((p for p in positions if p["coin"].upper() == short_coin
                           and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":             short_pos["coin"],
                "size":             short_pos["size"],
                "side_to_close":    "buy",   # covering short
                "value_usd":        short_pos["value_usd"],
                "current_side":     "short",
                "k484_paired":      True,
                "k484_close_order": 1,        # close short first
                "venue":            "HL",
                "note":             f"K484 AVAX-BTC short leg {short_coin} — cover first (HL-only)",
            })
            total_notional += short_pos["value_usd"]

        # Long leg second
        long_coin = k484_pair["long_symbol"]
        long_pos  = next((p for p in positions if p["coin"].upper() == long_coin
                          and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":             long_pos["coin"],
                "size":             long_pos["size"],
                "side_to_close":    "sell",
                "value_usd":        long_pos["value_usd"],
                "current_side":     "long",
                "k484_paired":      True,
                "k484_close_order": 2,        # close long second
                "venue":            "HL",
                "note":             f"K484 AVAX-BTC long leg {long_coin} — sell second (HL-only)",
            })
            total_notional += long_pos["value_usd"]

    # K493 ATOM-BTC paired positions: short leg first, then long leg (K499 Phase 4)
    if k493_pair:
        # Short leg first (avoid uncovered short)
        short_coin = k493_pair["short_symbol"]
        short_pos  = next((p for p in positions if p["coin"].upper() == short_coin
                           and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":             short_pos["coin"],
                "size":             short_pos["size"],
                "side_to_close":    "buy",   # covering short
                "value_usd":        short_pos["value_usd"],
                "current_side":     "short",
                "k493_paired":      True,
                "k493_close_order": 1,        # close short first
                "venue":            "HL",
                "note":             f"K493 ATOM-BTC short leg {short_coin} — cover first (HL-only)",
            })
            total_notional += short_pos["value_usd"]

        # Long leg second
        long_coin = k493_pair["long_symbol"]
        long_pos  = next((p for p in positions if p["coin"].upper() == long_coin
                          and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":             long_pos["coin"],
                "size":             long_pos["size"],
                "side_to_close":    "sell",
                "value_usd":        long_pos["value_usd"],
                "current_side":     "long",
                "k493_paired":      True,
                "k493_close_order": 2,        # close long second
                "venue":            "HL",
                "note":             f"K493 ATOM-BTC long leg {long_coin} — sell second (HL-only)",
            })
            total_notional += long_pos["value_usd"]

    # K500 INJ-BTC paired positions: short leg first, then long leg (K506 Phase 4)
    if k500_pair:
        # Short leg first (avoid uncovered short)
        short_coin = k500_pair["short_symbol"]
        short_pos  = next((p for p in positions if p["coin"].upper() == short_coin
                           and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":             short_pos["coin"],
                "size":             short_pos["size"],
                "side_to_close":    "buy",   # covering short
                "value_usd":        short_pos["value_usd"],
                "current_side":     "short",
                "k500_paired":      True,
                "k500_close_order": 1,        # close short first
                "venue":            "HL",
                "note":             f"K500 INJ-BTC short leg {short_coin} — cover first (HL-only)",
            })
            total_notional += short_pos["value_usd"]

        # Long leg second
        long_coin = k500_pair["long_symbol"]
        long_pos  = next((p for p in positions if p["coin"].upper() == long_coin
                          and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":             long_pos["coin"],
                "size":             long_pos["size"],
                "side_to_close":    "sell",
                "value_usd":        long_pos["value_usd"],
                "current_side":     "long",
                "k500_paired":      True,
                "k500_close_order": 2,        # close long second
                "venue":            "HL",
                "note":             f"K500 INJ-BTC long leg {long_coin} — sell second (HL-only)",
            })
            total_notional += long_pos["value_usd"]

    # K507 SEI-BTC paired positions: short leg first, then long leg (K514 Phase 4)
    # HL+Bybit split: SEI on HL, BTC on Bybit (or reverse based on direction)
    if k507_pair:
        # Short leg first (avoid uncovered short) — close on its venue
        short_coin  = k507_pair["short_symbol"]
        short_venue = k507_pair.get("short_venue", "Bybit")
        short_pos   = next((p for p in positions if p["coin"].upper() == short_coin
                            and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":             short_pos["coin"],
                "size":             short_pos["size"],
                "side_to_close":    "buy",   # covering short
                "value_usd":        short_pos["value_usd"],
                "current_side":     "short",
                "k507_paired":      True,
                "k507_close_order": 1,        # close short first
                "venue":            short_venue,
                "note":             (
                    f"K507 SEI-BTC short leg {short_coin} — "
                    f"cover first ({short_venue}). HL+Bybit 1.5%+1.5% split (K514)."
                ),
            })
            total_notional += short_pos["value_usd"]

        # Long leg second — close on its venue
        long_coin  = k507_pair["long_symbol"]
        long_venue = k507_pair.get("long_venue", "HL")
        long_pos   = next((p for p in positions if p["coin"].upper() == long_coin
                           and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":             long_pos["coin"],
                "size":             long_pos["size"],
                "side_to_close":    "sell",
                "value_usd":        long_pos["value_usd"],
                "current_side":     "long",
                "k507_paired":      True,
                "k507_close_order": 2,        # close long second
                "venue":            long_venue,
                "note":             (
                    f"K507 SEI-BTC long leg {long_coin} — "
                    f"sell second ({long_venue}). HL+Bybit 1.5%+1.5% split (K514)."
                ),
            })
            total_notional += long_pos["value_usd"]

    # K512 APT-BTC paired positions: short leg first, then long leg (K520 Phase 4)
    # HL+Bybit split: APT on HL, BTC on Bybit (or reverse based on direction)
    if k512_pair:
        # Short leg first (avoid uncovered short) — close on its venue
        short_coin  = k512_pair["short_symbol"]
        short_venue = k512_pair.get("short_venue", "Bybit")
        short_pos   = next((p for p in positions if p["coin"].upper() == short_coin
                            and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":             short_pos["coin"],
                "size":             short_pos["size"],
                "side_to_close":    "buy",   # covering short
                "value_usd":        short_pos["value_usd"],
                "current_side":     "short",
                "k512_paired":      True,
                "k512_close_order": 1,        # close short first
                "venue":            short_venue,
                "note":             (
                    f"K512 APT-BTC short leg {short_coin} — "
                    f"cover first ({short_venue}). HL+Bybit 1%+1% split (K520)."
                ),
            })
            total_notional += short_pos["value_usd"]

        # Long leg second — close on its venue
        long_coin  = k512_pair["long_symbol"]
        long_venue = k512_pair.get("long_venue", "HL")
        long_pos   = next((p for p in positions if p["coin"].upper() == long_coin
                           and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":             long_pos["coin"],
                "size":             long_pos["size"],
                "side_to_close":    "sell",
                "value_usd":        long_pos["value_usd"],
                "current_side":     "long",
                "k512_paired":      True,
                "k512_close_order": 2,        # close long second
                "venue":            long_venue,
                "note":             (
                    f"K512 APT-BTC long leg {long_coin} — "
                    f"sell second ({long_venue}). HL+Bybit 1%+1% split (K520)."
                ),
            })
            total_notional += long_pos["value_usd"]

    # K507 TIA-BTC paired positions: short leg first, then long leg (K524 Phase 4)
    # HL-only: both TIA and BTC legs on HL (1% sleeve, smaller weight)
    if k507_tia_pair:
        # Short leg first (avoid uncovered short) — both legs on HL
        short_coin  = k507_tia_pair["short_symbol"]
        short_venue = k507_tia_pair.get("short_venue", "HL")
        short_pos   = next((p for p in positions if p["coin"].upper() == short_coin
                            and p["side"] == "short"), None)
        if short_pos:
            close_list.append({
                "coin":                 short_pos["coin"],
                "size":                 short_pos["size"],
                "side_to_close":        "buy",   # covering short
                "value_usd":            short_pos["value_usd"],
                "current_side":         "short",
                "k507_tia_paired":      True,
                "k507_tia_close_order": 1,        # close short first
                "venue":                short_venue,
                "note":                 (
                    f"K507 TIA-BTC short leg {short_coin} — "
                    f"cover first ({short_venue}). HL-only 1% sleeve (K524)."
                ),
            })
            total_notional += short_pos["value_usd"]

        # Long leg second — also on HL
        long_coin  = k507_tia_pair["long_symbol"]
        long_venue = k507_tia_pair.get("long_venue", "HL")
        long_pos   = next((p for p in positions if p["coin"].upper() == long_coin
                           and p["side"] == "long"), None)
        if long_pos:
            close_list.append({
                "coin":                 long_pos["coin"],
                "size":                 long_pos["size"],
                "side_to_close":        "sell",
                "value_usd":            long_pos["value_usd"],
                "current_side":         "long",
                "k507_tia_paired":      True,
                "k507_tia_close_order": 2,        # close long second
                "venue":                long_venue,
                "note":                 (
                    f"K507 TIA-BTC long leg {long_coin} — "
                    f"sell second ({long_venue}). HL-only 1% sleeve (K524)."
                ),
            })
            total_notional += long_pos["value_usd"]

    # All other positions: close in any order (non-K449, non-K457, non-K476, non-K484, non-K493, non-K500, non-K507, non-K507-TIA, non-K512, non-K541, non-K521)
    handled_coins = k449_coins | k457_coins | k476_coins | k484_coins | k493_coins | k500_coins | k507_coins | k512_coins | k507_tia_coins | k541_coins | k521_coins
    for p in positions:
        coin = p.get("coin", "").upper()
        if coin in handled_coins:
            continue   # already handled above
        side_to_close = "sell" if p["side"] == "long" else "buy"
        close_list.append({
            "coin":          p["coin"],
            "size":          p["size"],
            "side_to_close": side_to_close,
            "value_usd":     p["value_usd"],
            "current_side":  p["side"],
            "k449_paired":   False,
            "k457_basket":   False,
        })
        total_notional += p["value_usd"]

    n_pos = len(close_list)
    slippage_usd = total_notional * (SLIPPAGE_ESTIMATE_PCT / 100.0)

    return {
        "cancel_orders":          cancel_list,
        "close_positions":        close_list,
        "total_notional_usd":     total_notional,
        "estimated_time_s":       ESTIMATED_TIME_PER_POS * n_pos,
        "slippage_estimate_usd":  slippage_usd,
        "position_count":         n_pos,
        "order_count":            len(cancel_list),
        "k449_paired_detected":   k449_pair is not None,
        "k449_pair_detail":       k449_pair,
        "k457_basket_detected":   k457_basket is not None,
        "k457_basket_detail":     k457_basket,
        "k476_paired_detected":   k476_pair is not None,
        "k476_pair_detail":       k476_pair,
        "k484_paired_detected":   k484_pair is not None,
        "k484_pair_detail":       k484_pair,
        "k493_paired_detected":   k493_pair is not None,
        "k493_pair_detail":       k493_pair,
        "k500_paired_detected":   k500_pair is not None,
        "k500_pair_detail":       k500_pair,
        "k507_paired_detected":   k507_pair is not None,
        "k507_pair_detail":       k507_pair,
        "k512_paired_detected":   k512_pair is not None,
        "k512_pair_detail":       k512_pair,
        "k507_tia_paired_detected": k507_tia_pair is not None,
        "k507_tia_pair_detail":     k507_tia_pair,
        "k628_paired_detected":   k628_pair is not None,
        "k628_pair_detail":       k628_pair,
        "k541_detected":          k541_pos is not None,
        "k541_detail":            k541_pos,
        "k495_detected":          k495_pos is not None,
        "k495_detail":            k495_pos,
        "k521_detected":          k521_pos is not None,
        "k521_detail":            k521_pos,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pre-check / Post-check
# ─────────────────────────────────────────────────────────────────────────────

def run_precheck(user: str, dry_run: bool, logger: logging.Logger) -> Dict:
    """Collect current state snapshot before exit."""
    logger.info("=== PRE-CHECK ===")
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    balance   = fetch_balance(user, dry_run=dry_run)
    positions = fetch_positions(user, dry_run=dry_run)
    orders    = fetch_orders(user, dry_run=dry_run)
    plan      = plan_exit(positions, orders)

    snapshot = {
        "type":       "precheck",
        "timestamp":  ts,
        "user":       user,
        "dry_run":    dry_run,
        "balance":    balance,
        "positions":  positions,
        "orders":     orders,
        "plan":       plan,
    }

    fname = LOGS_DIR / f"emergency_hl_exit_precheck_{ts}.json"
    if not dry_run:
        with open(fname, "w") as f:
            json.dump(snapshot, f, indent=2)
        logger.info(f"Pre-check saved: {fname}")
    else:
        logger.info(f"[DRY-RUN] Pre-check would save: {fname}")

    logger.info(f"Balance: ${balance.get('usdc_balance', 0):.2f} USDC | "
                f"Positions: {len(positions)} | Open orders: {len(orders)}")
    logger.info(f"Total notional to close: ${plan['total_notional_usd']:.2f}")

    # ── K429 AUM Context (read portfolio_aum_state for deployed_capital awareness) ──
    try:
        _aum_state_path = REPO_ROOT / "data" / "portfolio_aum_state.json"
        if _aum_state_path.exists():
            with open(_aum_state_path) as _af:
                _aum_st = json.load(_af)
            _aum     = _aum_st.get("current_aum_usdc",       0)
            _deploy  = _aum_st.get("deployed_capital_usdc",  0)
            _cum_pct = _aum_st.get("cumulative_pnl_pct",     0.0)
            logger.info(
                f"[K429] AUM state: current=${_aum:,.0f} | deployed=${_deploy:,.0f} | "
                f"cumPnL={_cum_pct:+.3f}%"
            )
            snapshot["k429_aum_context"] = {
                "current_aum_usdc":      _aum,
                "deployed_capital_usdc": _deploy,
                "cumulative_pnl_pct":    _cum_pct,
            }
    except Exception:
        pass  # AUM context is informational only; do not disrupt emergency exit

    return snapshot


def run_postcheck(user: str, logger: logging.Logger) -> Dict:
    """Collect state snapshot after exit (5 min after)."""
    logger.info("=== POST-CHECK (waiting 5 minutes for settlements) ===")
    logger.info("Sleeping 300 seconds...")
    time.sleep(300)

    ts        = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    balance   = fetch_balance(user, dry_run=False)
    positions = fetch_positions(user, dry_run=False)
    orders    = fetch_orders(user, dry_run=False)

    # Verify closure
    residual = [p for p in positions if p["value_usd"] > POSITION_NOISE_USD]
    all_closed = len(residual) == 0
    all_orders_cleared = len(orders) == 0

    snapshot = {
        "type":             "postcheck",
        "timestamp":        ts,
        "user":             user,
        "balance":          balance,
        "positions":        positions,
        "orders":           orders,
        "residual_positions": residual,
        "all_closed":       all_closed,
        "all_orders_cleared": all_orders_cleared,
        "status":           "CLEAN" if (all_closed and all_orders_cleared) else "RESIDUAL_WARNING",
    }

    fname = LOGS_DIR / f"emergency_hl_exit_postcheck_{ts}.json"
    with open(fname, "w") as f:
        json.dump(snapshot, f, indent=2)
    logger.info(f"Post-check saved: {fname}")

    if all_closed and all_orders_cleared:
        logger.info("POST-CHECK PASSED: All positions closed, all orders cleared.")
    else:
        logger.warning(f"POST-CHECK WARNING: {len(residual)} residual positions, "
                       f"{len(orders)} open orders remaining.")
        for p in residual:
            logger.warning(f"  Residual: {p['coin']} {p['side']} ${p['value_usd']:.2f}")

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dry-run Report
# ─────────────────────────────────────────────────────────────────────────────

def dry_run_report(precheck: Dict, plan: Dict, logger: logging.Logger) -> None:
    """Print human-readable dry-run plan."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("  EMERGENCY HL EXIT — DRY-RUN PLAN (no actual trading)")
    logger.info("=" * 70)

    bal = precheck.get("balance", {})
    logger.info(f"  User:              {precheck.get('user', 'unknown')}")
    logger.info(f"  USDC Balance:      ${bal.get('usdc_balance', 0):.2f}")
    logger.info(f"  Withdrawable:      ${bal.get('withdrawable', 0):.2f}")
    logger.info(f"  Unrealized PnL:    ${bal.get('unrealized_pnl', 0):.2f}")
    logger.info("")

    orders_to_cancel = plan.get("cancel_orders", [])
    if orders_to_cancel:
        logger.info(f"  STEP 1: Cancel {len(orders_to_cancel)} open orders:")
        for coin, oid in orders_to_cancel:
            logger.info(f"    - {coin} oid={oid}")
    else:
        logger.info("  STEP 1: No open orders to cancel.")
    logger.info("")

    positions_to_close = plan.get("close_positions", [])
    if positions_to_close:
        logger.info(f"  STEP 2: Close {len(positions_to_close)} positions (market, reduce-only):")
        for p in positions_to_close:
            logger.info(f"    - {p['coin']:<12} {p['current_side']:<6} "
                        f"size={p['size']:.6f}  notional=${p['value_usd']:.2f}  "
                        f"→ {p['side_to_close'].upper()}")
    else:
        logger.info("  STEP 2: No positions to close. (no positions found)")
    logger.info("")

    logger.info(f"  Total notional:    ${plan.get('total_notional_usd', 0):.2f}")
    logger.info(f"  Est. slippage:     ${plan.get('slippage_estimate_usd', 0):.2f} "
                f"({SLIPPAGE_ESTIMATE_PCT} bps)")
    est_t = plan.get("estimated_time_s", 0)
    logger.info(f"  Estimated time:    ~{est_t}s (~{est_t//60}m {est_t%60}s)")
    logger.info("")
    logger.info("  To EXECUTE this plan, run with --EXECUTE flag.")
    logger.info("  EXECUTE requires: HL_PRIVATE_KEY env var + interactive confirm.")
    logger.info("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# 5. HL Exchange API — Order submission (signing)
# ─────────────────────────────────────────────────────────────────────────────

def _build_cancel_action(coin: str, oid: int) -> Dict:
    """Build HL cancel order action payload."""
    return {
        "type":    "cancel",
        "cancels": [{"coin": coin, "oid": oid}],
    }


def _build_market_close_action(coin: str, size: float, is_buy: bool) -> Dict:
    """
    Build HL market-close order action.
    Uses IOC (Immediate-or-Cancel) + reduce-only flag for safety.
    Price: set far outside market to guarantee fill (HL market order via limit IOC).
      For sell: very low px (e.g. 0.001)
      For buy:  very high px (e.g. 999999999)
    """
    px = "0.001" if not is_buy else "999999999"
    return {
        "type": "order",
        "orders": [{
            "coin":       coin,
            "isBuy":      is_buy,
            "sz":         str(round(size, 8)),
            "limitPx":    px,
            "orderType":  {"limit": {"tif": "Ioc"}},   # IOC = fill-or-kill at limit
            "reduceOnly": True,
        }],
        "grouping": "na",
    }


def _sign_hl_action(action: Dict, private_key_hex: str, nonce: int, vault_address: Optional[str] = None) -> Dict:
    """
    Sign a HL exchange action using SECP256K1.
    HL signing protocol:
      1. Compute keccak256 of action_hash (action JSON + nonce + vaultAddress if present)
      2. Sign with SECP256K1 private key
      3. Include signature as {r, s, v} in request body

    NOTE: This requires eth_account (from web3 ecosystem) for actual SECP256K1 signing.
    Since we cannot guarantee eth_account is installed, we raise ImportError with guidance
    rather than silently failing.

    Returns: dict with {action, nonce, signature}
    """
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError:
        raise ImportError(
            "eth_account package required for live execution.\n"
            "Install with: pip install eth-account\n"
            "This is a one-time dependency only needed for --EXECUTE mode."
        )

    # HL action signing: encode as connection_id + action bytes
    # Reference: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/signing
    action_bytes = json.dumps(action, separators=(",", ":"), sort_keys=True).encode()

    # Build the phantom agent hash (HL protocol)
    # connection_id = keccak256(abi.encode(action_bytes, nonce))
    # For simplicity, we use the structured hash per HL SDK
    nonce_bytes = struct.pack(">Q", nonce)  # big-endian uint64
    vault_bytes = b"\x00" * 20  # no vault

    raw_hash = hashlib.sha3_256(action_bytes + nonce_bytes + vault_bytes).digest()

    # eth_account sign
    msg = encode_defunct(raw_hash)
    signed = Account.sign_message(msg, private_key=private_key_hex)

    return {
        "action":  action,
        "nonce":   nonce,
        "signature": {
            "r": hex(signed.r),
            "s": hex(signed.s),
            "v": signed.v,
        },
        "vaultAddress": vault_address,
    }


def _submit_hl_exchange(payload: Dict, logger: logging.Logger) -> Dict:
    """POST to HL exchange endpoint."""
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library required.")

    resp = requests.post(
        HL_EXCHANGE_URL,
        json=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ct-emergency-exit/1.0"},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.debug(f"Exchange response: {json.dumps(result)}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 6. Execute Exit
# ─────────────────────────────────────────────────────────────────────────────

def execute_exit(plan: Dict, private_key: str, user: str, logger: logging.Logger) -> bool:
    """
    ACTUAL TRADING — only callable from --EXECUTE path after double-confirm.
    1. Cancel all open orders (sequentially)
    2. Submit market-close orders (reduce-only, IOC) for each position
    3. Verify after each step

    Private key is passed as argument, NEVER logged.
    """
    logger.warning("*** EXECUTE MODE ACTIVE — REAL TRADING COMMENCING ***")

    nonce_base = int(time.time() * 1000)
    success    = True

    # Step 1: Cancel all open orders
    cancel_list = plan.get("cancel_orders", [])
    if cancel_list:
        logger.info(f"Cancelling {len(cancel_list)} open orders...")
        for i, (coin, oid) in enumerate(cancel_list):
            try:
                action  = _build_cancel_action(coin, oid)
                nonce   = nonce_base + i
                payload = _sign_hl_action(action, private_key, nonce)
                result  = _submit_hl_exchange(payload, logger)
                status  = result.get("status", "unknown")
                logger.info(f"  Cancelled {coin} oid={oid}: {status}")
                time.sleep(CANCEL_WAIT_SECONDS)
            except Exception as exc:
                logger.error(f"  CANCEL FAILED {coin} oid={oid}: {exc}")
                success = False

    # Step 2: Market-close all positions
    close_list  = plan.get("close_positions", [])
    nonce_base2 = int(time.time() * 1000)

    if close_list:
        logger.info(f"Closing {len(close_list)} positions (market IOC reduce-only)...")
        for i, pos in enumerate(close_list):
            coin          = pos["coin"]
            size          = pos["size"]
            is_buy        = (pos["side_to_close"] == "buy")
            try:
                action  = _build_market_close_action(coin, size, is_buy)
                nonce   = nonce_base2 + i
                payload = _sign_hl_action(action, private_key, nonce)
                result  = _submit_hl_exchange(payload, logger)
                status  = result.get("status", "unknown")
                logger.info(f"  Closed {coin} (size={size:.6f}, {'BUY' if is_buy else 'SELL'}): {status}")

                # Verify: check position shrinks
                time.sleep(POST_CLOSE_VERIFY_WAIT)
                current = fetch_positions(user, dry_run=False)
                remaining = next((p for p in current if p["coin"] == coin), None)
                if remaining and remaining["value_usd"] > POSITION_NOISE_USD:
                    logger.warning(f"  VERIFY: {coin} still has ${remaining['value_usd']:.2f} residual")
                    success = False
                else:
                    logger.info(f"  VERIFY: {coin} confirmed closed (or within noise threshold)")

                time.sleep(CLOSE_WAIT_SECONDS)

            except Exception as exc:
                logger.error(f"  CLOSE FAILED {coin}: {exc}")
                success = False

    return success


# ─────────────────────────────────────────────────────────────────────────────
# 7. Alert Mechanism
# ─────────────────────────────────────────────────────────────────────────────

def write_emergency_status(triggered: bool, plan: Optional[Dict], logger: logging.Logger) -> None:
    """Write machine-readable status JSON for HTML dashboard + flag file."""
    ts  = datetime.datetime.utcnow().isoformat() + "Z"
    obj = {
        "triggered":        triggered,
        "timestamp_utc":    ts,
        "total_notional":   plan.get("total_notional_usd", 0) if plan else 0,
        "position_count":   plan.get("position_count", 0) if plan else 0,
        "status":           "EMERGENCY_EXIT_TRIGGERED" if triggered else "STANDBY",
    }
    with open(EMERGENCY_STATUS_JSON, "w") as f:
        json.dump(obj, f, indent=2)
    logger.info(f"Emergency status JSON written: {EMERGENCY_STATUS_JSON}")

    if triggered:
        with open(EMERGENCY_FLAG_FILE, "w") as f:
            f.write(f"EMERGENCY EXIT TRIGGERED\n{ts}\n")
        logger.critical(f"EMERGENCY FLAG FILE written: {EMERGENCY_FLAG_FILE}")
        logger.critical("K302a daemons will refuse to trade while this flag file exists.")
        logger.critical(f"To re-enable trading: rm {EMERGENCY_FLAG_FILE}")


def send_ntfy_alert(message: str, title: str, priority: str = "urgent",
                    logger: Optional[logging.Logger] = None) -> None:
    """Send emergency notification via ntfy.sh (best-effort, no crash on fail)."""
    try:
        import requests
        resp = requests.post(
            f"https://ntfy.sh/{NTFY_EMERGENCY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title":    title,
                "Priority": priority,
                "Tags":     "rotating_light,skull",
            },
            timeout=10,
        )
        if logger:
            logger.info(f"ntfy.sh alert sent (HTTP {resp.status_code}): {title}")
    except Exception as exc:
        if logger:
            logger.warning(f"ntfy.sh alert failed (non-critical): {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# 7b. Bybit Close-All (K378/K380 gap fix — Phase 6)
# ─────────────────────────────────────────────────────────────────────────────

# Bybit API v5 endpoints (public testable, auth required for trading)
BYBIT_API_URL       = "https://api.bybit.com"
BYBIT_CANCEL_ALL    = "/v5/order/cancel-all"
BYBIT_POSITION_LIST = "/v5/position/list"
BYBIT_CLOSE_ROUTE   = "/v5/order/create"     # market order to close

def _bybit_signed_request(
    method: str,
    endpoint: str,
    params: Dict,
    api_key: str,
    api_secret: str,
    logger: logging.Logger,
) -> Dict:
    """
    Submit authenticated Bybit v5 API request using HMAC-SHA256.
    Returns response JSON dict; raises RuntimeError on failure.
    """
    try:
        import requests
        import hmac
        import hashlib
    except ImportError:
        raise RuntimeError("requests + hmac/hashlib required (stdlib + requests).")

    ts_ms  = str(int(time.time() * 1000))
    recv_window = "5000"

    if method.upper() == "GET":
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sign_payload = ts_ms + api_key + recv_window + query
    else:
        body_str = json.dumps(params, separators=(",", ":"))
        sign_payload = ts_ms + api_key + recv_window + body_str

    signature = hmac.new(
        api_secret.encode("utf-8"),
        sign_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "X-BAPI-API-KEY":     api_key,
        "X-BAPI-TIMESTAMP":   ts_ms,
        "X-BAPI-SIGN":        signature,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type":       "application/json",
        "User-Agent":         "ct-emergency-exit/1.0",
    }

    url = BYBIT_API_URL + endpoint
    try:
        if method.upper() == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=20)
        else:
            resp = requests.post(url, data=body_str, headers=headers, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        if result.get("retCode", 0) != 0:
            logger.warning(f"Bybit API non-zero retCode: {result.get('retCode')} — {result.get('retMsg')}")
        return result
    except Exception as exc:
        raise RuntimeError(f"Bybit API request failed ({endpoint}): {exc}")


def close_bybit_positions(
    api_key: str,
    api_secret: str,
    dry_run: bool,
    logger: logging.Logger,
    category: str = "linear",
) -> bool:
    """
    K378 Phase 6 gap fix: close all Bybit positions + cancel all orders.
    Uses Bybit v5 API:
      1. POST /v5/order/cancel-all  (cancel all open orders)
      2. GET  /v5/position/list     (fetch all open positions)
      3. POST /v5/order/create × N  (market close each position)

    category: "linear" (USDT perps, default) | "inverse" | "spot"
    api_key + api_secret: read from BYBIT_API_KEY / BYBIT_API_SECRET env vars at call time.
    Returns True on success (all positions attempted), False if any error.

    PAPER-TRADE SAFE: in dry_run=True returns without calling Bybit API.
    """
    if dry_run:
        logger.info("  [DRY-RUN] close_bybit_positions — skipping API calls (dry-run mode).")
        return True

    if not api_key or not api_secret:
        logger.error("Bybit credentials not provided. Set BYBIT_API_KEY + BYBIT_API_SECRET.")
        return False

    success = True

    # Step 1: Cancel all open orders
    logger.info("Bybit Step 1: Cancelling all open orders...")
    try:
        cancel_payload = {"category": category, "settleCoin": "USDT"}
        result = _bybit_signed_request(
            "POST", BYBIT_CANCEL_ALL, cancel_payload, api_key, api_secret, logger
        )
        cancelled_count = len(result.get("result", {}).get("list", []))
        logger.info(f"  Bybit cancel-all complete: {cancelled_count} orders cancelled "
                    f"(retCode={result.get('retCode')})")
        time.sleep(1.5)
    except Exception as exc:
        logger.error(f"  Bybit cancel-all FAILED: {exc}")
        success = False

    # Step 2: Fetch open positions
    logger.info("Bybit Step 2: Fetching open positions...")
    positions = []
    try:
        pos_params = {"category": category, "settleCoin": "USDT"}
        pos_result = _bybit_signed_request(
            "GET", BYBIT_POSITION_LIST, pos_params, api_key, api_secret, logger
        )
        raw_positions = pos_result.get("result", {}).get("list", [])
        for p in raw_positions:
            size = float(p.get("size", "0") or "0")
            if size < 1e-9:
                continue  # skip zero positions
            positions.append({
                "symbol":     p.get("symbol", ""),
                "size":       size,
                "side":       p.get("side", ""),          # "Buy" or "Sell"
                "value_usd":  float(p.get("positionValue", "0") or "0"),
            })
        logger.info(f"  Bybit open positions: {len(positions)}")
    except Exception as exc:
        logger.error(f"  Bybit position fetch FAILED: {exc}")
        return False

    if not positions:
        logger.info("  No Bybit positions to close.")
        return success

    # Step 3: Market-close each position
    logger.info(f"Bybit Step 3: Market-closing {len(positions)} positions...")
    import urllib.error as _urllib_error
    for pos in positions:
        symbol     = pos["symbol"]
        size       = str(pos["size"])
        # Opposite side to close: if position is "Buy" → close with "Sell"
        close_side = "Sell" if pos["side"] == "Buy" else "Buy"
        close_payload = {
            "category":    category,
            "symbol":      symbol,
            "side":        close_side,
            "orderType":   "Market",
            "qty":         size,
            "reduceOnly":  True,
            "timeInForce": "IOC",
        }
        _attempts = 0
        while _attempts < 2:
            try:
                result = _bybit_signed_request(
                    "POST", BYBIT_CLOSE_ROUTE, close_payload, api_key, api_secret, logger
                )
                order_id = result.get("result", {}).get("orderId", "N/A")
                logger.info(
                    f"  Closed {symbol} {close_side} qty={size} "
                    f"(orderId={order_id}, retCode={result.get('retCode')})"
                )
                time.sleep(CLOSE_WAIT_SECONDS)
                break  # success — exit retry loop
            except Exception as exc:
                import requests as _req_mod
                _transient = isinstance(exc, (_req_mod.exceptions.Timeout, _urllib_error.URLError))
                if _transient and _attempts == 0:
                    logger.warning(f"  Bybit close {symbol} transient error (attempt 1): {exc} — retrying in 2s")
                    time.sleep(2)
                    _attempts += 1
                    continue
                logger.error(f"  Bybit close FAILED {symbol}: {exc}")
                success = False
                break

    return success


# ─────────────────────────────────────────────────────────────────────────────
# 7c. OKX Close-All (K456 OKX integration scaffold — Phase 3 venue)
# ─────────────────────────────────────────────────────────────────────────────

# OKX API v5 endpoints (auth required for trading; read-only does not need keys)
OKX_API_URL              = "https://www.okx.com"
OKX_CANCEL_BATCH_ROUTE   = "/api/v5/trade/cancel-batch-orders"
OKX_POSITION_LIST_ROUTE  = "/api/v5/account/positions"
OKX_CLOSE_POSITION_ROUTE = "/api/v5/trade/close-position"


def _okx_signed_request(
    method: str,
    endpoint: str,
    params: Dict,
    api_key: str,
    api_secret: str,
    passphrase: str,
    logger: logging.Logger,
) -> Dict:
    """
    Submit authenticated OKX v5 API request using HMAC-SHA256.
    OKX auth headers:
      OK-ACCESS-KEY       — API key
      OK-ACCESS-SIGN      — base64(HMAC-SHA256(timestamp+method+path+body, secret))
      OK-ACCESS-TIMESTAMP — ISO 8601 UTC timestamp (seconds + milliseconds)
      OK-ACCESS-PASSPHRASE — passphrase set at API key creation

    Returns response JSON dict; raises RuntimeError on failure.
    """
    import base64
    import urllib.request
    import urllib.error

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
         f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"

    if method.upper() == "GET":
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        path_with_query = endpoint + ("?" + query if query else "")
        body_str        = ""
    else:
        path_with_query = endpoint
        body_str        = json.dumps(params, separators=(",", ":"))

    sign_payload = ts + method.upper() + path_with_query + body_str
    signature    = base64.b64encode(
        hmac.new(
            api_secret.encode("utf-8"),
            sign_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode()

    headers = {
        "OK-ACCESS-KEY":        api_key,
        "OK-ACCESS-SIGN":       signature,
        "OK-ACCESS-TIMESTAMP":  ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type":         "application/json",
        "User-Agent":           "ct-emergency-exit/1.0",
    }

    url = OKX_API_URL + path_with_query
    try:
        if method.upper() == "GET":
            req = urllib.request.Request(url, headers=headers)
        else:
            req = urllib.request.Request(
                OKX_API_URL + endpoint,
                data=body_str.encode("utf-8"),
                headers=headers,
                method="POST",
            )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("code") != "0":
            logger.warning(
                f"OKX API non-zero code: {result.get('code')} — {result.get('msg')}"
            )
        return result
    except Exception as exc:
        raise RuntimeError(f"OKX API request failed ({endpoint}): {exc}")


def close_okx_positions(
    api_key:    str,
    api_secret: str,
    passphrase: str,
    dry_run:    bool,
    logger:     logging.Logger,
    inst_type:  str = "SWAP",
) -> bool:
    """
    K456 scaffold: close all OKX perpetual swap positions + cancel all orders.

    Uses OKX v5 API:
      1. GET  /api/v5/account/positions           — fetch all open SWAP positions
      2. POST /api/v5/trade/close-position × N    — market-close each position
         (mgnMode=cross, autoCxl=true to auto-cancel related orders)

    inst_type: "SWAP" (perpetual swaps, default) | "FUTURES" | "MARGIN"
    Credentials: read from OKX_API_KEY / OKX_API_SECRET / OKX_PASSPHRASE env vars.

    Returns True on success (all positions attempted), False if any error.

    PAPER-TRADE SAFE: in dry_run=True returns without calling OKX API.

    OKX close-position endpoint fields:
      instId   — e.g. "BTC-USDT-SWAP"
      mgnMode  — "cross" | "isolated" (use "cross" for cross-margin perps)
      posSide  — "long" | "short" | "net" (use "net" for one-way mode)
      autoCxl  — "true" (auto-cancel related open orders)
    """
    if dry_run:
        logger.info("  [DRY-RUN] close_okx_positions — skipping API calls (dry-run mode).")
        logger.info("    Would fetch OKX positions and close all SWAP perpetuals.")
        return True

    logger.info(f"OKX Step 1: Fetching open positions (instType={inst_type})...")
    positions = []
    try:
        resp = _okx_signed_request(
            "GET", OKX_POSITION_LIST_ROUTE,
            {"instType": inst_type},
            api_key, api_secret, passphrase, logger,
        )
        for item in resp.get("data", []):
            pos_amt = float(item.get("pos", 0) or 0)
            if abs(pos_amt) > 0:
                positions.append(item)
        logger.info(f"  OKX open positions: {len(positions)}")
    except Exception as exc:
        logger.error(f"  OKX position fetch FAILED: {exc}")
        return False

    if not positions:
        logger.info("  No OKX positions to close.")
        return True

    logger.info(f"OKX Step 2: Closing {len(positions)} positions (market, autoCxl=true)...")
    all_ok = True
    for pos in positions:
        inst_id  = pos.get("instId", "")
        pos_side = pos.get("posSide", "net")
        mgn_mode = pos.get("mgnMode", "cross")

        if not inst_id:
            continue

        close_params = {
            "instId":  inst_id,
            "mgnMode": mgn_mode,
            "posSide": pos_side,
            "autoCxl": "true",
        }
        try:
            result = _okx_signed_request(
                "POST", OKX_CLOSE_POSITION_ROUTE,
                close_params,
                api_key, api_secret, passphrase, logger,
            )
            if result.get("code") == "0":
                data = result.get("data", [{}])
                clt_ord_id = data[0].get("clOrdId", "") if data else ""
                logger.info(
                    f"  OKX close {inst_id} ({pos_side}): OK  clOrdId={clt_ord_id}"
                )
            else:
                logger.warning(
                    f"  OKX close {inst_id} warning: code={result.get('code')} "
                    f"msg={result.get('msg')}"
                )
                all_ok = False
        except Exception as exc:
            logger.error(f"  OKX close FAILED {inst_id}: {exc}")
            all_ok = False
        time.sleep(0.3)   # rate-limit: OKX trading API

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# 7d. Aevo Close-All (K460 Aevo integration scaffold — 4th venue)
# ─────────────────────────────────────────────────────────────────────────────

def close_aevo_positions(
    api_key:    str,
    api_secret: str,
    dry_run:    bool,
    logger:     logging.Logger,
) -> bool:
    """
    K460 scaffold: close all Aevo perpetual positions.

    TODO: Full implementation when Aevo API auth is added post-K460.
    Aevo REST base: https://api.aevo.xyz
    Read-only (no auth): /funding, /markets, /orderbook.
    Trading auth: API key + HMAC-SHA256 signature (TODO post-K460).

    Current scope: STUB — read-only scaffold only.
    Activate: when AEVO_API_KEY + AEVO_API_SECRET env vars are configured
              and v6.20 Aevo trading integration is live.

    Returns True on dry-run (safe). Returns False stub in live mode (not implemented).
    """
    if dry_run:
        logger.info(
            "  [DRY-RUN] close_aevo_positions — STUB (K460 scaffold, read-only). "
            "No API call made."
        )
        logger.info(
            "    Aevo trading auth TODO: implement after API auth phase (post-K460). "
            "Dashboard: data/aevo_dashboard.json | Fetcher: scripts/aevo_fr_fetcher.py"
        )
        return True

    # STUB: live Aevo close not yet implemented (K460 read-only scope)
    logger.warning(
        "close_aevo_positions: STUB — not yet implemented (K460 read-only scaffold). "
        "Set --no-aevo to skip. Full auth implementation planned post-K460 when "
        "AEVO_API_KEY + AEVO_API_SECRET are configured."
    )
    logger.warning(
        "  Manual action required: close Aevo positions via https://app.aevo.xyz "
        "if any exist. Aevo fetcher: scripts/aevo_fr_fetcher.py"
    )
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 7e. dYdX v4 Close-All (K460 dYdX v4 integration scaffold — 5th venue)
# ─────────────────────────────────────────────────────────────────────────────

def close_dydx_positions(
    dry_run: bool,
    logger:  logging.Logger,
) -> bool:
    """
    K460 scaffold: close all dYdX v4 Cosmos perpetual positions.

    TODO: Full implementation when dYdX v4 Cosmos signing is added post-K460.
    dYdX v4 is a Cosmos appchain — trading requires Cosmos SDK transaction signing
    (NOT EVM). Requires dYdX Python client or Cosmos protobuf construction.

    Indexer (read-only, no auth): https://indexer.dydx.trade/v4
    Trading (Cosmos signing required — TODO):
      - dYdX SDK: https://github.com/dydxprotocol/v4-clients
      - Requires DYDX_MNEMONIC or DYDX_PRIVATE_KEY env var (Cosmos format, not EVM)

    Current scope: STUB — read-only scaffold only.
    Returns True on dry-run (safe). Returns False stub in live mode (not implemented).
    """
    if dry_run:
        logger.info(
            "  [DRY-RUN] close_dydx_positions — STUB (K460 scaffold, read-only). "
            "No API call made."
        )
        logger.info(
            "    dYdX v4 is Cosmos chain (not EVM) — signing requires Cosmos SDK (TODO post-K460). "
            "Indexer (read-only): https://indexer.dydx.trade/v4 | "
            "Dashboard: data/dydx_v4_dashboard.json | Fetcher: scripts/dydx_v4_fr_fetcher.py"
        )
        return True

    # STUB: live dYdX v4 close not yet implemented (K460 read-only scope)
    logger.warning(
        "close_dydx_positions: STUB — not yet implemented (K460 read-only scaffold). "
        "dYdX v4 requires Cosmos SDK signing (not EVM). "
        "Set --no-dydx to skip. Full implementation planned post-K460."
    )
    logger.warning(
        "  Manual action required: close dYdX v4 positions via https://dydx.trade "
        "if any exist. Indexer (read positions): "
        "GET https://indexer.dydx.trade/v4/addresses/{address}/subaccountNumber/0/openPositions"
    )
    return False


def close_jlp_positions(
    dry_run: bool,
    logger:  logging.Logger,
) -> bool:
    """
    K468 scaffold: close Jupiter Perpetuals JLP (Solana LP) position.

    JLP is a Solana-based liquidity provider token for Jupiter Perpetuals.
    It is NOT a HL/Bybit/OKX/Aevo/dYdX position — it lives on Solana.

    K467 analysis:
      - JLP current APY: ~1.68% (K467 baseline)
      - Break-even APY: ~21% (IL + hedge cost + basis risk)
      - Entry trigger: >= 25% gross APY (K468 monitor fires alert)
      - Reduce trigger: < 15% APY (exit half)
      - Exit trigger: < 10% sustained 14d (exit all)

    To close JLP manually:
      1. Go to https://jup.ag/perp (Jupiter Perpetuals UI) or
         https://jupresear.ch (Jupiter Explorer)
      2. Connect Solana wallet (Phantom, Backpack, etc.)
      3. Navigate to "Earn" / "JLP" tab
      4. Click "Withdraw" to redeem JLP tokens for underlying assets
      5. Swap underlying assets (BTC/ETH/SOL/USDC/USDT) to USDC via Jupiter swap

    Hedge leg (if JLP was hedged on HL per §36 runbook):
      - Close the corresponding short position on HL (delta hedge)
      - Run: python3 scripts/emergency_hl_exit.py --EXECUTE --user <addr>

    NOTE: Solana wallet API signing is a USER responsibility.
    This script does NOT have access to Solana private keys.
    Full automation planned post-K468 when Solana wallet SDK integrated.

    Current scope: STUB — guidance only.
    Returns True on dry-run (safe). Returns False in live mode (not implemented).
    """
    if dry_run:
        logger.info(
            "  [DRY-RUN] close_jlp_positions — K468 STUB (Solana LP, guidance only). "
            "No API call made."
        )
        logger.info(
            "    JLP is Solana-based — NOT on HL/Bybit/OKX. Manual close required."
        )
        logger.info(
            "    Close via Jupiter UI: https://jup.ag/perp → Earn → JLP → Withdraw."
        )
        logger.info(
            "    Then close HL delta hedge short (if hedged) via main HL exit."
        )
        logger.info(
            "    Dashboard: data/jlp_apy_dashboard.json | Monitor: scripts/jlp_apy_monitor.py | "
            "Runbook: docs/k302a_runbook.md §36"
        )
        return True

    # STUB: live JLP close not yet implemented (K468 scaffold — Solana wallet required)
    logger.warning(
        "close_jlp_positions: STUB — Solana wallet signing not implemented (K468 scaffold). "
        "JLP must be closed manually via Jupiter UI: https://jup.ag/perp → Earn → JLP → Withdraw."
    )
    logger.warning(
        "  After JLP withdrawal: swap underlying tokens to USDC via jup.ag. "
        "Close HL delta hedge (if active) via standard HL exit. "
        "See: docs/k302a_runbook.md §36 for full JLP exit procedure."
    )
    return False


def close_spark_positions(
    dry_run: bool,
    logger:  logging.Logger,
) -> bool:
    """
    K473 scaffold: close Spark sUSDS (Sky/MakerDAO) stablecoin yield position.

    Spark sUSDS is an Ethereum-based yield-bearing stablecoin — NOT a HL/Bybit/OKX
    perpetual position. No HL delta hedge is required (stablecoin, not directional).

    K473 context:
      - sUSDS: Spark Protocol (Sky/MakerDAO DSR-based), Ethereum mainnet
      - Pool: USDS / Ethereum (DefiLlama ID: 54e9b138-3146-4c1f-8dce-1cb948f5ef96)
      - Current APY: ~3.34% (K473 live fetch, 2026-05-30)
      - Combined 50/50 with sUSDe: ~3.61% (K473 blended estimate)
      - Redemption: INSTANT (no lockup, unlike sUSDe 7d cooldown)

    To close sUSDS manually:
      1. Connect Ethereum wallet (MetaMask/Ledger) to https://app.spark.fi/
      2. Navigate to Earn → sUSDS
      3. Click "Withdraw" to redeem sUSDS for USDS
      4. Optionally swap USDS → USDC via Uniswap or Curve

    Or via Sky Protocol directly:
      1. Go to https://sky.money/ (formerly MakerDAO)
      2. Connect wallet → Savings → Withdraw

    NOTE: No HL/Bybit positions involved — this is a pure DeFi stablecoin position.
    Redemption is instant. No delta hedge to unwind on HL.
    This script CANNOT access Ethereum private keys. Wallet action is user responsibility.

    Current scope: STUB — guidance only.
    Returns True on dry-run (safe). Returns False in live mode (not implemented).
    """
    if dry_run:
        logger.info(
            "  [DRY-RUN] close_spark_positions — K473 STUB (Spark sUSDS, guidance only). "
            "No API call made."
        )
        logger.info(
            "    sUSDS is Ethereum DeFi — NOT a HL/Bybit/OKX perp position. No delta hedge."
        )
        logger.info(
            "    Close via Spark UI: https://app.spark.fi/ → Earn → sUSDS → Withdraw."
        )
        logger.info(
            "    Or via Sky: https://sky.money/ → Savings → Withdraw. Redemption is INSTANT."
        )
        logger.info(
            "    Dashboard: data/spark_usds_dashboard.json | Monitor: scripts/spark_usds_monitor.py | "
            "Runbook: docs/k302a_runbook.md §37"
        )
        return True

    # STUB: live sUSDS close not yet implemented (K473 scaffold — Ethereum wallet required)
    logger.warning(
        "close_spark_positions: STUB — Ethereum wallet signing not implemented (K473 scaffold). "
        "sUSDS must be redeemed manually via Spark UI: https://app.spark.fi/ → Earn → sUSDS → Withdraw."
    )
    logger.warning(
        "  Redemption is INSTANT (no lockup). After withdrawal, swap USDS → USDC if needed. "
        "No HL delta hedge required (sUSDS is not a directional perp position). "
        "See: docs/k302a_runbook.md §37 for full Spark sUSDS exit procedure."
    )
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 8. Interactive Confirm (--EXECUTE guard)
# ─────────────────────────────────────────────────────────────────────────────

def double_confirm(plan: Dict, user: str) -> bool:
    """
    Require interactive double-confirm before executing live trading.
    Refuses if not TTY. Returns True only if both confirmations are 'yes'.
    """
    if not sys.stdin.isatty():
        print("ERROR: --EXECUTE requires an interactive terminal (TTY).")
        print("       Pipe/redirect detected. Refusing to execute for safety.")
        return False

    n_pos  = plan.get("position_count", 0)
    n_ord  = plan.get("order_count", 0)
    notional = plan.get("total_notional_usd", 0)

    print()
    print("=" * 70)
    print("  !! WARNING: THIS WILL EXECUTE REAL TRADES ON HYPERLIQUID !!")
    print("=" * 70)
    print(f"  User address:    {user}")
    print(f"  Positions to close: {n_pos}")
    print(f"  Orders to cancel:   {n_ord}")
    print(f"  Total notional:     ${notional:.2f} USD")
    print(f"  Estimated slippage: ${plan.get('slippage_estimate_usd', 0):.2f} USD")
    print()
    print("  This action is IRREVERSIBLE. All positions will be closed at market.")
    print()

    try:
        ans1 = input("  Confirm #1 — type 'yes' to proceed: ").strip().lower()
        if ans1 != "yes":
            print("  Aborted (first confirm not 'yes').")
            return False

        ans2 = input("  Confirm #2 — type 'EXECUTE' to confirm: ").strip()
        if ans2 != "EXECUTE":
            print("  Aborted (second confirm not 'EXECUTE').")
            return False
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted (keyboard interrupt).")
        return False

    print("  Confirmed. Proceeding with emergency exit...")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 9. Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "K357 Emergency HyperLiquid Exit Script (K355 critical gap mitigation)\n"
            "K380: --include-bybit flag added (K378 Phase 6 Bybit gap fix)\n"
            "K456: --include-okx flag added (3rd venue, OKX SWAP perpetuals)\n"
            "K460: --include-aevo flag added (4th venue, STUB scaffold)\n"
            "K460: --include-dydx flag added (5th venue, Cosmos chain STUB scaffold)\n"
            "K502: --include-k495 flag added (K495 DEX-CEX flow divergence, LONG BTC+ETH+SOL, bear-conditional)\n"
            "K506: --include-k500 flag added (K500 INJ-BTC FR differential, 34th daemon, Cosmos 2nd CONFIRMED)\n"
            "K514: --include-k507 flag added (K507 SEI-BTC FR differential, 35th daemon, Cosmos 3rd CONFIRMED, HL+Bybit split)\n"
            "K520: --include-k512 flag added (K512 APT-BTC FR differential, 36th daemon, Move-VM #1 family CONFIRMED, HL+Bybit split)\n"
            "K524: --include-k507-tia flag added (K507 TIA-BTC FR differential, 37th daemon, Celestia modular DA CONFIRMED, HL-only 1%)\n"
            "K550: --include-k541 flag added (K541 stablecoin supply growth, 38th daemon, V3 acceleration, DefiLlama API, BTC+ETH+SOL LONG)\n"
            "K565: --include-k521 flag added (K521 options 25d skew, 39th daemon, DVOL+skew V4 composite, Deribit free API, BTC LONG)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe dry-run (default, no real trades):
  python3 scripts/emergency_hl_exit.py --dry-run --user 0x0000000000000000000000000000000000000000

  # Using env var for address:
  export HL_USER_ADDRESS=0x...
  python3 scripts/emergency_hl_exit.py --dry-run

  # LIVE EXECUTION — HL only (requires HL_PRIVATE_KEY + interactive confirm):
  export HL_USER_ADDRESS=0x...
  export HL_PRIVATE_KEY=0x...
  python3 scripts/emergency_hl_exit.py --EXECUTE

  # LIVE EXECUTION — HL + Bybit (K380 gap fix, default --include-bybit=True):
  export HL_USER_ADDRESS=0x...
  export HL_PRIVATE_KEY=0x...
  export BYBIT_API_KEY=...
  export BYBIT_API_SECRET=...
  python3 scripts/emergency_hl_exit.py --EXECUTE --include-bybit

  # HL only (skip Bybit):
  python3 scripts/emergency_hl_exit.py --EXECUTE --no-bybit

  # LIVE EXECUTION — HL + Bybit + OKX (K456 3rd venue):
  export OKX_API_KEY=...
  export OKX_API_SECRET=...
  export OKX_PASSPHRASE=...
  python3 scripts/emergency_hl_exit.py --EXECUTE --include-okx

Trigger conditions (per §14 runbook):
  - CFTC/regulatory enforcement action against HL
  - HL platform alert (exploit, insolvency signal, ADL cascade)
  - HYPE token -40% in 7 days
  - Custom user trigger (operator discretion)

Bybit emergency exit (§14 update, K380):
  - Requires BYBIT_API_KEY + BYBIT_API_SECRET env vars
  - Cancels all open Bybit orders, then market-closes all linear positions
  - See: docs/k302a_runbook.md §14.7 (Bybit gap fix)

OKX emergency exit (K456 §30.5):
  - Requires OKX_API_KEY + OKX_API_SECRET + OKX_PASSPHRASE env vars
  - Closes all OKX SWAP perpetual positions (mgnMode=cross, autoCxl=true)
  - Scaffold-only at K456 — activate when OKX trading is live (v6.20)
  - See: docs/k302a_runbook.md §30.5

USDY sleeve emergency guidance (K415 §21.6):
  - USDY (Ondo Finance) is T-bill backed — safe to HOLD through HL/Bybit crisis
  - Redemption: 1 business day AFTER 40-day initial lock expires (cannot be rushed)
  - Recommended: DO NOT redeem during emergency — HOLD USDY and exit HL/Bybit only
  - If capital needed post-crisis: redeem at ondo.finance (takes 1 business day)
  - See: docs/k302a_runbook.md §21.6
  - Use --include-usdy flag to print USDY guidance during emergency exit
        """,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run",  dest="dry_run",  action="store_true", default=True,
                            help="Dry-run mode (default): fetch positions and print plan, no trades")
    mode_group.add_argument("--EXECUTE",  dest="execute",  action="store_true", default=False,
                            help="LIVE execution: actually cancel orders and close positions")
    parser.add_argument("--user", dest="user", default=None,
                        help="HL user address (0x...); fallback: HL_USER_ADDRESS env var")
    parser.add_argument("--skip-postcheck", action="store_true",
                        help="Skip post-execution verification (not recommended)")
    # K380: Bybit emergency exit flag (default True per K378 Phase 6)
    bybit_group = parser.add_mutually_exclusive_group()
    bybit_group.add_argument("--include-bybit", dest="include_bybit", action="store_true",
                             default=True,
                             help="(default) Include Bybit close-all in emergency exit (K380 gap fix)")
    bybit_group.add_argument("--no-bybit",      dest="include_bybit", action="store_false",
                             help="Skip Bybit close-all (HL only)")
    # K456: OKX emergency exit flag (scaffold — activate when OKX trading is live in v6.20)
    okx_group = parser.add_mutually_exclusive_group()
    okx_group.add_argument(
        "--include-okx",
        dest="include_okx",
        action="store_true",
        default=False,
        help=(
            "K456: Include OKX close-all in emergency exit (3rd venue, v6.20 scaffold). "
            "Requires OKX_API_KEY + OKX_API_SECRET + OKX_PASSPHRASE env vars. "
            "Use when OKX trading positions exist (post v6.20 go-live). "
            "See: docs/k302a_runbook.md §30.5"
        ),
    )
    okx_group.add_argument(
        "--no-okx",
        dest="include_okx",
        action="store_false",
        help="Skip OKX close-all (default — OKX not yet live at K456)",
    )

    # K415: USDY emergency exit documentation flag
    # IMPORTANT: USDY is NOT part of the standard emergency exit.
    #   - USDY is T-bill backed; hold through HL/Bybit crisis (see §21.6)
    #   - Redemption: 1 business day AFTER 40-day initial lock (no emergency cancel)
    #   - Emergency redemption is SLOWER than HL/Bybit (cannot be rushed)
    #   - Default recommendation: hold USDY through crisis — do NOT redeem
    #   - Only redeem if user needs capital after HL+Bybit exit AND 40-day lock has expired
    parser.add_argument(
        "--include-usdy",
        dest="include_usdy",
        action="store_true",
        default=False,
        help=(
            "K415: Document USDY redemption note during emergency exit. "
            "WARNING: USDY is T-bill backed — safer to HOLD through HL/Bybit crisis. "
            "Redemption: 1 business day (post 40-day lock only). Cannot be rushed. "
            "Only flag if you explicitly want to redeem USDY after HL/Bybit exit."
        ),
    )

    # K460: Aevo emergency exit flag (stub scaffold — 4th venue)
    aevo_group = parser.add_mutually_exclusive_group()
    aevo_group.add_argument(
        "--include-aevo",
        dest="include_aevo",
        action="store_true",
        default=False,
        help=(
            "K460: Include Aevo close-all in emergency exit (4th venue, STUB scaffold). "
            "STUB only at K460 — full auth TODO post-K460. "
            "Dry-run: prints guidance. Live: warns manual action required at app.aevo.xyz. "
            "See: docs/k302a_runbook.md §33.5"
        ),
    )
    aevo_group.add_argument(
        "--no-aevo",
        dest="include_aevo",
        action="store_false",
        help="Skip Aevo close-all (default — Aevo not yet live at K460)",
    )

    # K460: dYdX v4 emergency exit flag (stub scaffold — 5th venue, Cosmos chain)
    dydx_group = parser.add_mutually_exclusive_group()
    dydx_group.add_argument(
        "--include-dydx",
        dest="include_dydx",
        action="store_true",
        default=False,
        help=(
            "K460: Include dYdX v4 close-all in emergency exit (5th venue, Cosmos chain STUB). "
            "STUB only at K460 — Cosmos signing TODO post-K460. "
            "Dry-run: prints guidance. Live: warns manual action required at dydx.trade. "
            "See: docs/k302a_runbook.md §33.6"
        ),
    )
    dydx_group.add_argument(
        "--no-dydx",
        dest="include_dydx",
        action="store_false",
        help="Skip dYdX v4 close-all (default — dYdX trading not yet live at K460)",
    )

    # K459: K457 basket emergency exit flag
    # K457 = BTC+ETH+SOL simultaneous carry basket (HL+Bybit legs)
    # Sequential close: short legs first (avoid uncovered short), then long legs.
    # Default: off (basket positions are auto-detected via _detect_k457_basket_positions).
    # Use --include-k457 to print K457-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k457",
        dest="include_k457",
        action="store_true",
        default=False,
        help=(
            "K459: Include K457 BTC+ETH+SOL basket-specific close summary and protocol note "
            "during emergency exit. K457 basket positions (HL+Bybit, 6 legs) are detected "
            "automatically; this flag just prints the structured close plan explicitly. "
            "Close protocol: short legs first (avoid uncovered short), then long legs. "
            "Requires: K457 basket daemon running (com.cryptolab.k457-basket). "
            "See: docs/k302a_runbook.md §32"
        ),
    )

    # K465: Lighter emergency exit flag (stub scaffold — 6th venue, zkEVM)
    lighter_group = parser.add_mutually_exclusive_group()
    lighter_group.add_argument(
        "--include-lighter",
        dest="include_lighter",
        action="store_true",
        default=False,
        help=(
            "K465: Include Lighter close-all in emergency exit (6th venue, zkEVM STUB scaffold). "
            "STUB only at K465 — full auth TODO post-K465. "
            "Dry-run: prints guidance. Live: warns manual action required at lighter.xyz. "
            "zkEVM settlement — close via Lighter web UI or SDK (API keys required). "
            "See: docs/k302a_runbook.md §35.5"
        ),
    )
    lighter_group.add_argument(
        "--no-lighter",
        dest="include_lighter",
        action="store_false",
        help="Skip Lighter close-all (default — Lighter not yet live at K465)",
    )

    # K465: Vertex emergency exit flag (stub scaffold — 7th venue, USDC margin)
    vertex_group = parser.add_mutually_exclusive_group()
    vertex_group.add_argument(
        "--include-vertex",
        dest="include_vertex",
        action="store_true",
        default=False,
        help=(
            "K465: Include Vertex close-all in emergency exit (7th venue, USDC margin STUB scaffold). "
            "STUB only at K465 — full auth TODO post-K465. "
            "Dry-run: prints guidance. Live: warns manual action required at app.vertexprotocol.com. "
            "USDC margin — close via Vertex web UI or SDK (wallet signing required). "
            "Product IDs: BTC=2, ETH=4 (POST /execute to Gateway). "
            "See: docs/k302a_runbook.md §35.6"
        ),
    )
    vertex_group.add_argument(
        "--no-vertex",
        dest="include_vertex",
        action="store_false",
        help="Skip Vertex close-all (default — Vertex not yet live at K465)",
    )

    # K468: JLP (Jupiter Perpetuals LP) emergency exit flag (stub scaffold — Solana venue)
    # JLP is a Solana-based LP position — NOT a HL/Bybit/OKX position.
    # Requires Solana wallet management (user responsibility). CANNOT be automated here.
    # Entry only when JLP APY >= 25% trigger fires (K468 monitor). Exit at < 15% (reduce) / < 10% sustained (full exit).
    parser.add_argument(
        "--include-jlp",
        dest="include_jlp",
        action="store_true",
        default=False,
        help=(
            "K468: Print JLP (Jupiter Perpetuals LP) emergency exit guidance (Solana STUB scaffold). "
            "STUB only — Solana wallet signing required (user responsibility). "
            "JLP is NOT on HL/Bybit/OKX — manual close required at jup.ag or Jupiter UI. "
            "K467 analysis: break-even 21%%, entry trigger >=25%%, reduce <15%%, exit <10%%. "
            "K468 monitor: scripts/jlp_apy_monitor.py (weekly DefiLlama poll). "
            "See: docs/k302a_runbook.md §36"
        ),
    )

    # K478: K476 SOL-BTC FR differential paired-trade emergency exit flag
    # K476 = SOL long + BTC short (or reverse) on HL — 2 legs, HL-only.
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # Default: off (K476 positions are auto-detected via _detect_k476_paired_positions).
    # Use --include-k476 to print K476-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k476",
        dest="include_k476",
        action="store_true",
        default=False,
        help=(
            "K478: Include K476 SOL-BTC paired-trade close summary during emergency exit. "
            "K476 positions (SOL+BTC, HL-only, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "Both legs on HyperLiquid only (K434 smart router HL-only). "
            "Requires: K476 daemon running (com.cryptolab.k476-sol-btc). "
            "See: docs/k302a_runbook.md §38"
        ),
    )

    # K489: K484 AVAX-BTC FR differential paired-trade emergency exit flag
    # K484 = AVAX long + BTC short (or reverse) on HL — 2 legs, HL-only.
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # Default: off (K484 positions are auto-detected via _detect_k484_paired_positions).
    # Use --include-k484 to print K484-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k484",
        dest="include_k484",
        action="store_true",
        default=False,
        help=(
            "K489: Include K484 AVAX-BTC paired-trade close summary during emergency exit. "
            "K484 positions (AVAX+BTC, HL-only, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "Both legs on HyperLiquid only (K434 smart router HL-only). "
            "OOS Sharpe 43.89 (#1 paired-trade family). "
            "Requires: K484 daemon running (com.cryptolab.k484-avax-btc). "
            "See: docs/k302a_runbook.md §38c"
        ),
    )

    # K499: K493 ATOM-BTC FR differential paired-trade emergency exit flag
    # K493 = ATOM long + BTC short (or reverse) on HL — 2 legs, HL-only.
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # Default: off (K493 positions are auto-detected via _detect_k493_paired_positions).
    # Use --include-k493 to print K493-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k493",
        dest="include_k493",
        action="store_true",
        default=False,
        help=(
            "K499: Include K493 ATOM-BTC paired-trade close summary during emergency exit. "
            "K493 positions (ATOM+BTC, HL-only, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "Both legs on HyperLiquid only (K434 smart router HL-only). "
            "OOS Sharpe 50.79 (#1 paired-trade family). G5a 0.1763 (Cosmos hypothesis). "
            "Requires: K493 daemon running (com.cryptolab.k493-atom-btc). "
            "See: docs/k302a_runbook.md §38d"
        ),
    )

    # K506: K500 INJ-BTC FR differential paired-trade emergency exit flag
    # K500 = INJ long + BTC short (or reverse) on HL — 2 legs, HL-only.
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # Default: off (K500 positions are auto-detected via _detect_k500_paired_positions).
    # Use --include-k500 to print K500-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k500",
        dest="include_k500",
        action="store_true",
        default=False,
        help=(
            "K506: Include K500 INJ-BTC paired-trade close summary during emergency exit. "
            "K500 positions (INJ+BTC, HL-only, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "Both legs on HyperLiquid only (K434 smart router HL-only). "
            "OOS Sharpe 11.23 (family rank #4). G5d 0.2893 PASS (Cosmos 2nd CONFIRMED). "
            "INJ DeFi-perp mechanics distinct from ATOM IBC/staking. "
            "Requires: K500 daemon running (com.cryptolab.k500-inj-btc). "
            "See: docs/k302a_runbook.md §38e"
        ),
    )

    # K514: K507 SEI-BTC FR differential paired-trade emergency exit flag
    # K507 = SEI long + BTC short (or reverse) — HL+Bybit split (1.5%+1.5%).
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # HL portion closes on HL; Bybit portion closes on Bybit.
    # Default: off (K507 positions are auto-detected via _detect_k507_paired_positions).
    # Use --include-k507 to print K507-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k507",
        dest="include_k507",
        action="store_true",
        default=False,
        help=(
            "K514: Include K507 SEI-BTC paired-trade close summary during emergency exit. "
            "K507 positions (SEI+BTC, HL+Bybit split, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "HL+Bybit split: SEI leg on HL (1.5%), BTC leg on Bybit (1.5%). "
            "Close each leg on its respective venue (HL IOC + Bybit IOC). "
            "OOS Sharpe 48.10 (family rank #2). Cosmos 3rd CONFIRMED. "
            "SEI EVM-compat + Cosmos SDK distinct from ATOM/INJ. "
            "Requires: K507 daemon running (com.cryptolab.k507-sei-btc). "
            "See: docs/k302a_runbook.md §38f"
        ),
    )

    # K520: K512 APT-BTC FR differential paired-trade emergency exit flag
    # K512 = APT long + BTC short (or reverse) — HL+Bybit split (1%+1%).
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # HL portion closes on HL; Bybit portion closes on Bybit.
    # Default: off (K512 positions are auto-detected via _detect_k512_paired_positions).
    # Use --include-k512 to print K512-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k512",
        dest="include_k512",
        action="store_true",
        default=False,
        help=(
            "K520: Include K512 APT-BTC paired-trade close summary during emergency exit. "
            "K512 positions (APT+BTC, HL+Bybit split, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "HL+Bybit split: APT leg on HL (1%), BTC leg on Bybit (1%). "
            "Close each leg on its respective venue (HL IOC + Bybit IOC). "
            "OOS Sharpe 51.10 (family rank #1 — highest in paired-trade family). "
            "Move-VM Block-STM + Move resource model creates orthogonal FR dynamics. "
            "OU half-life 0.27d. $302K/yr net @ $10M. "
            "Requires: K512 daemon running (com.cryptolab.k512-apt-btc). "
            "See: docs/k302a_runbook.md §38g"
        ),
    )

    # K524: K507 TIA-BTC FR differential paired-trade emergency exit flag
    # K507 TIA = TIA long + BTC short (or reverse) — HL-only (1% sleeve, no Bybit split).
    # Sequential close: short leg first (avoid uncovered short), then long leg.
    # Both legs close on HL (HL IOC reduce-only — HL-only spec).
    # Default: off (K507 TIA positions are auto-detected via _detect_k507_tia_paired_positions).
    # Use --include-k507-tia to print K507 TIA-specific close summary and ensure sequential ordering.
    parser.add_argument(
        "--include-k507-tia",
        dest="include_k507_tia",
        action="store_true",
        default=False,
        help=(
            "K524: Include K507 TIA-BTC paired-trade close summary during emergency exit. "
            "K507 TIA positions (TIA+BTC, HL-only, 2 legs) are detected automatically; "
            "this flag adds a structured summary. "
            "Close protocol: short leg first (avoid uncovered short), then long leg. "
            "HL-only: both TIA and BTC legs on HL (1% sleeve, no Bybit split). "
            "Close both legs on HL IOC reduce-only. "
            "OOS Sharpe 14.44 (family rank #6). Celestia modular DA CONFIRMED. "
            "G5d vs ATOM: 0.05 = LOWEST in family. $51K/yr net @ $10M. "
            "Requires: K507 TIA daemon running (com.cryptolab.k507-tia-btc). "
            "See: docs/k302a_runbook.md §38h"
        ),
    )

    # K550: K541 stablecoin supply growth emergency exit flag
    # K541 = LONG BTC+ETH+SOL on HL (3 legs) when 7d supply z-score 2nd derivative > 0.5.
    # Close protocol: IOC reduce-only BTC → ETH → SOL (all longs, HL-only).
    # Signal-based (daily cron 86400s) — closes when acceleration drops below threshold.
    # Default: off (K541 positions are auto-detected via _detect_k541_position).
    # Use --include-k541 to print K541-specific close summary during emergency exit.
    parser.add_argument(
        "--include-k541",
        dest="include_k541",
        action="store_true",
        default=False,
        help=(
            "K550: Include K541 stablecoin supply growth close summary during emergency exit. "
            "K541 positions (LONG BTC+ETH+SOL, HL-only, 3 legs) are detected automatically "
            "via _detect_k541_position(); this flag adds a structured summary. "
            "Close protocol: IOC reduce-only BTC → ETH → SOL (all longs, HL-only). "
            "Signal: 7d USDT+USDC supply z-score 2nd derivative > 0.5 (V3 acceleration). "
            "DefiLlama free API (stablecoins.llama.fi). "
            "OOS Sharpe 1.498. $294K/yr @$10M. G5 max corr 0.074 (orthogonal to FR-carry). "
            "90d paper-trade gate. 3% sleeve, 2x leverage. "
            "Requires: K541 daemon running (com.cryptolab.k541-stablecoin-supply). "
            "See: docs/k302a_runbook.md §40"
        ),
    )

    # K565: K521 options 25d skew emergency exit flag
    # K521 = LONG BTC on HL (1 leg) when DVOL z-score + ETH-BTC skew spread composite > 1.0 (V4).
    # Close protocol: IOC reduce-only LONG BTC (single leg, HL-only).
    # Signal-based (daily cron 86400s) — closes when composite z drops below threshold.
    # Default: off (K521 positions are auto-detected via _detect_k521_position).
    # Use --include-k521 to print K521-specific close summary during emergency exit.
    parser.add_argument(
        "--include-k521",
        dest="include_k521",
        action="store_true",
        default=False,
        help=(
            "K565: Include K521 options 25d skew close summary during emergency exit. "
            "K521 positions (LONG BTC, HL-only, 1 leg) are detected automatically "
            "via _detect_k521_position(); this flag adds a structured summary. "
            "Close protocol: IOC reduce-only LONG BTC (single leg, HL-only). "
            "Signal: Deribit DVOL z-score (60%) + ETH-BTC 25d skew spread z-score (40%) > 1.0 (V4). "
            "Deribit free public API (no auth). "
            "OOS Sharpe 1.019. $494K/yr @$10M. Max corr 0.199 (orthogonal, institutional axis). "
            "90d paper-trade gate (G3 DSR CONDITIONAL). 3% sleeve, 2x leverage. "
            "Requires: K521 daemon running (com.cryptolab.k521-options-skew). "
            "See: docs/k302a_runbook.md §41"
        ),
    )

    # K637: K628 JTO-BTC orthog emergency exit flag
    # K628 = Bybit-only JTO+BTC paired (2 legs) when residual EMA > 1.5σ.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = JTO_diff − 0.164×SEI_diff − 0.302×DOGE_diff (K628 OLS).
    # Use --include-k628 to print K628-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k628",
        dest="include_k628",
        action="store_true",
        default=False,
        help=(
            "K637: Include K628 JTO-BTC orthog close summary during emergency exit. "
            "K628 positions (JTO+BTC paired, Bybit-only) are detected automatically "
            "via _detect_k628_paired_positions(); this flag adds a structured summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = JTO_diff - 0.164*SEI_diff - 0.302*DOGE_diff (K628 OLS beta hardcoded). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 18.30 (residual). $17.85M/yr potential @$10M @4x (largest single-token). "
            "60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<20%. "
            "2% sleeve=$7.14M/yr | 3% sleeve=$10.7M/yr | Solana LST/MEV cluster (24th). "
            "Requires: K628 daemon running (com.cryptolab.k628-jto-orthog, 40th daemon). "
            "See: docs/k302a_runbook.md §42"
        ),
    )

    # K641: K635 IMX-BTC orthog emergency exit flag
    # K635 = Bybit-only IMX+BTC paired (2 legs) when residual EMA_168h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = IMX_diff - 0.254*SHIB_diff - 0.068*TIA_diff - 0.158*SEI_diff (K635 OLS MF, beta hardcoded).
    # EMA window: W=168h = 21 x 8h periods (optimal per K635 analysis).
    # Use --include-k635 to print K635-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k635",
        dest="include_k635",
        action="store_true",
        default=False,
        help=(
            "K641: Include K635 IMX-BTC orthog close summary during emergency exit. "
            "K635 positions (IMX+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = IMX_diff - 0.254*SHIB_diff - 0.068*TIA_diff - 0.158*SEI_diff (K635 OLS MF beta hardcoded). "
            "EMA window: W=168h = 21 x 8h periods (optimal per K635 analysis). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 24.81 (residual MF W=168h). $4.78M/yr @$10M @4x (2% sleeve). "
            "60d paper-trade gate: Realized Sh>=12 + fill>=60% + maxDD<20%. "
            "Cluster: Gaming L2 Infra (ImmutableX StarkEx ZK rollup for NFT/gaming). "
            "Requires: K635 daemon running (com.cryptolab.k635-imx-orthog, 43rd daemon). "
            "See: docs/k302a_runbook.md §44"
        ),
    )

    # K650: K645 BNB-BTC orthog emergency exit flag
    # K645 = Bybit-only BNB+BTC paired (2 legs) when residual EMA_168h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = BNB_diff - 0.539*ETH_diff (K645 OLS SF, beta hardcoded).
    # EMA window: W=168h = 21 x 8h periods (optimal per K645 analysis).
    # Use --include-k645 to print K645-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k645",
        dest="include_k645",
        action="store_true",
        default=False,
        help=(
            "K650: Include K645 BNB-BTC orthog close summary during emergency exit. "
            "K645 positions (BNB+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = BNB_diff - 0.539*ETH_diff (K645 OLS SF beta hardcoded). "
            "EMA window: W=168h = 21 x 8h periods (optimal per K645 analysis). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 7.07 (residual SF W=168h). $17,694/yr net @$10M @4x (3% sleeve). "
            "60d paper-trade gate: Realized Sh>=3.5 + fill>=60% + maxDD<20%. "
            "Cluster: Binance Ecosystem / BSC L1 (ETH-cluster unlock, 6th orthog, 45th daemon). "
            "ETH unlock: K480 BLOCKED (corr=0.435) -> K645 post-orth=0.1757 PASS. "
            "Requires: K645 daemon running (com.cryptolab.k645-bnb-orthog, 45th daemon). "
            "See: docs/k302a_runbook.md §47"
        ),
    )

    # K652: K648 POL-BTC orthog emergency exit flag
    # K648 = Bybit-only POL+BTC paired (2 legs) when residual EMA_168h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = POL_diff - 0.337443*OP_diff - 0.075509*SEI_diff - (-0.016480)*APT_diff
    #                  - 0.059789*TIA_diff - 0.042751*FIL_diff - 0.200488*SAND_diff (K648 OLS MF 6-factor).
    # EMA window: W=168h = 21 x 8h periods (optimal per K648 analysis).
    # Use --include-k648 to print K648-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k648",
        dest="include_k648",
        action="store_true",
        default=False,
        help=(
            "K652: Include K648 POL-BTC 6-factor orthog close summary during emergency exit. "
            "K648 positions (POL+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = POL_diff - 0.337443*OP_diff - 0.075509*SEI_diff "
            "- (-0.016480)*APT_diff - 0.059789*TIA_diff - 0.042751*FIL_diff - 0.200488*SAND_diff "
            "(K648 OLS MF 6-factor betas hardcoded). "
            "EMA window: W=168h = 21 x 8h periods (optimal per K648 analysis). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 23.41 (residual MF W=168h). $4,293,200/yr @$10M @4x (2% sleeve). "
            "60d paper-trade gate: Realized Sh>=12 + fill>=60% + maxDD<20%. "
            "Cluster: Polygon L2 / PoS / zkEVM (6-factor unlock: OP+SEI+APT+TIA+FIL+SAND, 47th daemon). "
            "6-factor unlock: K611 BLOCKED-ROLLUP-SIBLING -> K648 all post-orth corrs < 0.40 PASS. "
            "Requires: K648 daemon running (com.cryptolab.k648-pol-orthog, 47th daemon). "
            "See: docs/k302a_runbook.md §48"
        ),
    )

    # K642: K638 STX-BTC orthog emergency exit flag
    # K638 = Bybit-only STX+BTC paired (2 legs) when residual EMA_504h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = STX_diff - 0.203339*APT_diff - 0.125164*SEI_diff - 0.306518*DOGE_diff (K638 OLS MF, beta hardcoded).
    # EMA window: W=504h = 63 x 8h periods (optimal per K638 analysis).
    # Use --include-k638 to print K638-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k638",
        dest="include_k638",
        action="store_true",
        default=False,
        help=(
            "K642: Include K638 STX-BTC orthog close summary during emergency exit. "
            "K638 positions (STX+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = STX_diff - 0.203339*APT_diff - 0.125164*SEI_diff - 0.306518*DOGE_diff (K638 OLS MF beta hardcoded). "
            "EMA window: W=504h = 63 x 8h periods (optimal per K638 analysis). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 12.38 (residual MF W=504h). $65,018/yr net @$10M @4x (1.5% sleeve). "
            "60d paper-trade gate: Realized Sh>=6 + fill>=60% + maxDD<20%. "
            "Cluster: BTC-L2 / Stacks PoX (Bitcoin Layer-2, PoX stacking cycles). "
            "Requires: K638 daemon running (com.cryptolab.k638-stx-orthog, 44th daemon). "
            "See: docs/k302a_runbook.md §46"
        ),
    )

    # K651: K646 ALGO-BTC orthog emergency exit flag
    # K646 = Bybit-only ALGO+BTC paired (2 legs) when residual EMA_72h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = ALGO_diff - 0.411*FIL_diff (K646 OLS SF, beta hardcoded).
    # EMA window: W=72h = 9 x 8h periods (optimal per K646 analysis).
    # Use --include-k646 to print K646-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k646",
        dest="include_k646",
        action="store_true",
        default=False,
        help=(
            "K651: Include K646 ALGO-BTC orthog close summary during emergency exit. "
            "K646 positions (ALGO+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = ALGO_diff - 0.411*FIL_diff (K646 OLS SF beta hardcoded). "
            "EMA window: W=72h = 9 x 8h periods (optimal per K646 analysis). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 8.11 (residual SF W=72h). ~$20,325/yr net @$10M @4x (2% sleeve). "
            "60d paper-trade gate: Realized Sh>=4 + fill>=60% + maxDD<20%. "
            "Cluster: Enterprise/Utility L1 / Algorand PoS VRF (FIL-cluster unlock, 7th orthog, 46th daemon). "
            "FIL unlock: K522 BLOCKED (corr=0.6052) -> K646 post-orth=0.2546 PASS. "
            "Requires: K646 daemon running (com.cryptolab.k646-algo-orthog, 46th daemon). "
            "K646 on Bybit: ALGO_diff - 0.411*FIL_diff (K651 scaffold). "
            "See: docs/k302a_runbook.md §48"
        ),
    )

    # K654: K629 WLD-ETH FR Differential emergency exit flag
    # K629 = HL-primary WLD+ETH paired (2 legs) when diff EMA_168h > 1.5sigma.
    # Close protocol: IOC reduce-only on HL (BOTH legs on HL — HL concentration affected).
    # Signal: diff = WLD_FR - ETH_FR (direct, W=168h, no orthogonalization).
    # ETH-base fix: JUP-BTC cross-base corr=0.3437 PASS (K621 WLD-BTC was 0.4612 BLOCKED).
    # Use --include-k629 to print K629-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k629",
        dest="include_k629",
        action="store_true",
        default=False,
        help=(
            "K654: Include K629 WLD-ETH close summary during emergency exit. "
            "K629 positions (WLD+ETH paired, HL-primary) ARE included in HL emergency exit. "
            "This flag adds a structured K629-specific close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = WLD_FR - ETH_FR (direct differential, W=168h EMA, 1.5sigma threshold). "
            "HL concentration: ~59.5% post-K629 (within 65% limit). "
            "OOS Sharpe 19.90 (9/9 §6 PASS, IS=29.94, ratio=0.665). $94,210/yr @$10M @4x (3% sleeve). "
            "60d paper-trade gate: Realized Sh>=10 + fill>=60% + maxDD<15%. "
            "ETH-base fix: JUP-BTC cross-base corr=0.3437 PASS (K621 WLD-BTC blocked at 0.4612). "
            "Anti-corr with K449 ETH-BTC (corr=-0.2052): diversification benefit. "
            "Cluster: Biometric ID / World ID (Cluster 24, ETH-base unlock, 49th daemon). "
            "Escalation: K621 BLOCKED -> K624 BLOCKED -> K627 STILL-BLOCKED -> K629 PASS. "
            "Requires: K629 daemon running (com.cryptolab.k629-wld-eth, 49th daemon). "
            "See: docs/k302a_runbook.md §50"
        ),
    )

    # K653: K647 DOT-BTC orthog emergency exit flag
    # K647 = Bybit-only DOT+BTC paired (2 legs) when residual EMA_168h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration 64% after add, 1pp headroom).
    # Orthog: residual = DOT_diff - 0.642*INJ_diff (K647 OLS SF, beta hardcoded).
    # EMA window: W=168h = 21 x 8h periods (optimal per K647 analysis).
    # OOS R²=-4.11 STRUCTURAL BREAK WARNING — IS beta re-OLS every 30d mandatory.
    # Use --include-k647 to print K647-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k647",
        dest="include_k647",
        action="store_true",
        default=False,
        help=(
            "K653: Include K647 DOT-BTC orthog close summary during emergency exit. "
            "K647 positions (DOT+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = DOT_diff - 0.642*INJ_diff (K647 OLS SF beta hardcoded). "
            "EMA window: W=168h = 21 x 8h periods (optimal per K647 analysis). "
            "HL concentration 64% (1pp headroom from 65% — 3% split HL 1.5%+Bybit 1.5%). "
            "OOS Sharpe 23.25 (residual SF W=168h). ~$103,586/yr net @$10M @4x (3% sleeve). "
            "60d paper-trade gate STRICT: Realized Sh>=12 + fill>=60% + maxDD<15% (OOS R²=-4.11 caution). "
            "IS beta re-OLS every 30d mandatory (structural break: IS DOT-INJ corr=0.616 -> OOS=0.045). "
            "Cluster: Governance/Staking / Polkadot relay chain (INJ-cluster unlock, 8th orthog, 48th daemon). "
            "INJ unlock: K513 BLOCKED (corr=0.4229) -> K647 post-orth=0.037 PASS. "
            "Requires: K647 daemon running (com.cryptolab.k647-dot-orthog, 48th daemon). "
            "K647 on Bybit: DOT_diff - 0.642*INJ_diff (K653 scaffold). "
            "See: docs/k302a_runbook.md §49"
        ),
    )

    # K669: K658 SOL-ETH FR Differential emergency exit flag
    # K658 = HL-primary SOL+ETH paired (2 legs) when sign(rolling_mean_168h(SOL_FR - ETH_FR)) != 0.
    # Close protocol: IOC reduce-only on HL (BOTH legs on HL — HL concentration affected).
    # Signal: diff = SOL_FR - ETH_FR (direct, W=168h rolling mean, zero threshold).
    # ETH-base wins: SOL-BTC K476 PnL corr=0.2131 PASS; dual sleeve K476 1.5% + K658 1.5%.
    # 52nd daemon — K669 scaffold.
    # Use --include-k658 to print K658-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k658",
        dest="include_k658",
        action="store_true",
        default=False,
        help=(
            "K669: Include K658 SOL-ETH close summary during emergency exit. "
            "K658 positions (SOL+ETH paired, HL-primary) ARE included in HL emergency exit. "
            "This flag adds a structured K658-specific close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = SOL_FR - ETH_FR (direct differential, W=168h rolling mean, sign threshold). "
            "HL concentration: neutral (K476 reduced 4%->1.5%, K658 adds 1.5% = net unchanged). "
            "OOS Sharpe 29.66 (ETH-base wins vs K476 Sh=16.30 +13.36). $42,332/yr @$10M @4x (1.5% sleeve). "
            "Dual-sleeve: K476 SOL-BTC 1.5% + K658 SOL-ETH 1.5% = ~$85K/yr est @$10M. "
            "K476 PnL corr=0.2131 PASS (diversified dual sleeve). K449 ETH-BTC critical corr=0.0488. "
            "60d paper-trade gate: Realized Sh>=15 + fill>=60% + maxDD<15%. "
            "Cluster: SOL L1 Monolithic SVM / DePIN-Retail (ETH-base wins, 52nd daemon). "
            "Requires: K658 daemon running (com.cryptolab.k658-sol-eth, 52nd daemon). "
            "See: docs/k302a_runbook.md §53"
        ),
    )

    # K668: K663 TIA-ETH FR Differential emergency exit flag
    # K663 = HL-primary TIA+ETH paired (2 legs) when sign(rolling_mean_168h(TIA_FR - ETH_FR)) != 0.
    # Close protocol: IOC reduce-only on HL (BOTH legs on HL — HL concentration affected).
    # Signal: diff = TIA_FR - ETH_FR (direct, W=168h rolling mean, zero threshold).
    # ETH-base K660 SURPRISE: G5b TIA-BTC K507 corr=0.2309 PASS (K660 predicted BLOCKED-APT-style).
    # Dual-sleeve: K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = 3.0% total sleeve.
    # Use --include-k663 to print K663-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k663",
        dest="include_k663",
        action="store_true",
        default=False,
        help=(
            "K668: Include K663 TIA-ETH close summary during emergency exit. "
            "K663 positions (TIA+ETH paired, HL-primary) ARE included in HL emergency exit. "
            "This flag adds a structured K663-specific close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = TIA_FR - ETH_FR (direct differential, W=168h rolling mean, zero threshold). "
            "HL concentration: ~61.0% post-K663 (within 65% limit, +1.5pp from ~59.5%). "
            "OOS Sharpe 17.13 (9/9 §6 PASS, IS=31.31, ratio=0.548). $63,060/yr net @$10M @4x (1.5% sleeve). "
            "Dual-sleeve: K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = ~$114,598/yr net @$10M. "
            "G5b corr=0.2309 PASS (K660 predicted BLOCKED-APT-style; TIA vol_ratio=2.12x DA spikes). "
            "60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<15%. "
            "Cluster: Modular DA / Celestia (ETH-base K660 SURPRISE, 51st daemon). "
            "Requires: K663 daemon running (com.cryptolab.k663-tia-eth, 51st daemon). "
            "See: docs/k302a_runbook.md §52"
        ),
    )

    # K677: K661 AVAX-ETH FR Differential emergency exit flag
    # K661 = HL-primary AVAX+ETH paired (2 legs) when sign(rolling_mean_168h(AVAX_FR - ETH_FR)) != 0.
    # Close protocol: IOC reduce-only on HL (BOTH legs on HL — HL concentration affected).
    # Signal: diff = AVAX_FR - ETH_FR (direct, W=168h rolling mean, zero threshold).
    # ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89; PnL corr=0.3731 PASS dual-sleeve.
    # G5a ETH-BTC K449 corr=-0.008 (CRITICAL shared-leg check — minimal HL ETH leg risk).
    # Dual-sleeve: K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = 3.0% total sleeve.
    # Use --include-k661 to print K661-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k661",
        dest="include_k661",
        action="store_true",
        default=False,
        help=(
            "K677: Include K661 AVAX-ETH close summary during emergency exit. "
            "K661 positions (AVAX+ETH paired, HL-primary) ARE included in HL emergency exit. "
            "This flag adds a structured K661-specific close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = AVAX_FR - ETH_FR (direct differential, W=168h rolling mean, zero threshold). "
            "HL concentration: ~64.0% post-K661 (within 65% limit, +~1.5pp from ~62.5%). "
            "OOS Sharpe 28.26 (6/7 §6 gates, G6 structural 18.6/yr). $63,416/yr net @$10M @4x (1.5% sleeve). "
            "Dual-sleeve: K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = ~$139,099/yr net @$10M. "
            "G5a K449 ETH-BTC corr=-0.008 PASS (CRITICAL: shared ETH leg minimal risk). "
            "G5b K484 AVAX-BTC corr=0.3731 PASS (family orthogonality — dual eligible). "
            "ACCEPT CONDITIONAL: BTC-base (K484) marginally superior Sh=43.89; but dual-sleeve justified. "
            "60d paper-trade gate: Realized Sh>=14 + fill>=60% + maxDD<15%. "
            "Cluster: AVAX Subnet/RWA (Avalanche9000, RWA tokenization, ETH-base, 53rd daemon). "
            "Requires: K661 daemon running (com.cryptolab.k661-avax-eth, 53rd daemon). "
            "See: docs/k302a_runbook.md §54"
        ),
    )

    # K659: K656 GALA-BTC dual-factor orthog emergency exit flag
    # K656 = Bybit-only GALA+BTC paired (2 legs) when residual rolling_mean_504h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL cap 66.5% > 65%, Bybit-only mandatory).
    # Orthog: residual = GALA_diff - 0.22738*JUP_diff - 0.405439*FIL_diff (K656 OLS DF, betas hardcoded).
    # Rolling window: W=504h = 63 x 8h periods (optimal per K656 analysis, DF dual-factor).
    # 50th daemon MILESTONE — 9th orthog scaffold — gaming cluster COMPLETE.
    # Use --include-k656 to print K656-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k656",
        dest="include_k656",
        action="store_true",
        default=False,
        help=(
            "K659: Include K656 GALA-BTC dual-factor orthog close summary during emergency exit. "
            "K656 positions (GALA+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = GALA_diff - 0.22738*JUP_diff - 0.405439*FIL_diff (K656 OLS DF betas hardcoded). "
            "Rolling window: W=504h = 63 x 8h periods (optimal per K656 dual-factor analysis). "
            "HL concentration: UNCHANGED at 64.5% (Bybit-only; HL cap breach 66.5% > 65%). "
            "OOS Sharpe 8.3211 (residual DF W=504h). $48,143/yr net @$10M @4x (2% sleeve). "
            "60d paper-trade gate: Realized Sh>=4 + fill>=60% + maxDD<20%. "
            "K620 dual blockers cleared: JUP 0.4308->0.0495, FIL 0.4114->0.0184. "
            "IS R²=0.4731 LARGEST in K6xx series (FIRST dual-factor JUP+FIL orthog). "
            "Gaming cluster COMPLETE: SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) all ACCEPT COND. "
            "Cluster: Gaming Publisher / Gala Games P2E / GalaChain L1 (9th orthog, 50th daemon MILESTONE). "
            "Requires: K656 daemon running (com.cryptolab.k656-gala-orthog, 50th daemon). "
            "K656 on Bybit: GALA_diff - 0.22738*JUP_diff - 0.405439*FIL_diff (K659 scaffold). "
            "See: docs/k302a_runbook.md §51"
        ),
    )

    # K683: K679 APT-SOL FR Differential emergency exit flag
    # K679 = Bybit-only APT+SOL paired (2 legs, FIRST ALT-ALT pair).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL at 65.5% OVER cap, Bybit-only).
    # Signal: diff = APT_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold).
    # K512+K476 overlap warning: K679 STANDALONE — close K679 independently of K512/K476.
    # Bybit-only: APT-PERP + SOL-PERP both on Bybit. HL UNCHANGED at 65.5%.
    # Use --include-k679 to print K679-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k679",
        dest="include_k679",
        action="store_true",
        default=False,
        help=(
            "K683: Include K679 APT-SOL close summary during emergency exit. "
            "K679 positions (APT+SOL paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = APT_FR - SOL_FR (direct alt-alt differential, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 65.5% (Bybit-only — HL OVER cap, no HL positions). "
            "OOS Sharpe 39.29 (FIRST ALT-ALT pair record). $234,700/yr net @$10M @4x (3% standalone sleeve). "
            "K512+K476 overlap: close K679 STANDALONE (do not assume K512 APT-BTC / K476 SOL-BTC netting). "
            "60d paper-trade gate: Realized Sh>=20 + fill>=60% + maxDD<15%. "
            "APT FR: Move-VM Block-STM adoption cycles (Aptos Foundation, Move ecosystem events). "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, validator economics). "
            "Cluster: APT-SOL Alt-Alt (Move-VM vs SVM, FIRST ALT-ALT, 55th daemon). "
            "Requires: K679 daemon running (com.cryptolab.k679-apt-sol, 55th daemon). "
            "See: docs/k302a_runbook.md §55"
        ),
    )

    # K685: K682 ATOM-SOL FR Differential emergency exit flag
    # K682 = Bybit-only ATOM+SOL paired (2 legs, SECOND ALT-ALT pair).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL at 62.5%, Bybit-only preferred).
    # Signal: diff = ATOM_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold).
    # K493+K476 overlap warning: K682 STANDALONE — close K682 independently of K493/K476.
    # Anti-corr: K682 vs K493 = -0.5195 (HEDGES K493 portfolio exposure). Close independently.
    # Bybit-only: ATOM-PERP + SOL-PERP both on Bybit. HL UNCHANGED at 62.5%.
    # Use --include-k682 to print K682-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k682",
        dest="include_k682",
        action="store_true",
        default=False,
        help=(
            "K685: Include K682 ATOM-SOL close summary during emergency exit. "
            "K682 positions (ATOM+SOL paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = ATOM_FR - SOL_FR (direct alt-alt differential, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 62.5% (Bybit-only — no HL positions). "
            "OOS Sharpe 43.43 (SECOND ALT-ALT pair, > K679 39.29). $214,638/yr net @$10M @4x (2% standalone sleeve). "
            "K493+K476 overlap: close K682 STANDALONE. Anti-corr K682/K493=-0.5195 (HEDGES K493, close independently). "
            "Math identity: ATOM-SOL = -(BTC-ATOM) + (BTC-SOL) = -K493_dir + K476_dir. "
            "60d paper-trade gate: Realized Sh>=22 + fill>=60% + maxDD<15%. "
            "ATOM FR: Cosmos IBC governance-driven episodics (new chain launches, staking inflation -3.27%/ann). "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, validator economics, +7.73%/ann). "
            "Cluster: ATOM-SOL Alt-Alt (Cosmos IBC vs SVM DePIN-Retail, SECOND ALT-ALT, 55th daemon 2nd). "
            "Requires: K682 daemon running (com.cryptolab.k682-atom-sol). "
            "See: docs/k302a_runbook.md §57"
        ),
    )

    # K687: K684 SOL-INJ FR Differential emergency exit flag
    # K684 = Bybit-only SOL+INJ paired (2 legs, THIRD ALT-ALT pair).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — Bybit-only preferred, HL stays at 62.5%).
    # Signal: diff = SOL_FR - INJ_FR (direct alt-alt, W=168h rolling mean, zero threshold).
    # K476+K500 overlap warning: K684 STANDALONE — close K684 independently of K476/K500.
    # K679 SOL-exposure: K684 + K679 share SOL leg — close independently, monitor SOL exposure.
    # Bybit-only: SOL-PERP + INJ-PERP both on Bybit. HL UNCHANGED at 62.5%.
    # Use --include-k684 to print K684-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k684",
        dest="include_k684",
        action="store_true",
        default=False,
        help=(
            "K687: Include K684 SOL-INJ close summary during emergency exit. "
            "K684 positions (SOL+INJ paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = SOL_FR - INJ_FR (direct alt-alt differential, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 62.5% (Bybit-only — no HL positions, headroom preserved). "
            "OOS Sharpe 9.65 (THIRD ALT-ALT pair, 216d OOS). $114,316/yr net @$10M @4x (3% standalone sleeve). "
            "K476+K500 algebraic overlap: SOL-INJ = K476_dir - K500_dir. Close K684 STANDALONE. "
            "K679 SOL-exposure: K684 + K679 share SOL leg — close independently, monitor SOL notional. "
            "Math identity: SOL-INJ = (SOL-BTC) - (INJ-BTC) = K476_dir - K500_dir. "
            "60d paper-trade gate: Realized Sh>=5 + fill>=60% + maxDD<15%. "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, ETF speculation, +7.7% ann). "
            "INJ FR: Cosmos DeFi perp DEX (liquidation cascades, INJ burn, IBC bridge, +3.6% ann episodic). "
            "Cluster: SOL-INJ Alt-Alt (SVM DePIN-Retail vs Cosmos-DeFi-Perp, THIRD ALT-ALT, 56th daemon). "
            "Requires: K684 daemon running (com.cryptolab.k684-sol-inj, 56th daemon). "
            "See: docs/k302a_runbook.md §58"
        ),
    )

    # K689: K686 AVAX-SOL FR Differential emergency exit flag
    # K686 = Bybit-only AVAX+SOL paired (2 legs, FOURTH ALT-ALT pair).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — Bybit-only preferred, HL stays at 62.5%).
    # Signal: diff = AVAX_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold).
    # K484+K476 overlap warning: K686 STANDALONE — close K686 independently of K484/K476.
    # K682/K679 SOL-exposure: K686+K682+K679 share SOL leg — close independently, monitor SOL.
    # Bybit-only: AVAX-PERP + SOL-PERP both on Bybit. HL UNCHANGED at 62.5%.
    # Use --include-k686 to print K686-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k686",
        dest="include_k686",
        action="store_true",
        default=False,
        help=(
            "K689: Include K686 AVAX-SOL close summary during emergency exit. "
            "K686 positions (AVAX+SOL paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = AVAX_FR - SOL_FR (direct alt-alt differential, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 62.5% (Bybit-only — no HL positions, headroom preserved). "
            "OOS Sharpe 50.27 (FOURTH ALT-ALT pair, HIGHEST Sh in alt-alt family). $102,153/yr net @$10M @4x (3% standalone sleeve). "
            "K484+K476 algebraic overlap: AVAX-SOL = K484_dir - K476_dir. Close K686 STANDALONE. "
            "Anti-corr K686 vs K484 = -0.6295 (K686 HEDGES K484 long-AVAX exposure). "
            "K682/K679 SOL-exposure: K686+K682+K679 share SOL leg — close independently, monitor SOL notional. "
            "Math identity: AVAX-SOL = (AVAX-BTC) - (SOL-BTC) = K484_dir - K476_dir. "
            "Same-tier L1 exception: AVAX/SOL vol ratio=0.85x. ADF stat -13.99, OU half-life=3.6h (FASTEST). "
            "60d paper-trade gate: Realized Sh>=25 + fill>=60% + maxDD<15%. "
            "AVAX FR: Subnet launches, Avalanche9000, RWA institutional, HFT colocation (+6.39% ann episodic). "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, ETF speculation, +7.73% ann). "
            "Cluster: AVAX-SOL Alt-Alt (Avalanche Subnet institutional vs Solana SVM retail, FOURTH ALT-ALT, 57th daemon). "
            "Requires: K686 daemon running (com.cryptolab.k686-avax-sol, 57th daemon). "
            "See: docs/k302a_runbook.md §59"
        ),
    )

    # K693: K690 SEI-SOL FR Differential emergency exit flag
    # K690 = Bybit-only SEI+SOL paired (2 legs, FIFTH ALT-ALT pair).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — Bybit-only preferred, HL stays at 62.5%).
    # Signal: diff = SEI_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold).
    # K507+K476 overlap warning: K690 STANDALONE — close K690 independently of K507/K476.
    # K682/K686 SOL-exposure: K690+K682+K686 share SOL leg — close independently, monitor SOL.
    # Bybit-only: SEI-PERP + SOL-PERP both on Bybit. HL UNCHANGED at 62.5%.
    # Use --include-k690 to print K690-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k690",
        dest="include_k690",
        action="store_true",
        default=False,
        help=(
            "K693: Include K690 SEI-SOL close summary during emergency exit. "
            "K690 positions (SEI+SOL paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = SEI_FR - SOL_FR (direct alt-alt differential, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 62.5% (Bybit-only — no HL positions, headroom preserved). "
            "OOS Sharpe 25.11 (FIFTH ALT-ALT pair, WF 12/12 UNPRECEDENTED). $104,174/yr net @$10M @4x (3% standalone sleeve). "
            "K507+K476 algebraic overlap: SEI-SOL = K507_dir - K476_dir. Close K690 STANDALONE. "
            "Anti-corr K690 vs K507 = -0.5109 (K690 HEDGES K507 long-SEI exposure). "
            "K682/K686 SOL-exposure: K690+K682+K686 share SOL leg — close independently, monitor SOL notional. "
            "Math identity: SEI-SOL = (SEI-BTC) - (SOL-BTC) = K507_dir - K476_dir. "
            "Mid-cap alt-alt exception: SEI/SOL vol ratio=1.32x. ADF stat -12.7158 (p=1.01e-23), OU half-life=4.41h (STRONG). "
            "60d paper-trade gate: Realized Sh>=12 + fill>=60% + maxDD<15%. "
            "SEI FR: Cosmos EVM parallel chain demand, DeFi/CosmWasm launches, NEGATIVE mean -3.65%/ann (short-sellers dominate). "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, ETF speculation, +7.70% ann). "
            "Cluster: SEI-SOL Alt-Alt (Cosmos EVM parallel vs Solana SVM retail, FIFTH ALT-ALT, 58th daemon). "
            "Requires: K690 daemon running (com.cryptolab.k690-sei-sol, 58th daemon). "
            "See: docs/k302a_runbook.md §60"
        ),
    )

    # K697: K694 TIA-SOL FR Differential emergency exit flag
    # K694 = Bybit-only TIA+SOL paired (2 legs, SIXTH ALT-ALT pair, CONDITIONAL).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — Bybit-only preferred, HL stays at 62.5%).
    # Signal: diff = TIA_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold).
    # K476 overlap: TIA-SOL = K_TIA_BTC - K476_dir — close K694 standalone.
    # SOL-exposure: K694+K679+K682+K684+K686+K690 all share SOL leg — close independently.
    # Bybit-only: TIA-PERP + SOL-PERP both on Bybit. HL UNCHANGED at 62.5%.
    # Use --include-k694 to print K694-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k694",
        dest="include_k694",
        action="store_true",
        default=False,
        help=(
            "K697: Include K694 TIA-SOL close summary during emergency exit. "
            "K694 positions (TIA+SOL paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = TIA_FR - SOL_FR (direct alt-alt differential, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 62.5% (Bybit-only — no HL positions, headroom preserved). "
            "HL-only would push HL to 65.5% (OVER 65% cap) — Bybit-only mandatory for K694. "
            "OOS Sharpe 19.09 (SIXTH ALT-ALT pair, CONDITIONAL G4 11/12). $58,354/yr net @$10M @4x (3% standalone). "
            "K691 lesson: TIA-APT REJECT (G5b APT corr=0.4712). K694 TIA-SOL: SOL saturation PASS (corr=0.2275). "
            "K476 decomposition: TIA-SOL = K_TIA_BTC_dir - K476_dir. Close K694 STANDALONE. "
            "Natural SOL-short hedge: K694 BULL_TIA offsets SOL-long in K679+K682+K686+K690. "
            "SOL exposure: K694+K679+K682+K684+K686+K690 all have SOL leg — close independently, monitor SOL notional. "
            "TIA FR: Celestia DA demand (rollup blob fees, episodic +1.08%/ann). "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF/POPCAT, Firedancer, ETF, +7.70% ann). "
            "Cluster: TIA-SOL Alt-Alt (Celestia DA vs Solana SVM retail, SIXTH ALT-ALT, 59th daemon). "
            "Requires: K694 daemon running (com.cryptolab.k694-tia-sol, 59th daemon). "
            "See: docs/k302a_runbook.md §61"
        ),
    )

    # K699: K696 ENA-SOL FR Differential emergency exit flag
    # K696 = Bybit-only ENA+SOL paired (2 legs, SEVENTH ALT-ALT pair, FIRST CROSS-CLUSTER, ACCEPT).
    # Close protocol: IOC reduce-only on Bybit (NOT HL — Bybit-only preferred, HL stays at 62.5%).
    # Signal: diff = ENA_FR - SOL_FR (direct alt-alt cross-cluster, W=168h rolling mean, zero threshold).
    # MR6 ENA cap: K616 (existing ENA-BTC) + K696 (ENA-SOL) combined ENA — close K696 standalone.
    # SOL-exposure: K696+K694+K690+K686+K684+K682+K679+K476 all share SOL leg — close independently.
    # Bybit-only: ENA-PERP + SOL-PERP both on Bybit. HL UNCHANGED at 62.5%.
    # Use --include-k696 to print K696-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k696",
        dest="include_k696",
        action="store_true",
        default=False,
        help=(
            "K699: Include K696 ENA-SOL close summary during emergency exit. "
            "K696 positions (ENA+SOL paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = ENA_FR - SOL_FR (direct alt-alt cross-cluster, W=168h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 62.5% (Bybit-only — no HL positions, headroom preserved). "
            "HL-only would push HL to 65.5% (OVER 65% cap) — Bybit-only mandatory for K696. "
            "OOS Sharpe 26.93 (SEVENTH ALT-ALT, FIRST CROSS-CLUSTER, ACCEPT 15/17 gates G4 11/12). $93,187/yr net @$10M @4x (3% standalone). "
            "MR6 ENA cap: K616 ENA-BTC + K696 ENA-SOL combined ENA < 6% AUM — close K696 STANDALONE from K616. "
            "MR8/MR9: ENA new vertex (outside alt-alt algebraic group). ENA-SOL = K616_dir - K476_dir (K616 perp K476, corr=0.0094). "
            "G5b K476 corr=0.1765 PASS. G5c K616 corr=-0.7427 signed PASS (PnL corr=0.6723 complementary). "
            "ENA FR: Ethena sUSDe protocol equity (sUSDe yield = stETH + perp short capture, -7.65%/ann mean). "
            "SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF/POPCAT, Firedancer, ETF, +7.70% ann persistent). "
            "Double carry: ENA FR < 0 (37.2% of time) — SHORT ENA earns |ENA FR| + SHORT SOL earns SOL FR simultaneously. "
            "SOL exposure: K696+K694+K690+K686+K684+K682+K679+K476 share SOL (8 strategies) — close independently, monitor combined SOL notional. "
            "Cluster: ENA-SOL Alt-Alt FIRST CROSS-CLUSTER (synth stable infra vs SVM retail, 60th daemon MILESTONE). "
            "Requires: K696 daemon running (com.cryptolab.k696-ena-sol, 60th daemon). "
            "See: docs/k302a_runbook.md §62"
        ),
    )

    # K701: K698 LINK-ETH emergency exit flag
    # K698 = Bybit-only LINK+ETH paired (2 legs), direct FR differential W=120h rolling mean.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 64.5%).
    # Bybit-only: HL-only would push HL from 64.5% to 67.0% > 65% cap.
    # LINK-ETH: oracle middleware (Chainlink) vs Ethereum L1 (DeFi/staking). 4th ETH-base scaffold.
    # Use --include-k698 to print K698-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k698",
        dest="include_k698",
        action="store_true",
        default=False,
        help=(
            "K701: Include K698 LINK-ETH close summary during emergency exit. "
            "K698 positions (LINK+ETH paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Signal: diff = LINK_FR - ETH_FR (direct differential, W=120h rolling mean, zero threshold). "
            "HL concentration UNCHANGED at 64.5% (Bybit-only — HL-only would push to 67.0% > 65% cap). "
            "OOS Sharpe 12.07 (W=120h, 8/8 §6 gates, oracle vs ETH L1). $28,997/yr net @$10M @4x (2.5% sleeve). "
            "G5a K557 LINK-BTC critical: corr=0.0578 PASS. G5b K449 ETH-BTC critical: corr=-0.0036 PASS. "
            "K695 lesson: LINK-SOL REJECTED G5c=0.497. K698 avoids SOL leg — clean oracle expansion. "
            "MR9: LINK-ETH = LINK-BTC - ETH-BTC (max_err=5.42e-20). Position corr=0.1254 de-correlated. "
            "K557 coordination: LINK in K557 1.5% + K698 2.5% = 4.0% max combined LINK AUM. "
            "LINK FR: oracle demand (Chainlink integrations, CCIP, feed launches, MM floor ~1.25e-5/hr). "
            "ETH FR: DeFi/staking yields (stETH/LST demand, Pectra upgrades, L1 gas). "
            "Cluster: Oracle middleware vs Ethereum L1 (4th ETH-base scaffold, 1st oracle-ETH pair, 61st daemon). "
            "Requires: K698 daemon running (com.cryptolab.k698-link-eth, 61st daemon). "
            "See: docs/k302a_runbook.md §62"
        ),
    )

    # K750: K747 TAO-SOL alt-alt emergency exit flag
    # K747 = HL-only TAO+SOL paired (2 legs) on HL (TAO-PERP + SOL-PERP, maxLeverage=5).
    # Close protocol: IOC reduce-only on HL (short leg first, then long leg).
    # Signal: W=168h rolling mean of (TAO_FR - SOL_FR), zero threshold.
    # HL concentration: 65.0% AT CAP (paper-gate strict — PAPER_TRADE=True until K498 OKX).
    # G8 FAIL: Bybit TAO 84.6% floor-capped (structural). K735 precedent. HL-only mandatory.
    # G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED (best WF in alt-alt family).
    # TAO = 13th vertex. MR9 L002: all future TAO-X pairs blocked.
    # Use --include-k747 to print K747-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k747",
        dest="include_k747",
        action="store_true",
        default=False,
        help=(
            "K750: Include K747 TAO-SOL close summary during emergency exit. "
            "K747 positions (TAO+SOL paired, HL-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = TAO_FR - SOL_FR (direct differential, W=168h rolling mean, zero threshold). "
            "HL-only: TAO-PERP + SOL-PERP both on HL (maxLeverage=5, asset index=116). "
            "HL concentration 65.0% AT CAP (paper-gate strict — PAPER_TRADE=True default). "
            "G8 FAIL: Bybit TAO 84.6% floor-capped (structural). K735 HBAR-SOL precedent. "
            "OOS Sharpe 12.233 (W=168h). G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED. "
            "G5c AVAX bypass: 0.0126 PASS (AI L1 != AVAX subnet cluster). "
            "TAO = 13th vertex. MR9 L002: all future TAO-X auto-blocked. "
            "K523 central $17,210/yr net @$10M @4x (2.5% sleeve). "
            "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%. "
            "Live trigger: K498 OKX activation (HL% < 65%) + 60d gate. "
            "Cluster: Bittensor AI L1 × Solana SVM (15th alt-alt, 69th daemon). "
            "Requires: K747 daemon running (com.cryptolab.k747-tao-sol, 69th daemon). "
            "See: docs/k302a_runbook.md §63"
        ),
    )

    # K756: K754 PEPE-SOL alt-alt emergency exit flag
    # K754 = HL primary PEPE+SOL paired (2 legs) on HL (PEPE-PERP + SOL-PERP).
    # Close protocol: IOC reduce-only on HL (short leg first, then long leg).
    # Signal: W=84h rolling mean of (PEPE_FR - SOL_FR), zero threshold. G6-safe (64/yr).
    # HL concentration: 66.8% AT CAP (K751 audit, paper-gate strict — PAPER_TRADE=True until K498/v6.52).
    # G4 WF 12/12 ALL POSITIVE (min_sh=5.56). 22/22 G5 PASS (max_corr=0.247).
    # PEPE = 14th vertex. MR9 L002: all future PEPE-X pairs blocked.
    # L003/L010 proximity warning: monthly AVAX/HBAR recheck required.
    # Use --include-k754 to print K754-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k754",
        dest="include_k754",
        action="store_true",
        default=False,
        help=(
            "K756: Include K754 PEPE-SOL close summary during emergency exit. "
            "K754 positions (PEPE+SOL paired, HL primary) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = PEPE_FR - SOL_FR (direct differential, W=84h rolling mean, zero threshold). "
            "HL primary: PEPE-PERP + SOL-PERP both on HL. Bybit fallback (1000PEPE denomination). "
            "HL concentration 66.8% AT CAP (K751 audit — paper-gate strict — PAPER_TRADE=True default). "
            "G4 WF 12/12 ALL POSITIVE (min_sh=5.56). 22/22 G5 PASS (max_corr=0.247 G5l SEI-SOL). "
            "G6: 64.2 entries/yr OOS PASS (W=84h G6-safe vs W=168h 29.5/yr FAIL). "
            "OOS Sharpe 44.43 (W=84h). MaxDD OOS=-0.107% (very contained). "
            "L003 AVAX: raw_corr=0.4125 PASS — proximity warning, monthly recheck. "
            "L010 HBAR: raw_corr=0.4272 PASS — proximity warning, monthly recheck. "
            "PEPE = 14th vertex. MR9 L002: all future PEPE-X auto-blocked. "
            "K523 central $62,000/yr net @$10M @4x (2.5% sleeve). "
            "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%. "
            "Live trigger: K498/v6.52 OKX activation (HL% < 65%) + 60d gate. "
            "Cluster: Ethereum ERC-20 meme leader × Solana SVM (16th alt-alt, 71st daemon). "
            "Requires: K754 daemon running (com.cryptolab.k754-pepe-sol, 71st daemon). "
            "See: docs/k302a_runbook.md §71"
        ),
    )

    # K761: K759 WIF-SOL alt-alt emergency exit flag
    # K759 = HL primary WIF+SOL paired (2 legs) on HL (WIF-PERP + SOL-PERP).
    # Close protocol: IOC reduce-only on HL (short leg first, then long leg).
    # Signal: W=168h rolling mean of (WIF_FR - SOL_FR), zero threshold. G6-safe (31.2/yr).
    # HL concentration: 66.8% AT CAP (K751 audit, paper-gate strict — PAPER_TRADE=True until K498/v6.52).
    # G4 WF 12/12 ALL POSITIVE (min_sh=9.895). G5 all PASS (max_corr=0.3819 G5w PEPE-SOL).
    # G5w PEPE-SOL=0.382 (0.018 margin) → reduced sleeve 2.0% (vs 2.5% standard).
    # L011 borderline: raw_corr(WIF,SOL)=0.487 — monthly recheck required.
    # WIF = 15th vertex. MR9 L002: all future WIF-X pairs blocked.
    # Use --include-k759 to print K759-specific HL close summary during emergency exit.
    parser.add_argument(
        "--include-k759",
        dest="include_k759",
        action="store_true",
        default=False,
        help=(
            "K761: Include K759 WIF-SOL close summary during emergency exit. "
            "K759 positions (WIF+SOL paired, HL primary) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on HL (short leg first, then long leg). "
            "Signal: diff = WIF_FR - SOL_FR (direct differential, W=168h rolling mean, zero threshold). "
            "HL primary: WIF-PERP + SOL-PERP both on HL. Bybit fallback (WIFUSDT). "
            "HL concentration 66.8% AT CAP (K751 audit — paper-gate strict — PAPER_TRADE=True default). "
            "G4 WF 12/12 ALL POSITIVE (min_sh=9.895). G5 all PASS (max_corr=0.3819 G5w PEPE-SOL). "
            "G5w PEPE-SOL=0.382 (0.018 margin) → reduced sleeve 2.0% (vs 2.5% standard). "
            "G6: 31.2 entries/yr OOS PASS (W=168h G6-safe vs 30/yr minimum). "
            "OOS Sharpe 24.45 (W=168h). MaxDD OOS=-0.216% (very contained). "
            "L011 raw_corr(WIF,SOL)=0.487 PASS (< 0.50 SOL-ecosystem threshold, borderline). "
            "OOS L011 corr=0.054 (near-zero — regime-switch cleans signal). Monthly recheck. "
            "L003 AVAX: raw_corr=0.3823 PASS. L010 HBAR: raw_corr=0.4011 PASS. "
            "WIF = 15th vertex. MR9 L002: all future WIF-X auto-blocked. "
            "K523 central $54,245/yr net @$10M @4x (2.0% sleeve, reduced from 2.5%). "
            "60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%. "
            "Live trigger: K498/v6.52 OKX activation (HL% < 65%) + 60d gate. "
            "Cluster: Solana meme × Solana SVM (17th alt-alt, 72nd daemon). "
            "Requires: K759 daemon running (com.cryptolab.k759-wif-sol, 72nd daemon). "
            "See: docs/k302a_runbook.md §72"
        ),
    )

    # K639: K631 WLD-BTC orthog emergency exit flag
    # K631 = Bybit-only WLD+BTC paired (2 legs) when residual EMA_72h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = WLD_diff - 0.458795*JUP_diff (K631 OLS, beta hardcoded).
    # EMA window: W=72h = 9 x 8h periods (optimal per K631 sweep).
    # Use --include-k631 to print K631-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k631",
        dest="include_k631",
        action="store_true",
        default=False,
        help=(
            "K639: Include K631 WLD-BTC orthog close summary during emergency exit. "
            "K631 positions (WLD+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = WLD_diff - 0.458795*JUP_diff (K631 OLS beta hardcoded). "
            "EMA window: W=72h = 9 × 8h periods (optimal per K631 sweep). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 18.04 (residual W=72h). $2.9M/yr @$10M @4x (2% sleeve). "
            "60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<20%. "
            "Cluster: Biometric ID / World ID (privacy-tech + AI-identity narrative). "
            "Requires: K631 daemon running (com.cryptolab.k631-wld-orthog, 41st daemon). "
            "See: docs/k302a_runbook.md §43"
        ),
    )

    # K640: K633 OP-BTC orthog emergency exit flag
    # K633 = Bybit-only OP+BTC paired (2 legs) when residual EMA_72h > 1.5sigma.
    # Close protocol: IOC reduce-only on Bybit (NOT HL — HL concentration UNCHANGED at 65%).
    # Orthog: residual = OP_diff - 0.542224*FIL_diff (K633 OLS, beta hardcoded).
    # EMA window: W=72h = 9 x 8h periods (optimal per K633 sweep).
    # Use --include-k633 to print K633-specific Bybit close summary during emergency exit.
    parser.add_argument(
        "--include-k633",
        dest="include_k633",
        action="store_true",
        default=False,
        help=(
            "K640: Include K633 OP-BTC orthog close summary during emergency exit. "
            "K633 positions (OP+BTC paired, Bybit-only) are detected automatically; "
            "this flag adds a structured close summary. "
            "Close protocol: IOC reduce-only on Bybit (short leg first, then long leg). "
            "Orthog: residual = OP_diff - 0.542224*FIL_diff (K633 OLS beta hardcoded). "
            "EMA window: W=72h = 9 × 8h periods (optimal per K633 sweep). "
            "HL concentration UNCHANGED (Bybit-only strategy — HL NOT affected). "
            "OOS Sharpe 12.68 (residual W=72h). $2.32M/yr @$10M @4x (full potential). "
            "2% sleeve: $46,373/yr carry contribution. "
            "60d paper-trade gate: Realized Sh>=5 + fill>=60% + maxDD<20%. "
            "Cluster: L2 Rollup / Optimism Superchain (L2 cluster unlock, 42nd daemon). "
            "Requires: K633 daemon running (com.cryptolab.k633-op-orthog, 42nd daemon). "
            "See: docs/k302a_runbook.md §44"
        ),
    )

    # K502: K495 DEX-CEX flow divergence bear-conditional emergency exit flag
    # K495 = LONG BTC+ETH+SOL on HL (3 legs) when DEX-CEX z-score > 1.0 in bear regime.
    # Close protocol: IOC market orders (reduce-only) BTC → ETH → SOL (largest notional first).
    # Bear-conditional: gate closes on bull-regime flip (90d BTC return >= 0).
    # Auto-exit via bear-gate flip is already in k495_dex_cex_flow_run.py (daily cron).
    # Use --include-k495 to print K495-specific close summary during emergency exit.
    parser.add_argument(
        "--include-k495",
        dest="include_k495",
        action="store_true",
        default=False,
        help=(
            "K502: Include K495 DEX-CEX flow divergence close summary during emergency exit. "
            "K495 positions (LONG BTC+ETH+SOL, HL-only, 3 legs) are detected automatically "
            "via _detect_k495_position(); this flag adds a structured summary. "
            "Close protocol: IOC reduce-only BTC → ETH → SOL (largest notional first). "
            "All 3 legs on HyperLiquid only. Bear-conditional: bear gate auto-closes on BULL flip. "
            "OOS Sharpe bear-conditional 4.59. $323K/yr net @$10M. "
            "Orthogonal to FR-carry: corr K208=-0.017, K280=0.008, K449=0.107. "
            "Requires: K495 daemon running (com.cryptolab.k495-dex-cex-flow). "
            "See: docs/k302a_runbook.md §39"
        ),
    )

    # K473: Spark sUSDS (Sky/MakerDAO) emergency exit flag (stub scaffold — Ethereum DeFi)
    # sUSDS is an Ethereum DeFi yield position — NOT a perp/futures position on HL/Bybit/OKX.
    # Redemption is instant (no lockup). No HL delta hedge required.
    # Activated as part of K473 50/50 sUSDe+sUSDS sleeve (v6.21 candidate).
    parser.add_argument(
        "--include-spark",
        dest="include_spark",
        action="store_true",
        default=False,
        help=(
            "K473: Print Spark sUSDS emergency exit guidance (Ethereum DeFi STUB scaffold). "
            "STUB only — Ethereum wallet signing required (user responsibility). "
            "sUSDS is NOT on HL/Bybit/OKX — manual redeem at app.spark.fi or sky.money. "
            "Redemption is INSTANT (no lockup). No HL delta hedge needed. "
            "K473 monitor: scripts/spark_usds_monitor.py (weekly DefiLlama poll). "
            "Dashboard: data/spark_usds_dashboard.json. "
            "See: docs/k302a_runbook.md §37"
        ),
    )

    args = parser.parse_args()

    # Determine mode
    execute_mode = args.execute
    dry_run      = not execute_mode

    logger = setup_logging(to_file=True)

    logger.info(f"K357 Emergency HL Exit Script — {'EXECUTE MODE' if execute_mode else 'DRY-RUN MODE'}")
    logger.info(f"REPO_ROOT: {REPO_ROOT}")

    # Resolve user address
    user = args.user or os.environ.get("HL_USER_ADDRESS", "")
    if not user:
        logger.error("No user address provided. Use --user 0x... or set HL_USER_ADDRESS env var.")
        return 1

    user = user.strip()
    if not user.startswith("0x") or len(user) != 42:
        logger.warning(f"User address format looks unusual: {user}")
        logger.warning("Expected format: 0x + 40 hex characters")

    logger.info(f"User address: {user}")

    # Write initial standby status
    write_emergency_status(triggered=False, plan=None, logger=logger)

    # --- PRE-CHECK ---
    precheck = run_precheck(user, dry_run=dry_run, logger=logger)
    positions = precheck.get("positions", [])
    orders    = precheck.get("orders", [])
    plan      = precheck.get("plan", {})

    if len(positions) == 0 and len(orders) == 0:
        logger.info("No positions or open orders found. Nothing to exit.")
        if dry_run:
            logger.info("[DRY-RUN] Mock data: API not called. In live run this would fetch real positions.")

    # --- DRY-RUN REPORT ---
    dry_run_report(precheck, plan, logger)

    # --- EXECUTE PATH ---
    if execute_mode:
        # Load private key ONLY at execution moment, NEVER log it
        private_key = os.environ.get("HL_PRIVATE_KEY", "")
        if not private_key:
            logger.error("HL_PRIVATE_KEY environment variable not set. Cannot execute.")
            logger.error("Set: export HL_PRIVATE_KEY=0x<your_private_key>")
            return 1

        # Validate key format (basic check — never log the actual key)
        pk_clean = private_key.strip()
        if not pk_clean.startswith("0x"):
            pk_clean = "0x" + pk_clean
        if len(pk_clean) != 66:
            logger.error("HL_PRIVATE_KEY format invalid (expected 0x + 64 hex chars). Aborting.")
            return 1

        # Double-confirm
        confirmed = double_confirm(plan, user)
        if not confirmed:
            logger.info("Execution aborted by user.")
            return 0

        # Send pre-execution alert
        notional = plan.get("total_notional_usd", 0)
        send_ntfy_alert(
            message=(f"EMERGENCY HL EXIT TRIGGERED\n"
                     f"User: {user}\n"
                     f"Positions: {len(positions)} | Notional: ${notional:.0f}\n"
                     f"Executing market close..."),
            title="EMERGENCY HL EXIT",
            priority="urgent",
            logger=logger,
        )

        # Write emergency status (triggered)
        write_emergency_status(triggered=True, plan=plan, logger=logger)

        # Execute HL exit
        success = execute_exit(plan, pk_clean, user, logger)

        # Clear HL private key from memory (best-effort in Python)
        pk_clean = "0" * len(pk_clean)
        del private_key, pk_clean

        if success:
            logger.info("HL EXIT EXECUTION COMPLETED — verifying positions...")
        else:
            logger.error("HL EXIT EXECUTION HAD ERRORS — check logs and verify manually")

        # K380 Phase 6: Bybit close-all (gap fix per K378 activation criteria #6)
        bybit_success = True
        if args.include_bybit:
            logger.info("=== BYBIT EMERGENCY CLOSE-ALL (K380 gap fix) ===")
            bybit_api_key    = os.environ.get("BYBIT_API_KEY", "")
            bybit_api_secret = os.environ.get("BYBIT_API_SECRET", "")
            if not bybit_api_key or not bybit_api_secret:
                logger.warning(
                    "BYBIT_API_KEY or BYBIT_API_SECRET not set — skipping Bybit close. "
                    "Set env vars to enable: export BYBIT_API_KEY=... BYBIT_API_SECRET=..."
                )
                bybit_success = False
            else:
                bybit_success = close_bybit_positions(
                    api_key=bybit_api_key,
                    api_secret=bybit_api_secret,
                    dry_run=False,
                    logger=logger,
                )
                if bybit_success:
                    logger.info("Bybit close-all COMPLETE.")
                else:
                    logger.error("Bybit close-all HAD ERRORS — verify Bybit positions manually.")
                # Clear Bybit secrets from memory
                bybit_api_key    = "0" * len(bybit_api_key)
                bybit_api_secret = "0" * len(bybit_api_secret)
                del bybit_api_key, bybit_api_secret
        else:
            logger.info("Bybit close-all skipped (--no-bybit flag).")

        # K456: OKX emergency close-all (3rd venue, scaffold — activate post v6.20)
        okx_success = True
        if args.include_okx:
            logger.info("=== OKX EMERGENCY CLOSE-ALL (K456 3rd venue scaffold) ===")
            okx_api_key    = os.environ.get("OKX_API_KEY", "")
            okx_api_secret = os.environ.get("OKX_API_SECRET", "")
            okx_passphrase = os.environ.get("OKX_PASSPHRASE", "")
            if not okx_api_key or not okx_api_secret or not okx_passphrase:
                logger.warning(
                    "OKX_API_KEY, OKX_API_SECRET, or OKX_PASSPHRASE not set — "
                    "skipping OKX close. Set env vars to enable: "
                    "export OKX_API_KEY=... OKX_API_SECRET=... OKX_PASSPHRASE=..."
                )
                okx_success = False
            else:
                okx_success = close_okx_positions(
                    api_key=okx_api_key,
                    api_secret=okx_api_secret,
                    passphrase=okx_passphrase,
                    dry_run=False,
                    logger=logger,
                )
                if okx_success:
                    logger.info("OKX close-all COMPLETE.")
                else:
                    logger.error("OKX close-all HAD ERRORS — verify OKX positions manually.")
                # Clear OKX secrets from memory
                okx_api_key    = "0" * len(okx_api_key)
                okx_api_secret = "0" * len(okx_api_secret)
                okx_passphrase = "0" * len(okx_passphrase)
                del okx_api_key, okx_api_secret, okx_passphrase
        else:
            logger.info(
                "OKX close-all skipped (--no-okx, default at K456 scaffold). "
                "Use --include-okx when OKX trading positions exist (post v6.20)."
            )

        # K478: K476 SOL-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K476 positions (SOL+BTC on HL) are included in the main HL exit.
        # This flag adds a structured summary of the K476-specific sequential close protocol.
        if args.include_k476:
            logger.info("=== K476 SOL-BTC PAIRED CLOSE SUMMARY (K478 §38) ===")
            success_k476 = close_k476_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k476:
                logger.info("  K476 SOL-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K476 SOL-BTC close: had errors — verify HL positions manually.")
            logger.info("  See: docs/k302a_runbook.md §38 (K476 SOL-BTC strategy playbook)")
        else:
            if plan.get("k476_paired_detected"):
                logger.info(
                    "K476 SOL-BTC paired positions detected — included in HL exit above. "
                    "Use --include-k476 to print detailed SOL-BTC sequential close summary (§38)."
                )

        # K489: K484 AVAX-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K484 positions (AVAX+BTC on HL) are included in the main HL exit.
        # This flag adds a structured summary of the K484-specific sequential close protocol.
        if args.include_k484:
            logger.info("=== K484 AVAX-BTC PAIRED CLOSE SUMMARY (K489 §38c) ===")
            success_k484 = close_k484_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k484:
                logger.info("  K484 AVAX-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K484 AVAX-BTC close: had errors — verify HL positions manually.")
            logger.info("  See: docs/k302a_runbook.md §38c (K484 AVAX-BTC strategy playbook)")
        else:
            if plan.get("k484_paired_detected"):
                logger.info(
                    "K484 AVAX-BTC paired positions detected — included in HL exit above. "
                    "Use --include-k484 to print detailed AVAX-BTC sequential close summary (§38c)."
                )

        # K499: K493 ATOM-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K493 positions (ATOM+BTC on HL) are included in the main HL exit.
        # This flag adds a structured summary of the K493-specific sequential close protocol.
        if args.include_k493:
            logger.info("=== K493 ATOM-BTC PAIRED CLOSE SUMMARY (K499 §38d) ===")
            success_k493 = close_k493_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k493:
                logger.info("  K493 ATOM-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K493 ATOM-BTC close: had errors — verify HL positions manually.")
            logger.info("  See: docs/k302a_runbook.md §38d (K493 ATOM-BTC strategy playbook)")
        else:
            if plan.get("k493_paired_detected"):
                logger.info(
                    "K493 ATOM-BTC paired positions detected — included in HL exit above. "
                    "Use --include-k493 to print detailed ATOM-BTC sequential close summary (§38d)."
                )

        # K506: K500 INJ-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K500 positions (INJ+BTC on HL) are included in the main HL exit.
        # This flag adds a structured summary of the K500-specific sequential close protocol.
        if args.include_k500:
            logger.info("=== K500 INJ-BTC PAIRED CLOSE SUMMARY (K506 §38e) ===")
            success_k500 = close_k500_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k500:
                logger.info("  K500 INJ-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K500 INJ-BTC close: had errors — verify HL positions manually.")
            logger.info("  See: docs/k302a_runbook.md §38e (K500 INJ-BTC strategy playbook)")
        else:
            if plan.get("k500_paired_detected"):
                logger.info(
                    "K500 INJ-BTC paired positions detected — included in HL exit above. "
                    "Use --include-k500 to print detailed INJ-BTC sequential close summary (§38e)."
                )

        # K520: K512 APT-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K512 positions (APT+BTC, HL+Bybit split) are included in the main HL+Bybit exit.
        # This flag adds a structured summary of the K512-specific sequential close protocol.
        # HL+Bybit split: APT on HL, BTC on Bybit (or reverse). Close each leg on its venue.
        if args.include_k512:
            logger.info("=== K512 APT-BTC PAIRED CLOSE SUMMARY (K520 §38g) ===")
            success_k512 = close_k512_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k512:
                logger.info("  K512 APT-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K512 APT-BTC close: had errors — verify HL+Bybit positions manually.")
            logger.info("  HL+Bybit split: APT leg on HL (IOC), BTC leg on Bybit (IOC)")
            logger.info("  See: docs/k302a_runbook.md §38g (K512 APT-BTC strategy playbook)")
        else:
            if plan.get("k512_paired_detected"):
                logger.info(
                    "K512 APT-BTC paired positions detected — included in HL+Bybit exit above. "
                    "Use --include-k512 to print detailed APT-BTC sequential close summary (§38g). "
                    "HL+Bybit split: APT@HL + BTC@Bybit (1%+1%)."
                )

        # K514: K507 SEI-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K507 positions (SEI+BTC, HL+Bybit split) are included in the main HL+Bybit exit.
        # This flag adds a structured summary of the K507-specific sequential close protocol.
        # HL+Bybit split: SEI on HL, BTC on Bybit (or reverse). Close each leg on its venue.
        if args.include_k507:
            logger.info("=== K507 SEI-BTC PAIRED CLOSE SUMMARY (K514 §38f) ===")
            success_k507 = close_k507_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k507:
                logger.info("  K507 SEI-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K507 SEI-BTC close: had errors — verify HL+Bybit positions manually.")
            logger.info("  HL+Bybit split: SEI leg on HL (IOC), BTC leg on Bybit (IOC)")
            logger.info("  See: docs/k302a_runbook.md §38f (K507 SEI-BTC strategy playbook)")
        else:
            if plan.get("k507_paired_detected"):
                logger.info(
                    "K507 SEI-BTC paired positions detected — included in HL+Bybit exit above. "
                    "Use --include-k507 to print detailed SEI-BTC sequential close summary (§38f). "
                    "HL+Bybit split: SEI@HL + BTC@Bybit (1.5%+1.5%)."
                )

        # K524: K507 TIA-BTC paired close summary (documentation; positions auto-detected in plan_exit)
        # K507 TIA positions (TIA+BTC, HL-only) are included in the main HL exit.
        # This flag adds a structured summary of the K507 TIA-specific sequential close protocol.
        # HL-only: both legs on HL (1% sleeve, no Bybit split).
        if args.include_k507_tia:
            logger.info("=== K507 TIA-BTC PAIRED CLOSE SUMMARY (K524 §38h) ===")
            success_k507_tia = close_k507_tia_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k507_tia:
                logger.info("  K507 TIA-BTC close: complete (or no position detected).")
            else:
                logger.warning("  K507 TIA-BTC close: had errors — verify HL positions manually.")
            logger.info("  HL-only: both TIA and BTC legs on HL (IOC reduce-only)")
            logger.info("  See: docs/k302a_runbook.md §38h (K507 TIA-BTC strategy playbook)")
        else:
            if plan.get("k507_tia_paired_detected"):
                logger.info(
                    "K507 TIA-BTC paired positions detected — included in HL exit above. "
                    "Use --include-k507-tia to print detailed TIA-BTC sequential close summary (§38h). "
                    "HL-only: both TIA@HL + BTC@HL (1% sleeve, no split)."
                )

        # K550: K541 stablecoin supply growth close summary (documentation; positions auto-detected)
        # K541 positions (LONG BTC+ETH+SOL, HL-only) are included in the main HL exit.
        # This flag adds a structured summary of the K541-specific sequential close protocol.
        # HL-only: all 3 legs on HL (daily cron 86400s, 3% sleeve, 2x leverage).
        if args.include_k541:
            logger.info("=== K541 STABLECOIN SUPPLY GROWTH CLOSE SUMMARY (K550 §40) ===")
            success_k541 = close_k541_position(plan=plan, logger=logger, dry_run=False)
            if success_k541:
                logger.info("  K541 stablecoin supply close: complete (or no position detected).")
            else:
                logger.warning("  K541 stablecoin supply close: had errors — verify HL positions manually.")
            logger.info("  HL-only: all 3 legs (BTC+ETH+SOL) on HL (IOC reduce-only)")
            logger.info("  Signal: 7d USDT+USDC supply z-score 2nd derivative (V3 acceleration)")
            logger.info("  DefiLlama API: stablecoins.llama.fi (free public)")
            logger.info("  See: docs/k302a_runbook.md §40 (K541 stablecoin supply playbook)")
        else:
            if plan.get("k541_detected"):
                logger.info(
                    "K541 stablecoin supply positions detected — included in HL exit above. "
                    "Use --include-k541 to print detailed BTC+ETH+SOL LONG close summary (§40). "
                    "HL-only: BTC@HL + ETH@HL + SOL@HL (3% sleeve, 2x leverage)."
                )

        # K565: K521 options 25d skew close summary (documentation; positions auto-detected)
        # K521 positions (LONG BTC, HL-only, single leg) are included in the main HL exit.
        # This flag adds a structured summary of the K521-specific close protocol.
        # HL-only: 1 leg on HL (daily cron 86400s, 3% sleeve, 2x leverage).
        if args.include_k521:
            logger.info("=== K521 OPTIONS 25d SKEW CLOSE SUMMARY (K565 §41) ===")
            success_k521 = close_k521_position(plan=plan, logger=logger, dry_run=False)
            if success_k521:
                logger.info("  K521 options skew close: complete (or no position detected).")
            else:
                logger.warning("  K521 options skew close: had errors — verify HL BTC position manually.")
            logger.info("  HL-only: LONG BTC on HL (IOC reduce-only, single leg)")
            logger.info("  Signal: Deribit DVOL z-score (60%) + ETH-BTC 25d skew spread (40%) V4 composite")
            logger.info("  Deribit API: free public (no auth) — DVOL index + options book summary")
            logger.info("  See: docs/k302a_runbook.md §41 (K521 options skew playbook)")
        else:
            if plan.get("k521_detected"):
                logger.info(
                    "K521 options skew positions detected — included in HL exit above. "
                    "Use --include-k521 to print detailed BTC LONG close summary (§41). "
                    "HL-only: BTC@HL (3% sleeve, 2x leverage, single leg)."
                )

        # K637: K628 JTO-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K628 positions (JTO+BTC, Bybit-only) are NOT in the HL exit above.
        # K628 is Bybit-only: HL concentration UNCHANGED. Use --include-k628 for Bybit summary.
        if args.include_k628:
            logger.info("=== K628 JTO-BTC ORTHOG CLOSE SUMMARY (K637 §42) ===")
            success_k628 = close_k628_paired_positions(plan=plan, logger=logger, dry_run=False)
            if success_k628:
                logger.info("  K628 JTO-BTC orthog close: complete (or no position detected).")
            else:
                logger.warning("  K628 JTO-BTC orthog close: had errors — verify Bybit JTO+BTC positions manually.")
            logger.info("  Bybit-only: JTO+BTC both legs on Bybit (IOC reduce-only)")
            logger.info("  Orthog: residual = JTO_diff - 0.164*SEI_diff - 0.302*DOGE_diff (K628 OLS)")
            logger.info("  HL concentration: UNCHANGED at 65% (K628 is Bybit-only)")
            logger.info("  OOS Sharpe 18.30 residual | $17.85M/yr potential @$10M @4x")
            logger.info("  See: docs/k302a_runbook.md §42 (K628 JTO orthog playbook)")
        else:
            if plan.get("k628_paired_detected"):
                logger.info(
                    "K628 JTO-BTC orthog positions detected — on Bybit (NOT HL). "
                    "Use --include-k628 to print detailed Bybit close summary (§42). "
                    "Bybit-only: JTO@Bybit + BTC@Bybit (2% sleeve, 4x leverage). "
                    "HL concentration UNCHANGED at 65%."
                )

        # K641: K635 IMX-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K635 positions (IMX+BTC, Bybit-only) are NOT in the HL exit above.
        # K635 is Bybit-only: HL concentration UNCHANGED. Use --include-k635 for Bybit summary.
        if args.include_k635:
            logger.info("=== K635 IMX-BTC ORTHOG CLOSE SUMMARY (K641 §44) ===")
            logger.info("  K635 IMX-BTC orthog: Bybit-only (IMX+BTC both legs on Bybit)")
            logger.info("  Orthog: residual = IMX_diff - 0.254*SHIB_diff - 0.068*TIA_diff - 0.158*SEI_diff (K635 OLS MF, beta hardcoded)")
            logger.info("  EMA window: W=168h = 21 x 8h periods (optimal per K635 analysis)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65% (K635 is Bybit-only)")
            logger.info("  OOS Sharpe 24.81 (residual MF W=168h) | $4.78M/yr @$10M @4x (2% sleeve)")
            logger.info("  Cluster: Gaming L2 Infra (ImmutableX StarkEx ZK rollup for NFT/gaming)")
            logger.info("  60d gate: Realized Sh>=12 + fill>=60% + maxDD<20%")
            logger.info("  See: docs/k302a_runbook.md §44 (K635 IMX orthog playbook)")
        else:
            logger.info(
                "K635 IMX-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k635 for Bybit close summary (§44). "
                "HL concentration UNCHANGED at 65%."
            )

        # K650: K645 BNB-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K645 positions (BNB+BTC, Bybit-only) are NOT in the HL exit above.
        # K645 is Bybit-only: HL concentration UNCHANGED. Use --include-k645 for Bybit summary.
        if args.include_k645:
            logger.info("=== K645 BNB-BTC ORTHOG CLOSE SUMMARY (K650 §47) ===")
            logger.info("  K645 BNB-BTC orthog: Bybit-only (BNB+BTC both legs on Bybit)")
            logger.info("  Orthog: residual = BNB_diff - 0.539*ETH_diff (K645 OLS SF, beta hardcoded)")
            logger.info("  EMA window: W=168h = 21 x 8h periods (optimal per K645 analysis)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65% (K645 is Bybit-only)")
            logger.info("  OOS Sharpe 7.07 (residual SF W=168h) | $17,694/yr net @$10M @4x (3% sleeve)")
            logger.info("  ETH unlock: K480 BLOCKED (corr=0.435) -> K645 post-orth=0.1757 PASS")
            logger.info("  Cluster: Binance Ecosystem / BSC L1 (6th orthog, 45th daemon)")
            logger.info("  60d gate: Realized Sh>=3.5 + fill>=60% + maxDD<20%")
            logger.info("  See: docs/k302a_runbook.md §47 (K645 BNB orthog playbook)")
        else:
            logger.info(
                "K645 BNB-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k645 for Bybit close summary (§47). "
                "HL concentration UNCHANGED at 65%."
            )

        # K653: K647 DOT-BTC orthog close summary (Bybit-only — HL 64% after 1pp headroom)
        # K647 positions (DOT+BTC, Bybit-only) are NOT in the HL exit above.
        # K647 HL impact: 1pp headroom (65%->64%); 3% split HL 1.5%+Bybit 1.5%.
        # Use --include-k647 for Bybit summary. OOS R²=-4.11 structural break — monitor tightly.
        if args.include_k647:
            logger.info("=== K647 DOT-BTC ORTHOG CLOSE SUMMARY (K653 §49) ===")
            logger.info("  K647 DOT-BTC orthog: Bybit-only (DOT+BTC both legs on Bybit)")
            logger.info("  Orthog: residual = DOT_diff - 0.642*INJ_diff (K647 OLS SF, beta hardcoded)")
            logger.info("  EMA window: W=168h = 21 x 8h periods (optimal per K647 analysis)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: 64% (1pp headroom from 65%; 3% split HL 1.5%+Bybit 1.5%)")
            logger.info("  OOS Sharpe 23.25 (residual SF W=168h) | ~$103,586/yr net @$10M @4x (3% sleeve)")
            logger.info("  OOS R²=-4.11 STRUCTURAL BREAK WARNING: IS beta re-OLS every 30d mandatory")
            logger.info("  INJ unlock: K513 BLOCKED (corr=0.4229) -> K647 post-orth=0.037 PASS")
            logger.info("  Cluster: Governance/Staking / Polkadot relay chain (8th orthog, 48th daemon)")
            logger.info("  60d gate STRICT: Realized Sh>=12 + fill>=60% + maxDD<15% (OOS R² caution)")
            logger.info("  See: docs/k302a_runbook.md §49 (K647 DOT orthog playbook)")
        else:
            logger.info(
                "K647 DOT-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k647 for Bybit close summary (§49). "
                "HL concentration 64% (1pp headroom — K647 3% split HL 1.5%+Bybit 1.5%)."
            )

        # K669: K658 SOL-ETH close summary (HL-primary — positions ARE in HL exit above)
        # K658 positions (SOL+ETH, HL-primary) ARE closed by the HL emergency exit above.
        # This block adds structured K658-specific close summary when --include-k658 is used.
        if args.include_k658:
            logger.info("=== K658 SOL-ETH FR DIFFERENTIAL CLOSE SUMMARY (K669 §53) ===")
            logger.info("  K658 SOL-ETH: HL-primary (SOL-PERP + ETH-PERP both legs on HL)")
            logger.info("  Signal: diff = SOL_FR - ETH_FR (direct, W=168h rolling mean, sign threshold)")
            logger.info("  ETH-base wins: SOL-BTC K476 PnL corr=0.2131 PASS (diversified dual sleeve)")
            logger.info("  Close: IOC reduce-only HL — short leg first, then long leg")
            logger.info("  HL concentration: neutral (K476 reduced 4%->1.5%, K658 adds 1.5% = net unchanged)")
            logger.info("  OOS Sharpe 29.66 (ETH-base wins vs K476 Sh=16.30 +13.36) | $42,332/yr @$10M @4x (1.5%)")
            logger.info("  Dual-sleeve: K476 SOL-BTC 1.5% + K658 SOL-ETH 1.5% = ~$85K/yr est @$10M")
            logger.info("  Cluster: SOL L1 Monolithic SVM / DePIN-Retail (ETH-base, 52nd daemon)")
            logger.info("  60d gate: Realized Sh>=15 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §53 (K658 SOL-ETH playbook)")
        else:
            logger.info(
                "K658 SOL-ETH: HL-primary (SOL-PERP + ETH-PERP on HL). "
                "K658 positions ARE included in the HL emergency exit above. "
                "Use --include-k658 for structured K658 close summary (§53). "
                "HL concentration neutral (K476 reduced 4%->1.5%, K658 adds 1.5% = net unchanged)."
            )

        # K668: K663 TIA-ETH close summary (HL-primary — positions ARE in HL exit above)
        # K663 positions (TIA+ETH, HL-primary) ARE closed by the HL emergency exit above.
        # This block adds structured K663-specific close summary when --include-k663 is used.
        if args.include_k663:
            logger.info("=== K663 TIA-ETH FR DIFFERENTIAL CLOSE SUMMARY (K668 §52) ===")
            logger.info("  K663 TIA-ETH: HL-primary (TIA-PERP + ETH-PERP both legs on HL)")
            logger.info("  Signal: diff = TIA_FR - ETH_FR (direct, W=168h rolling mean, zero threshold)")
            logger.info("  ETH-base K660 SURPRISE: G5b TIA-BTC K507 corr=0.2309 PASS (K660 predicted BLOCKED-APT-style)")
            logger.info("  Close: IOC reduce-only HL — short leg first, then long leg")
            logger.info("  HL concentration: ~61.0% post-K663 (within 65% limit, +1.5pp from ~59.5%)")
            logger.info("  OOS Sharpe 17.13 (9/9 §6 PASS) | $63,060/yr net @$10M @4x (1.5% sleeve)")
            logger.info("  Dual-sleeve: K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = ~$114,598/yr net @$10M")
            logger.info("  Cluster: Modular DA / Celestia (ETH-base, K660 SURPRISE, 51st daemon)")
            logger.info("  60d gate: Realized Sh>=8 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §52 (K663 TIA-ETH playbook)")
        else:
            logger.info(
                "K663 TIA-ETH: HL-primary (TIA-PERP + ETH-PERP on HL). "
                "K663 positions ARE included in the HL emergency exit above. "
                "Use --include-k663 for structured K663 close summary (§52). "
                "HL concentration ~61.0% (within 65% limit)."
            )

        # K677: K661 AVAX-ETH close summary (HL-primary — positions ARE in HL exit above)
        # K661 positions (AVAX+ETH, HL-primary) ARE closed by the HL emergency exit above.
        # This block adds structured K661-specific close summary when --include-k661 is used.
        if args.include_k661:
            logger.info("=== K661 AVAX-ETH FR DIFFERENTIAL CLOSE SUMMARY (K677 §54) ===")
            logger.info("  K661 AVAX-ETH: HL-primary (AVAX-PERP + ETH-PERP both legs on HL)")
            logger.info("  Signal: diff = AVAX_FR - ETH_FR (direct, W=168h rolling mean, zero threshold)")
            logger.info("  ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base marginally better)")
            logger.info("  PnL corr=0.3731 < 0.40 -> dual-sleeve eligible with K484 AVAX-BTC")
            logger.info("  G5a K449 ETH-BTC corr=-0.008 (CRITICAL: shared ETH leg minimal risk)")
            logger.info("  Close: IOC reduce-only HL — short leg first, then long leg")
            logger.info("  HL concentration: ~64.0% post-K661 (within 65% limit, +~1.5pp from ~62.5%)")
            logger.info("  OOS Sharpe 28.26 (6/7 §6 gates, G6 structural) | $63,416/yr net @$10M @4x (1.5% sleeve)")
            logger.info("  Dual-sleeve: K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = ~$139,099/yr net @$10M")
            logger.info("  Cluster: AVAX Subnet/RWA (Avalanche9000, RWA tokenization, ETH-base, 53rd daemon)")
            logger.info("  60d gate: Realized Sh>=14 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §54 (K661 AVAX-ETH playbook)")
        else:
            logger.info(
                "K661 AVAX-ETH: HL-primary (AVAX-PERP + ETH-PERP on HL). "
                "K661 positions ARE included in the HL emergency exit above. "
                "Use --include-k661 for structured K661 close summary (§54). "
                "HL concentration ~64.0% (within 65% limit). G5a K449 corr=-0.008 (ETH leg OK)."
            )

        # K654: K629 WLD-ETH close summary (HL-primary — positions ARE in HL exit above)
        # K629 positions (WLD+ETH, HL-primary) ARE closed by the HL emergency exit above.
        # This block adds structured K629-specific close summary when --include-k629 is used.
        if args.include_k629:
            logger.info("=== K629 WLD-ETH FR DIFFERENTIAL CLOSE SUMMARY (K654 §50) ===")
            logger.info("  K629 WLD-ETH: HL-primary (WLD-PERP + ETH-PERP both legs on HL)")
            logger.info("  Signal: diff = WLD_FR - ETH_FR (direct, W=168h EMA, 1.5sigma threshold)")
            logger.info("  ETH-base fix: JUP-BTC cross-base corr=0.3437 PASS (K621 WLD-BTC=0.4612 BLOCKED)")
            logger.info("  Close: IOC reduce-only HL — short leg first, then long leg")
            logger.info("  HL concentration: ~59.5% post-K629 (within 65% limit)")
            logger.info("  OOS Sharpe 19.90 (9/9 §6 PASS) | $94,210/yr @$10M @4x (3% sleeve)")
            logger.info("  Anti-corr with K449 ETH-BTC (corr=-0.2052): diversification benefit")
            logger.info("  Cluster: Biometric ID / World ID (Cluster 24, ETH-base unlock, 49th daemon)")
            logger.info("  60d gate: Realized Sh>=10 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §50 (K629 WLD-ETH playbook)")
        else:
            logger.info(
                "K629 WLD-ETH: HL-primary (WLD-PERP + ETH-PERP on HL). "
                "K629 positions ARE included in the HL emergency exit above. "
                "Use --include-k629 for structured K629 close summary (§50). "
                "HL concentration ~59.5% (within 65% limit)."
            )

        # K659: K656 GALA-BTC dual-factor orthog close summary (Bybit-only — HL NOT affected)
        # K656 positions (GALA+BTC, Bybit-only) are NOT in the HL exit above.
        # K656 is Bybit-only: HL concentration UNCHANGED. Use --include-k656 for Bybit summary.
        # 50th daemon MILESTONE — gaming cluster COMPLETE (SAND+AXS+IMX+GALA).
        if args.include_k656:
            logger.info("=== K656 GALA-BTC DUAL-FACTOR ORTHOG CLOSE SUMMARY (K659 §51) ===")
            logger.info("  K656 GALA-BTC orthog: Bybit-only (GALA+BTC both legs on Bybit)")
            logger.info("  Orthog: residual = GALA_diff - 0.22738*JUP_diff - 0.405439*FIL_diff (K656 OLS DF dual-factor, betas hardcoded)")
            logger.info("  Rolling window: W=504h = 63 x 8h periods (optimal per K656 dual-factor analysis)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 64.5% (K656 is Bybit-only; HL cap 66.5% > 65%)")
            logger.info("  OOS Sharpe 8.3211 (residual DF W=504h) | $48,143/yr net @$10M @4x (2% sleeve)")
            logger.info("  K620 dual blockers cleared: JUP 0.4308->0.0495 (-87%), FIL 0.4114->0.0184 (-96%)")
            logger.info("  IS R²=0.4731 LARGEST in K6xx orthog series (FIRST dual-factor JUP+FIL)")
            logger.info("  Gaming cluster COMPLETE: SAND(K583)+AXS(K591)+IMX(K635)+GALA(K656) all ACCEPT COND")
            logger.info("  Cluster: Gaming Publisher / Gala Games P2E / GalaChain L1 (9th orthog, 50th daemon MILESTONE)")
            logger.info("  60d gate: Realized Sh>=4 + fill>=60% + maxDD<20% (50% of OOS Sh=8.32)")
            logger.info("  See: docs/k302a_runbook.md §51 (K656 GALA orthog playbook)")
        else:
            logger.info(
                "K656 GALA-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k656 for Bybit close summary (§51). "
                "HL concentration UNCHANGED at 64.5% (HL cap breach 66.5% > 65%, Bybit-only). "
                "50th daemon MILESTONE — gaming cluster COMPLETE (SAND+AXS+IMX+GALA)."
            )

        # K652: K648 POL-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K648 positions (POL+BTC, Bybit-only) are NOT in the HL exit above.
        # K648 is Bybit-only: HL concentration UNCHANGED. Use --include-k648 for Bybit summary.
        if args.include_k648:
            logger.info("=== K648 POL-BTC ORTHOG CLOSE SUMMARY (K652 §48) ===")
            logger.info("  K648 POL-BTC orthog: Bybit-only (POL+BTC both legs on Bybit)")
            logger.info("  Orthog: residual = POL_diff - 0.337443*OP_diff - 0.075509*SEI_diff "
                        "- (-0.016480)*APT_diff - 0.059789*TIA_diff - 0.042751*FIL_diff "
                        "- 0.200488*SAND_diff (K648 OLS MF 6-factor, betas hardcoded)")
            logger.info("  EMA window: W=168h = 21 x 8h periods (optimal per K648 analysis)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65% (K648 is Bybit-only)")
            logger.info("  OOS Sharpe 23.41 (residual MF W=168h) | $4,293,200/yr @$10M @4x (2% sleeve)")
            logger.info("  6-factor unlock: K611 BLOCKED-ROLLUP-SIBLING -> K648 all post-orth < 0.40 PASS")
            logger.info("  Cluster: Polygon L2 / PoS / zkEVM (AggLayer + MATIC->POL + zkEVM gas + validator re-staking)")
            logger.info("  60d gate: Realized Sh>=12 + fill>=60% + maxDD<20%")
            logger.info("  See: docs/k302a_runbook.md §48 (K648 POL orthog playbook)")
        else:
            logger.info(
                "K648 POL-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k648 for Bybit close summary (§48). "
                "HL concentration UNCHANGED at 65%."
            )

        # K642: K638 STX-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K638 positions (STX+BTC, Bybit-only) are NOT in the HL exit above.
        # K638 is Bybit-only: HL concentration UNCHANGED. Use --include-k638 for Bybit summary.
        if args.include_k638:
            logger.info("=== K638 STX-BTC ORTHOG CLOSE SUMMARY (K642 §46) ===")
            logger.info("  K638 STX-BTC orthog: Bybit-only (STX+BTC both legs on Bybit)")
            logger.info("  Orthog: residual = STX_diff - 0.203339*APT_diff - 0.125164*SEI_diff - 0.306518*DOGE_diff (K638 OLS MF, beta hardcoded)")
            logger.info("  EMA window: W=504h = 63 x 8h periods (optimal per K638 analysis)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65% (K638 is Bybit-only)")
            logger.info("  OOS Sharpe 12.38 (residual MF W=504h) | $65,018/yr net @$10M @4x (1.5% sleeve)")
            logger.info("  Cluster: BTC-L2 / Stacks PoX (Bitcoin Layer-2, PoX stacking cycles)")
            logger.info("  60d gate: Realized Sh>=6 + fill>=60% + maxDD<20%")
            logger.info("  See: docs/k302a_runbook.md §46 (K638 STX orthog playbook)")
        else:
            logger.info(
                "K638 STX-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k638 for Bybit close summary (§46). "
                "HL concentration UNCHANGED at 65%."
            )

        # K639: K631 WLD-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K631 positions (WLD+BTC, Bybit-only) are NOT in the HL exit above.
        # K631 is Bybit-only: HL concentration UNCHANGED. Use --include-k631 for Bybit summary.
        if args.include_k631:
            logger.info("=== K631 WLD-BTC ORTHOG CLOSE SUMMARY (K639 §43) ===")
            logger.info("  K631 WLD-BTC orthog: Bybit-only (WLD+BTC both legs on Bybit)")
            logger.info(f"  Orthog: residual = WLD_diff - 0.458795*JUP_diff (K631 OLS, β hardcoded)")
            logger.info("  EMA window: W=72h = 9 × 8h periods (optimal per K631 sweep)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65% (K631 is Bybit-only)")
            logger.info("  OOS Sharpe 18.04 (residual W=72h) | $2.9M/yr @$10M @4x (2% sleeve)")
            logger.info("  Cluster: Biometric ID / World ID (privacy-tech + AI-identity)")
            logger.info("  60d gate: Realized Sh>=8 + fill>=60% + maxDD<20%")
            logger.info("  See: docs/k302a_runbook.md §43 (K631 WLD orthog playbook)")
        else:
            logger.info(
                "K631 WLD-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k631 for Bybit close summary (§43). "
                "HL concentration UNCHANGED at 65%."
            )

        # K640: K633 OP-BTC orthog close summary (Bybit-only — HL NOT affected)
        # K633 positions (OP+BTC, Bybit-only) are NOT in the HL exit above.
        # K633 is Bybit-only: HL concentration UNCHANGED. Use --include-k633 for Bybit summary.
        if args.include_k633:
            logger.info("=== K633 OP-BTC ORTHOG CLOSE SUMMARY (K640 §44) ===")
            logger.info("  K633 OP-BTC orthog: Bybit-only (OP+BTC both legs on Bybit)")
            logger.info(f"  Orthog: residual = OP_diff - 0.542224*FIL_diff (K633 OLS, β hardcoded)")
            logger.info("  EMA window: W=72h = 9 × 8h periods (optimal per K633 sweep)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65% (K633 is Bybit-only)")
            logger.info("  OOS Sharpe 12.68 (residual W=72h) | $2.32M/yr @$10M @4x (full potential)")
            logger.info("  2% sleeve: $46,373/yr carry contribution")
            logger.info("  Cluster: L2 Rollup / Optimism Superchain (L2 cluster unlock, 42nd daemon)")
            logger.info("  60d gate: Realized Sh>=5 + fill>=60% + maxDD<20%")
            logger.info("  See: docs/k302a_runbook.md §44 (K633 OP orthog playbook)")
        else:
            logger.info(
                "K633 OP-BTC orthog: Bybit-only (NOT HL). "
                "Use --include-k633 for Bybit close summary (§44). "
                "HL concentration UNCHANGED at 65%."
            )

        # K683: K679 APT-SOL close summary (Bybit-only — HL NOT affected)
        # K679 positions (APT+SOL, Bybit-only) are NOT in the HL exit above.
        # K679 is Bybit-only (HL at 65.5% OVER cap — mandatory). HL UNCHANGED at 65.5%.
        # Close K679 independently of K512 APT-BTC and K476 SOL-BTC (standalone).
        if args.include_k679:
            logger.info("=== K679 APT-SOL CLOSE SUMMARY (K683 §55) ===")
            logger.info("  K679 APT-SOL: Bybit-only (APT-PERP + SOL-PERP both legs on Bybit)")
            logger.info("  FIRST ALT-ALT pair: APT vs SOL (no BTC/ETH base)")
            logger.info("  Signal: diff = APT_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 65.5% (K679 is Bybit-only, HL OVER cap)")
            logger.info("  K512+K476 overlap: close K679 STANDALONE (do not net with K512 APT-BTC / K476 SOL-BTC)")
            logger.info("  OOS Sharpe 39.29 (FIRST ALT-ALT record) | $234,700/yr net @$10M @4x (3% sleeve)")
            logger.info("  APT FR: Move-VM Block-STM adoption (Aptos Foundation, Move ecosystem events)")
            logger.info("  SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, validator economics)")
            logger.info("  Cluster: APT-SOL Alt-Alt (Move-VM vs SVM DePIN-Retail, 55th daemon)")
            logger.info("  60d gate: Realized Sh>=20 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §55 (K679 APT-SOL playbook)")
        else:
            logger.info(
                "K679 APT-SOL: Bybit-only (NOT HL — HL at 65.5% OVER cap). "
                "K679 positions ARE NOT in the HL exit above (Bybit-only mandatory). "
                "Close K679 on Bybit independently of K512/K476. "
                "Use --include-k679 for Bybit close summary (§55). "
                "HL concentration UNCHANGED at 65.5%."
            )

        # K685: K682 ATOM-SOL close summary (Bybit-only — HL NOT affected)
        # K682 positions (ATOM+SOL, Bybit-only) are NOT in the HL exit above.
        # K682 is Bybit-only (HL at 62.5%, Bybit avoids 65% cap risk). HL UNCHANGED at 62.5%.
        # Close K682 independently of K493 ATOM-BTC and K476 SOL-BTC (standalone).
        # Note: K682 anti-corr with K493 (-0.5195) = HEDGES — close independently anyway.
        if args.include_k682:
            logger.info("=== K682 ATOM-SOL CLOSE SUMMARY (K685 §57) ===")
            logger.info("  K682 ATOM-SOL: Bybit-only (ATOM-PERP + SOL-PERP both legs on Bybit)")
            logger.info("  SECOND ALT-ALT pair: ATOM vs SOL (no BTC/ETH base)")
            logger.info("  Signal: diff = ATOM_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 62.5% (K682 is Bybit-only)")
            logger.info("  K493+K476 overlap: close K682 STANDALONE (anti-corr=-0.5195 HEDGES K493, close independently)")
            logger.info("  Math identity: ATOM-SOL = -(BTC-ATOM) + (BTC-SOL) = -K493_dir + K476_dir")
            logger.info("  OOS Sharpe 43.43 (SECOND ALT-ALT > K679 39.29) | $214,638/yr net @$10M @4x (2% sleeve)")
            logger.info("  ATOM FR: Cosmos IBC governance-driven episodics (staking -3.27%/ann bias)")
            logger.info("  SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, +7.73%/ann)")
            logger.info("  Cluster: ATOM-SOL Alt-Alt (Cosmos IBC vs SVM DePIN-Retail, SECOND ALT-ALT)")
            logger.info("  60d gate: Realized Sh>=22 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §57 (K682 ATOM-SOL playbook)")
        else:
            logger.info(
                "K682 ATOM-SOL: Bybit-only (NOT HL — HL at 62.5%, Bybit avoids cap risk). "
                "K682 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K682 on Bybit independently of K493/K476. "
                "Use --include-k682 for Bybit close summary (§57). "
                "HL concentration UNCHANGED at 62.5%."
            )

        # K687: K684 SOL-INJ close summary (Bybit-only — HL NOT affected)
        # K684 positions (SOL+INJ, Bybit-only) are NOT in the HL exit above.
        # K684 is Bybit-only (HL at 62.5%, Bybit-only preferred — headroom preserved). HL UNCHANGED at 62.5%.
        # Close K684 independently of K476 SOL-BTC and K500 INJ-BTC (standalone).
        # Note: K684 + K679 share SOL leg — close independently, monitor SOL notional.
        if args.include_k684:
            logger.info("=== K684 SOL-INJ CLOSE SUMMARY (K687 §58) ===")
            logger.info("  K684 SOL-INJ: Bybit-only (SOL-PERP + INJ-PERP both legs on Bybit)")
            logger.info("  THIRD ALT-ALT pair: SOL vs INJ (no BTC/ETH base)")
            logger.info("  Signal: diff = SOL_FR - INJ_FR (direct alt-alt, W=168h rolling mean, zero threshold)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 62.5% (K684 is Bybit-only, headroom preserved)")
            logger.info("  K476+K500 overlap: close K684 STANDALONE (SOL-INJ = K476_dir - K500_dir algebraic identity)")
            logger.info("  K679 SOL-exposure: K684 + K679 share SOL leg — close independently, monitor SOL notional")
            logger.info("  OOS Sharpe 9.65 (THIRD ALT-ALT, 216d OOS) | $114,316/yr net @$10M @4x (3% sleeve)")
            logger.info("  SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, ETF speculation, +7.7% ann)")
            logger.info("  INJ FR: Cosmos DeFi perp DEX (liquidation cascades, INJ burn, IBC bridge, +3.6% ann episodic)")
            logger.info("  Cluster: SOL-INJ Alt-Alt (SVM DePIN-Retail vs Cosmos-DeFi-Perp, 56th daemon)")
            logger.info("  60d gate: Realized Sh>=5 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §58 (K684 SOL-INJ playbook)")
        else:
            logger.info(
                "K684 SOL-INJ: Bybit-only (NOT HL — HL at 62.5%, Bybit-only preferred). "
                "K684 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K684 on Bybit independently of K476/K500. "
                "Use --include-k684 for Bybit close summary (§58). "
                "HL concentration UNCHANGED at 62.5%."
            )

        # K689: K686 AVAX-SOL close summary (Bybit-only — HL NOT affected)
        # K686 positions (AVAX+SOL, Bybit-only) are NOT in the HL exit above.
        # K686 is Bybit-only (HL at 62.5%, Bybit-only preferred — headroom preserved). HL UNCHANGED at 62.5%.
        # Close K686 independently of K484 AVAX-BTC and K476 SOL-BTC (standalone).
        # Note: K686+K682+K679 all share SOL leg — close independently, monitor SOL notional.
        if args.include_k686:
            logger.info("=== K686 AVAX-SOL CLOSE SUMMARY (K689 §59) ===")
            logger.info("  K686 AVAX-SOL: Bybit-only (AVAX-PERP + SOL-PERP both legs on Bybit)")
            logger.info("  FOURTH ALT-ALT pair: AVAX vs SOL (no BTC/ETH base)")
            logger.info("  Signal: diff = AVAX_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 62.5% (K686 is Bybit-only, headroom preserved)")
            logger.info("  K484+K476 overlap: close K686 STANDALONE (AVAX-SOL = K484_dir - K476_dir algebraic identity)")
            logger.info("  Anti-corr K686 vs K484 = -0.6295 (K686 HEDGES K484 long-AVAX — close independently)")
            logger.info("  K682/K679 SOL-exposure: K686+K682+K679 share SOL leg — close independently, monitor SOL notional")
            logger.info("  OOS Sharpe 50.27 (FOURTH ALT-ALT, HIGHEST in family) | $102,153/yr net @$10M @4x (3% sleeve)")
            logger.info("  AVAX FR: Subnet launches, Avalanche9000, RWA institutional, HFT colocation (+6.39% ann episodic)")
            logger.info("  SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, ETF speculation, +7.73% ann)")
            logger.info("  Same-tier L1: AVAX/SOL vol ratio=0.85x. ADF -13.99, OU half-life=3.6h (FASTEST in family)")
            logger.info("  Cluster: AVAX-SOL Alt-Alt (Avalanche institutional vs Solana retail, 57th daemon)")
            logger.info("  60d gate: Realized Sh>=25 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §59 (K686 AVAX-SOL playbook)")
        else:
            logger.info(
                "K686 AVAX-SOL: Bybit-only (NOT HL — HL at 62.5%, Bybit-only preferred). "
                "K686 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K686 on Bybit independently of K484/K476. "
                "Use --include-k686 for Bybit close summary (§59). "
                "HL concentration UNCHANGED at 62.5%."
            )

        # K693: K690 SEI-SOL close summary (Bybit-only — HL NOT affected)
        # K690 positions (SEI+SOL, Bybit-only) are NOT in the HL exit above.
        # K690 is Bybit-only (HL at 62.5%, Bybit-only preferred — headroom preserved). HL UNCHANGED at 62.5%.
        # Close K690 independently of K507 SEI-BTC and K476 SOL-BTC (standalone).
        # Note: K690+K682+K686 all share SOL leg — close independently, monitor SOL notional.
        if args.include_k690:
            logger.info("=== K690 SEI-SOL CLOSE SUMMARY (K693 §60) ===")
            logger.info("  K690 SEI-SOL: Bybit-only (SEI-PERP + SOL-PERP both legs on Bybit)")
            logger.info("  FIFTH ALT-ALT pair: SEI vs SOL (no BTC/ETH base)")
            logger.info("  Signal: diff = SEI_FR - SOL_FR (direct alt-alt, W=168h rolling mean, zero threshold)")
            logger.info("  Close: IOC reduce-only Bybit — short leg first, then long leg")
            logger.info("  HL concentration: UNCHANGED at 62.5% (K690 is Bybit-only, headroom preserved)")
            logger.info("  K507+K476 overlap: close K690 STANDALONE (SEI-SOL = K507_dir - K476_dir algebraic identity)")
            logger.info("  Anti-corr K690 vs K507 = -0.5109 (K690 HEDGES K507 long-SEI — close independently)")
            logger.info("  K682/K686 SOL-exposure: K690+K682+K686 share SOL leg — close independently, monitor SOL notional")
            logger.info("  OOS Sharpe 25.11 (FIFTH ALT-ALT, WF 12/12 UNPRECEDENTED) | $104,174/yr net @$10M @4x (3% sleeve)")
            logger.info("  SEI FR: Cosmos EVM parallel chain, DeFi/CosmWasm launches, NEGATIVE mean -3.65%/ann (short-sellers dominate)")
            logger.info("  SOL FR: DePIN/Retail/meme-coin premium (BONK/WIF, Firedancer, ETF speculation, +7.70% ann)")
            logger.info("  Mid-cap alt-alt: SEI/SOL vol ratio=1.32x. ADF p=1.01e-23, OU half-life=4.41h (STRONG)")
            logger.info("  Carry dominant: BEAR_SEI (~90%+): LONG SOL/SHORT SEI = carry-positive in both legs")
            logger.info("  Cluster: SEI-SOL Alt-Alt (Cosmos EVM parallel vs Solana SVM retail, 58th daemon)")
            logger.info("  60d gate: Realized Sh>=12 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §60 (K690 SEI-SOL playbook)")
        else:
            logger.info(
                "K690 SEI-SOL: Bybit-only (NOT HL — HL at 62.5%, Bybit-only preferred). "
                "K690 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K690 on Bybit independently of K507/K476. "
                "Use --include-k690 for Bybit close summary (§60). "
                "HL concentration UNCHANGED at 62.5%."
            )

        # K697: K694 TIA-SOL close summary (Bybit-only — HL NOT affected)
        # K694 positions (TIA+SOL, Bybit-only) are NOT in the HL exit above.
        # K694 is Bybit-only (HL at 62.5%, Bybit-only mandatory — HL-only would breach 65% cap). HL UNCHANGED.
        # Close K694 independently of K476 TIA-BTC and K690 SEI-SOL (standalone).
        # Note: K694+K679+K682+K684+K686+K690 all share SOL leg — close independently, monitor SOL notional.
        if args.include_k694:
            logger.info("=== K694 TIA-SOL CLOSE SUMMARY (K697 §61) ===")
            logger.info("  K694 TIA-SOL: Bybit-only (TIA-PERP + SOL-PERP both legs on Bybit)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BEAR_TIA (dominant): short TIA first → sell long SOL second")
            logger.info("  BULL_TIA (DA spike): short SOL first → sell long TIA second")
            logger.info("  HL concentration: UNCHANGED at 62.5% (K694 is Bybit-only — HL-only would breach 65% cap)")
            logger.info("  K476 decomp: TIA-SOL = K_TIA_BTC - K476_dir — close K694 STANDALONE")
            logger.info("  K691 lesson: TIA-APT REJECT (APT G5b=0.4712). K694 SOL saturation=0.2275 PASS.")
            logger.info("  SOL exposure: K694+K679+K682+K684+K686+K690 share SOL leg — close independently")
            logger.info("  Natural SOL-short hedge: K694 BULL_TIA offsets SOL-long in K679+K682+K686+K690")
            logger.info("  OU half-life: 3.46h (FASTEST in alt-alt family). Cross-arch: Celestia DA vs SVM retail.")
            logger.info("  60d gate: Realized Sh>=9 + fill>=60% + maxDD<15%")
            logger.info("  See: docs/k302a_runbook.md §61 (K694 TIA-SOL playbook)")
        else:
            logger.info(
                "K694 TIA-SOL: Bybit-only (NOT HL — HL at 62.5%, Bybit-only mandatory). "
                "K694 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K694 on Bybit independently of K476/K690. "
                "Use --include-k694 for Bybit close summary (§61). "
                "HL concentration UNCHANGED at 62.5%."
            )

        # K699: K696 ENA-SOL close summary (Bybit-only — HL NOT affected)
        # K696 positions (ENA+SOL, Bybit-only) are NOT in the HL exit above.
        # K696 is Bybit-only (HL at 62.5%, Bybit-only mandatory — HL-only would breach 65% cap). HL UNCHANGED.
        # Close K696 independently of K616 ENA-BTC and K694/K690 SOL strategies (standalone).
        # MR6: combined ENA notional (K616+K696) < 6% AUM — close K696 standalone, monitor ENA combined.
        # Note: K696+K694+K690+K686+K684+K682+K679+K476 all share SOL leg — close independently.
        if args.include_k696:
            logger.info("=== K696 ENA-SOL CLOSE SUMMARY (K699 §62 ALT-ALT) ===")
            logger.info("  K696 ENA-SOL: Bybit-only (ENA-PERP + SOL-PERP both legs on Bybit)")
            logger.info("  SEVENTH ALT-ALT pair, FIRST CROSS-CLUSTER: ENA synth stable infra vs SOL SVM retail")
            logger.info("  Signal: diff = ENA_FR - SOL_FR (direct alt-alt cross-cluster, W=168h rolling mean, zero threshold)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BEAR_ENA (dominant 61.5%): short ENA first → sell long SOL second")
            logger.info("  BULL_ENA (sUSDe surge 38.5%): short SOL first → sell long ENA second")
            logger.info("  HL concentration: UNCHANGED at 62.5% (K696 is Bybit-only — HL-only would breach 65% cap)")
            logger.info("  MR8/MR9: ENA new vertex. ENA-SOL = K616_dir - K476_dir (K616 perp K476, corr=0.0094)")
            logger.info("  MR6 ENA cap: K616 ENA-BTC + K696 ENA-SOL combined ENA < 6% AUM — close K696 STANDALONE")
            logger.info("  G5b K476 corr=0.1765 PASS. G5c K616 corr=-0.7427 signed PASS (PnL corr K616=0.6723).")
            logger.info("  SOL exposure: K696+K694+K690+K686+K684+K682+K679+K476 share SOL (8 strategies) — close independently")
            logger.info("  Double carry: ENA FR < 0 (37.2% of time) — SHORT ENA earns |ENA FR| + SHORT SOL earns SOL FR")
            logger.info("  ENA FR: Ethena sUSDe protocol equity (-7.65%/ann mean, structurally negative)")
            logger.info("  SOL FR: DePIN/Retail premium (BONK/WIF/POPCAT, Firedancer, ETF, +7.70% ann)")
            logger.info("  OOS Sh=26.93 (ACCEPT 15/17 gates, G4 11/12, G6 20.8/yr). $93,187/yr net @$10M @4x (3% sleeve)")
            logger.info("  ADF stat -13.0808 (strongest stationary in alt-alt family). OU half-life=3.75h STRONG.")
            logger.info("  60d gate: Realized Sh>=13 + fill>=60% + maxDD<15%")
            logger.info("  60th daemon MILESTONE: 7th alt-alt accepted, 9th evaluated, FIRST CROSS-CLUSTER")
            logger.info("  See: docs/k302a_runbook.md §62 (K696 ENA-SOL alt-alt playbook)")
        else:
            logger.info(
                "K696 ENA-SOL: Bybit-only (NOT HL — HL at 62.5%, Bybit-only mandatory). "
                "K696 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K696 on Bybit independently of K616/K694/K690. "
                "Use --include-k696 for Bybit close summary (§62 alt-alt). "
                "HL concentration UNCHANGED at 62.5%. MR6 ENA cap: K616+K696 < 6% AUM."
            )

        # K701: K698 LINK-ETH close summary (Bybit-only — HL NOT affected)
        # K698 positions (LINK+ETH, Bybit-only) are NOT in the HL exit above.
        # K698 is Bybit-only (HL at 64.5%, Bybit-only mandatory — HL-only would push to 67.0% > 65% cap). HL UNCHANGED.
        # K557 LINK leg coordination: close K698 LINK-ETH and K557 LINK-BTC independently.
        # Combined LINK exposure: K557 ~1.5% + K698 2.5% = 4.0% max LINK AUM — close both on Bybit.
        if args.include_k698:
            logger.info("=== K698 LINK-ETH CLOSE SUMMARY (K701 §62) ===")
            logger.info("  K698 LINK-ETH: Bybit-only (LINK-PERP + ETH-PERP both legs on Bybit)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BULL_LINK (dominant, 74.5% time): short ETH first → sell long LINK second")
            logger.info("  BEAR_LINK (ETH premium): short LINK first → sell long ETH second")
            logger.info("  HL concentration: UNCHANGED at 64.5% (K698 is Bybit-only — HL-only would breach 65% cap)")
            logger.info("  MR9: LINK-ETH = LINK-BTC - ETH-BTC (FR-level max_err=5.42e-20 confirmed)")
            logger.info("  Position-level corr=0.1254 de-correlated (different W=120h vs K557 W=168h)")
            logger.info("  K695 lesson: LINK-SOL REJECTED G5c=0.497. K698 avoids SOL. G5a K557=0.0578 PASS.")
            logger.info("  G5a corr(K698, K557 LINK-BTC) = 0.0578 PASS (CRITICAL — clean LINK expansion)")
            logger.info("  G5b corr(K698, K449 ETH-BTC) = -0.0036 PASS (CRITICAL anti-corr)")
            logger.info("  K557 coord: K557 LINK-BTC ~1.5% + K698 LINK-ETH 2.5% = 4.0% max combined LINK AUM")
            logger.info("  Close K698 STANDALONE (independent of K557, K449 — de-correlated execution)")
            logger.info("  LINK FR: oracle middleware anchor ~1.25e-5/hr (DeFi integrations, CCIP, feeds)")
            logger.info("  ETH FR: DeFi/staking yields (stETH/LST demand, Pectra upgrades, L1 gas)")
            logger.info("  OOS Sh=12.07 (W=120h), $28,997/yr net @$10M @4x (2.5% sleeve)")
            logger.info("  60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%")
            logger.info("  4th ETH-base scaffold, 1st oracle-ETH pair (K629/K658/K661/K698 ETH-base family)")
            logger.info("  See: docs/k302a_runbook.md §62 (K698 LINK-ETH playbook)")
        else:
            logger.info(
                "K698 LINK-ETH: Bybit-only (NOT HL — HL at 64.5%, Bybit-only mandatory). "
                "K698 positions ARE NOT in the HL exit above (Bybit-only). "
                "Close K698 on Bybit independently of K557/K449. "
                "Use --include-k698 for Bybit close summary (§62). "
                "HL concentration UNCHANGED at 64.5%."
            )

        # K750: K747 TAO-SOL alt-alt close summary (HL-only — positions ARE in HL exit above)
        # K747 positions (TAO+SOL, HL-only) are included in the main HL exit plan above.
        # HL 65.0% AT CAP (paper-gate: PAPER_TRADE=True default — no live capital yet).
        # Live only after K498 OKX activation + 60d gate passage.
        if args.include_k747:
            logger.info("=== K747 TAO-SOL CLOSE SUMMARY (K750 §63) ===")
            logger.info("  K747 TAO-SOL: HL-only (TAO-PERP + SOL-PERP both legs on HL)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BULL_TAO (dominant — TAO AI premium >> SOL retail): short SOL first → sell long TAO second")
            logger.info("  BEAR_TAO (rare — SOL meme spike): short TAO first → sell long SOL second")
            logger.info("  HL concentration: 65.0% AT CAP (paper-gate — PAPER_TRADE=True until K498 OKX)")
            logger.info("  G8 FAIL: Bybit TAO 84.6% floor-capped (structural venue noise, not signal failure)")
            logger.info("  K735 G8 precedent: HBAR-SOL ACCEPT CONDITIONAL with same structural pattern")
            logger.info("  HL TAO: maxLeverage=5, asset index=116, $12.3M/24h volume (liquid)")
            logger.info("  G4 WF: 12/12 ALL POSITIVE — UNPRECEDENTED (best WF in alt-alt family)")
            logger.info("  G5b corr(K747, K476 SOL-BTC) = 0.2229 PASS (SOL saturation)")
            logger.info("  G5c corr(K747, K484 AVAX-BTC) = 0.0126 PASS (AVAX cluster bypass)")
            logger.info("  G5k corr(K747, K687 AVAX-SOL) = 0.1286 PASS (AVAX-SOL cluster bypass)")
            logger.info("  K746 ONDO: BLOCKED G5c=-0.4148/G5k=-0.5842. K747 TAO: 0.013/0.129 PASS.")
            logger.info("  AI L1 compute marketplace (GPU scarcity) != AVAX subnet appchain (institutional).")
            logger.info("  TAO = 13th vertex. MR9 L002: all future TAO-X pairs auto-blocked.")
            logger.info("  TAO FR: Bittensor AI compute (GPU scarcity/NVDA cycles, subnet launches, +16.34%/ann)")
            logger.info("  SOL FR: DePIN/Retail meme-coin (BONK/WIF/POPCAT, Firedancer, ETF, +7.706%/ann)")
            logger.info("  OOS Sh=12.233 (W=168h), K523 central $17,210/yr net @$10M @4x (2.5% sleeve)")
            logger.info("  K523 3-point: conservative=$12,907 central=$17,210 optimistic=$45,289/yr")
            logger.info("  60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%")
            logger.info("  Live trigger: K498 OKX activation (HL% < 65%) + 60d gate passage")
            logger.info("  15th alt-alt scaffold, 69th daemon. HL-only (positions in main HL exit)")
            logger.info("  See: docs/k302a_runbook.md §63 (K747 TAO-SOL playbook)")
        else:
            logger.info(
                "K747 TAO-SOL: HL-only (positions ARE in HL exit above — TAO-PERP + SOL-PERP on HL). "
                "HL 65.0% AT CAP (paper-gate — PAPER_TRADE=True default; no live capital until K498 OKX). "
                "G4 WF 12/12 ALL POSITIVE — UNPRECEDENTED. TAO = 13th vertex. "
                "Use --include-k747 for structured HL close summary (§63). "
                "G8 FAIL: Bybit TAO floor-capped. K735 precedent applies."
            )

        # K756: K754 PEPE-SOL alt-alt close summary (HL primary — positions ARE in HL exit above)
        # K754 positions (PEPE+SOL, HL primary) are included in the main HL exit plan above.
        # HL 66.8% AT CAP (paper-gate: PAPER_TRADE=True default — no live capital yet).
        # Live only after K498/v6.52 OKX activation + 60d gate passage.
        if args.include_k754:
            logger.info("=== K754 PEPE-SOL CLOSE SUMMARY (K756 §71) ===")
            logger.info("  K754 PEPE-SOL: HL primary (PEPE-PERP + SOL-PERP both legs on HL)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BULL_PEPE (Eth meme season): short SOL first → sell long PEPE second")
            logger.info("  BEAR_PEPE (SVM season dominant): short PEPE first → sell long SOL second")
            logger.info("  HL concentration: 66.8% AT CAP (K751 audit — paper-gate strict)")
            logger.info("  PAPER_TRADE=True default — no live capital until K498/v6.52 OKX reduces HL%")
            logger.info("  G4 WF: 12/12 ALL POSITIVE (min_sh=5.56) — strong WF validation")
            logger.info("  G5: 22/22 PASS (max_corr=0.247 G5l SEI-SOL — well below 0.40)")
            logger.info("  G6: 64.2 entries/yr OOS PASS (W=84h G6-safe vs W=168h 29.5/yr FAIL)")
            logger.info("  G8: HL+Bybit+OKX confirmed (Bybit=1000PEPE denomination, 3-venue presence)")
            logger.info("  L003 AVAX corr=0.4125 PASS (proximity warning — monthly recheck)")
            logger.info("  L010 HBAR corr=0.4272 PASS (proximity warning — monthly recheck)")
            logger.info("  L004 OOS carry=73.7% PASS (meme carry artifact, not full-period 84.7%)")
            logger.info("  L007 FIL-SOL pre-screen=0.2517 PASS (SOL-beta cluster absent)")
            logger.info("  PEPE = 14th vertex (Eth ERC-20 meme cluster). MR9 L002: all future PEPE-X blocked.")
            logger.info("  V = {APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE}")
            logger.info("  PEPE FR: ERC-20 meme bull rotations, social virality, CEX catalysts. P99=1.66bps Max=6.66bps.")
            logger.info("  SOL FR: DePIN/Retail BONK/WIF Firedancer ETF +7.706%/ann. Min=-20.51bps cascade.")
            logger.info("  MaxDD OOS=-0.107% (very contained — differential mean-reversion well-behaved)")
            logger.info("  OOS Sh=44.43 (W=84h), K523 central $62,000/yr net @$10M @4x (2.5% sleeve)")
            logger.info("  K523 3-point: conservative=$34,758 central=$62,000 optimistic=$85,678/yr")
            logger.info("  60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%")
            logger.info("  Live trigger: K498/v6.52 OKX activation (HL% < 65%) + 60d gate passage")
            logger.info("  16th alt-alt scaffold, 71st daemon. HL primary (positions in main HL exit)")
            logger.info("  See: docs/k302a_runbook.md §71 (K754 PEPE-SOL playbook)")
        else:
            logger.info(
                "K754 PEPE-SOL: HL primary (positions ARE in HL exit above — PEPE-PERP + SOL-PERP on HL). "
                "HL 66.8% AT CAP (K751 audit — paper-gate strict; no live capital until K498/v6.52 OKX). "
                "G4 WF 12/12 ALL POSITIVE (min_sh=5.56). PEPE = 14th vertex. "
                "L003/L010 proximity warning: monthly AVAX/HBAR recheck. "
                "Use --include-k754 for structured HL close summary (§71)."
            )

        # K761: K759 WIF-SOL alt-alt close summary (HL primary — positions ARE in HL exit above)
        # K759 positions (WIF+SOL, HL primary) are included in the main HL exit plan above.
        # HL 66.8% AT CAP (paper-gate: PAPER_TRADE=True default — no live capital yet).
        # Live only after K498/v6.52 OKX activation + 60d gate passage.
        if args.include_k759:
            logger.info("=== K759 WIF-SOL CLOSE SUMMARY (K761 §72) ===")
            logger.info("  K759 WIF-SOL: HL primary (WIF-PERP + SOL-PERP both legs on HL)")
            logger.info("  Close protocol: IOC reduce-only SHORT first (avoid naked short), then LONG")
            logger.info("  BULL_WIF (SOL meme season): short SOL first → sell long WIF second")
            logger.info("  BEAR_WIF (SVM season dominant): short WIF first → sell long SOL second")
            logger.info("  HL concentration: 66.8% AT CAP (K751 audit — paper-gate strict)")
            logger.info("  PAPER_TRADE=True default — no live capital until K498/v6.52 OKX reduces HL%")
            logger.info("  G4 WF: 12/12 ALL POSITIVE (min_sh=9.895) — strong WF validation")
            logger.info("  G5: all PASS (max_corr=0.3819 G5w PEPE-SOL — 0.018 margin below 0.40)")
            logger.info("  G5w: PEPE-SOL=0.382 proximity → reduced sleeve 2.0% (vs 2.5% standard)")
            logger.info("  G6: 31.2 entries/yr OOS PASS (W=168h G6-safe vs 30/yr minimum)")
            logger.info("  G8: HL+Bybit+OKX confirmed (WIFUSDT, 3-venue presence CONFIRMED)")
            logger.info("  L011 WIF-SOL corr=0.487 PASS (< 0.50 SOL-ecosystem threshold, borderline)")
            logger.info("  L011 OOS corr=0.054 (near-zero — regime-switch cleans signal in OOS)")
            logger.info("  L003 AVAX corr=0.3823 PASS | L010 HBAR corr=0.4011 PASS")
            logger.info("  L004 OOS carry=77.5% PASS (full 87.2% warn — meme carry artifact)")
            logger.info("  L007 FIL-SOL pre-screen=0.3318 PASS")
            logger.info("  WIF = 15th vertex (SOL meme cluster). MR9 L002: all future WIF-X blocked.")
            logger.info("  V = {APT,ATOM,AVAX,BNB,ENA,FIL,HBAR,INJ,LDO,SEI,SOL,TIA,TAO,PEPE,WIF}")
            logger.info("  WIF FR: SOL-native meme, BONK/WIF/POPCAT rotation, CEX listings, SVM DEX.")
            logger.info("  WIF FR: vol_ratio=1.347x, P99=1.416bps Max=3.164bps. Q2 2024 +0.13bps diff.")
            logger.info("  SOL FR: DePIN/Retail Phantom Firedancer ETF +8.82%/ann. Min=-20.51bps cascade.")
            logger.info("  MaxDD OOS=-0.216% (very contained — differential mean-reversion well-behaved)")
            logger.info("  OOS Sh=24.45 (W=168h), K523 central $54,245/yr net @$10M @4x (2.0% sleeve)")
            logger.info("  K523 3-point: conservative=$20,655 central=$54,245 optimistic=$76,847/yr")
            logger.info("  60d gate: Realized Sh>=6 + fill>=60% + maxDD<15%")
            logger.info("  Live trigger: K498/v6.52 OKX activation (HL% < 65%) + 60d gate passage")
            logger.info("  17th alt-alt scaffold, 72nd daemon. HL primary (positions in main HL exit)")
            logger.info("  Cross-sleeve: WIF-SOL (2.0%) + PEPE-SOL (2.0%) = 4.0% meme-vs-SOL combined")
            logger.info("  See: docs/k302a_runbook.md §72 (K759 WIF-SOL playbook)")
        else:
            logger.info(
                "K759 WIF-SOL: HL primary (positions ARE in HL exit above — WIF-PERP + SOL-PERP on HL). "
                "HL 66.8% AT CAP (K751 audit — paper-gate strict; no live capital until K498/v6.52 OKX). "
                "G4 WF 12/12 ALL POSITIVE (min_sh=9.895). WIF = 15th vertex. "
                "G5w PEPE-SOL=0.382 proximity → 2.0% sleeve. L011 WIF-SOL=0.487 monthly recheck. "
                "Use --include-k759 for structured HL close summary (§72)."
            )

        # K459: K457 basket close summary (documentation; positions auto-detected in plan_exit)
        # K457 basket positions (BTC/ETH/SOL HL+Bybit) are included in the main HL exit.
        # This flag adds a structured summary of the K457-specific close protocol.
        if args.include_k457:
            logger.info("=== K457 BASKET CLOSE SUMMARY (K459 §32) ===")
            k457_detail = plan.get("k457_basket_detail")
            if k457_detail:
                logger.info(f"  K457 basket detected: {k457_detail.get('long_count', 0)} long legs, "
                            f"{k457_detail.get('short_count', 0)} short legs")
                logger.info(f"  Total basket notional: ${k457_detail.get('total_notional', 0):,.0f}")
                logger.info(f"  Close protocol: {k457_detail.get('close_protocol', 'SHORTS_FIRST → LONGS')}")
                for leg in k457_detail.get("short_legs", []):
                    logger.info(f"    [PHASE 1 - SHORT] BUY-COVER {leg['coin']} ${leg['value_usd']:,.0f}")
                for leg in k457_detail.get("long_legs", []):
                    logger.info(f"    [PHASE 2 - LONG]  SELL      {leg['coin']} ${leg['value_usd']:,.0f}")
            else:
                logger.info("  No K457 basket positions detected (basket may be NEUTRAL or 60d paper-trade).")
            logger.info("  K457 basket positions included in main HL exit plan above.")
            logger.info("  See: docs/k302a_runbook.md §32 (K457 basket strategy playbook)")
        else:
            if plan.get("k457_basket_detected"):
                logger.info(
                    "K457 basket positions detected in plan — included in HL exit above. "
                    "Use --include-k457 to print detailed basket close summary (§32)."
                )

        # K415: USDY emergency documentation (NOT a redemption execution)
        # USDY redemption is intentionally NOT automated here.
        # Rationale: T-bill yield = safe harbor during HL/Bybit crisis. Hold is optimal.
        if args.include_usdy:
            logger.info("=== USDY SLEEVE NOTE (K415 §21.6) ===")
            logger.info("  USDY is T-bill backed — safe to HOLD through HL/Bybit crisis.")
            logger.info("  Redemption: 1 business day AFTER 40-day initial lock expires.")
            logger.info("  Emergency redemption CANNOT be expedited (no cancel mechanism).")
            logger.info("  Recommended action: HOLD USDY through crisis.")
            logger.info("  Rationale: HL/Bybit positions are time-sensitive; USDY is not.")
            logger.info("  If capital needed post-crisis: redeem via ondo.finance (1bd).")
            logger.info("  See: docs/k302a_runbook.md §21.6 (USDY redemption procedure)")
            logger.info("  LIMITATION: This script does NOT submit redemption to Ondo —")
            logger.info("    USDY redemption is a user action via ondo.finance portal.")
        else:
            logger.info(
                "USDY: not flagged for redemption. "
                "Recommend HOLD through crisis (T-bill safe, see §21.6). "
                "Use --include-usdy to print USDY guidance."
            )

        # Post-check (HL only — Bybit/OKX have no equivalent read-back in this scaffold)
        if not args.skip_postcheck:
            postcheck = run_postcheck(user, logger)
            status    = postcheck.get("status", "UNKNOWN")
            logger.info(f"Post-check status: {status}")

            # Send completion alert (include Bybit + OKX status)
            bybit_status_str = "OK" if bybit_success else "ERRORS (check logs)"
            okx_status_str   = (
                "OK" if okx_success
                else ("SKIPPED (not flagged)" if not args.include_okx else "ERRORS (check logs)")
            )
            send_ntfy_alert(
                message=(f"EMERGENCY EXIT COMPLETE\n"
                         f"HL status: {status}\n"
                         f"Bybit close-all: {bybit_status_str}\n"
                         f"OKX close-all: {okx_status_str}\n"
                         f"Residual HL positions: {len(postcheck.get('residual_positions', []))}"),
                title="EMERGENCY EXIT COMPLETE",
                priority="high",
                logger=logger,
            )
        else:
            logger.warning("Post-check skipped by --skip-postcheck flag")

        # K460: Aevo emergency close-all (4th venue, STUB scaffold)
        aevo_success = True
        if args.include_aevo:
            logger.info("=== AEVO EMERGENCY CLOSE-ALL (K460 4th venue STUB scaffold) ===")
            aevo_api_key    = os.environ.get("AEVO_API_KEY", "")
            aevo_api_secret = os.environ.get("AEVO_API_SECRET", "")
            aevo_success = close_aevo_positions(
                api_key=aevo_api_key,
                api_secret=aevo_api_secret,
                dry_run=False,
                logger=logger,
            )
            if aevo_success:
                logger.info("Aevo close-all: STUB returned OK (no actual API call yet).")
            else:
                logger.warning(
                    "Aevo close-all: STUB not implemented. Manual close required at app.aevo.xyz."
                )
        else:
            logger.info("Aevo close-all skipped (--no-aevo, default at K460 scaffold).")

        # K460: dYdX v4 emergency close-all (5th venue, Cosmos chain STUB scaffold)
        dydx_success = True
        if args.include_dydx:
            logger.info("=== dYdX v4 EMERGENCY CLOSE-ALL (K460 5th venue Cosmos STUB scaffold) ===")
            dydx_success = close_dydx_positions(dry_run=False, logger=logger)
            if dydx_success:
                logger.info("dYdX v4 close-all: STUB returned OK (no actual Cosmos tx yet).")
            else:
                logger.warning(
                    "dYdX v4 close-all: STUB not implemented (Cosmos signing TODO). "
                    "Manual close required at dydx.trade."
                )
        else:
            logger.info("dYdX v4 close-all skipped (--no-dydx, default at K460 scaffold).")

        # K468: JLP (Jupiter Perpetuals LP) emergency exit — Solana STUB scaffold
        jlp_success = True
        if args.include_jlp:
            logger.info("=== JLP EMERGENCY CLOSE GUIDANCE (K468 Solana LP STUB scaffold) ===")
            jlp_success = close_jlp_positions(dry_run=False, logger=logger)
            if jlp_success:
                logger.info("JLP close: STUB returned OK (no actual Solana tx — manual close required).")
            else:
                logger.warning(
                    "JLP close: STUB not implemented (Solana wallet signing required). "
                    "Manual close: https://jup.ag/perp → Earn → JLP → Withdraw."
                )
        else:
            logger.info(
                "JLP close skipped (--include-jlp not set, default off at K468 scaffold). "
                "Use --include-jlp to print JLP guidance if JLP position is active."
            )

        # K473: Spark sUSDS (Sky/MakerDAO) emergency exit — Ethereum DeFi STUB scaffold
        spark_success = True
        if args.include_spark:
            logger.info("=== SPARK sUSDS EMERGENCY REDEMPTION GUIDANCE (K473 Ethereum DeFi STUB scaffold) ===")
            spark_success = close_spark_positions(dry_run=False, logger=logger)
            if spark_success:
                logger.info("Spark sUSDS: STUB returned OK (no actual Ethereum tx — manual redemption required).")
            else:
                logger.warning(
                    "Spark sUSDS: STUB not implemented (Ethereum wallet signing required). "
                    "Manual redemption: https://app.spark.fi/ → Earn → sUSDS → Withdraw."
                )
        else:
            logger.info(
                "Spark sUSDS close skipped (--include-spark not set, default off at K473 scaffold). "
                "Use --include-spark to print Spark sUSDS guidance if sUSDS position is active."
            )

        overall_success = success and bybit_success and okx_success and aevo_success and dydx_success and jlp_success and spark_success  # k512 close is embedded in HL+Bybit exit above
        return 0 if overall_success else 1

    # Dry-run success
    logger.info("")
    logger.info("DRY-RUN COMPLETE. No trades executed.")
    logger.info("When ready to execute:")
    logger.info("  1. Verify the plan above is correct")
    logger.info("  2. Export HL_USER_ADDRESS, HL_PRIVATE_KEY, BYBIT_API_KEY, BYBIT_API_SECRET env vars")
    logger.info("  3. For OKX (v6.20): export OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE env vars")
    logger.info("  4. Aevo (v6.20, K460): export AEVO_API_KEY, AEVO_API_SECRET (STUB — TODO post-K460)")
    logger.info("  5. dYdX v4 (v6.20, K460): Cosmos SDK signing required (STUB — TODO post-K460)")
    logger.info("  6. Run: python3 scripts/emergency_hl_exit.py --EXECUTE")
    logger.info("     (adds Bybit close-all by default; use --no-bybit to skip)")
    logger.info("     (adds OKX close-all with --include-okx; default off at K456 scaffold)")
    logger.info("     (adds Aevo close-all with --include-aevo; STUB at K460 scaffold)")
    logger.info("     (adds dYdX v4 close-all with --include-dydx; STUB at K460 scaffold)")
    logger.info("  7. Confirm both interactive prompts")
    if args.include_bybit:
        logger.info("  [DRY-RUN] Bybit close-all would be attempted (--include-bybit=True)")
    else:
        logger.info("  [DRY-RUN] Bybit close-all would be skipped (--no-bybit)")
    if args.include_okx:
        logger.info("  [DRY-RUN] OKX close-all would be attempted (--include-okx)")
    else:
        logger.info("  [DRY-RUN] OKX close-all would be skipped (default --no-okx at K456 scaffold)")
    if args.include_aevo:
        logger.info("  [DRY-RUN] Aevo close-all STUB would be attempted (--include-aevo)")
    else:
        logger.info("  [DRY-RUN] Aevo close-all would be skipped (default --no-aevo at K460 scaffold)")
    if args.include_dydx:
        logger.info("  [DRY-RUN] dYdX v4 close-all STUB would be attempted (--include-dydx)")
    else:
        logger.info("  [DRY-RUN] dYdX v4 close-all would be skipped (default --no-dydx at K460 scaffold)")

    # K415: USDY dry-run note
    logger.info("")
    logger.info("  [USDY — K415 §21.6] USDY sleeve emergency guidance:")
    logger.info("    USDY is T-bill backed → HOLD through HL/Bybit crisis (do NOT redeem).")
    logger.info("    Redemption: 1 business day post 40-day lock. Cannot be rushed.")
    logger.info("    Redeem at ondo.finance only if capital needed after HL+Bybit exit.")
    logger.info("    Use --include-usdy to see USDY guidance during --EXECUTE mode.")

    # K459: K457 basket dry-run note
    logger.info("")
    logger.info("  [K457 basket — K459 §32] BTC+ETH+SOL basket emergency guidance:")
    logger.info("    K457 basket positions (HL+Bybit, up to 6 legs) auto-detected in plan.")
    logger.info("    Close protocol: SHORT LEGS FIRST (avoid uncovered short), then LONG LEGS.")
    logger.info("    Basket is in 60d paper-trade — no real positions until v6.20 activation.")
    logger.info("    Use --include-k457 to print structured basket close summary.")
    logger.info("    See: docs/k302a_runbook.md §32")

    # K468: JLP (Jupiter Perpetuals LP) dry-run note
    logger.info("")
    logger.info("  [JLP — K468 §36] Jupiter Perpetuals LP emergency guidance:")
    logger.info("    JLP is Solana-based (NOT on HL/Bybit/OKX) — manual close required.")
    logger.info("    Close: https://jup.ag/perp → Earn → JLP → Withdraw. Then swap to USDC.")
    logger.info("    Entry only when K468 monitor fires ENTRY_READY (gross APY >= 25%).")
    logger.info("    K467: current APY 1.68% << break-even 21% — no position expected now.")
    logger.info("    If position active: close JLP on Solana, then close HL delta hedge short.")
    logger.info("    Use --include-jlp to print JLP guidance during --EXECUTE mode.")
    logger.info("    See: docs/k302a_runbook.md §36 | Monitor: data/jlp_apy_dashboard.json")
    if args.include_jlp:
        logger.info("  [DRY-RUN] JLP close guidance STUB would be printed (--include-jlp)")
    else:
        logger.info("  [DRY-RUN] JLP close would be skipped (default --no-jlp at K468 scaffold)")

    # K473: Spark sUSDS (Sky/MakerDAO) dry-run note
    logger.info("")
    logger.info("  [Spark sUSDS — K473 §37] Spark sUSDS emergency guidance:")
    logger.info("    sUSDS is Ethereum DeFi (NOT a HL/Bybit/OKX perp) — manual redemption required.")
    logger.info("    Redeem: https://app.spark.fi/ → Earn → sUSDS → Withdraw (INSTANT, no lockup).")
    logger.info("    Or via Sky: https://sky.money/ → Savings → Withdraw.")
    logger.info("    K473: 50/50 sUSDe+sUSDS sleeve (v6.21 candidate), combined APY ~3.6–4.5%.")
    logger.info("    sUSDS current APY: ~3.34% (K473 live fetch). No HL delta hedge needed.")
    logger.info("    Use --include-spark to print sUSDS guidance during --EXECUTE mode.")
    logger.info("    See: docs/k302a_runbook.md §37 | Monitor: data/spark_usds_dashboard.json")
    if args.include_spark:
        logger.info("  [DRY-RUN] Spark sUSDS guidance STUB would be printed (--include-spark)")
    else:
        logger.info("  [DRY-RUN] Spark sUSDS close would be skipped (default --no-spark at K473 scaffold)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

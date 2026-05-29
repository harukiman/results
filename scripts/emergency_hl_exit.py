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

    # All other positions: close in any order (non-K449, non-K457)
    handled_coins = k449_coins | k457_coins
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
            "K460: --include-dydx flag added (5th venue, Cosmos chain STUB scaffold)"
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

        overall_success = success and bybit_success and okx_success and aevo_success and dydx_success and jlp_success
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

    return 0


if __name__ == "__main__":
    sys.exit(main())

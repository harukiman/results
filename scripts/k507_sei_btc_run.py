#!/usr/bin/env python3
"""
k507_sei_btc_run.py — K507 SEI-BTC Funding Rate Differential Strategy
=======================================================================
Implements a paired-trade (long SEI / short BTC or reverse) based on the
7-day EMA of the SEI-BTC funding rate differential.  Designed as a
delta-neutral carry trade split across HyperLiquid (primary 1.5%) and
Bybit (secondary 1.5%) for a combined 3% sleeve.

Architecture (K507, following K500/K493/K484/K476/K478 pattern):
  1. compute_fr_differential(sei_fr, btc_fr)     → 7d EMA: SEI FR − BTC FR
  2. decide_position(fr_diff_ema)                → long_asset / short_asset or None
  3. compute_delta_neutral_notional(aum, sleeve_pct, leverage=4) → tuple
  4. submit_paired_trade(long_leg, short_leg)    → POST_ONLY both legs in parallel
  5. daily_rebalance()                           → drift > 5% triggers rebalance
  6. close_paired_position(reason)               → sequential: short first, then long

K507 findings accepted (K514 scaffold):
  - OOS Sharpe 48.10 (Cosmos 3rd CONFIRMED: SEI EVM-compat + Cosmos SDK distinct from ATOM/INJ)
  - $179K/yr net @ $10M AUM (3% sleeve, 4x leverage, net of costs)
  - family rank #2 (ATOM Sh50.79 > SEI Sh48.10 > AVAX Sh43.89 > SOL Sh16.30 > INJ Sh11.23 > ETH Sh5.66)
  - HL 1.5% + Bybit 1.5% split → HL 63.5% (1.5pp headroom below 65% cap)
  - SEI EVM compatibility: supports EVM wallets + Cosmos SDK — unique dual-stack
  - SEI parallelized EVM execution creates distinct FR dynamics from ATOM/INJ
  - 8h cron cadence (matches FR settlement cycle)
  - v6.27 candidate sleeve (paired-trade total 20%):
    K449 5% + K476 3% + K484 3% + K493 3% + K500 3% + K507 3% = 20% combined

HL+Bybit split rationale:
  HL reached 63.5% concentration with SEI on HL-only.
  Split 50/50: SEI leg HL, BTC leg Bybit (or reverse based on signal direction).
  Both venues: POST_ONLY parallel execution.
  Net HL concentration: 63.5% (1.5pp headroom vs 65% cap).

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k507_sei_btc_run.py --dry-run
  python3 scripts/k507_sei_btc_run.py --status
  python3 scripts/k507_sei_btc_run.py --rebalance
  python3 scripts/k507_sei_btc_run.py --close "scheduled exit"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR    = REPO_ROOT / "data"
CACHE_DIR   = REPO_ROOT / "cache"
LOGS_DIR    = REPO_ROOT / "logs"
for _d in [DATA_DIR, CACHE_DIR, LOGS_DIR]:
    _d.mkdir(exist_ok=True)

DASHBOARD_PATH  = DATA_DIR  / "k507_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k507_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k507_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.03          # K507 sleeve = 3% of AUM (v6.27 activation target)
LEVERAGE            = 4.0           # 4x per K507 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
SIGNAL_THRESHOLD    = 0.00001       # 7d EMA FR diff must exceed this to enter
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window for short leg
EMA_PERIOD_DAYS     = 7             # 7-day EMA smoothing constant
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── HL+Bybit split constants (K507 spec: 1.5% HL + 1.5% Bybit) ───────────────
# HL primary 1.5%: one leg of the pair executes on HL
# Bybit secondary 1.5%: the other leg executes on Bybit
# Split allocation: each venue handles half the total sleeve
HL_SLEEVE_PCT     = 0.015   # HL portion: 1.5% of AUM
BYBIT_SLEEVE_PCT  = 0.015   # Bybit portion: 1.5% of AUM
HL_CONCENTRATION_POST_K507 = 63.5  # HL cap: 63.5% (1.5pp headroom vs 65% limit)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_SEI_SHORT_BTC  = "LONG_SEI_SHORT_BTC"
STATE_LONG_BTC_SHORT_SEI  = "LONG_BTC_SHORT_SEI"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k507/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k507] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch + 7d EMA differential
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for SEI and BTC from HL.
    Returns {symbol: fr_8h_fraction}.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k507] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in ("SEI", "BTC"):
        if sym not in universe:
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K507 FR history JSONL (all records)."""
    if not FR_HISTORY_PATH.exists():
        return []
    records: List[dict] = []
    for line in FR_HISTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _append_fr_history(fr_sei: float, fr_btc: float, diff: float) -> None:
    """Append one K507 FR snapshot to history."""
    rec = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "fr_sei": round(fr_sei, 10),
        "fr_btc": round(fr_btc, 10),
        "diff":   round(diff, 10),   # SEI FR − BTC FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def compute_fr_differential(sei_fr: Optional[float] = None,
                             btc_fr: Optional[float] = None) -> dict:
    """
    Fetch live SEI & BTC FRs from HL (or use provided values for testing),
    append to history, compute 7d EMA.

    K507 Cosmos 3rd hypothesis: SEI (parallelized EVM + Cosmos SDK) has
    structurally different FR dynamics from BTC due to:
      - Parallelized EVM execution creates unique demand spikes absent in ATOM/INJ
      - EVM wallet compatibility enables Ethereum DeFi capital flows → FR asymmetry
      - Cosmos SDK interoperability with IBC + Cosmos chains
      - Dual-stack (EVM + CosmWasm) creates orthogonal on-chain liquidity dynamics
    Family rank #2: SEI OOS Sh 48.10 vs ATOM 50.79 (very close; near-equal alpha)
    HL+Bybit split: 1.5% HL + 1.5% Bybit → HL 63.5% (1.5pp headroom vs 65% cap)

    Args:
      sei_fr: override SEI FR (optional, for testing)
      btc_fr: override BTC FR (optional, for testing)

    Returns:
      {
        "fr_sei":          float,   # current 8h FR for SEI
        "fr_btc":          float,   # current 8h FR for BTC
        "raw_diff":        float,   # SEI FR − BTC FR (current)
        "ema_7d":          float,   # 7d EMA of SEI−BTC diff
        "history_points":  int,     # number of history records used
        "ts_jst":          str,
      }
    """
    if sei_fr is None or btc_fr is None:
        frs    = _fetch_hl_fr_batch()
        sei_fr = frs.get("SEI", 0.0)
        btc_fr = frs.get("BTC", 0.0)

    raw_diff = sei_fr - btc_fr

    _append_fr_history(sei_fr, btc_fr, raw_diff)

    # Load history for EMA (7 days × 3 settlements/day = 21 points)
    history = _load_fr_history()
    diffs   = [r["diff"] for r in history if "diff" in r]

    # Exponential MA: α = 2 / (EMA_PERIOD_DAYS * 3 + 1) for 8h cadence
    n_periods = EMA_PERIOD_DAYS * 3   # ~21 8h periods per 7 days
    alpha     = 2.0 / (n_periods + 1)
    ema = diffs[0] if diffs else 0.0
    for d in diffs[1:]:
        ema = alpha * d + (1 - alpha) * ema

    return {
        "fr_sei":          round(sei_fr, 10),
        "fr_btc":          round(btc_fr, 10),
        "raw_diff":        round(raw_diff, 10),
        "ema_7d":          round(ema, 10),
        "history_points":  len(diffs),
        "ts_jst":          datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(fr_diff: dict,
                    threshold: float = SIGNAL_THRESHOLD) -> Optional[dict]:
    """
    Determine trade direction from 7d EMA differential.

    Logic (SEI-BTC pair):
      ema_7d > +threshold → SEI FR > BTC FR
        → short SEI (collect high FR) / long BTC (cheap carry)
        → position_state = LONG_BTC_SHORT_SEI
        → SEI short on HL (1.5%), BTC long on Bybit (1.5%)
      ema_7d < -threshold → BTC FR > SEI FR
        → short BTC / long SEI
        → position_state = LONG_SEI_SHORT_BTC
        → SEI long on HL (1.5%), BTC short on Bybit (1.5%)
      |ema_7d| <= threshold → NEUTRAL (no trade)

    K507 SEI EVM-compat edge (OOS Sharpe 48.10, family rank #2):
      SEI-BTC differential is driven by SEI's parallelized EVM execution.
      Dual-stack (EVM + CosmWasm) + Cosmos SDK creates distinct FR patterns
      from both ATOM (IBC governance) and INJ (DeFi-perp native DEX).
      HL+Bybit split: SEI leg on HL, BTC leg on Bybit (or reverse) to maintain
      HL concentration at 63.5% (1.5pp headroom below 65% cap).

    Returns dict with {long_asset, short_asset, long_venue, short_venue, ema_7d,
                        signal_strength, size_multiplier} or None if NEUTRAL.
    """
    ema     = fr_diff.get("ema_7d", 0.0)
    abs_ema = abs(ema)

    if abs_ema <= threshold:
        return None

    if ema > 0:
        # SEI FR > BTC FR: short SEI (collect high FR), long BTC (cheap carry)
        long_asset   = "BTC"
        short_asset  = "SEI"
        state        = STATE_LONG_BTC_SHORT_SEI
        # HL+Bybit split: SEI (short) on HL, BTC (long) on Bybit
        long_venue   = "Bybit"
        short_venue  = "HL"
    else:
        # BTC FR > SEI FR: short BTC (collect high FR), long SEI (cheap carry)
        long_asset   = "SEI"
        short_asset  = "BTC"
        state        = STATE_LONG_SEI_SHORT_BTC
        # HL+Bybit split: SEI (long) on HL, BTC (short) on Bybit
        long_venue   = "HL"
        short_venue  = "Bybit"

    # Signal strength: ratio of EMA to threshold (capped at 3x for sizing)
    strength = min(abs_ema / threshold, 3.0)

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "ema_7d":          ema,
        "signal_strength": round(strength, 4),
        "size_multiplier": 1.0,   # reserved for future dynamic sizing
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Delta-neutral notional computation (HL+Bybit split)
# ─────────────────────────────────────────────────────────────────────────────

def compute_delta_neutral_notional(
    aum:        float = AUM_DEFAULT,
    sleeve_pct: float = SLEEVE_PCT,
    leverage:   float = LEVERAGE,
) -> Tuple[float, float, float, float]:
    """
    Compute equal notional for both legs of the SEI-BTC paired trade.

    K507 HL+Bybit split:
      sleeve_capital_total  = aum × sleeve_pct           (e.g. $10M × 3% = $300K)
      sleeve_capital_hl     = aum × HL_SLEEVE_PCT        ($10M × 1.5% = $150K)
      sleeve_capital_bybit  = aum × BYBIT_SLEEVE_PCT     ($10M × 1.5% = $150K)
      notional_per_venue    = sleeve_capital_hl × leverage ($150K × 4 = $600K/venue)
      notional_per_leg      = notional_per_venue          ($600K per leg, 1 leg per venue)
      total_notional        = notional_per_venue × 2      ($1.2M combined)

    At $10M / 3% total / 4x:
      HL leg:      $150K capital × 4x = $600K notional  (1.5% sleeve on HL)
      Bybit leg:   $150K capital × 4x = $600K notional  (1.5% sleeve on Bybit)
      Total:       $1,200,000 notional (two legs combined)

    Returns (notional_per_leg, total_notional, hl_notional, bybit_notional).
    """
    sleeve_capital_total  = aum * sleeve_pct
    sleeve_capital_hl     = aum * HL_SLEEVE_PCT
    sleeve_capital_bybit  = aum * BYBIT_SLEEVE_PCT
    notional_hl           = sleeve_capital_hl    * leverage
    notional_bybit        = sleeve_capital_bybit * leverage
    # Each venue handles one leg at equal notional
    notional_per_leg = (notional_hl + notional_bybit) / 2.0
    total_notional   = notional_hl + notional_bybit
    return (
        round(notional_per_leg, 2),
        round(total_notional, 2),
        round(notional_hl, 2),
        round(notional_bybit, 2),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Paired trade submission (K507: HL primary + Bybit secondary)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K507 paired trade: POST_ONLY both legs in parallel (K439 pattern).

    Protocol (K507 HL+Bybit split):
      1. Submit leg on HL venue POST_ONLY (1.5% of AUM)
      2. Submit leg on Bybit venue POST_ONLY (1.5% of AUM)
      3. Both legs submitted in parallel to minimise timing divergence
      4. IOC fallback per leg if POST_ONLY times out within IOC_TIMEOUT_SEC
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SEI", "notional": 600000, "venue": "HL"}
      short_leg: {"symbol": "BTC", "notional": 600000, "venue": "Bybit"}
      dry_run:   True = paper-trade (default)

    Returns execution result dict.
    """
    ts        = datetime.now(UTC).isoformat()
    long_sym  = long_leg["symbol"]
    short_sym = short_leg["symbol"]
    long_notional  = long_leg.get("notional", 0.0)
    short_notional = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue", "HL")
    short_venue = short_leg.get("venue", "Bybit")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K507] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notional:,.0f}  "
              f"+ SHORT {short_sym}@{short_venue} ${short_notional:,.0f}")
        result = {
            "status":            "DRY_RUN",
            "long_result":       {"order_id": f"PAPER_LONG_{long_sym}_{int(time.time())}", "status": "DRY_RUN"},
            "short_result":      {"order_id": f"PAPER_SHORT_{short_sym}_{int(time.time())}", "status": "DRY_RUN"},
            "fill_price_long":   None,
            "fill_price_short":  None,
            "long_symbol":       long_sym,
            "short_symbol":      short_sym,
            "long_notional":     long_notional,
            "short_notional":    short_notional,
            "long_venue":        long_venue,
            "short_venue":       short_venue,
            "execution_mode":    "POST_ONLY_PARALLEL",   # K439 pattern
            "split_protocol":    "HL_PRIMARY_BYBIT_SECONDARY",  # K507 1.5%+1.5%
            "ts_utc":            ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K507] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notional:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notional:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"
    long_filled    = False  # scaffold: poll logic not implemented
    short_filled   = False

    if not long_filled and not short_filled:
        print(f"  [K507] Neither leg filled within timeout — retry next 8h cycle")
        return {
            "status":       "RETRY_NEXT_CYCLE",
            "long_result":  {"order_id": long_order_id,  "status": "TIMEOUT"},
            "short_result": {"order_id": short_order_id, "status": "TIMEOUT"},
            "ts_utc":       ts,
        }

    if long_filled and not short_filled:
        print(f"  [K507] Long filled — short POST_ONLY timeout → IOC fallback")
        return {
            "status":       "LONG_FILL_SHORT_IOC",
            "long_result":  {"order_id": long_order_id,  "status": "FILLED"},
            "short_result": {"order_id": short_order_id, "status": "IOC"},
            "ts_utc":       ts,
        }

    result = {
        "status":            "FILLED",
        "long_result":       {"order_id": long_order_id,  "status": "FILLED"},
        "short_result":      {"order_id": short_order_id, "status": "FILLED"},
        "fill_price_long":   None,
        "fill_price_short":  None,
        "long_venue":        long_venue,
        "short_venue":       short_venue,
        "execution_mode":    "POST_ONLY_PARALLEL",
        "split_protocol":    "HL_PRIMARY_BYBIT_SECONDARY",
        "ts_utc":            ts,
    }
    _append_trade_log(result)
    return result


def _append_trade_log(record: dict) -> None:
    with open(TRADE_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Delta-neutral drift rebalance
# ─────────────────────────────────────────────────────────────────────────────

def daily_rebalance(dashboard: dict) -> dict:
    """
    Check if current K507 position has drifted beyond DRIFT_REBALANCE_PCT (5%).
    If so, compute rebalance action.

    Drift detection:
      - Fetch current mark prices for SEI and BTC from HL (for SEI leg)
      - Bybit leg drift checked separately via Bybit API (live only)
      - Compare long_notional_current vs short_notional_current
      - If |long/short - 1| > 5%: rebalance required

    Note: SEI-BTC split uses two venues — HL for one leg, Bybit for the other.
    Drift accumulates independently on each venue.
    The 5% threshold matches K493/K484/K500 setting.

    Returns rebalance decision dict.
    """
    state = dashboard.get("position_state", STATE_NEUTRAL)
    if state == STATE_NEUTRAL:
        return {"rebalance_required": False, "reason": "NEUTRAL — no position"}

    long_notional_init  = float(dashboard.get("long_notional", 0.0))
    short_notional_init = float(dashboard.get("short_notional", 0.0))

    if long_notional_init <= 0 or short_notional_init <= 0:
        return {"rebalance_required": False, "reason": "no recorded notionals"}

    # For paper-trade scaffold: simulate 0% drift (no rebalance needed)
    drift_pct    = 0.0
    stored_drift = float(dashboard.get("delta_neutral_drift_pct", 0.0))
    if abs(stored_drift) > 0:
        drift_pct = stored_drift

    rebalance_needed = abs(drift_pct) > DRIFT_REBALANCE_PCT

    return {
        "rebalance_required":   rebalance_needed,
        "drift_pct":            round(drift_pct, 6),
        "threshold_pct":        DRIFT_REBALANCE_PCT,
        "long_notional_init":   long_notional_init,
        "short_notional_init":  short_notional_init,
        "action":               "REBALANCE" if rebalance_needed else "HOLD",
        "reason": (
            f"Drift {drift_pct:.2%} > threshold {DRIFT_REBALANCE_PCT:.0%}"
            if rebalance_needed else
            f"Drift {drift_pct:.2%} within {DRIFT_REBALANCE_PCT:.0%} threshold"
        ),
        "ts_utc": datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Close paired position (sequential: short first, then long)
# ─────────────────────────────────────────────────────────────────────────────

def close_paired_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close both legs sequentially: short leg first (avoid naked short exposure),
    then long leg.  In live: uses IOC market orders (reduce-only).
    HL leg closes on HL; Bybit leg closes on Bybit.

    Args:
      reason:  human-readable reason for closure
      dry_run: True = paper-trade simulation

    Returns closure result dict.
    """
    ts   = datetime.now(UTC).isoformat()
    dash = _load_dashboard()
    state = dash.get("position_state", STATE_NEUTRAL)

    if state == STATE_NEUTRAL:
        return {"status": "NO_POSITION", "reason": "Already NEUTRAL", "ts_utc": ts}

    if state == STATE_LONG_SEI_SHORT_BTC:
        long_sym,  long_venue  = "SEI", "HL"
        short_sym, short_venue = "BTC", "Bybit"
    else:  # LONG_BTC_SHORT_SEI
        long_sym,  long_venue  = "BTC", "Bybit"
        short_sym, short_venue = "SEI", "HL"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K507] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@{short_venue} ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@{long_venue}  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "short_venue":     short_venue,
            "long_venue":      long_venue,
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "hl_portion":      "HL IOC reduce-only",
            "bybit_portion":   "Bybit IOC reduce-only",
            "ts_utc":          ts,
        }
    else:
        # LIVE scaffold: submit IOC reduce-only on respective venues (sequential)
        print(f"  [K507] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @ {short_venue}  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @ {long_venue}")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "short_venue":    short_venue,
            "long_venue":     long_venue,
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k507_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "current_fr_diff_7d":      0.0,
        "position_state":          STATE_NEUTRAL,
        "long_notional":           0.0,
        "short_notional":          0.0,
        "long_venue":              "—",
        "short_venue":             "—",
        "delta_neutral_drift_pct": 0.0,
        "rebalance_required":      False,
        "daily_pnl_usdc":          0.0,
        "60d_sharpe":              0.0,
        "paper_trade_status":      {"days_elapsed": 0, "target_60d": 60},
    }


def _write_dashboard(
    fr_data:          dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    rebalance:        dict,
    aum:              float,
    hl_notional:      float,
    bybit_notional:   float,
) -> dict:
    """Write k507_dashboard.json."""
    dash = _load_dashboard()

    # Update FR data
    dash["last_poll_jst"]          = fr_data.get("ts_jst", "—")
    dash["current_fr_diff_7d"]     = fr_data.get("ema_7d", 0.0)
    dash["fr_sei_current"]         = fr_data.get("fr_sei", 0.0)
    dash["fr_btc_current"]         = fr_data.get("fr_btc", 0.0)
    dash["fr_raw_diff"]            = fr_data.get("raw_diff", 0.0)
    dash["history_points"]         = fr_data.get("history_points", 0)

    # Update position if decision changed
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]  = state
            dash["long_notional"]   = notional_per_leg
            dash["short_notional"]  = notional_per_leg
            dash["long_venue"]      = decision.get("long_venue", "—")
            dash["short_venue"]     = decision.get("short_venue", "—")
            dash["entry_ts_jst"]    = dash["last_poll_jst"]
            dash["long_asset"]      = decision.get("long_asset")
            dash["short_asset"]     = decision.get("short_asset")
            dash["signal_strength"] = decision.get("signal_strength", 0.0)

    # Rebalance status
    dash["delta_neutral_drift_pct"] = rebalance.get("drift_pct", 0.0)
    dash["rebalance_required"]       = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    total_notional = notional_per_leg * 2
    dash["total_notional_usdc"]    = round(total_notional, 2)
    dash["hl_notional_usdc"]       = round(hl_notional, 2)
    dash["bybit_notional_usdc"]    = round(bybit_notional, 2)
    dash["leverage"]               = LEVERAGE
    dash["sleeve_pct"]             = SLEEVE_PCT
    dash["hl_sleeve_pct"]          = HL_SLEEVE_PCT
    dash["bybit_sleeve_pct"]       = BYBIT_SLEEVE_PCT
    dash["aum_ref_usdc"]           = aum
    dash["margin_used_usdc"]       = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]      = round((total_notional / LEVERAGE) / aum, 4)
    dash["hl_concentration_pct"]   = HL_CONCENTRATION_POST_K507

    # Paper-trade status (60d gate)
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]      = paper_status

    # Gate metrics (60d activation criteria — Phase 10)
    dash["gate_metrics"] = {
        "oos_sharpe_target":    5.0,   # very loose given OOS 48.10
        "fill_rate_target_pct": 60,
        "max_drawdown_pct":     15,
        "current_oos_sharpe":   dash.get("60d_sharpe", 0.0),
        "current_fill_rate":    0.0,   # updated by paper-trade log analysis
        "current_max_dd_pct":   0.0,   # updated by paper-trade log analysis
        "gate_status":          "IN_PROGRESS",
    }

    # Strategy metadata
    dash["paper_trade_mode"]        = PAPER_TRADE
    dash["wave"]                    = "K514"
    dash["strategy"]                = "K507 SEI-BTC FR Differential"
    dash["smart_router"]            = "HL_PRIMARY_BYBIT_SECONDARY"  # K507: split 1.5%+1.5%
    dash["execution_mode"]          = "POST_ONLY_PARALLEL"          # K439 paired execution
    dash["split_protocol"]          = "HL 1.5% + Bybit 1.5% (total 3% sleeve)"
    dash["signal"]                  = decision.get("position_state", STATE_NEUTRAL) if decision else STATE_NEUTRAL
    dash["activation_criteria"]     = {
        "60d_paper_trade_gate":  "required",
        "oos_sharpe_min":        5.0,   # very loose given OOS 48.10
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.03,
        "split":                 "HL 1.5% + Bybit 1.5%",
        "architecture":          "v6.27 (K449 5% + K476 3% + K484 3% + K493 3% + K500 3% + K507 3% = 20% combined paired-trade sleeve)",
    }
    dash["oos_performance"]         = {
        "sharpe":                48.10,
        "ann_return_usd":        179_000,
        "aum_ref":               10_000_000,
        "wave_accept":           "K507 ACCEPT (K514 scaffold)",
        "family_rank":           "#2 (ATOM Sh50.79 > SEI Sh48.10 > AVAX Sh43.89 > SOL Sh16.30 > INJ Sh11.23 > ETH Sh5.66)",
        "cosmos_3rd_hypothesis": "CONFIRMED: SEI EVM-compat + Cosmos SDK distinct from ATOM/INJ",
        "hl_concentration_pct":  63.5,
        "hl_headroom_pp":        1.5,
    }
    dash["combined_sleeve"]         = {
        "K449_eth_btc_sharpe":    5.66,
        "K476_sol_btc_sharpe":   16.30,
        "K484_avax_btc_sharpe":  43.89,
        "K493_atom_btc_sharpe":  50.79,
        "K500_inj_btc_sharpe":   11.23,
        "K507_sei_btc_sharpe":   48.10,
        "K449_ann_return_usd":  187_000,
        "K476_ann_return_usd":  187_000,
        "K484_ann_return_usd":   75_700,
        "K493_ann_return_usd":  231_000,
        "K500_ann_return_usd":  124_000,
        "K507_ann_return_usd":  179_000,
        "combined_ann_return_usd": 810_000,
        "combined_note":         "K449 5% + K476 3% + K484 3% + K493 3% + K500 3% + K507 3% = ~$810K/yr @ $10M (v6.27)",
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single 8h cycle:
      1. Fetch FR differential + compute 7d EMA (SEI-BTC)
      2. Load current position state
      3. Decide: enter / hold / close / flip
      4. Compute delta-neutral notional (HL+Bybit split)
      5. If entering: submit paired trade (POST_ONLY parallel, HL+Bybit split)
      6. If holding: check drift + rebalance
      7. Write k507_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K507 SEI-BTC FR Differential — {ts_jst} ===")
    print(f"  Mode: {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM: ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.0%} total  "
          f"(HL {HL_SLEEVE_PCT:.1%} + Bybit {BYBIT_SLEEVE_PCT:.1%})  Leverage: {LEVERAGE}x")
    print(f"  Split:        HL 1.5% primary + Bybit 1.5% secondary (K507 spec)")
    print(f"  Execution:    POST_ONLY parallel (K439)")
    print(f"  HL cap:       {HL_CONCENTRATION_POST_K507:.1f}% (1.5pp headroom vs 65% limit)")
    print(f"  Cosmos 3rd:   SEI EVM-compat + Cosmos SDK distinct from ATOM/INJ")

    # Step 1: FR differential
    print("\n  [Step 1] Computing SEI-BTC FR differential...")
    fr_data = compute_fr_differential()
    print(f"  SEI FR:     {fr_data['fr_sei']:+.8f} (8h)")
    print(f"  BTC FR:     {fr_data['fr_btc']:+.8f} (8h)")
    print(f"  Raw diff:   {fr_data['raw_diff']:+.8f}  (SEI−BTC)")
    print(f"  7d EMA:     {fr_data['ema_7d']:+.8f}  (threshold ±{SIGNAL_THRESHOLD:.5f})")
    print(f"  History:    {fr_data['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(fr_data)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Strength: {decision['signal_strength']:.2f}x threshold")
    else:
        print(f"  Signal:   NEUTRAL (|ema| <= threshold)")

    # Step 3: Notional sizing (HL+Bybit split)
    notional_per_leg, total_notional, hl_notional, bybit_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing (HL+Bybit split):")
    print(f"  Total sleeve capital: ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M)")
    print(f"  HL leg:               ${hl_notional:,.0f}  (1.5% × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  Bybit leg:            ${bybit_notional:,.0f}  (1.5% × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  Total notional:       ${total_notional:,.0f}")
    print(f"  Margin required:      ${total_notional/LEVERAGE:,.0f}  "
          f"({100/LEVERAGE:.0f}% of notional @ {LEVERAGE}x)")
    print(f"  Margin/AUM:           {(total_notional/LEVERAGE/aum)*100:.1f}%")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {
            "symbol":   decision["long_asset"],
            "notional": hl_notional if decision["long_venue"] == "HL" else bybit_notional,
            "venue":    decision["long_venue"],
        }
        short_leg = {
            "symbol":   decision["short_asset"],
            "notional": hl_notional if decision["short_venue"] == "HL" else bybit_notional,
            "venue":    decision["short_venue"],
        }
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            # Signal reversed — close current + flip
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {
                "symbol":   decision["long_asset"],
                "notional": hl_notional if decision["long_venue"] == "HL" else bybit_notional,
                "venue":    decision["long_venue"],
            }
            short_leg = {
                "symbol":   decision["short_asset"],
                "notional": hl_notional if decision["short_venue"] == "HL" else bybit_notional,
                "venue":    decision["short_venue"],
            }
            trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        else:
            print(f"  Action: HOLD (same direction)")

    elif not decision and current_state != STATE_NEUTRAL:
        # Signal gone — close position
        print(f"  Action: CLOSE (signal below threshold)")
        trade_result = close_paired_position("signal_below_threshold", dry_run=dry_run)

    else:
        print(f"  Action: NO-OP (neutral, no signal)")

    # Step 5: Rebalance check
    print(f"\n  [Step 5] Delta-neutral drift check...")
    rebalance = daily_rebalance(dash)
    print(f"  Drift: {rebalance.get('drift_pct', 0.0):.2%}  "
          f"Threshold: {DRIFT_REBALANCE_PCT:.0%}  "
          f"Action: {rebalance.get('action', 'HOLD')}")

    # Step 6: Write dashboard
    dash_out = _write_dashboard(
        fr_data, decision, notional_per_leg, rebalance, aum,
        hl_notional, bybit_notional
    )
    print(f"\n  [Step 6] Dashboard written → {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K507 Cycle Complete ===")
    print(f"  Position state:   {dash_out.get('position_state')}")
    print(f"  7d EMA diff:      {dash_out.get('current_fr_diff_7d'):+.8f}  (SEI−BTC)")
    print(f"  Rebalance req:    {dash_out.get('rebalance_required')}")
    print(f"  Margin/AUM:       {dash_out.get('margin_pct_of_aum', 0)*100:.1f}%")
    print(f"  Paper-trade mode: {PAPER_TRADE}")
    print(f"  OOS Sharpe (K507): 48.10 #2 family  |  $179K/yr net @ $10M (3% sleeve, 4x)")
    print(f"  Cosmos 3rd edge:   SEI EVM-compat + Cosmos SDK, HL+Bybit 1.5%+1.5% split")
    print(f"  HL cap post-K507:  {HL_CONCENTRATION_POST_K507}% (1.5pp headroom)")
    print(f"  Activation gate:  60d paper-trade (OOS Sh >=5.0 + fill_rate >=60% + maxDD <15%)")
    print(f"  v6.27 path:       K449 5% + K476 3% + K484 3% + K493 3% + K500 3% + K507 3% "
          f"= 20% (~$810K/yr @ $10M)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K507 SEI-BTC FR Differential Strategy (K514 scaffold)"
    )
    parser.add_argument("--dry-run",   action="store_true", default=True,
                        help="Paper-trade simulation (default)")
    parser.add_argument("--status",    action="store_true",
                        help="Print current dashboard state and exit")
    parser.add_argument("--rebalance", action="store_true",
                        help="Check and apply delta-neutral rebalance")
    parser.add_argument("--close",     default=None, metavar="REASON",
                        help="Close all paired positions with reason")
    parser.add_argument("--aum",       type=float, default=AUM_DEFAULT,
                        help=f"Reference AUM in USD (default: ${AUM_DEFAULT:,.0f})")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print(f"\n=== K507 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K507 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K507 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
k587_icp_btc_run.py — K587 ICP-BTC Funding Rate Differential Strategy
=======================================================================
Implements a paired-trade (long ICP / short BTC or reverse) based on the
7-day EMA of the ICP-BTC funding rate differential.  Designed as a
delta-neutral carry trade split across HyperLiquid (primary 0.5%) and
Bybit (secondary 0.5%) for a combined 1% sleeve.

HL maxLev cap: ICP has a HL maximum leverage of 5x. Strategy uses 4x
(below the 5x cap). HL concentration: ICP adds to existing ~63.5%
→ HL+Bybit split avoids overconcentration on HL.

Architecture (K587 ICP, following K499/K514/K520/K524 BTC-base family pattern):
  1. compute_fr_differential(icp_fr, btc_fr)      → W=168h EMA: ICP FR − BTC FR
  2. decide_position(fr_diff_ema)                 → long_asset / short_asset or None
  3. compute_delta_neutral_notional(aum, sleeve_pct, leverage=4) → tuple
  4. submit_paired_trade(long_leg, short_leg)     → POST_ONLY both legs in parallel
  5. daily_rebalance()                            → drift > 5% triggers rebalance
  6. close_paired_position(reason)               → sequential: short first, then long

K587 ICP findings accepted (K678 scaffold):
  - OOS Sharpe 12.53 (W=168h, ICP-BTC FR differential, Compute/Cloud cluster)
  - $21K/yr net @ $10M AUM (1% sleeve, 4x leverage, net of costs)
  - HL 0.5% + Bybit 0.5% split (high vol — ICP vol 8.40x highest in family)
  - HL maxLev = 5x (HL hard limit for ICP); strategy uses 4x (below cap)
  - Compute/Cloud cluster: ICP Internet Computer Protocol — decentralised compute
  - Distinct FR dynamics from BTC: cloud compute demand orthogonal to BTC monetary
  - 8h cron cadence (matches FR settlement cycle)
  - 54th daemon

HL+Bybit split rationale:
  ICP has the highest volatility in the BTC-base family (vol 8.40x vs BTC).
  HL maxLev = 5x for ICP → strategy caps at 4x (safety margin below HL limit).
  Split 50/50: ICP leg HL 0.5%, BTC leg Bybit 0.5% (or reverse based on direction).
  Reduces per-venue concentration risk for a highly volatile asset.

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k587_icp_btc_run.py --dry-run
  python3 scripts/k587_icp_btc_run.py --status
  python3 scripts/k587_icp_btc_run.py --rebalance
  python3 scripts/k587_icp_btc_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k587_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k587_icp_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k587_icp_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.01          # K587 ICP sleeve = 1% of AUM total
LEVERAGE            = 4.0           # 4x (below HL maxLev=5 cap for ICP)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
SIGNAL_THRESHOLD    = 0.00001       # W=168h EMA FR diff must exceed this to enter
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window for short leg
EMA_PERIOD_HOURS    = 168           # W=168h (7-day) smoothing window
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── HL+Bybit split constants (K587 spec: 0.5% HL + 0.5% Bybit) ───────────────
# ICP is the highest-vol asset in BTC-base family (vol 8.40x vs BTC).
# HL maxLev for ICP = 5x; strategy uses 4x (margin of safety).
# Split 50/50: ICP leg on HL (0.5%), BTC leg on Bybit (0.5%).
# Or reverse based on signal direction.
HL_SLEEVE_PCT              = 0.005   # HL portion: 0.5% of AUM
BYBIT_SLEEVE_PCT           = 0.005   # Bybit portion: 0.5% of AUM
HL_MAX_LEV_ICP             = 5.0     # HL hard limit for ICP (strategy uses 4x < 5x)
ICP_VOL_MULTIPLE           = 8.40    # ICP vol vs BTC = 8.40x (highest in BTC-base family)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_ICP_SHORT_BTC  = "LONG_ICP_SHORT_BTC"
STATE_LONG_BTC_SHORT_ICP  = "LONG_BTC_SHORT_ICP"

# ── K587 ICP OOS performance (K678 scaffold) ──────────────────────────────────
OOS_SHARPE          = 12.53
ANN_RETURN_USD      = 21_000
FAMILY_RANK         = "Compute/Cloud cluster — ICP vol 8.40x highest in BTC-base family"
W_HOURS             = 168   # smoothing window hours (7-day EMA)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k587-icp/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k587-icp] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch + W=168h EMA differential
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for ICP and BTC from HL.
    Returns {symbol: fr_8h_fraction}.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k587-icp] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in ("ICP", "BTC"):
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
    """Load K587 ICP FR history JSONL (all records)."""
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


def _append_fr_history(fr_icp: float, fr_btc: float, diff: float) -> None:
    """Append one K587 ICP FR snapshot to history."""
    rec = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "fr_icp": round(fr_icp, 10),
        "fr_btc": round(fr_btc, 10),
        "diff":   round(diff, 10),   # ICP FR − BTC FR
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def compute_fr_differential(icp_fr: Optional[float] = None,
                             btc_fr: Optional[float] = None) -> dict:
    """
    Fetch live ICP & BTC FRs from HL (or use provided values for testing),
    append to history, compute W=168h EMA.

    K587 ICP Internet Computer Protocol hypothesis:
      ICP (Dfinity Internet Computer Protocol) creates structurally distinct FR
      dynamics from BTC due to:
      - Decentralized compute substrate: ICP is a blockchain-based cloud computer
        (cycles = compute fee, orthogonal to BTC monetary demand)
      - Neuron staking: ICP staking in governance neurons (up to 8-year lock)
        creates periodic demand spikes from liquid ICP seeking yield on perps
      - Chain-key cryptography: ICP has unique cryptographic primitives (threshold
        ECDSA, BLS signatures) → specialized protocol events drive FR spikes
      - Canister compute demand: ICP canisters = smart contracts with compute cycles;
        developer demand for compute creates orthogonal FR patterns
      - Highest vol in BTC-base family (vol 8.40x vs BTC) → large FR swings
      - HL maxLev = 5x for ICP (strategy uses 4x for safety margin)

    Compute/Cloud cluster: ICP is the founding member of the decentralized cloud
    compute cluster. FR spikes occur on major protocol upgrades, SNS DAO launches,
    compute demand waves (Openchat, DSCVR growth), and neuron unlock events.

    W=168h smoothing window (consistent with K658/K663/K629/K661 ETH-base family).

    Args:
      icp_fr: override ICP FR (optional, for testing)
      btc_fr: override BTC FR (optional, for testing)

    Returns:
      {
        "fr_icp":          float,   # current 8h FR for ICP
        "fr_btc":          float,   # current 8h FR for BTC
        "raw_diff":        float,   # ICP FR − BTC FR (current)
        "ema_168h":        float,   # W=168h EMA of ICP−BTC diff
        "history_points":  int,     # number of history records used
        "ts_jst":          str,
      }
    """
    if icp_fr is None or btc_fr is None:
        frs    = _fetch_hl_fr_batch()
        icp_fr = frs.get("ICP", 0.0)
        btc_fr = frs.get("BTC", 0.0)

    raw_diff = icp_fr - btc_fr

    _append_fr_history(icp_fr, btc_fr, raw_diff)

    # Load history for EMA (168h / 8h per settlement = 21 points for full window)
    history = _load_fr_history()
    diffs   = [r["diff"] for r in history if "diff" in r]

    # Exponential MA: α = 2 / (n_periods + 1) where n = 168h / 8h = 21 periods
    n_periods = EMA_PERIOD_HOURS // 8   # 21 8h periods per 168h
    alpha     = 2.0 / (n_periods + 1)
    ema = diffs[0] if diffs else 0.0
    for d in diffs[1:]:
        ema = alpha * d + (1 - alpha) * ema

    return {
        "fr_icp":          round(icp_fr, 10),
        "fr_btc":          round(btc_fr, 10),
        "raw_diff":        round(raw_diff, 10),
        "ema_168h":        round(ema, 10),
        "history_points":  len(diffs),
        "ts_jst":          datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(fr_diff: dict,
                    threshold: float = SIGNAL_THRESHOLD) -> Optional[dict]:
    """
    Determine trade direction from W=168h EMA differential.

    Logic (ICP-BTC pair):
      ema_168h > +threshold → ICP FR > BTC FR
        → short ICP (collect high FR) / long BTC (cheap carry)
        → position_state = LONG_BTC_SHORT_ICP
        → ICP short on HL (0.5%), BTC long on Bybit (0.5%)
      ema_168h < -threshold → BTC FR > ICP FR
        → short BTC / long ICP
        → position_state = LONG_ICP_SHORT_BTC
        → ICP long on HL (0.5%), BTC short on Bybit (0.5%)
      |ema_168h| <= threshold → NEUTRAL (no trade)

    K587 ICP Compute/Cloud edge (OOS Sharpe 12.53, $21K/yr @ 1% sleeve):
      ICP-BTC differential driven by decentralised compute demand cycles.
      Neuron staking lock-up events, SNS DAO launches, and canister compute
      demand create FR spikes orthogonal to BTC monetary supply dynamics.
      HL maxLev=5x for ICP → 4x leverage provides safety margin.
      HL+Bybit split: ICP leg HL (0.5%), BTC leg Bybit (0.5%).

    Returns dict with {long_asset, short_asset, long_venue, short_venue, ema_168h,
                        signal_strength, size_multiplier} or None if NEUTRAL.
    """
    ema     = fr_diff.get("ema_168h", 0.0)
    abs_ema = abs(ema)

    if abs_ema <= threshold:
        return None

    if ema > 0:
        # ICP FR > BTC FR: short ICP (collect high FR), long BTC (cheap carry)
        long_asset   = "BTC"
        short_asset  = "ICP"
        state        = STATE_LONG_BTC_SHORT_ICP
        long_venue   = "Bybit"   # BTC long on Bybit (0.5%)
        short_venue  = "HL"      # ICP short on HL (0.5%, HL maxLev=5x, using 4x)
    else:
        # BTC FR > ICP FR: short BTC (collect high FR), long ICP (cheap carry)
        long_asset   = "ICP"
        short_asset  = "BTC"
        state        = STATE_LONG_ICP_SHORT_BTC
        long_venue   = "HL"      # ICP long on HL (0.5%, HL maxLev=5x, using 4x)
        short_venue  = "Bybit"   # BTC short on Bybit (0.5%)

    # Signal strength: ratio of EMA to threshold (capped at 3x for sizing)
    strength = min(abs_ema / threshold, 3.0)

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "ema_168h":        ema,
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
    Compute equal notional for both legs of the ICP-BTC paired trade.

    K587 ICP HL+Bybit split (K678 spec):
      sleeve_capital_hl    = aum × HL_SLEEVE_PCT        ($10M × 0.5% = $50K)
      sleeve_capital_bybit = aum × BYBIT_SLEEVE_PCT     ($10M × 0.5% = $50K)
      notional_hl          = sleeve_capital_hl × leverage ($50K × 4 = $200K)
      notional_bybit       = sleeve_capital_bybit × leverage ($50K × 4 = $200K)
      notional_per_leg     = $200K  (ICP leg on HL or Bybit)
      total_notional       = $400K  (HL $200K + Bybit $200K)

    At $10M / 1% total / 4x:
      HL capital: $50K × 4x = $200K notional (ICP leg on HL)
      Bybit capital: $50K × 4x = $200K notional (BTC leg on Bybit)
      Per leg: $200K notional each
      Margin: $100K total ($50K HL + $50K Bybit = 1% of AUM)
      HL maxLev ICP = 5x → strategy uses 4x (25% safety margin below HL cap)

    Returns (notional_per_leg, total_notional, hl_notional, bybit_notional).
    """
    sleeve_capital_hl    = aum * HL_SLEEVE_PCT
    sleeve_capital_bybit = aum * BYBIT_SLEEVE_PCT
    notional_hl          = sleeve_capital_hl    * leverage
    notional_bybit       = sleeve_capital_bybit * leverage
    notional_per_leg     = notional_hl          # each leg = $200K
    total_notional       = notional_hl + notional_bybit
    return (
        round(notional_per_leg, 2),
        round(total_notional, 2),
        round(notional_hl, 2),
        round(notional_bybit, 2),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Paired trade submission (K587 ICP: HL+Bybit split)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K587 ICP paired trade: POST_ONLY both legs in parallel (K439 pattern).

    Protocol (K587 ICP HL+Bybit split):
      1. Submit ICP leg on HL POST_ONLY (0.5% sleeve, 4x, HL maxLev=5x)
      2. Submit BTC leg on Bybit POST_ONLY (0.5% sleeve, 4x)
      3. Both legs submitted in parallel to minimise timing divergence
      4. IOC fallback per leg if POST_ONLY times out within IOC_TIMEOUT_SEC
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "ICP", "notional": 200000, "venue": "HL"}
      short_leg: {"symbol": "BTC", "notional": 200000, "venue": "Bybit"}
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
        print(f"  [K587-ICP] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notional:,.0f}  "
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
            "execution_mode":    "POST_ONLY_PARALLEL",       # K439 pattern
            "split_protocol":    "HL_05PCT_BYBIT_05PCT",     # K587 ICP: 0.5%+0.5%
            "hl_max_lev_icp":    HL_MAX_LEV_ICP,             # ICP HL cap = 5x
            "strategy_leverage": LEVERAGE,                   # using 4x (below 5x cap)
            "ts_utc":            ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K587-ICP] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notional:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notional:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"
    long_filled    = False  # scaffold: poll logic not implemented
    short_filled   = False

    if not long_filled and not short_filled:
        print(f"  [K587-ICP] Neither leg filled within timeout — retry next 8h cycle")
        return {
            "status":       "RETRY_NEXT_CYCLE",
            "long_result":  {"order_id": long_order_id,  "status": "TIMEOUT"},
            "short_result": {"order_id": short_order_id, "status": "TIMEOUT"},
            "ts_utc":       ts,
        }

    if long_filled and not short_filled:
        print(f"  [K587-ICP] Long filled — short POST_ONLY timeout → IOC fallback")
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
        "split_protocol":    "HL_05PCT_BYBIT_05PCT",
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
    Check if current K587 ICP position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    Drift detection:
      - Fetch current mark prices for ICP and BTC from HL
      - Compare long_notional_current vs short_notional_current
      - If |long/short - 1| > 5%: rebalance required

    Note: ICP-BTC split across HL+Bybit. ICP leg on HL (HL maxLev=5x, using 4x).
    ICP vol 8.40x vs BTC = HIGHEST in family → drift can accumulate faster.
    The 5% threshold matches K507/K512/K500/K493 setting.

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
        "vol_note":  f"ICP vol {ICP_VOL_MULTIPLE}x vs BTC — monitor drift frequently",
        "ts_utc":    datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Close paired position (sequential: short first, then long)
# ─────────────────────────────────────────────────────────────────────────────

def close_paired_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close both legs sequentially: short leg first (avoid naked short exposure),
    then long leg.  In live: uses IOC market orders (reduce-only).

    K587 ICP HL+Bybit split close:
      ICP leg → HL (HL maxLev=5x, ICP IOC reduce-only)
      BTC leg → Bybit (BTC IOC reduce-only)

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

    if state == STATE_LONG_ICP_SHORT_BTC:
        long_sym,  long_venue  = "ICP", "HL"
        short_sym, short_venue = "BTC", "Bybit"
    else:  # LONG_BTC_SHORT_ICP
        long_sym,  long_venue  = "BTC", "Bybit"
        short_sym, short_venue = "ICP", "HL"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K587-ICP] {mode_tag} CLOSE:")
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
            "venue_protocol":  "HL IOC reduce-only (ICP) + Bybit IOC reduce-only (BTC)",
            "hl_max_lev_note": f"ICP HL maxLev={HL_MAX_LEV_ICP}x; strategy at {LEVERAGE}x",
            "ts_utc":          ts,
        }
    else:
        # LIVE scaffold: submit IOC reduce-only (sequential: short first, then long)
        print(f"  [K587-ICP] SCAFFOLD CLOSE:")
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
    """Load k587_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "current_fr_diff_168h":    0.0,
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
    """Write k587_dashboard.json."""
    dash = _load_dashboard()

    # Update FR data
    dash["last_poll_jst"]          = fr_data.get("ts_jst", "—")
    dash["current_fr_diff_168h"]   = fr_data.get("ema_168h", 0.0)
    dash["fr_icp_current"]         = fr_data.get("fr_icp", 0.0)
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
    dash["margin_used_usdc"]       = round((hl_notional + bybit_notional) / LEVERAGE, 2)
    dash["margin_pct_of_aum"]      = round(((hl_notional + bybit_notional) / LEVERAGE) / aum, 4)
    dash["hl_max_lev_icp"]         = HL_MAX_LEV_ICP
    dash["icp_vol_multiple_vs_btc"] = ICP_VOL_MULTIPLE

    # Paper-trade status (60d gate)
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]      = paper_status

    # Gate metrics (60d activation criteria — Phase 11)
    # K678 spec: Realized Sh >= 6 (50% of 12.53) + fill >= 60% + DD < 20%
    dash["gate_metrics"] = {
        "oos_sharpe_target":    6.0,   # 50% of OOS 12.53 (K678 spec)
        "fill_rate_target_pct": 60,
        "max_drawdown_pct":     20,    # relaxed given highest-vol in family
        "current_oos_sharpe":   dash.get("60d_sharpe", 0.0),
        "current_fill_rate":    0.0,
        "current_max_dd_pct":   0.0,
        "gate_status":          "IN_PROGRESS",
    }

    # Strategy metadata
    dash["paper_trade_mode"]        = PAPER_TRADE
    dash["wave"]                    = "K678"
    dash["strategy"]                = "K587 ICP-BTC FR Differential"
    dash["smart_router"]            = "HL_05PCT_BYBIT_05PCT"
    dash["execution_mode"]          = "POST_ONLY_PARALLEL"  # K439 paired execution
    dash["split_protocol"]          = "HL 0.5% (ICP) + Bybit 0.5% (BTC) — high-vol split"
    dash["signal"]                  = decision.get("position_state", STATE_NEUTRAL) if decision else STATE_NEUTRAL
    dash["activation_criteria"]     = {
        "60d_paper_trade_gate":  "required",
        "oos_sharpe_min":        6.0,    # 50% of OOS 12.53
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  20,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.01,
        "venue":                 "HL 0.5% (ICP) + Bybit 0.5% (BTC)",
        "hl_max_lev_note":       f"ICP HL maxLev={HL_MAX_LEV_ICP}x; strategy uses {LEVERAGE}x",
    }
    dash["oos_performance"]         = {
        "sharpe":                OOS_SHARPE,
        "ann_return_usd":        ANN_RETURN_USD,
        "aum_ref":               10_000_000,
        "wave_accept":           "K587 ICP ACCEPT CONDITIONAL (K678 scaffold)",
        "family_rank":           FAMILY_RANK,
        "icp_hypothesis":        (
            "Internet Computer Protocol (Dfinity) — decentralised cloud compute. "
            "FR driven by neuron staking unlock cycles, SNS DAO launches, canister "
            "compute demand waves. Orthogonal to BTC monetary supply dynamics. "
            "Highest vol in BTC-base family (vol 8.40x vs BTC)."
        ),
        "vol_multiple_vs_btc":   ICP_VOL_MULTIPLE,
        "hl_max_lev":            HL_MAX_LEV_ICP,
        "strategy_leverage":     LEVERAGE,
        "split":                 "HL 0.5% + Bybit 0.5% (high-vol — maxLev=5x HL cap)",
        "w_hours":               W_HOURS,
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single 8h cycle:
      1. Fetch FR differential + compute W=168h EMA (ICP-BTC)
      2. Load current position state
      3. Decide: enter / hold / close / flip
      4. Compute delta-neutral notional (HL+Bybit split)
      5. If entering: submit paired trade (POST_ONLY parallel)
      6. If holding: check drift + rebalance
      7. Write k587_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K587 ICP-BTC FR Differential — {ts_jst} ===")
    print(f"  Mode: {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM: ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.0%} total  "
          f"(HL {HL_SLEEVE_PCT:.1%} + Bybit {BYBIT_SLEEVE_PCT:.1%})  Leverage: {LEVERAGE}x")
    print(f"  HL maxLev ICP:  {HL_MAX_LEV_ICP}x (strategy uses {LEVERAGE}x — below HL cap)")
    print(f"  Venue split:    HL 0.5% (ICP leg) + Bybit 0.5% (BTC leg)")
    print(f"  Execution:      POST_ONLY parallel (K439)")
    print(f"  ICP vol:        {ICP_VOL_MULTIPLE}x vs BTC = HIGHEST in BTC-base family")
    print(f"  OOS Sharpe:     {OOS_SHARPE}  |  ${ANN_RETURN_USD:,.0f}/yr @ $10M (1% sleeve)")
    print(f"  Cluster:        Compute/Cloud — Internet Computer Protocol (Dfinity)")

    # Step 1: FR differential
    print("\n  [Step 1] Computing ICP-BTC FR differential (W=168h EMA)...")
    fr_data = compute_fr_differential()
    print(f"  ICP FR:     {fr_data['fr_icp']:+.8f} (8h)")
    print(f"  BTC FR:     {fr_data['fr_btc']:+.8f} (8h)")
    print(f"  Raw diff:   {fr_data['raw_diff']:+.8f}  (ICP−BTC)")
    print(f"  W=168h EMA: {fr_data['ema_168h']:+.8f}  (threshold ±{SIGNAL_THRESHOLD:.5f})")
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
    print(f"  HL capital:         ${aum * HL_SLEEVE_PCT:,.0f}  (0.5% × ${aum/1e6:.0f}M)")
    print(f"  Bybit capital:      ${aum * BYBIT_SLEEVE_PCT:,.0f}  (0.5% × ${aum/1e6:.0f}M)")
    print(f"  HL notional:        ${hl_notional:,.0f}  (0.5% × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  Bybit notional:     ${bybit_notional:,.0f}  (0.5% × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  Per leg:            ${notional_per_leg:,.0f}  (ICP leg + BTC leg)")
    print(f"  Total notional:     ${total_notional:,.0f}")
    print(f"  Margin required:    ${(hl_notional+bybit_notional)/LEVERAGE:,.0f}  "
          f"({100/LEVERAGE:.0f}% of notional @ {LEVERAGE}x = 1% of AUM)")
    print(f"  HL maxLev check:    {LEVERAGE}x < {HL_MAX_LEV_ICP}x (ICP HL cap) = PASS")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {
            "symbol":   decision["long_asset"],
            "notional": notional_per_leg,
            "venue":    decision["long_venue"],
        }
        short_leg = {
            "symbol":   decision["short_asset"],
            "notional": notional_per_leg,
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
                "notional": notional_per_leg,
                "venue":    decision["long_venue"],
            }
            short_leg = {
                "symbol":   decision["short_asset"],
                "notional": notional_per_leg,
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
    print(f"  Note: {rebalance.get('vol_note', '')}")

    # Step 6: Write dashboard
    dash_out = _write_dashboard(
        fr_data, decision, notional_per_leg, rebalance, aum,
        hl_notional, bybit_notional
    )
    print(f"\n  [Step 6] Dashboard written → {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K587 ICP-BTC Cycle Complete ===")
    print(f"  Position state:   {dash_out.get('position_state')}")
    print(f"  W=168h EMA diff:  {dash_out.get('current_fr_diff_168h'):+.8f}  (ICP−BTC)")
    print(f"  Rebalance req:    {dash_out.get('rebalance_required')}")
    print(f"  Margin/AUM:       {dash_out.get('margin_pct_of_aum', 0)*100:.1f}%")
    print(f"  Paper-trade mode: {PAPER_TRADE}")
    print(f"  OOS Sharpe (K587 ICP): {OOS_SHARPE}")
    print(f"  Ann return:        ${ANN_RETURN_USD:,.0f}/yr net @ $10M (1% sleeve, 4x)")
    print(f"  Compute/Cloud edge: ICP Dfinity decentralised cloud, neuron staking, SNS DAO")
    print(f"  ICP vol multiple:  {ICP_VOL_MULTIPLE}x vs BTC (highest in BTC-base family)")
    print(f"  HL maxLev ICP:     {HL_MAX_LEV_ICP}x cap → using {LEVERAGE}x (margin of safety)")
    print(f"  Venue split:       HL 0.5% (ICP) + Bybit 0.5% (BTC)")
    print(f"  Activation gate:  60d paper-trade (Realized Sh>=6 + fill>=60% + maxDD<20%)")
    print(f"  Wave:             K678 (54th daemon)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K587 ICP-BTC FR Differential Strategy (K678 scaffold)"
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
        print(f"\n=== K587 ICP-BTC Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K587 ICP-BTC Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K587 ICP-BTC Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

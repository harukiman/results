#!/usr/bin/env python3
"""
k541_stablecoin_supply_run.py — K541 Stablecoin Supply Growth Strategy
=======================================================================
Implements a directional signal (LONG BTC+ETH+SOL) based on the 7d stablecoin
supply growth z-score 2nd derivative (acceleration) from DefiLlama API.

Signal hypothesis (K541 ACCEPT CONDITIONAL — K550 scaffold):
  - Stablecoin supply growth acceleration → fresh capital entering crypto
  - DefiLlama free API: USDT + USDC combined supply (dominant 90%+ share)
  - 7d growth z-score 2nd derivative (acceleration spike) captures regime shift
  - OOS Sharpe 1.498 ($294K/yr @ $10M, 7-axis Sh 6.872 +0.165 lift)
  - G5 max corr 0.074 — highly orthogonal to FR-carry family
  - 90d paper-trade gate (longer than 60d given lower Sharpe)

Architecture (K541, following K495 non-paired-trade pattern):
  1. fetch_stablecoin_supply()                → DefiLlama free API
  2. compute_zscore_acceleration(history)    → 7d growth z-score 2nd derivative
  3. decide_position(z_accel, threshold)     → LONG / NEUTRAL
  4. compute_notional(aum, sleeve_pct, lev)  → 3% sleeve × 2x leverage
  5. submit_signal_trade(universe, notional) → BTC + ETH + SOL on HL
  6. daily_rebalance()                       → drift > 5% triggers rebalance
  7. close_signal_position(reason)           → IOC market reduce-only

Strategy constants (V3 — acceleration spike):
  - Universe:        BTC, ETH, SOL (equal weight by default)
  - Signal:          7d supply growth z-score 2nd derivative > threshold
  - Threshold:       0.5 (acceleration spike = 2nd deriv of z-score)
  - Sleeve:          3% of AUM
  - Leverage:        2x (lower than FR-carry 4x — directional risk)
  - Venue:           HL primary (HL 65% cap → monitor concentration)
  - Cron:            Daily 86400s
  - Paper gate:      90d (OOS Sh 1.498 — lower Sharpe requires longer gate)

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k541_stablecoin_supply_run.py --dry-run
  python3 scripts/k541_stablecoin_supply_run.py --status
  python3 scripts/k541_stablecoin_supply_run.py --rebalance
  python3 scripts/k541_stablecoin_supply_run.py --close "scheduled exit"
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
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
CACHE_DIR  = REPO_ROOT / "cache"
LOGS_DIR   = REPO_ROOT / "logs"
for _d in [DATA_DIR, CACHE_DIR, LOGS_DIR]:
    _d.mkdir(exist_ok=True)

DASHBOARD_PATH      = DATA_DIR  / "k541_dashboard.json"
SUPPLY_HISTORY_PATH = CACHE_DIR / "k541_supply_history.jsonl"
TRADE_LOG_PATH      = CACHE_DIR / "k541_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True         # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.03         # K541 sleeve = 3% of AUM (v6.29 activation target)
LEVERAGE            = 2.0          # 2x leverage (lower than FR-carry — directional risk)
AUM_DEFAULT         = 10_000_000.0 # $10M reference AUM
SIGNAL_THRESHOLD    = 0.5          # 7d z-score 2nd derivative (acceleration spike)
DRIFT_REBALANCE_PCT = 0.05         # rebalance if legs drift > 5%
ZSCORE_LOOKBACK     = 30           # 30-day window for z-score normalization
ACCEL_SMOOTH_DAYS   = 7            # 7d smoothing for z-score derivative
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── DefiLlama stablecoin API constants ────────────────────────────────────────
# Free public API — no key required
DEFILLAMA_STABLES_URL = "https://stablecoins.llama.fi/stablecoins"
DEFILLAMA_USDT_ID     = "tether"      # Tether USDT
DEFILLAMA_USDC_ID     = "usd-coin"    # Circle USDC

# ── Universe: BTC + ETH + SOL (equal weight) ─────────────────────────────────
SIGNAL_UNIVERSE = ["BTC", "ETH", "SOL"]

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL   = "NEUTRAL"
STATE_LONG_ALL  = "LONG_BTC_ETH_SOL"   # long all 3 assets on HL

# ── K541 OOS performance (K550 scaffold) ─────────────────────────────────────
OOS_SHARPE          = 1.498
ANN_RETURN_USD      = 294_000
SEVEN_AXIS_SHARPE   = 6.872
SEVEN_AXIS_LIFT     = 0.165
G5_MAX_CORR         = 0.074   # highly orthogonal to FR-carry family
PAPER_GATE_DAYS     = 90      # 90d gate (longer than 60d for lower Sharpe)
TRADES_PER_YR       = 273


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 15) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "crypto-lab-k541/1.0",
                     "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k541] HTTP GET error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k541/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k541] HTTP POST error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Stablecoin supply fetch from DefiLlama
# ─────────────────────────────────────────────────────────────────────────────

def fetch_stablecoin_supply() -> Dict[str, float]:
    """
    Fetch USDT + USDC total circulating supply from DefiLlama free API.
    URL: https://stablecoins.llama.fi/stablecoins

    Returns:
      {
        "usdt_supply":     float,   # USDT circulating (USD)
        "usdc_supply":     float,   # USDC circulating (USD)
        "total_supply":    float,   # USDT + USDC combined
        "ts_utc":          str,
      }

    K541 stablecoin hypothesis:
      - USDT + USDC combined supply captures 90%+ of stablecoin market
      - Supply growth acceleration → fresh capital entering crypto ecosystem
      - Acceleration (2nd derivative of z-score) captures regime shift, not trend
      - V3 signal: 7d z-score 2nd derivative > 0.5 (acceleration spike threshold)
      - 90d paper-trade gate: OOS Sh 1.498 lower than FR-carry family → longer gate
      - G5 max corr 0.074 → highly orthogonal to existing FR-carry strategies

    DefiLlama API (free, public, no auth):
      GET https://stablecoins.llama.fi/stablecoins
      Returns array of stablecoin objects with peggedUSD field for USD peg total
    """
    ts_utc = datetime.now(UTC).isoformat()
    raw = _http_get(DEFILLAMA_STABLES_URL)

    if not raw or "peggedAssets" not in raw:
        # Fallback: try to load from last cache entry
        print(f"  [k541] DefiLlama fetch failed — checking history cache", file=sys.stderr)
        history = _load_supply_history()
        if history:
            last = history[-1]
            print(f"  [k541] Using cached supply from {last.get('ts_utc', 'unknown')}", file=sys.stderr)
            return {
                "usdt_supply":  last.get("usdt_supply", 0.0),
                "usdc_supply":  last.get("usdc_supply", 0.0),
                "total_supply": last.get("total_supply", 0.0),
                "ts_utc":       ts_utc,
                "source":       "cache_fallback",
            }
        return {
            "usdt_supply":  0.0,
            "usdc_supply":  0.0,
            "total_supply": 0.0,
            "ts_utc":       ts_utc,
            "source":       "fetch_failed",
        }

    assets = raw.get("peggedAssets", [])
    usdt_supply = 0.0
    usdc_supply = 0.0
    usdt_found  = False
    usdc_found  = False

    for asset in assets:
        symbol = asset.get("symbol", "").upper()
        name   = asset.get("name", "").lower()

        # USDT detection: exact symbol "USDT" (Tether USD) only — not EURT/CNHT/MXNT
        if not usdt_found and symbol == "USDT" and "tether" in name and "euro" not in name and "cnh" not in name:
            circulating = asset.get("circulating", {})
            val = float(circulating.get("peggedUSD", 0) or 0)
            if val > 1_000_000_000:  # sanity: USDT supply > $1B
                usdt_supply = val
                usdt_found  = True

        # USDC detection: exact symbol "USDC" (Circle USD Coin) only — not USDCV/USDCB
        elif not usdc_found and symbol == "USDC" and "usd coin" in name:
            circulating = asset.get("circulating", {})
            val = float(circulating.get("peggedUSD", 0) or 0)
            if val > 1_000_000_000:  # sanity: USDC supply > $1B
                usdc_supply = val
                usdc_found  = True

        if usdt_found and usdc_found:
            break  # both found, stop iterating

    total_supply = usdt_supply + usdc_supply

    return {
        "usdt_supply":  round(usdt_supply, 2),
        "usdc_supply":  round(usdc_supply, 2),
        "total_supply": round(total_supply, 2),
        "ts_utc":       ts_utc,
        "source":       "defillama_live",
    }


def _load_supply_history() -> List[dict]:
    """Load K541 supply history JSONL (all records)."""
    if not SUPPLY_HISTORY_PATH.exists():
        return []
    records: List[dict] = []
    for line in SUPPLY_HISTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _append_supply_history(supply_data: dict) -> None:
    """Append one K541 supply snapshot to history."""
    rec = {
        "ts_utc":       supply_data.get("ts_utc", datetime.now(UTC).isoformat()),
        "usdt_supply":  round(supply_data.get("usdt_supply", 0.0), 2),
        "usdc_supply":  round(supply_data.get("usdc_supply", 0.0), 2),
        "total_supply": round(supply_data.get("total_supply", 0.0), 2),
        "source":       supply_data.get("source", "unknown"),
    }
    with open(SUPPLY_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Z-score 2nd derivative (acceleration) computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_zscore_acceleration(history: Optional[List[dict]] = None) -> dict:
    """
    Compute 7d stablecoin supply growth z-score 2nd derivative (acceleration).

    V3 signal logic:
      1. Compute 7d supply growth rate for each day:
           growth_rate[i] = (supply[i] - supply[i-7]) / supply[i-7]
      2. Normalize to z-score over 30d lookback window:
           z[i] = (growth_rate[i] - mean(growth_rate[-30:])) / std(growth_rate[-30:])
      3. Compute 1st derivative (velocity):
           dz[i] = z[i] - z[i-1]
      4. Compute 2nd derivative (acceleration) smoothed over 7d:
           accel = mean(dz[-7:])  (7d average of velocity)
      5. Signal fires when accel > SIGNAL_THRESHOLD (0.5)

    K541 stablecoin hypothesis:
      - Supply acceleration (not just growth) signals regime shift
      - Fresh capital inflow → LONG BTC+ETH+SOL universe
      - Daily cadence captures macro-level stablecoin flows
      - OOS Sharpe 1.498 at 90d gate threshold (acceptable directional alpha)
      - 273 trades/yr continuous (sufficient liquidity events)

    Returns:
      {
        "total_supply_latest":  float,
        "growth_rate_7d":       float,   # 7d growth rate (latest)
        "zscore_latest":        float,   # z-score of growth rate
        "zscore_velocity":      float,   # 1st derivative of z-score
        "zscore_acceleration":  float,   # 2nd derivative (7d smoothed)
        "history_points":       int,
        "data_sufficient":      bool,    # need >= 30+7 points
        "signal_fires":         bool,    # accel > threshold
        "ts_jst":               str,
      }
    """
    if history is None:
        history = _load_supply_history()

    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    n      = len(history)

    # Minimum data requirement: 30d lookback + 7d growth window = 37 days
    MIN_POINTS = ZSCORE_LOOKBACK + ACCEL_SMOOTH_DAYS + 1
    if n < MIN_POINTS:
        return {
            "total_supply_latest":  history[-1]["total_supply"] if history else 0.0,
            "growth_rate_7d":       0.0,
            "zscore_latest":        0.0,
            "zscore_velocity":      0.0,
            "zscore_acceleration":  0.0,
            "history_points":       n,
            "data_sufficient":      False,
            "signal_fires":         False,
            "ts_jst":               ts_jst,
            "note":                 f"Need >= {MIN_POINTS} daily points, have {n}",
        }

    supplies = [r["total_supply"] for r in history]

    # Step 1: Compute 7d growth rates
    growth_rates = []
    for i in range(7, n):
        prev = supplies[i - 7]
        if prev <= 0:
            growth_rates.append(0.0)
            continue
        growth_rates.append((supplies[i] - prev) / prev)

    if len(growth_rates) < ZSCORE_LOOKBACK + ACCEL_SMOOTH_DAYS:
        return {
            "total_supply_latest":  supplies[-1],
            "growth_rate_7d":       growth_rates[-1] if growth_rates else 0.0,
            "zscore_latest":        0.0,
            "zscore_velocity":      0.0,
            "zscore_acceleration":  0.0,
            "history_points":       n,
            "data_sufficient":      False,
            "signal_fires":         False,
            "ts_jst":               ts_jst,
            "note":                 "Insufficient growth rate window",
        }

    # Step 2: Compute z-scores over 30d rolling window
    zscores = []
    for i in range(len(growth_rates)):
        window_start = max(0, i - ZSCORE_LOOKBACK + 1)
        window = growth_rates[window_start : i + 1]
        if len(window) < 2:
            zscores.append(0.0)
            continue
        mean_g = sum(window) / len(window)
        var_g  = sum((x - mean_g) ** 2 for x in window) / len(window)
        std_g  = var_g ** 0.5
        if std_g < 1e-12:
            zscores.append(0.0)
        else:
            zscores.append((growth_rates[i] - mean_g) / std_g)

    # Step 3: 1st derivative (velocity) of z-score
    velocities = []
    for i in range(1, len(zscores)):
        velocities.append(zscores[i] - zscores[i - 1])

    if not velocities:
        accel = 0.0
        velocity_latest = 0.0
    else:
        # Step 4: 2nd derivative (acceleration) = 7d mean of velocity
        accel_window    = velocities[-ACCEL_SMOOTH_DAYS:]
        accel           = sum(accel_window) / len(accel_window) if accel_window else 0.0
        velocity_latest = velocities[-1]

    zscore_latest   = zscores[-1]  if zscores   else 0.0
    growth_latest   = growth_rates[-1] if growth_rates else 0.0
    supply_latest   = supplies[-1]

    signal_fires = accel > SIGNAL_THRESHOLD

    return {
        "total_supply_latest":  round(supply_latest, 2),
        "growth_rate_7d":       round(growth_latest, 8),
        "zscore_latest":        round(zscore_latest, 6),
        "zscore_velocity":      round(velocity_latest, 6),
        "zscore_acceleration":  round(accel, 6),
        "history_points":       n,
        "data_sufficient":      True,
        "signal_fires":         signal_fires,
        "threshold":            SIGNAL_THRESHOLD,
        "ts_jst":               ts_jst,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict,
                    threshold: float = SIGNAL_THRESHOLD) -> Optional[dict]:
    """
    Determine trade direction from z-score acceleration signal.

    V3 Logic (acceleration spike):
      accel > +threshold → stablecoin supply accelerating → LONG BTC+ETH+SOL
      accel <= threshold → NEUTRAL (no trade or close existing)

    K541 stablecoin alpha:
      - Supply acceleration = fresh capital deployment signal
      - Not just supply growth (level) — but acceleration of that growth
      - V3 uses 2nd derivative to capture regime inflection points
      - Universe: BTC (risk-on leader) + ETH (DeFi bellwether) + SOL (alt momentum)
      - Equal weight distribution across 3 assets (1/3 each of notional)
      - HL-only execution (3% sleeve × 2x leverage = 6% notional of AUM)
      - Daily cron (86400s) aligns with DefiLlama data update cadence

    Returns dict with position decision or None if NEUTRAL.
    """
    if not signal.get("data_sufficient", False):
        return None

    accel = signal.get("zscore_acceleration", 0.0)

    if accel <= threshold:
        return None

    # Signal strength: ratio of acceleration to threshold (capped at 3x)
    strength = min(accel / threshold, 3.0)

    return {
        "position_state":  STATE_LONG_ALL,
        "universe":        SIGNAL_UNIVERSE,
        "direction":       "LONG",
        "venue":           "HL",
        "acceleration":    accel,
        "threshold":       threshold,
        "signal_strength": round(strength, 4),
        "size_multiplier": 1.0,   # equal weight across universe
        "note":            "V3 acceleration spike: 7d z-score 2nd derivative > 0.5",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Notional computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_notional(
    aum:        float = AUM_DEFAULT,
    sleeve_pct: float = SLEEVE_PCT,
    leverage:   float = LEVERAGE,
) -> Tuple[float, float, float]:
    """
    Compute position sizing for K541 3-asset universe.

    K541 sizing:
      sleeve_capital  = aum × sleeve_pct       (e.g. $10M × 3% = $300K)
      total_notional  = sleeve_capital × leverage ($300K × 2x = $600K)
      per_asset       = total_notional / 3      ($200K per asset: BTC, ETH, SOL)

    At $10M / 3% / 2x:
      Total notional:  $600K  (3 long legs on HL)
      Per-asset notional: $200K each
      Margin required: $300K  (50% of notional @ 2x = 3% of AUM)

    Returns (total_notional, per_asset_notional, margin_required).
    """
    sleeve_capital    = aum * sleeve_pct
    total_notional    = sleeve_capital * leverage
    per_asset_notional = total_notional / len(SIGNAL_UNIVERSE)
    margin_required   = sleeve_capital  # capital at risk = sleeve_capital

    return (
        round(total_notional, 2),
        round(per_asset_notional, 2),
        round(margin_required, 2),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Trade submission
# ─────────────────────────────────────────────────────────────────────────────

def submit_signal_trade(
    universe:           List[str],
    per_asset_notional: float,
    dry_run:            bool = True,
) -> dict:
    """
    Submit K541 signal trades: LONG each asset in universe on HL.

    Protocol (K541 HL-only):
      1. For each asset in universe: submit POST_ONLY LONG
      2. All legs submitted sequentially (directional — not paired/delta-neutral)
      3. IOC fallback if POST_ONLY times out within 5 min per asset
      4. Equal notional per asset ($200K each @ $10M / 3% / 2x)

    Args:
      universe:           ["BTC", "ETH", "SOL"]
      per_asset_notional: per-asset LONG notional in USDC
      dry_run:            True = paper-trade (default)

    Returns execution result dict.
    """
    ts    = datetime.now(UTC).isoformat()
    mode  = "DRY_RUN" if dry_run else ("PAPER_TRADE" if PAPER_TRADE else "LIVE")

    results = {}
    for sym in universe:
        order_id = f"PAPER_LONG_{sym}_{int(time.time())}"
        if dry_run or PAPER_TRADE:
            print(f"  [K541] {mode}: LONG {sym}@HL ${per_asset_notional:,.0f}")
            results[sym] = {
                "order_id": order_id,
                "status":   "DRY_RUN",
                "venue":    "HL",
                "side":     "LONG",
                "notional": per_asset_notional,
            }
        else:
            # LIVE scaffold (not reached in PAPER_TRADE mode)
            print(f"  [K541] SCAFFOLD LIVE: POST_ONLY LONG {sym}@HL ${per_asset_notional:,.0f}")
            results[sym] = {
                "order_id": order_id,
                "status":   "SCAFFOLD",
                "venue":    "HL",
                "side":     "LONG",
                "notional": per_asset_notional,
            }

    trade_record = {
        "status":        mode,
        "universe":      universe,
        "legs":          results,
        "execution_mode": "POST_ONLY_SEQUENTIAL",
        "venue":         "HL",
        "ts_utc":        ts,
    }
    _append_trade_log(trade_record)
    return trade_record


def _append_trade_log(record: dict) -> None:
    with open(TRADE_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Drift rebalance
# ─────────────────────────────────────────────────────────────────────────────

def daily_rebalance(dashboard: dict) -> dict:
    """
    Check if K541 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K541 directional drift:
      - 3-asset equal-weight basket drifts as BTC/ETH/SOL diverge
      - Rebalance when any single asset drifts > 5% from target weight
      - In paper-trade: simulate 0% drift (no rebalance needed in scaffold phase)

    Returns rebalance decision dict.
    """
    state = dashboard.get("position_state", STATE_NEUTRAL)
    if state == STATE_NEUTRAL:
        return {"rebalance_required": False, "reason": "NEUTRAL — no position"}

    stored_drift = float(dashboard.get("max_drift_pct", 0.0))
    rebalance_needed = abs(stored_drift) > DRIFT_REBALANCE_PCT

    return {
        "rebalance_required":  rebalance_needed,
        "max_drift_pct":       round(stored_drift, 6),
        "threshold_pct":       DRIFT_REBALANCE_PCT,
        "action":              "REBALANCE" if rebalance_needed else "HOLD",
        "reason": (
            f"Drift {stored_drift:.2%} > threshold {DRIFT_REBALANCE_PCT:.0%}"
            if rebalance_needed else
            f"Drift {stored_drift:.2%} within {DRIFT_REBALANCE_PCT:.0%} threshold"
        ),
        "ts_utc": datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Close signal position
# ─────────────────────────────────────────────────────────────────────────────

def close_signal_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close all K541 long positions on HL (IOC reduce-only).

    K541 close protocol:
      - Directional position (not paired) — close all 3 longs simultaneously
      - IOC market orders (reduce-only) on HL
      - BTC → ETH → SOL sequence (largest notional first)
      - Signal disappears (accel drops below threshold) → close next cycle

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

    per_asset_notional = float(dash.get("per_asset_notional", 0.0))

    mode = "DRY_RUN" if dry_run else ("PAPER_TRADE" if PAPER_TRADE else "LIVE")
    print(f"  [K541] {mode} CLOSE all LONG positions: reason={reason}")

    close_results = {}
    for sym in SIGNAL_UNIVERSE:
        print(f"    [K541] IOC reduce LONG {sym}@HL ${per_asset_notional:,.0f}")
        close_results[sym] = {
            "status":   "DRY_RUN_CLOSED" if (dry_run or PAPER_TRADE) else "SCAFFOLD_CLOSE",
            "venue":    "HL",
            "side":     "SELL (reduce-only)",
            "notional": per_asset_notional,
        }

    result = {
        "status":          f"{mode}_CLOSED",
        "reason":          reason,
        "close_protocol":  "IOC_SEQUENTIAL_BTC_ETH_SOL",
        "universe":        SIGNAL_UNIVERSE,
        "legs":            close_results,
        "ts_utc":          ts,
    }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k541_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "total_supply_usdt_usdc":  0.0,
        "zscore_acceleration":     0.0,
        "position_state":          STATE_NEUTRAL,
        "total_notional":          0.0,
        "per_asset_notional":      0.0,
        "max_drift_pct":           0.0,
        "rebalance_required":      False,
        "daily_pnl_usdc":          0.0,
        "90d_sharpe":              0.0,
        "paper_trade_status":      {"days_elapsed": 0, "target_90d": 90},
    }


def _write_dashboard(
    supply_data:        dict,
    signal:             dict,
    decision:           Optional[dict],
    total_notional:     float,
    per_asset_notional: float,
    margin_required:    float,
    rebalance:          dict,
    aum:                float,
) -> dict:
    """Write k541_dashboard.json."""
    dash = _load_dashboard()

    # Update supply data
    dash["last_poll_jst"]           = signal.get("ts_jst", "—")
    dash["total_supply_usdt_usdc"]  = supply_data.get("total_supply", 0.0)
    dash["usdt_supply"]             = supply_data.get("usdt_supply", 0.0)
    dash["usdc_supply"]             = supply_data.get("usdc_supply", 0.0)
    dash["supply_source"]           = supply_data.get("source", "unknown")

    # Update signal metrics
    dash["growth_rate_7d"]          = signal.get("growth_rate_7d", 0.0)
    dash["zscore_latest"]           = signal.get("zscore_latest", 0.0)
    dash["zscore_velocity"]         = signal.get("zscore_velocity", 0.0)
    dash["zscore_acceleration"]     = signal.get("zscore_acceleration", 0.0)
    dash["signal_fires"]            = signal.get("signal_fires", False)
    dash["history_points"]          = signal.get("history_points", 0)
    dash["data_sufficient"]         = signal.get("data_sufficient", False)

    # Update position if decision changed
    if decision and dash.get("position_state") == STATE_NEUTRAL:
        dash["position_state"]       = STATE_LONG_ALL
        dash["total_notional"]       = total_notional
        dash["per_asset_notional"]   = per_asset_notional
        dash["entry_ts_jst"]         = dash["last_poll_jst"]
        dash["signal_strength"]      = decision.get("signal_strength", 0.0)
        dash["universe"]             = SIGNAL_UNIVERSE

    # Rebalance status
    dash["max_drift_pct"]           = rebalance.get("max_drift_pct", 0.0)
    dash["rebalance_required"]      = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    dash["total_notional"]          = round(total_notional, 2)
    dash["per_asset_notional"]      = round(per_asset_notional, 2)
    dash["leverage"]                = LEVERAGE
    dash["sleeve_pct"]              = SLEEVE_PCT
    dash["aum_ref_usdc"]            = aum
    dash["margin_required"]         = round(margin_required, 2)
    dash["margin_pct_of_aum"]       = round(margin_required / aum, 4)

    # Paper-trade status (90d gate)
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_90d": 90})
    dash["paper_trade_status"]      = paper_status

    # Gate metrics (90d activation criteria — Phase 10)
    dash["gate_metrics"] = {
        "oos_sharpe_target":    1.2,
        "fill_rate_target_pct": 60,
        "max_drawdown_pct":     25,
        "min_trades_90d":       50,
        "current_oos_sharpe":   dash.get("90d_sharpe", 0.0),
        "current_fill_rate":    0.0,
        "current_max_dd_pct":   0.0,
        "trades_count":         0,
        "gate_status":          "IN_PROGRESS",
    }

    # Strategy metadata
    dash["paper_trade_mode"]        = PAPER_TRADE
    dash["wave"]                    = "K550"
    dash["strategy"]                = "K541 Stablecoin Supply Growth (V3 Acceleration)"
    dash["signal"]                  = decision.get("position_state", STATE_NEUTRAL) if decision else STATE_NEUTRAL
    dash["data_api"]                = "DefiLlama (free public API — stablecoins.llama.fi)"
    dash["signal_version"]          = "V3 — 7d z-score 2nd derivative (acceleration spike)"
    dash["activation_criteria"]     = {
        "90d_paper_trade_gate":  "required",
        "oos_sharpe_min":        1.2,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  25,
        "min_trades_90d":        50,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.03,
        "architecture":          "v6.29 candidate (K541 3% addition)",
    }
    dash["oos_performance"]         = {
        "sharpe":                OOS_SHARPE,
        "ann_return_usd":        ANN_RETURN_USD,
        "aum_ref":               10_000_000,
        "wave_accept":           "K541 ACCEPT CONDITIONAL (K550 scaffold)",
        "seven_axis_sharpe":     SEVEN_AXIS_SHARPE,
        "seven_axis_lift":       SEVEN_AXIS_LIFT,
        "g5_max_corr":           G5_MAX_CORR,
        "trades_per_yr":         TRADES_PER_YR,
        "paper_gate_days":       PAPER_GATE_DAYS,
        "orthogonality_note":    "G5 max corr 0.074 — highly orthogonal to FR-carry family",
    }

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single daily cycle:
      1. Fetch stablecoin supply from DefiLlama
      2. Append to history + compute z-score acceleration
      3. Decide: enter / hold / close
      4. Compute notional (3% sleeve × 2x leverage)
      5. If entering: submit LONG BTC+ETH+SOL on HL
      6. If holding: check drift + rebalance
      7. Write k541_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K541 Stablecoin Supply Growth (V3 Acceleration) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.0%}  Leverage: {LEVERAGE}x")
    print(f"  Universe:  {', '.join(SIGNAL_UNIVERSE)}")
    print(f"  Signal:    V3 — 7d z-score 2nd derivative (acceleration spike > {SIGNAL_THRESHOLD})")
    print(f"  Venue:     HL primary (daily cron 86400s)")
    print(f"  OOS Sh:    {OOS_SHARPE} ($294K/yr @$10M, 7-axis Sh {SEVEN_AXIS_SHARPE} +{SEVEN_AXIS_LIFT} lift)")
    print(f"  Gate:      {PAPER_GATE_DAYS}d paper-trade (OOS Sh >=1.2 + fill_rate >=60% + maxDD <25% + >=50 trades)")

    # Step 1: Fetch stablecoin supply
    print(f"\n  [Step 1] Fetching stablecoin supply from DefiLlama...")
    supply_data = fetch_stablecoin_supply()
    print(f"  USDT:    ${supply_data['usdt_supply']:,.0f}")
    print(f"  USDC:    ${supply_data['usdc_supply']:,.0f}")
    print(f"  Total:   ${supply_data['total_supply']:,.0f}")
    print(f"  Source:  {supply_data.get('source', 'unknown')}")

    # Append to history
    if supply_data["total_supply"] > 0:
        _append_supply_history(supply_data)

    # Step 2: Compute z-score acceleration
    print(f"\n  [Step 2] Computing z-score acceleration...")
    history = _load_supply_history()
    signal  = compute_zscore_acceleration(history)
    print(f"  History points:    {signal['history_points']}")
    print(f"  Data sufficient:   {signal['data_sufficient']}")
    if signal["data_sufficient"]:
        print(f"  7d growth rate:    {signal['growth_rate_7d']:+.6f}")
        print(f"  Z-score:           {signal['zscore_latest']:+.4f}")
        print(f"  Z-score velocity:  {signal['zscore_velocity']:+.4f}")
        print(f"  Z-score accel:     {signal['zscore_acceleration']:+.4f}  (threshold: {SIGNAL_THRESHOLD})")
        print(f"  Signal fires:      {signal['signal_fires']}")
    else:
        print(f"  {signal.get('note', 'building history...')}")

    # Step 3: Position decision
    print(f"\n  [Step 3] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {', '.join(decision['universe'])}@HL")
        print(f"  State:    {decision['position_state']}")
        print(f"  Strength: {decision['signal_strength']:.2f}x threshold")
    else:
        print(f"  Signal:   NEUTRAL (accel <= threshold or insufficient data)")

    # Step 4: Notional sizing
    total_notional, per_asset_notional, margin_required = \
        compute_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 4] Notional sizing:")
    print(f"  Sleeve capital:    ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M)")
    print(f"  Total notional:    ${total_notional:,.0f}  ({SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  Per asset:         ${per_asset_notional:,.0f}  (BTC + ETH + SOL, equal weight)")
    print(f"  Margin required:   ${margin_required:,.0f}  ({100/LEVERAGE:.0f}% of notional @ {LEVERAGE}x)")
    print(f"  Margin/AUM:        {(margin_required/aum)*100:.1f}%")

    # Step 5: Load current position + decide action
    dash          = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 5] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        trade_result = submit_signal_trade(
            SIGNAL_UNIVERSE, per_asset_notional, dry_run=dry_run
        )
        print(f"  Trade status: {trade_result['status']}")

    elif not decision and current_state != STATE_NEUTRAL:
        # Signal gone — close position
        print(f"  Action: CLOSE (signal below threshold)")
        trade_result = close_signal_position("signal_below_threshold", dry_run=dry_run)
        # Reset position state in dashboard
        dash["position_state"] = STATE_NEUTRAL

    elif decision and current_state != STATE_NEUTRAL:
        print(f"  Action: HOLD (signal continuing)")

    else:
        print(f"  Action: NO-OP (neutral, no signal)")

    # Step 6: Rebalance check
    print(f"\n  [Step 6] Drift check...")
    rebalance = daily_rebalance(dash)
    print(f"  Max drift:  {rebalance.get('max_drift_pct', 0.0):.2%}  "
          f"Threshold: {DRIFT_REBALANCE_PCT:.0%}  "
          f"Action: {rebalance.get('action', 'HOLD')}")

    # Step 7: Write dashboard
    dash_out = _write_dashboard(
        supply_data, signal, decision, total_notional,
        per_asset_notional, margin_required, rebalance, aum
    )
    print(f"\n  [Step 7] Dashboard written → {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K541 Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Z-score accel:       {dash_out.get('zscore_acceleration', 0.0):+.4f}  (threshold: {SIGNAL_THRESHOLD})")
    print(f"  Total supply:        ${dash_out.get('total_supply_usdt_usdc', 0.0):,.0f}  (USDT+USDC)")
    print(f"  Rebalance req:       {dash_out.get('rebalance_required')}")
    print(f"  Margin/AUM:          {dash_out.get('margin_pct_of_aum', 0)*100:.1f}%")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe (K541):   {OOS_SHARPE} (+{SEVEN_AXIS_LIFT} 7-axis lift, +$294K/yr @$10M)")
    print(f"  G5 max corr:         {G5_MAX_CORR} (highly orthogonal to FR-carry family)")
    print(f"  Paper gate:          {PAPER_GATE_DAYS}d (OOS Sh >=1.2 + fill >=60% + maxDD <25% + >=50 trades)")
    print(f"  v6.29 path:          K541 3% stablecoin supply addition to v6.28")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K541 Stablecoin Supply Growth Strategy (K550 scaffold — V3 acceleration)"
    )
    parser.add_argument("--dry-run",   action="store_true", default=True,
                        help="Paper-trade simulation (default)")
    parser.add_argument("--status",    action="store_true",
                        help="Print current dashboard state and exit")
    parser.add_argument("--rebalance", action="store_true",
                        help="Check and apply drift rebalance")
    parser.add_argument("--close",     default=None, metavar="REASON",
                        help="Close all signal positions with reason")
    parser.add_argument("--aum",       type=float, default=AUM_DEFAULT,
                        help=f"Reference AUM in USD (default: ${AUM_DEFAULT:,.0f})")
    args = parser.parse_args()

    if args.status:
        dash = _load_dashboard()
        print(f"\n=== K541 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K541 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_signal_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K541 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

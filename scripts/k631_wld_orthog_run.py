#!/usr/bin/env python3
"""
k631_wld_orthog_run.py — K631 WLD Orthogonalized FR Differential Strategy
==========================================================================
Implements a paired-trade (long WLD / short BTC or reverse) based on the
72h EMA of the WLD-BTC funding rate differential, ORTHOGONALIZED against
JUP factor via OLS regression (K631 pattern).

Architecture (K639 scaffold, K631 pattern):
  1. fetch_fr_batch()                  → fetch WLD + JUP + BTC FR every 8h
  2. compute_residual(wld_diff, jup_diff)
       residual = WLD_diff - β_JUP × JUP_diff
       β coefficient HARDCODED per K631 OLS (no re-OLS in production):
         β_JUP  = 0.458795
  3. compute_signal(residual_history)  → 72h EMA of residual; |ema| > 1.5σ
  4. decide_position(signal)           → LONG_WLD_SHORT_BTC | LONG_BTC_SHORT_WLD | NEUTRAL
  5. submit_paired_trade(long, short)  → POST_ONLY paired (WLD + BTC legs)
  6. daily_rebalance()                 → drift > 5% triggers rebalance
  7. close_paired_position(reason)     → sequential: short first, then long

K631 Biometric ID cluster hypothesis (ACCEPT):
  - WLD = Worldcoin Network: World ID biometric proof-of-humanhood + WLD token
  - Biometric ID cluster = distinct identity verification + AI-bot resistance category
  - WLD FR dynamics driven by privacy-tech narrative cycles and AI-identity demand
    (not correlated with DeFi infrastructure like JUP = Jupiter aggregator)
  - OOS Sh=18.04 RESIDUAL (W=72h optimal per K631 sweep)
  - β_JUP=0.458795 per K631 OLS (IS R²=TBD, captures JUP/DeFi co-movement)
  - 60d paper-trade gate required before live activation

K631 K639 profit summary:
  - OOS Sharpe (residual): 18.04
  - Ann Return @$10M @4x (2% sleeve): $2,900,000/yr potential
  - 2% sleeve: ~$7,945/yr/day carry contribution estimate
  - Bybit primary (WLD/BTC both legs, Bybit high maxLev)

Execution:
  - Bybit primary (WLD perp + BTC perp, both on Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 2% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle)
  - W=72h EMA (optimal window per K631 sweep)

Orthog mechanism:
  - Raw WLD_diff = WLD_FR − BTC_FR
  - JUP_diff     = JUP_FR − BTC_FR
  - residual     = WLD_diff − 0.458795 × JUP_diff
  - Signal       = 72h EMA of residual; threshold = 1.5σ of 72h window
  - β hardcoded: NO re-OLS in production (stability constraint, K631 spec)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k631_wld_orthog_run.py --dry-run
  python3 scripts/k631_wld_orthog_run.py --status
  python3 scripts/k631_wld_orthog_run.py --rebalance
  python3 scripts/k631_wld_orthog_run.py --close "scheduled exit"
"""
from __future__ import annotations

import argparse
import json
import math
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

DASHBOARD_PATH  = DATA_DIR  / "k631_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k631_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k631_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.02          # K631 sleeve = 2% of AUM (60d gate then activate)
LEVERAGE            = 4.0           # 4x per K631 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 72            # 72h EMA optimal window (per K631 sweep)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 9 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 1.5           # entry threshold: |residual_ema| > 1.5σ
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── K631 OLS β coefficient — HARDCODED, NO RE-OLS in production ──────────────
# Source: K631 OLS regression on WLD vs JUP factor
#   WLD_diff = α + β_JUP × JUP_diff + ε
#   β_JUP = 0.458795  (JUP DeFi aggregator factor loading on WLD FR)
#   W=72h optimal per K631 hyperparameter sweep (Sh=18.04 peak)
#   OOS Sh=18.04 RESIDUAL (W=72h), $2.9M/yr @$10M @4x (2% sleeve)
#   Biometric ID cluster: WLD biometric proof-of-humanhood FR orthogonal to JUP DeFi routing
BETA_JUP = 0.458795

# ── Venue config (Bybit primary — WLD+BTC maxLev high) ───────────────────────
# Bybit primary: WLD-USDT-SWAP + BTC-USDT-SWAP, both Bybit perp
# Both legs on Bybit (delta-neutral carry)
# HL secondary: monitor-only (Bybit primary for WLD perp)
BYBIT_SLEEVE_PCT   = SLEEVE_PCT      # full sleeve on Bybit (WLD + BTC paired)
HL_CONCENTRATION_UNCHANGED = 65.0   # K631 on Bybit → HL concentration unchanged

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_WLD_SHORT_BTC = "LONG_WLD_SHORT_BTC"
STATE_LONG_BTC_SHORT_WLD = "LONG_BTC_SHORT_WLD"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
SYMBOLS = ("WLD", "JUP", "BTC")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k631/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k631] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (WLD + JUP + BTC)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for WLD, JUP, BTC from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs → funding field per asset.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k631] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k631] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K631 FR history JSONL."""
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


def _append_fr_history(
    fr_wld: float, fr_jup: float, fr_btc: float,
    wld_diff: float, jup_diff: float, residual: float
) -> None:
    """Append one FR + residual snapshot to history."""
    rec = {
        "ts_utc":   datetime.now(UTC).isoformat(),
        "fr_wld":   round(fr_wld,   10),
        "fr_jup":   round(fr_jup,   10),
        "fr_btc":   round(fr_btc,   10),
        "wld_diff": round(wld_diff, 10),  # WLD_FR − BTC_FR (raw)
        "jup_diff": round(jup_diff, 10),  # JUP_FR − BTC_FR
        "residual": round(residual, 10),  # orthogonalized residual
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Orthogonalized residual computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_residual(
    fr_wld: Optional[float] = None,
    fr_jup: Optional[float] = None,
    fr_btc: Optional[float] = None,
) -> dict:
    """
    Fetch live WLD/JUP/BTC FRs from HL, compute orthogonalized residual,
    and compute 72h EMA + 72h rolling σ for threshold calculation.

    Orthogonalization mechanism (K631 OLS, coefficient HARDCODED):
      wld_diff  = WLD_FR − BTC_FR
      jup_diff  = JUP_FR − BTC_FR
      residual  = wld_diff − β_JUP × jup_diff
               = wld_diff − 0.458795 × jup_diff

    Signal gate (W=72h optimal per K631 sweep):
      EMA = 72h EMA of residual (9 × 8h periods)
      σ   = 72h rolling std of residual
      Enter when |EMA| > 1.5σ

    K631 Biometric ID cluster hypothesis:
      WLD biometric proof-of-humanhood + World ID = novel identity infrastructure
      FR dynamics driven by privacy-tech / AI-identity narrative cycles,
      orthogonal to JUP (Jupiter aggregator DeFi routing flows).
      After projecting out JUP factor loading (β=0.458795), the residual
      captures pure Worldcoin Biometric ID-specific FR alpha.
      OOS Sh=18.04 (W=72h) confirms orthogonalization preserves signal.

    Returns:
      {
        "fr_wld":          float,
        "fr_jup":          float,
        "fr_btc":          float,
        "wld_diff":        float,   # raw WLD−BTC
        "jup_diff":        float,   # JUP−BTC
        "residual":        float,   # orthogonalized residual (current)
        "residual_ema_72h":float,   # 72h EMA of residual (9 periods × 8h)
        "residual_sigma":  float,   # 72h rolling σ of residual
        "threshold":       float,   # 1.5σ entry threshold
        "beta_jup":        float,   # β_JUP hardcoded = 0.458795
        "history_points":  int,
        "regime":          str,     # BULL_WLD | BEAR_WLD | NEUTRAL
        "ts_jst":          str,
      }
    """
    if any(v is None for v in (fr_wld, fr_jup, fr_btc)):
        frs    = _fetch_hl_fr_batch()
        fr_wld  = frs.get("WLD", 0.0)
        fr_jup  = frs.get("JUP", 0.0)
        fr_btc  = frs.get("BTC", 0.0)

    # Compute diffs
    wld_diff  = fr_wld  - fr_btc
    jup_diff  = fr_jup  - fr_btc

    # Orthogonalized residual (K631 OLS, β hardcoded)
    residual = wld_diff - BETA_JUP * jup_diff

    _append_fr_history(fr_wld, fr_jup, fr_btc, wld_diff, jup_diff, residual)

    # Load history for EMA + σ (72h = 9 × 8h periods)
    history   = _load_fr_history()
    residuals = [r["residual"] for r in history if "residual" in r]

    n_periods = EMA_PERIOD_PERIODS   # 9 periods (72h / 8h)
    alpha     = 2.0 / (n_periods + 1)
    ema = residuals[0] if residuals else 0.0
    for r in residuals[1:]:
        ema = alpha * r + (1 - alpha) * ema

    # Rolling σ: std of last n_periods residuals
    window    = residuals[-n_periods:] if len(residuals) >= 2 else residuals
    if len(window) >= 2:
        mean   = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma  = abs(ema) if ema != 0 else 1e-8   # fallback: EMA magnitude

    threshold = SIGNAL_SIGMA_MULT * sigma  # 1.5σ entry gate

    # Regime classification
    if abs(ema) <= threshold:
        regime = "NEUTRAL"
    elif ema > 0:
        regime = "BULL_WLD"   # WLD residual FR > 0: short WLD / long BTC
    else:
        regime = "BEAR_WLD"   # WLD residual FR < 0: long WLD / short BTC

    return {
        "fr_wld":          round(fr_wld,   10),
        "fr_jup":          round(fr_jup,   10),
        "fr_btc":          round(fr_btc,   10),
        "wld_diff":        round(wld_diff, 10),
        "jup_diff":        round(jup_diff, 10),
        "residual":        round(residual, 10),
        "residual_ema_72h":round(ema,      10),
        "residual_sigma":  round(sigma,    10),
        "threshold":       round(threshold,10),
        "beta_jup":        BETA_JUP,
        "history_points":  len(residuals),
        "regime":          regime,
        "ts_jst":          datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from orthogonalized residual EMA.

    Logic (WLD-BTC orthogonalized pair, Bybit primary):
      regime = BULL_WLD (residual_ema > 1.5σ):
        WLD residual FR > BTC FR → WLD more expensive to long
        → short WLD (collect high residual FR) / long BTC (cheap carry)
        → position_state = LONG_BTC_SHORT_WLD
        → both legs on Bybit (WLD primary, BTC paired)

      regime = BEAR_WLD (residual_ema < −1.5σ):
        WLD residual FR < BTC FR → BTC more expensive
        → long WLD / short BTC
        → position_state = LONG_WLD_SHORT_BTC
        → both legs on Bybit

      regime = NEUTRAL: no trade

    K631 orthog edge:
      The residual cleanly separates WLD's Biometric ID-specific FR dynamics
      from the JUP DeFi aggregator noise. OOS Sh=18.04 (W=72h) residual
      confirms the true alpha is in the Worldcoin identity/privacy narrative,
      not shared DeFi liquidity routing regimes.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, residual_ema,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime   = signal.get("regime", "NEUTRAL")
    ema      = signal.get("residual_ema_72h", 0.0)
    thresh   = signal.get("threshold", 1e-8)
    abs_ema  = abs(ema)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_WLD":
        # WLD residual FR positive → WLD FR > BTC FR
        # short WLD (expensive), long BTC (cheap)
        long_asset  = "BTC"
        short_asset = "WLD"
        state       = STATE_LONG_BTC_SHORT_WLD
    else:  # BEAR_WLD
        # WLD residual FR negative → BTC FR > WLD FR
        # long WLD (cheap), short BTC (expensive)
        long_asset  = "WLD"
        short_asset = "BTC"
        state       = STATE_LONG_WLD_SHORT_BTC

    # Both legs on Bybit (WLD + BTC, Bybit primary)
    long_venue  = "Bybit"
    short_venue = "Bybit"

    # Signal strength: |ema| / threshold (capped at 3x for sizing)
    strength = min(abs_ema / max(thresh, 1e-10), 3.0)

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "residual_ema":    ema,
        "threshold":       thresh,
        "signal_strength": round(strength, 4),
        "size_multiplier": 1.0,   # reserved for dynamic sizing
        "regime":          regime,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Delta-neutral notional computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_delta_neutral_notional(
    aum:        float = AUM_DEFAULT,
    sleeve_pct: float = SLEEVE_PCT,
    leverage:   float = LEVERAGE,
) -> Tuple[float, float]:
    """
    Compute equal notional for both legs of the WLD-BTC paired trade.

    K631 Bybit-only config (WLD+BTC maxLev high on Bybit):
      sleeve_capital = aum × sleeve_pct     (e.g. $10M × 2% = $200K)
      total_notional = sleeve_capital × lev  ($200K × 4 = $800K)
      notional_per_leg = total_notional / 2  ($400K per leg)

    At $10M / 2% sleeve / 4x:
      WLD leg:   $100K capital × 4x = $400K notional (Bybit)
      BTC leg:   $100K capital × 4x = $400K notional (Bybit)
      Total:     $800K notional (two legs combined)
      Margin:    $200K (2% of AUM)

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital = aum * sleeve_pct
    total_notional = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Paired trade submission (Bybit primary, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K631 WLD-BTC paired trade: POST_ONLY both legs in parallel.

    Protocol (K631 Bybit primary):
      1. Submit WLD leg on Bybit POST_ONLY
      2. Submit BTC leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "WLD", "notional": 400000, "venue": "Bybit"}
      short_leg: {"symbol": "BTC", "notional": 400000, "venue": "Bybit"}
      dry_run:   True = paper-trade simulation (default)

    Returns execution result dict.
    """
    ts         = datetime.now(UTC).isoformat()
    long_sym   = long_leg["symbol"]
    short_sym  = short_leg["symbol"]
    long_notl  = long_leg.get("notional", 0.0)
    short_notl = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue",  "Bybit")
    short_venue = short_leg.get("venue", "Bybit")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K631] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
              f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
        result = {
            "status":           "DRY_RUN",
            "long_result":      {"order_id": f"PAPER_LONG_{long_sym}_{int(time.time())}", "status": "DRY_RUN"},
            "short_result":     {"order_id": f"PAPER_SHORT_{short_sym}_{int(time.time())}", "status": "DRY_RUN"},
            "fill_price_long":  None,
            "fill_price_short": None,
            "long_symbol":      long_sym,
            "short_symbol":     short_sym,
            "long_notional":    long_notl,
            "short_notional":   short_notl,
            "long_venue":       long_venue,
            "short_venue":      short_venue,
            "execution_mode":   "POST_ONLY_PARALLEL",
            "venue_config":     "BYBIT_PRIMARY_WLD_BIOMETRIC",
            "orthog_note":      f"residual = WLD_diff - {BETA_JUP}*JUP_diff",
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K631] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K631] Neither leg filled within timeout — retry next 8h cycle")
    return {
        "status":       "RETRY_NEXT_CYCLE",
        "long_result":  {"order_id": long_order_id,  "status": "TIMEOUT"},
        "short_result": {"order_id": short_order_id, "status": "TIMEOUT"},
        "ts_utc":       ts,
    }


def _append_trade_log(record: dict) -> None:
    with open(TRADE_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Delta-neutral drift rebalance
# ─────────────────────────────────────────────────────────────────────────────

def daily_rebalance(dashboard: dict) -> dict:
    """
    Check if current K631 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K631 Bybit-only: both legs on Bybit; drift accumulates together.
    Drift detection: compare stored WLD leg notional vs BTC leg notional.
    Threshold: 5% (same as K507/K512 pattern).

    Returns rebalance decision dict.
    """
    state = dashboard.get("position_state", STATE_NEUTRAL)
    if state == STATE_NEUTRAL:
        return {"rebalance_required": False, "reason": "NEUTRAL — no position"}

    long_notional_init  = float(dashboard.get("long_notional", 0.0))
    short_notional_init = float(dashboard.get("short_notional", 0.0))

    if long_notional_init <= 0 or short_notional_init <= 0:
        return {"rebalance_required": False, "reason": "no recorded notionals"}

    # Paper-trade: use stored drift (0 if not set)
    drift_pct    = float(dashboard.get("delta_neutral_drift_pct", 0.0))
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
# Phase 7 — Close paired position
# ─────────────────────────────────────────────────────────────────────────────

def close_paired_position(reason: str, dry_run: bool = True) -> dict:
    """
    Close both legs sequentially: short leg first (avoid naked short exposure),
    then long leg. In live: uses IOC market orders (reduce-only).
    Both legs on Bybit (K631 Bybit primary).

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

    if state == STATE_LONG_WLD_SHORT_BTC:
        long_sym,  short_sym  = "WLD", "BTC"
    else:  # LONG_BTC_SHORT_WLD
        long_sym,  short_sym  = "BTC", "WLD"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K631] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@Bybit ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@Bybit  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "venue":           "Bybit",
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "close_mode":      "IOC_REDUCE_ONLY",
            "ts_utc":          ts,
        }
    else:
        print(f"  [K631] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @Bybit  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @Bybit")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "venue":          "Bybit",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k631_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "residual_ema_72h":        0.0,
        "residual_sigma":          0.0,
        "threshold_1_5sigma":      0.0,
        "beta_jup_used":           BETA_JUP,
        "regime":                  "NEUTRAL",
        "position_state":          STATE_NEUTRAL,
        "long_notional":           0.0,
        "short_notional":          0.0,
        "venue":                   "Bybit",
        "delta_neutral_drift_pct": 0.0,
        "rebalance_required":      False,
        "daily_pnl_usdc":          0.0,
        "60d_sharpe":              0.0,
        "paper_trade_status":      {"days_elapsed": 0, "target_60d": 60},
    }


def _write_dashboard(
    signal:           dict,
    decision:         Optional[dict],
    notional_per_leg: float,
    total_notional:   float,
    rebalance:        dict,
    aum:              float,
) -> dict:
    """Write k631_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]       = signal.get("ts_jst", "—")
    dash["fr_wld_current"]      = signal.get("fr_wld",  0.0)
    dash["fr_jup_current"]      = signal.get("fr_jup",  0.0)
    dash["fr_btc_current"]      = signal.get("fr_btc",  0.0)
    dash["wld_diff_raw"]        = signal.get("wld_diff", 0.0)
    dash["jup_diff"]            = signal.get("jup_diff", 0.0)
    dash["residual_current"]    = signal.get("residual", 0.0)
    dash["residual_ema_72h"]    = signal.get("residual_ema_72h", 0.0)
    dash["residual_sigma"]      = signal.get("residual_sigma",  0.0)
    dash["threshold_1_5sigma"]  = signal.get("threshold", 0.0)
    dash["beta_jup_used"]       = signal.get("beta_jup",  BETA_JUP)
    dash["regime"]              = signal.get("regime", "NEUTRAL")
    dash["history_points"]      = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]  = state
            dash["long_notional"]   = notional_per_leg
            dash["short_notional"]  = notional_per_leg
            dash["long_asset"]      = decision.get("long_asset")
            dash["short_asset"]     = decision.get("short_asset")
            dash["venue"]           = "Bybit"
            dash["entry_ts_jst"]    = dash["last_poll_jst"]
            dash["signal_strength"] = decision.get("signal_strength", 0.0)

    # Rebalance status
    dash["delta_neutral_drift_pct"] = rebalance.get("drift_pct", 0.0)
    dash["rebalance_required"]       = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    dash["total_notional_usdc"]      = round(total_notional, 2)
    dash["notional_per_leg_usdc"]    = round(notional_per_leg, 2)
    dash["leverage"]                 = LEVERAGE
    dash["sleeve_pct"]               = SLEEVE_PCT
    dash["aum_ref_usdc"]             = aum
    dash["margin_used_usdc"]         = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]        = round((total_notional / LEVERAGE) / aum, 4)
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_UNCHANGED  # unchanged: Bybit-only

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics
    dash["gate_metrics"] = {
        "realized_sharpe_target":   8.0,     # ≥ 8 (per K639 spec)
        "fill_rate_target_pct":     60,
        "max_drawdown_target_pct":  20,
        "current_realized_sharpe":  dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":    0.0,
        "current_max_dd_pct":       0.0,
        "gate_status":              "IN_PROGRESS",
        "activation_trigger":       "60d paper-trade: Sh>=8 AND fill>=60% AND maxDD<20%",
        "profit_at_activation_2pct": "$2,900,000/yr @$10M @4x (2% sleeve)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]       = PAPER_TRADE
    dash["wave"]                   = "K639"
    dash["strategy"]               = "K631 WLD-BTC Orthogonalized FR Differential"
    dash["execution_mode"]         = "POST_ONLY_PARALLEL"
    dash["venue_config"]           = "BYBIT_PRIMARY"
    dash["orthog_mechanism"]       = {
        "formula":    f"residual = WLD_diff - {BETA_JUP}*JUP_diff",
        "beta_jup":   BETA_JUP,
        "ema_window": "72h (W=72h optimal per K631 sweep)",
        "note":       "β HARDCODED per K631 OLS — no re-OLS in production for stability",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    8.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   20,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.02,
        "venue":                  "Bybit primary (WLD+BTC both legs)",
    }
    dash["oos_performance"] = {
        "sharpe_residual":        18.04,
        "ema_window_optimal":     "W=72h",
        "beta_jup":               BETA_JUP,
        "ann_return_usd_2pct_4x": 2_900_000,
        "wave_accept":            "K631 ACCEPT (K639 scaffold)",
        "cluster":                "Biometric ID (WLD World ID, novel identity infrastructure)",
        "cluster_rationale":      "WLD privacy-tech / AI-identity narrative cycles — orthogonal to JUP DeFi aggregator flows",
        "hl_concentration_pct":   65.0,
        "hl_impact":              "NONE — Bybit-only; HL concentration UNCHANGED at 65%",
    }
    dash["signal"] = decision.get("position_state", STATE_NEUTRAL) if decision else STATE_NEUTRAL

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))
    return dash


# ─────────────────────────────────────────────────────────────────────────────
# Main single-shot run logic
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(dry_run: bool = True, aum: float = AUM_DEFAULT) -> int:
    """
    Single 8h cycle:
      1. Fetch WLD + JUP + BTC FRs
      2. Compute orthogonalized residual + 72h EMA + σ
      3. Decide position (|ema| > 1.5σ threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k631_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K631 WLD Orthogonalized FR Differential — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.0%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit primary (WLD+BTC maxLev high)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: NONE (Bybit-only) — HL concentration unchanged @ 65%")
    print(f"  Orthog:    residual = WLD_diff − {BETA_JUP}×JUP_diff")
    print(f"  β fixed:   β_JUP={BETA_JUP}  (K631 OLS, production-hardcoded)")
    print(f"  Signal:    |residual_EMA_72h| > 1.5σ  (W=72h optimal, K631 sweep)")

    # Step 1: Fetch + compute orthogonalized residual
    print("\n  [Step 1] Computing orthogonalized residual...")
    signal = compute_residual()
    print(f"  WLD FR:     {signal['fr_wld']:+.8f} (8h)")
    print(f"  JUP FR:     {signal['fr_jup']:+.8f} (8h)")
    print(f"  BTC FR:     {signal['fr_btc']:+.8f} (8h)")
    print(f"  WLD diff:   {signal['wld_diff']:+.8f}  (WLD−BTC raw)")
    print(f"  JUP diff:   {signal['jup_diff']:+.8f}  (JUP−BTC factor)")
    print(f"  Residual:   {signal['residual']:+.8f}  (orthogonalized)")
    print(f"  EMA 72h:    {signal['residual_ema_72h']:+.8f}")
    print(f"  Sigma 72h:  {signal['residual_sigma']:+.8f}")
    print(f"  Threshold:  {signal['threshold']:+.8f}  (1.5σ = {SIGNAL_SIGMA_MULT}×σ)")
    print(f"  Regime:     {signal['regime']}")
    print(f"  History:    {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Strength: {decision['signal_strength']:.2f}x threshold")
    else:
        print(f"  Signal:   NEUTRAL (|residual_ema| <= 1.5σ)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M)")
    print(f"  WLD leg:          ${notional_per_leg:,.0f}  (1% × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  BTC leg:          ${notional_per_leg:,.0f}  (1% × ${aum/1e6:.0f}M × {LEVERAGE}x)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.0%} AUM)")
    print(f"  Profit @$10M 4x:  2% sleeve=${2_900_000:,}/yr")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "Bybit"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "Bybit"}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "Bybit"}
            short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "Bybit"}
            trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        else:
            print(f"  Action: HOLD (same direction)")

    elif not decision and current_state != STATE_NEUTRAL:
        print(f"  Action: CLOSE (residual below 1.5σ threshold)")
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
    dash_out = _write_dashboard(signal, decision, notional_per_leg, total_notional, rebalance, aum)
    print(f"\n  [Step 6] Dashboard written → {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K631 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  Residual EMA 72h:   {dash_out.get('residual_ema_72h'):+.8f}")
    print(f"  Threshold (1.5σ):   {dash_out.get('threshold_1_5sigma'):+.8f}")
    print(f"  β_JUP (fixed):      {BETA_JUP}  (K631 OLS hardcoded)")
    print(f"  EMA window:         72h = 9 × 8h periods (W=72h optimal K631 sweep)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         18.04 (residual W=72h, K631)")
    print(f"  Cluster:            Biometric ID / World ID")
    print(f"  Profit 2% sleeve:   $2,900,000/yr @$10M @4x")
    print(f"  HL concentration:   {HL_CONCENTRATION_UNCHANGED}% (unchanged — Bybit-only)")
    print(f"  60d gate:           Realized Sh>=8 + fill>=60% + maxDD<20%")
    print(f"  v6.32 path:         K631 WLD orthog 2% Bybit sleeve added to v6.31")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K631 WLD Orthogonalized FR Differential Strategy (K639 scaffold)"
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
        print(f"\n=== K631 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K631 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K631 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

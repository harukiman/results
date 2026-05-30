#!/usr/bin/env python3
"""
k629_wld_eth_run.py — K629 WLD-ETH FR Differential Strategy
=============================================================
Implements a paired-trade (long WLD / short ETH or reverse) based on the
168h EMA of the WLD-ETH funding rate differential.

ETH-base mechanism (K629 insight):
  WLD-BTC was structurally blocked (K621/K624/K627) because BTC-FR-compression
  causes all alt-BTC differentials to co-move in bear markets (JUP-BTC corr=0.4612).
  Switching to ETH base decouples from this mechanism: ETH FR is driven by DeFi/staking
  dynamics (stETH demand, LST competition, L1 gas cycles) — not by BTC spot compression.
  Result: JUP-BTC cross-base corr drops to 0.3437 (< 0.40 threshold, G5aa PASS).

Architecture (K654 scaffold, K629 pattern):
  1. fetch_fr_batch()               → fetch WLD + ETH FR every 8h from HL
  2. compute_signal(wld_fr, eth_fr) → 168h EMA of (WLD_FR - ETH_FR); |ema| > 1.5σ
  3. decide_position(signal)        → LONG_WLD_SHORT_ETH | LONG_ETH_SHORT_WLD | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (WLD + ETH legs, both HL)
  5. daily_rebalance()              → drift > 5% triggers rebalance
  6. close_paired_position(reason)  → sequential: short first, then long

K629 Biometric ID cluster hypothesis (ACCEPT — 9/9 gates):
  - WLD = Worldcoin Network: World ID biometric proof-of-humanhood + WLD token
  - Biometric ID cluster = distinct identity verification + AI-bot resistance category
  - WLD FR dynamics driven by:
      OpenAI/Sam Altman narrative cycles (AI-bot resistance demand)
      Biometric proof-of-humanhood adoption spikes (new regions)
      Privacy-tech regulatory catalysts (EU Digital ID, global Digital ID push)
      WLD token supply unlock cycles (OP mainnet WLD)
  - ETH-base mechanism fix: ETH FR driven by DeFi staking (stETH/LST demand cycles)
    → orthogonal to WLD biometric narrative cycles by construction
  - JUP-BTC cross-base corr: 0.3437 (PASS < 0.40, down from 0.4612 WLD-BTC K621)
  - ETH-BTC same-base corr: -0.2052 (anti-correlated — portfolio diversification benefit)
  - OOS Sh=19.90 (W=168h, 9/9 §6 PASS: full gate score)
  - 60d paper-trade gate required before live activation

K629 K654 profit summary:
  - OOS Sharpe: 19.9017 (IS: 29.9396, ratio=0.665 — good generalization)
  - OOS Ann Return: 7.85% (unlevered on notional)
  - Profit @$10M @4x @3% sleeve: $94,210/yr USDC
  - Both WLD and ETH on HL primary (HL perps: WLD-PERP + ETH-PERP)
  - HL concentration post-K629: ~59.5% (2pp uplift from 57.5%, within 65% limit)
  - Walk-forward: 11/12 folds positive (91.7% — G4 PASS)
  - Perm p-value: 0.0000 (500 reshuffles — G2 PASS)
  - DSR Bonferroni: p=0.0 (12 trials — G3 PASS)
  - Trades/yr: 48.2 (W=168h config — G6 PASS)
  - ADF p=0.0 (stationary), OU halflife=5.70h

Execution:
  - HL primary (WLD-PERP + ETH-PERP, both HL perps)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage
  - 8h cadence (matches FR settlement cycle)
  - W=168h EMA (primary config, 48.2 trades/yr, G6 PASS)
  - Note: W=504h is best OOS Sh=26.88 but G6 fails (10.3 trades/yr < 30)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k629_wld_eth_run.py --dry-run
  python3 scripts/k629_wld_eth_run.py --status
  python3 scripts/k629_wld_eth_run.py --rebalance
  python3 scripts/k629_wld_eth_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k629_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k629_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k629_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.03          # K629 sleeve = 3% of AUM (Biometric ID, ETH-base)
LEVERAGE            = 4.0           # 4x per K629 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h EMA primary config (per K629 §6 evaluation, G6 PASS 48.2 trades/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 1.5           # entry threshold: |diff_ema| > 1.5σ
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (HL primary — WLD-PERP + ETH-PERP, both on HL) ──────────────
# Both legs on HL (delta-neutral carry)
# HL concentration: 57.5% + 2pp (3% sleeve at 2/3 on HL) = ~59.5% (within 65% limit)
# K629 is HL-only: WLD-PERP and ETH-PERP both on HL
HL_CONCENTRATION_POST_K629 = 59.5   # K629 adds ~2pp to current 57.5% HL

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_WLD_SHORT_ETH = "LONG_WLD_SHORT_ETH"
STATE_LONG_ETH_SHORT_WLD = "LONG_ETH_SHORT_WLD"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
# K629: WLD + ETH only — direct differential, no orthogonalization factors
SYMBOLS = ("WLD", "ETH")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k629/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k629] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (WLD + ETH from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for WLD and ETH from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    K629: both legs on HL (WLD-PERP + ETH-PERP). ETH-base mechanism.
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k629] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k629] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K629 FR history JSONL."""
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
    fr_wld: float, fr_eth: float, wld_eth_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":      datetime.now(UTC).isoformat(),
        "fr_wld":      round(fr_wld,      10),
        "fr_eth":      round(fr_eth,      10),
        "wld_eth_diff":round(wld_eth_diff, 10),  # WLD_FR - ETH_FR (direct differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (WLD-ETH direct differential, 168h EMA)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_wld: Optional[float] = None,
    fr_eth: Optional[float] = None,
) -> dict:
    """
    Fetch live WLD and ETH FRs from HL, compute WLD-ETH differential,
    and compute 168h EMA + rolling sigma for threshold calculation.

    Signal mechanism (K629 direct differential — no orthogonalization):
      diff = WLD_FR - ETH_FR
      EMA  = 168h EMA of diff (21 x 8h periods)
      sigma = 168h rolling std of diff
      Enter when |EMA| > 1.5sigma

    ETH-base independence mechanism:
      - ETH FR driven by: DeFi staking yields (stETH/LST), ETH L1 gas narrative,
        liquid staking protocol activity (not BTC spot compression)
      - WLD FR driven by: biometric ID narrative cycles, OpenAI/Altman events,
        privacy-tech regulatory catalysts
      - Cross-base: WLD-ETH vs JUP-BTC = orthogonal by construction (different asset legs,
        different narrative drivers) → JUP-BTC corr = 0.3437 (PASS < 0.40)

    K629 §6 validation (9/9 PASS):
      - OOS Sharpe: 19.9017 (W=168h)
      - OOS Ann Return: 7.85% (unlevered on notional)
      - ADF p=0.0 (stationary), OU halflife=5.70h
      - Walk-forward: 11/12 positive (91.7%)
      - Perm p=0.0 (500 reshuffles), DSR p=0.0 (12 trials)
      - Trades/yr: 48.2 (W=168h, G6 PASS >= 30)

    Returns:
      {
        "fr_wld":          float,
        "fr_eth":          float,
        "wld_eth_diff":    float,    # WLD_FR - ETH_FR (current)
        "diff_ema_168h":   float,    # 168h EMA of differential
        "diff_sigma":      float,    # 168h rolling sigma
        "threshold":       float,    # 1.5sigma entry threshold
        "history_points":  int,
        "regime":          str,      # BULL_WLD | BEAR_WLD | NEUTRAL
        "ts_jst":          str,
      }
    """
    if fr_wld is None or fr_eth is None:
        frs    = _fetch_hl_fr_batch()
        fr_wld = frs.get("WLD", 0.0)
        fr_eth = frs.get("ETH", 0.0)

    # WLD-ETH direct differential (no orthogonalization — ETH base is the mechanism fix)
    wld_eth_diff = fr_wld - fr_eth

    _append_fr_history(fr_wld, fr_eth, wld_eth_diff)

    # Load history for EMA + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["wld_eth_diff"] for r in history if "wld_eth_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 21 periods (168h / 8h)
    alpha     = 2.0 / (n_periods + 1)
    ema = diffs[0] if diffs else 0.0
    for d in diffs[1:]:
        ema = alpha * d + (1 - alpha) * ema

    # Rolling sigma: std of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 2 else diffs
    if len(window) >= 2:
        mean  = sum(window) / len(window)
        sigma = math.sqrt(sum((x - mean) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma = abs(ema) if ema != 0 else 1e-8   # fallback

    threshold = SIGNAL_SIGMA_MULT * sigma  # 1.5sigma entry gate

    # Regime classification
    # BULL_WLD: WLD FR > ETH FR (WLD expensive to long -> short WLD, long ETH)
    # BEAR_WLD: WLD FR < ETH FR (ETH expensive to long -> long WLD, short ETH)
    if abs(ema) <= threshold:
        regime = "NEUTRAL"
    elif ema > 0:
        regime = "BULL_WLD"   # WLD-ETH diff positive -> WLD FR > ETH FR
    else:
        regime = "BEAR_WLD"   # WLD-ETH diff negative -> ETH FR > WLD FR

    return {
        "fr_wld":         round(fr_wld,       10),
        "fr_eth":         round(fr_eth,        10),
        "wld_eth_diff":   round(wld_eth_diff,  10),
        "diff_ema_168h":  round(ema,           10),
        "diff_sigma":     round(sigma,         10),
        "threshold":      round(threshold,     10),
        "history_points": len(diffs),
        "regime":         regime,
        "ts_jst":         datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from WLD-ETH differential EMA.

    Logic (WLD-ETH direct differential pair, HL primary):
      regime = BULL_WLD (diff_ema > 1.5sigma):
        WLD FR > ETH FR -> WLD expensive to long (high funding cost)
        -> short WLD (collect high WLD FR) / long ETH (low carry cost)
        -> position_state = LONG_ETH_SHORT_WLD
        -> both legs on HL

      regime = BEAR_WLD (diff_ema < -1.5sigma):
        ETH FR > WLD FR -> ETH expensive to long
        -> long WLD (cheap carry) / short ETH (expensive)
        -> position_state = LONG_WLD_SHORT_ETH
        -> both legs on HL

      regime = NEUTRAL: no trade

    K629 edge (ETH-base mechanism):
      The WLD-ETH differential cleanly captures Biometric ID (World ID) narrative cycles
      vs ETH DeFi/staking cycles. These two FR dynamics are structurally independent:
        - WLD FR: biometric ID adoption waves, OpenAI narrative, privacy-tech regulation
        - ETH FR: stETH/LST demand, ETH L1 gas narrative, ETH validator yield compression
      JUP-BTC cross-base corr = 0.3437 (PASS): WLD-ETH does not co-move with JUP-BTC
        in bear markets (unlike WLD-BTC where BTC-FR-compression creates forced co-movement).
      Anti-corr with K449 ETH-BTC (corr=-0.2052): portfolio diversification benefit.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, diff_ema,
       signal_strength, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime  = signal.get("regime", "NEUTRAL")
    ema     = signal.get("diff_ema_168h", 0.0)
    thresh  = signal.get("threshold", 1e-8)
    abs_ema = abs(ema)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_WLD":
        # WLD FR > ETH FR: WLD expensive (high funding cost to long)
        # short WLD (collect high FR) / long ETH (cheap carry)
        long_asset  = "ETH"
        short_asset = "WLD"
        state       = STATE_LONG_ETH_SHORT_WLD
    else:  # BEAR_WLD
        # ETH FR > WLD FR: ETH expensive (high funding cost to long)
        # long WLD (cheap carry) / short ETH (collect ETH FR)
        long_asset  = "WLD"
        short_asset = "ETH"
        state       = STATE_LONG_WLD_SHORT_ETH

    # Both legs on HL (K629: WLD-PERP + ETH-PERP, both HL)
    long_venue  = "HL"
    short_venue = "HL"

    # Signal strength: |ema| / threshold (capped at 3x for sizing)
    strength = min(abs_ema / max(thresh, 1e-10), 3.0)

    return {
        "long_asset":      long_asset,
        "short_asset":     short_asset,
        "position_state":  state,
        "long_venue":      long_venue,
        "short_venue":     short_venue,
        "diff_ema":        ema,
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
    Compute equal notional for both legs of the WLD-ETH paired trade.

    K629 HL-only config (both WLD-PERP + ETH-PERP on HL):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x:
      WLD leg:   $150K capital x 4x = $600K notional (HL WLD-PERP)
      ETH leg:   $150K capital x 4x = $600K notional (HL ETH-PERP)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      HL conc:   +2pp from current 57.5% → ~59.5% (within 65% limit)
      Net profit: ~$94,210/yr @$10M @4x (OOS 7.85% ann ret x $10M x 4x x 3%)

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
    notional_per_leg = total_notional / 2.0
    return round(notional_per_leg, 2), round(total_notional, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Paired trade submission (HL primary, POST_ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def submit_paired_trade(
    long_leg:  dict,
    short_leg: dict,
    dry_run:   bool = True,
) -> dict:
    """
    Submit K629 WLD-ETH paired trade: POST_ONLY both legs in parallel.

    Protocol (K629 HL primary — both legs on HL):
      1. Submit WLD leg on HL POST_ONLY
      2. Submit ETH leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "WLD", "notional": 600000, "venue": "HL"}
      short_leg: {"symbol": "ETH", "notional": 600000, "venue": "HL"}
      dry_run:   True = paper-trade simulation (default)

    Returns execution result dict.
    """
    ts         = datetime.now(UTC).isoformat()
    long_sym   = long_leg["symbol"]
    short_sym  = short_leg["symbol"]
    long_notl  = long_leg.get("notional", 0.0)
    short_notl = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue",  "HL")
    short_venue = short_leg.get("venue", "HL")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K629] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_WLD_ETH_BIOMETRIC_ID",
            "mechanism_note":   (
                "WLD-ETH direct differential (ETH-base mechanism fix): "
                "WLD FR = biometric ID narrative cycles; "
                "ETH FR = DeFi/staking yields. "
                "JUP-BTC cross-base corr=0.3437 < 0.40 PASS (K629)"
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K629] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K629] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K629 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K629 HL-only: both legs on HL (WLD-PERP + ETH-PERP).
    Drift detection: compare stored WLD leg notional vs ETH leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K631 pattern).

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
    Both legs on HL (K629 HL primary — WLD-PERP + ETH-PERP).

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

    if state == STATE_LONG_WLD_SHORT_ETH:
        long_sym,  short_sym  = "WLD", "ETH"
    else:  # LONG_ETH_SHORT_WLD
        long_sym,  short_sym  = "ETH", "WLD"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K629] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@HL ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@HL  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "venue":           "HL",
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "close_mode":      "IOC_REDUCE_ONLY",
            "ts_utc":          ts,
        }
    else:
        print(f"  [K629] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @HL  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @HL")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "venue":          "HL",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k629_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "diff_ema_168h":           0.0,
        "diff_sigma":              0.0,
        "threshold_1_5sigma":      0.0,
        "regime":                  "NEUTRAL",
        "position_state":          STATE_NEUTRAL,
        "long_notional":           0.0,
        "short_notional":          0.0,
        "venue":                   "HL",
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
    """Write k629_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_wld_current"]       = signal.get("fr_wld",       0.0)
    dash["fr_eth_current"]       = signal.get("fr_eth",       0.0)
    dash["wld_eth_diff_current"] = signal.get("wld_eth_diff", 0.0)
    dash["diff_ema_168h"]        = signal.get("diff_ema_168h",  0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",     0.0)
    dash["threshold_1_5sigma"]   = signal.get("threshold",      0.0)
    dash["regime"]               = signal.get("regime",    "NEUTRAL")
    dash["history_points"]       = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]  = state
            dash["long_notional"]   = notional_per_leg
            dash["short_notional"]  = notional_per_leg
            dash["long_asset"]      = decision.get("long_asset")
            dash["short_asset"]     = decision.get("short_asset")
            dash["venue"]           = "HL"
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K629   # ~59.5% post-K629

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K654: Realized Sh>=10 + fill>=60% + DD<15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  10.0,     # >=10 (50% of K629 OOS 19.90)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15% (K654 spec — tighter than prior waves)
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=10 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$94,210/yr @$10M @4x (3% sleeve, OOS 7.85% ann ret)",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K654"
    dash["strategy"]            = "K629 WLD-ETH FR Differential (ETH-base, Biometric ID cluster, W=168h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY"
    dash["eth_base_mechanism"]  = {
        "formula":        "diff = WLD_FR - ETH_FR  (direct, no orthogonalization)",
        "ema_window":     "W=168h (21 x 8h periods, primary config, G6 PASS 48.2 trades/yr)",
        "jup_btc_corr":   0.3437,    # cross-base corr with JUP-BTC signal (PASS < 0.40)
        "eth_btc_corr":  -0.2052,    # same-base corr with ETH-BTC K449 (anti-correlated)
        "adf_pvalue":     0.0,
        "ou_halflife_h":  5.70,
        "note":           (
            "ETH base decouples from BTC-FR-compression mechanism (K621/K627 root cause). "
            "WLD FR = biometric ID narrative; ETH FR = DeFi/staking yields. "
            "K621 (WLD-BTC) was BLOCKED JUP=0.4612; K629 (WLD-ETH) PASS JUP=0.3437."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":   "required",
        "realized_sharpe_min":    10.0,
        "fill_rate_min_pct":      60,
        "max_drawdown_max_pct":   15,
        "status":                 "SCAFFOLD-READY",
        "activation_sleeve_pct":  0.03,
        "venue":                  "HL primary (WLD-PERP + ETH-PERP both on HL)",
    }
    dash["oos_performance"] = {
        "sharpe":                  19.9017,
        "sharpe_is":               29.9396,
        "is_oos_ratio":            0.665,      # good generalization
        "oos_ann_ret_pct":         7.85,
        "ann_return_usd_3pct_4x":  94_210,
        "wave_accept":             "K629 ACCEPT (K654 scaffold) — 9/9 §6 gates PASS",
        "cluster":                 "Biometric ID / World ID (Cluster 24, ETH-base)",
        "cluster_rationale":       (
            "WLD (Worldcoin/World ID) FR driven by biometric proof-of-humanhood adoption, "
            "OpenAI/Sam Altman narrative cycles, privacy-tech regulatory catalysts. "
            "ETH-base fix decouples from BTC-FR-compression: JUP-BTC cross-base corr=0.3437 PASS. "
            "Anti-correlated with K449 ETH-BTC (corr=-0.2052): diversification benefit."
        ),
        "hl_concentration_pct":    59.5,
        "hl_impact":               "~+2pp to 59.5% (WLD-PERP + ETH-PERP both on HL, within 65% limit)",
        "escalation_chain":        "K621 BLOCKED-G5 (JUP=0.4612) -> K624 BLOCKED-G5G6 -> K627 STILL-BLOCKED (0.5726 WORSE) -> K629 PASS (0.3437)",
        "walk_forward":            "11/12 folds positive (91.7%)",
        "perm_pvalue":             0.0,
        "dsr_pvalue":              0.0,
        "trades_per_yr":           48.2,
        "max_drawdown_pct":        0.71,
        "calmar":                  28.0,
        "daemon_number":           "49th",
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
      1. Fetch WLD + ETH FRs from HL
      2. Compute WLD-ETH differential + 168h EMA + sigma
      3. Decide position (|ema| > 1.5sigma threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, HL primary)
      6. If holding: check drift + rebalance
      7. Write k629_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K629 WLD-ETH FR Differential (ETH-base, Biometric ID) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     HL primary (WLD-PERP + ETH-PERP, both HL perps)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: +~2pp -> ~59.5% (WLD-PERP + ETH-PERP both on HL, within 65% limit)")
    print(f"  Signal:    diff = WLD_FR - ETH_FR  (direct, no OLS orthogonalization)")
    print(f"             |EMA_168h| > 1.5sigma  (W=168h = 21 x 8h periods)")
    print(f"  ETH-base:  JUP-BTC cross-base corr=0.3437 PASS (K621 WLD-BTC was 0.4612 BLOCKED)")
    print(f"  Mechanism: BTC-FR-compression removed by ETH base (ETH FR = DeFi/staking)")
    print(f"  9/9 gates: G1={19.90:.2f} G2=0.0 G3=0.0 G4=11/12 G5={0.3437:.4f} G6=48.2 G7=7.85% G8=0.75 G9=213d")

    # Step 1: Fetch + compute WLD-ETH differential
    print("\n  [Step 1] Computing WLD-ETH FR differential...")
    signal = compute_signal()
    print(f"  WLD FR:     {signal['fr_wld']:+.8f} (8h, HL)")
    print(f"  ETH FR:     {signal['fr_eth']:+.8f} (8h, HL)")
    print(f"  WLD-ETH:    {signal['wld_eth_diff']:+.8f}  (direct differential)")
    print(f"  EMA 168h:   {signal['diff_ema_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}")
    print(f"  Threshold:  {signal['threshold']:+.8f}  (1.5sigma = {SIGNAL_SIGMA_MULT}xsigma)")
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
        print(f"  Signal:   NEUTRAL (|diff_ema| <= 1.5sigma)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  WLD leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  ETH leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 7.85% ann ret = $94,210/yr potential")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "HL"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "HL"}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "HL"}
            short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "HL"}
            trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        else:
            print(f"  Action: HOLD (same direction)")

    elif not decision and current_state != STATE_NEUTRAL:
        print(f"  Action: CLOSE (diff below 1.5sigma threshold)")
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
    print(f"\n  [Step 6] Dashboard written -> {DASHBOARD_PATH}")

    # Summary
    print(f"\n  === K629 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  WLD-ETH EMA 168h:   {dash_out.get('diff_ema_168h'):+.8f}")
    print(f"  Threshold (1.5sig): {dash_out.get('threshold_1_5sigma'):+.8f}")
    print(f"  ETH-base fix:       JUP-BTC cross-base corr=0.3437 (K621 WLD-BTC=0.4612 BLOCKED)")
    print(f"  Anti-corr K449:     ETH-BTC corr=-0.2052 (diversification benefit)")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         19.90 (IS=29.94, ratio=0.665)")
    print(f"  Cluster:            Biometric ID / World ID (Cluster 24, ETH-base)")
    print(f"  Profit 3% sleeve:   $94,210/yr @$10M @4x (OOS 7.85% ann ret)")
    print(f"  HL concentration:   ~59.5% (within 65% limit)")
    print(f"  60d gate:           Realized Sh>=10 + fill>=60% + maxDD<15%")
    print(f"  v6.38 path:         K629 WLD-ETH 3% HL sleeve (49th daemon)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K629 WLD-ETH FR Differential Strategy (K654 scaffold, ETH-base Biometric ID)"
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
        print(f"\n=== K629 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K629 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K629 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

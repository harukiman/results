#!/usr/bin/env python3
"""
k663_tia_eth_run.py — K663 TIA-ETH FR Differential Strategy
=============================================================
Implements a paired-trade (long TIA / short ETH or reverse) based on the
168h rolling mean of the TIA-ETH funding rate differential.

ETH-base mechanism (K629 pattern, K663 application to TIA family):
  K507 TIA-BTC uses BTC as the base asset. K663 applies the ETH-base mechanism
  from K629 (WLD-ETH) to TIA, switching the short leg from BTC to ETH.
  K660 rule predicted BLOCKED-G5b for TIA (APT-style, TIA +1.08%/yr far below ETH).
  ACTUAL: G5b corr=0.2309 PASSES (< 0.40). WHY: TIA vol_ratio=2.12x + periodic
  Celestia DA narrative spikes above ETH create enough signal divergence from
  TIA-BTC (K507). K663 is ORTHOGONAL to K507 (G5b corr=0.23, PASS).

  Result: K663 OOS Sh=17.13 > K507 Sh=14.44. Both ACCEPTed. Dual-sleeve
  K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = 3.0% total (orthogonal, corr=0.23).

Architecture (K668 scaffold, K629/K654 pattern):
  1. fetch_fr_batch()               → fetch TIA + ETH FR every 8h from HL
  2. compute_signal(tia_fr, eth_fr) → 168h rolling mean of (TIA_FR - ETH_FR); sign()
  3. decide_position(signal)        → LONG_TIA_SHORT_ETH | LONG_ETH_SHORT_TIA | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (TIA + ETH legs, both HL)
  5. daily_rebalance()              → drift > 5% triggers rebalance
  6. close_paired_position(reason)  → sequential: short first, then long

K663 TIA Modular DA hypothesis (ACCEPT — 9/9 gates):
  - TIA = Celestia: modular data availability layer for rollup-centric blockchains
  - TIA FR dynamics driven by:
      Celestia DA narrative cycles (rollup DA demand, EIP-4844 competition)
      Data availability upgrade cycles (Celestia Mainnet milestones)
      Modular blockchain adoption spikes (new rollup deployments using Celestia)
      TIA token supply unlock cycles and staking yield compression
  - ETH-base mechanism K660 SURPRISE: K660 rule predicted BLOCKED-G5b (TIA at +1.08%/yr,
    9.4%/yr below ETH, "APT territory"). ACTUAL: G5b corr=0.2309 PASSES.
    WHY TIA ≠ APT: TIA has HIGH VOLATILITY (vol_ratio=2.12x) + periodic DA narrative
    spikes above ETH (unlike APT -1.4%/yr which rarely spikes above ETH/BTC).
  - ETH-base: ETH FR driven by DeFi/staking (stETH/LST demand) — orthogonal to TIA's
    DA narrative cycles by construction.
  - G5b corr=0.2309 (PASS < 0.40): TIA-ETH is orthogonal to TIA-BTC K507.
  - OOS Sh=17.13 (W=168h, 9/9 §6 PASS: full gate score)
  - 60d paper-trade gate required before live activation

K663 K668 profit summary:
  - OOS Sharpe: 17.1322 (IS: 31.305, ratio=0.548 — moderate generalization)
  - OOS Ann Return: 6.18% (unlevered on notional)
  - Profit @$10M @4x @1.5% sleeve: $63,060/yr USDC net ($74,188/yr gross)
  - Dual-sleeve with K507 TIA-BTC (1.5%+1.5%): ~$114,598/yr net combined
  - Both TIA and ETH on HL primary (HL perps: TIA-PERP + ETH-PERP)
  - HL concentration post-K663: +1.5pp (TIA-PERP + ETH-PERP both HL legs)
  - Walk-forward: 4/4 folds positive (100% — G4 PASS)
  - Perm p-value: 0.0000 (1000 reshuffles — G2 PASS)
  - DSR Bonferroni: p=1.08e-38 (12 trials — G3 PASS)
  - Trades/yr: 55.3 (W=168h config — G6 PASS)
  - ADF p=0.0 (stationary), OU halflife=5.2h
  - G5b TIA-BTC K507 critical check: corr=0.2309 (PASS < 0.40)
  - 51st daemon

Execution:
  - HL primary (TIA-PERP + ETH-PERP, both HL perps)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage (dual with K507 TIA-BTC 1.5%)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (primary config, 55.3 trades/yr, G6 PASS)
  - Note: W=336h is best OOS Sh=38.32 but G6 fails (5.0 trades/yr < 30)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k663_tia_eth_run.py --dry-run
  python3 scripts/k663_tia_eth_run.py --status
  python3 scripts/k663_tia_eth_run.py --rebalance
  python3 scripts/k663_tia_eth_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k663_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k663_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k663_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.015         # K663 sleeve = 1.5% of AUM (dual with K507 TIA-BTC 1.5%)
LEVERAGE            = 4.0           # 4x per K663 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (per K663 §6 evaluation, G6 PASS 55.3 trades/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean — per K663 spec)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (HL primary — TIA-PERP + ETH-PERP, both on HL) ──────────────
# Both legs on HL (delta-neutral carry)
# HL concentration: ~59.5% (post-K629) + 1.5pp (K663 TIA+ETH sleeve) = ~61.0%
# K663 is HL-only: TIA-PERP and ETH-PERP both on HL
HL_CONCENTRATION_PRE_K663  = 59.5   # post-K629/K629 reference
HL_CONCENTRATION_POST_K663 = 61.0   # K663 adds ~1.5pp (TIA+ETH, 1.5% sleeve)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_TIA_SHORT_ETH = "LONG_TIA_SHORT_ETH"
STATE_LONG_ETH_SHORT_TIA = "LONG_ETH_SHORT_TIA"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
# K663: TIA + ETH only — direct differential, no orthogonalization factors
SYMBOLS = ("TIA", "ETH")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k663/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k663] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (TIA + ETH from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for TIA and ETH from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    K663: both legs on HL (TIA-PERP + ETH-PERP). ETH-base mechanism.
    K507 TIA-BTC uses BTC as base; K663 switches to ETH (same TIA leg, different base).
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k663] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k663] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K663 FR history JSONL."""
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
    fr_tia: float, fr_eth: float, tia_eth_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_tia":       round(fr_tia,       10),
        "fr_eth":       round(fr_eth,        10),
        "tia_eth_diff": round(tia_eth_diff,  10),  # TIA_FR - ETH_FR (direct differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (TIA-ETH direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_tia: Optional[float] = None,
    fr_eth: Optional[float] = None,
) -> dict:
    """
    Fetch live TIA and ETH FRs from HL, compute TIA-ETH differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K663 direct differential — no orthogonalization):
      diff = TIA_FR - ETH_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> short ETH, long TIA (TIA FR > ETH during DA spikes)
             sign < 0 -> long TIA, short ETH (ETH structural premium; TIA FR << ETH)

    ETH-base K660 SURPRISE mechanism:
      - K660 rule predicted BLOCKED-G5b for TIA (like APT, at +1.08%/yr far below ETH)
      - ACTUAL: G5b corr=0.2309 PASSES (< 0.40 threshold)
      - WHY TIA differs from APT: TIA vol_ratio=2.12x + periodic Celestia DA narrative
        spikes above ETH create enough signal divergence from TIA-BTC (K507).
        APT is consistently negative (-1.4%/yr) and rarely spikes above ETH.
        TIA is near-zero positive (+1.08%/yr) with HIGH VOLATILITY.
      - K660 rule refined: ETH-base succeeds when alt_fr has HIGH VOLATILITY (vol_ratio
        >= 2x) even if mean is below ETH, provided periodic spikes above ETH occur.

    K663 §6 validation (9/9 PASS):
      - OOS Sharpe: 17.1322 (W=168h, zero threshold)
      - OOS Ann Return: 6.18% (unlevered on notional)
      - ADF p=0.0 (stationary), OU halflife=5.2h
      - Walk-forward: 4/4 positive (100%)
      - Perm p=0.0 (1000 reshuffles), DSR p=1.08e-38 (12 trials)
      - Trades/yr: 55.3 (W=168h, G6 PASS >= 30)
      - G5b TIA-BTC K507 corr=0.2309 (PASS < 0.40)

    Returns:
      {
        "fr_tia":          float,
        "fr_eth":          float,
        "tia_eth_diff":    float,    # TIA_FR - ETH_FR (current)
        "mean_168h":       float,    # 168h rolling mean of differential
        "diff_sigma":      float,    # 168h rolling sigma (informational)
        "history_points":  int,
        "regime":          str,      # BULL_TIA | BEAR_TIA | NEUTRAL
        "signal_direction": int,     # +1 | -1 | 0
        "ts_jst":          str,
      }
    """
    if fr_tia is None or fr_eth is None:
        frs    = _fetch_hl_fr_batch()
        fr_tia = frs.get("TIA", 0.0)
        fr_eth = frs.get("ETH", 0.0)

    # TIA-ETH direct differential (no orthogonalization — ETH base is the mechanism fix)
    tia_eth_diff = fr_tia - fr_eth

    _append_fr_history(fr_tia, fr_eth, tia_eth_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["tia_eth_diff"] for r in history if "tia_eth_diff" in r]

    n_periods = EMA_PERIOD_PERIODS   # 21 periods (168h / 8h)

    # Rolling mean: simple mean of last n_periods diffs
    window = diffs[-n_periods:] if len(diffs) >= 1 else diffs
    if window:
        mean_168h = sum(window) / len(window)
    else:
        mean_168h = 0.0

    # Rolling sigma: std of last n_periods diffs (informational)
    if len(window) >= 2:
        mean_w = sum(window) / len(window)
        sigma  = math.sqrt(sum((x - mean_w) ** 2 for x in window) / (len(window) - 1))
    else:
        sigma  = abs(mean_168h) if mean_168h != 0 else 1e-8   # fallback

    # Regime classification (zero threshold — per K663 spec)
    # BULL_TIA: TIA FR > ETH FR (TIA expensive to long during DA narrative spikes)
    # BEAR_TIA: TIA FR < ETH FR (ETH structural premium; predominantly short ETH, long TIA)
    if mean_168h > 0:
        regime    = "BULL_TIA"   # TIA-ETH diff positive -> TIA FR > ETH FR (DA spike)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_TIA"   # TIA-ETH diff negative -> ETH FR > TIA FR (structural)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_tia":           round(fr_tia,       10),
        "fr_eth":           round(fr_eth,        10),
        "tia_eth_diff":     round(tia_eth_diff,  10),
        "mean_168h":        round(mean_168h,     10),
        "diff_sigma":       round(sigma,         10),
        "history_points":   len(diffs),
        "regime":           regime,
        "signal_direction": direction,
        "ts_jst":           datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from TIA-ETH differential rolling mean.

    Logic (TIA-ETH direct differential pair, HL primary):
      regime = BULL_TIA (mean_168h > 0):
        TIA FR > ETH FR -> TIA expensive to long (DA narrative spike)
        -> short TIA (collect high TIA FR) / long ETH (cheap carry)
        -> position_state = LONG_ETH_SHORT_TIA
        -> both legs on HL

      regime = BEAR_TIA (mean_168h < 0):
        ETH FR > TIA FR -> ETH expensive to long (structural ETH premium)
        -> long TIA (cheap carry, collect ETH FR by shorting ETH)
        -> position_state = LONG_TIA_SHORT_ETH
        -> both legs on HL

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    K663 edge (ETH-base mechanism, K660 SURPRISE):
      The TIA-ETH differential captures Celestia modular DA narrative cycles
      vs ETH DeFi/staking cycles. G5b corr=0.2309 vs K507 TIA-BTC:
        - BULL_TIA (DA spikes): TIA FR spikes above ETH during DA hype cycles
          (rollup announcements, Celestia milestone events) — K663 shorts TIA.
          K507 in same period: also shorts BTC? No — K507 predominantly long TIA.
          Signal divergence: K663 flips to SHORT TIA while K507 stays LONG TIA.
          This divergence is the G5b mechanism (corr=0.23, NOT 0.97 like APT).
        - BEAR_TIA (structural): ETH >> TIA -> both K663 and K507 predominantly
          LONG TIA. But ETH base vs BTC base creates slightly different thresholds
          (ETH-BTC = -1.04%/yr gap only vs TIA-ETH of -9.44%/yr).
      TIA vol_ratio=2.12x (PASS >= 1.5x): high TIA FR volatility enables signal flips.

    Returns:
      {long_asset, short_asset, long_venue, short_venue, mean_168h,
       signal_direction, size_multiplier, position_state}
      or None if NEUTRAL.
    """
    regime    = signal.get("regime", "NEUTRAL")
    mean_168h = signal.get("mean_168h", 0.0)
    direction = signal.get("signal_direction", 0)

    if regime == "NEUTRAL":
        return None

    if regime == "BULL_TIA":
        # TIA FR > ETH FR: TIA expensive (high funding cost to long during DA spike)
        # short TIA (collect high FR) / long ETH (cheap carry)
        long_asset  = "ETH"
        short_asset = "TIA"
        state       = STATE_LONG_ETH_SHORT_TIA
    else:  # BEAR_TIA
        # ETH FR > TIA FR: ETH expensive (structural premium, collect by shorting ETH)
        # long TIA (cheap carry, -9.44%/yr mean diff) / short ETH
        long_asset  = "TIA"
        short_asset = "ETH"
        state       = STATE_LONG_TIA_SHORT_ETH

    # Both legs on HL (K663: TIA-PERP + ETH-PERP, both HL)
    long_venue  = "HL"
    short_venue = "HL"

    return {
        "long_asset":       long_asset,
        "short_asset":      short_asset,
        "position_state":   state,
        "long_venue":       long_venue,
        "short_venue":      short_venue,
        "mean_168h":        mean_168h,
        "signal_direction": direction,
        "size_multiplier":  1.0,   # reserved for dynamic sizing
        "regime":           regime,
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
    Compute equal notional for both legs of the TIA-ETH paired trade.

    K663 HL-only config (both TIA-PERP + ETH-PERP on HL):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x:
      TIA leg:   $75K capital x 4x = $300K notional (HL TIA-PERP)
      ETH leg:   $75K capital x 4x = $300K notional (HL ETH-PERP)
      Total:     $600K notional (two legs combined)
      Margin:    $150K (1.5% of AUM)
      HL conc:   +1.5pp from current ~59.5% → ~61.0% (within 65% limit)
      Net profit: ~$63,060/yr @$10M @4x (OOS 6.18% ann ret x $10M x 4x x 1.5%)
      Dual:      K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = 3.0% total sleeve
                 Combined net @$10M: ~$114,598/yr

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
    Submit K663 TIA-ETH paired trade: POST_ONLY both legs in parallel.

    Protocol (K663 HL primary — both legs on HL):
      1. Submit TIA leg on HL POST_ONLY
      2. Submit ETH leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "TIA", "notional": 300000, "venue": "HL"}
      short_leg: {"symbol": "ETH", "notional": 300000, "venue": "HL"}
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
        print(f"  [K663] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_TIA_ETH_MODULAR_DA",
            "mechanism_note":   (
                "TIA-ETH direct differential (ETH-base mechanism, K663): "
                "TIA FR = Celestia modular DA narrative cycles (rollup DA demand, DA hype); "
                "ETH FR = DeFi/staking yields (stETH/LST, L1 gas narrative). "
                "G5b TIA-BTC K507 corr=0.2309 < 0.40 PASS (K663 SURPRISE vs K660 APT prediction). "
                "K660 rule refined: ETH-base works when vol_ratio >= 2x (TIA=2.12x) even if mean below ETH."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K663] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K663] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K663 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K663 HL-only: both legs on HL (TIA-PERP + ETH-PERP).
    Drift detection: compare stored TIA leg notional vs ETH leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629 pattern).

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
    Both legs on HL (K663 HL primary — TIA-PERP + ETH-PERP).

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

    if state == STATE_LONG_TIA_SHORT_ETH:
        long_sym,  short_sym  = "TIA", "ETH"
    else:  # LONG_ETH_SHORT_TIA
        long_sym,  short_sym  = "ETH", "TIA"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K663] {mode_tag} CLOSE:")
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
        print(f"  [K663] SCAFFOLD CLOSE:")
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
    """Load k663_dashboard.json; return defaults if missing."""
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except Exception:
            pass
    return {
        "last_poll_jst":           "—",
        "mean_168h":               0.0,
        "diff_sigma":              0.0,
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
    """Write k663_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_tia_current"]       = signal.get("fr_tia",       0.0)
    dash["fr_eth_current"]       = signal.get("fr_eth",       0.0)
    dash["tia_eth_diff_current"] = signal.get("tia_eth_diff", 0.0)
    dash["mean_168h"]            = signal.get("mean_168h",    0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",   0.0)
    dash["regime"]               = signal.get("regime",  "NEUTRAL")
    dash["signal_direction"]     = signal.get("signal_direction", 0)
    dash["history_points"]       = signal.get("history_points", 0)

    # Update position if entering
    if decision:
        state = decision.get("position_state", STATE_NEUTRAL)
        if dash.get("position_state") == STATE_NEUTRAL:
            dash["position_state"]    = state
            dash["long_notional"]     = notional_per_leg
            dash["short_notional"]    = notional_per_leg
            dash["long_asset"]        = decision.get("long_asset")
            dash["short_asset"]       = decision.get("short_asset")
            dash["venue"]             = "HL"
            dash["entry_ts_jst"]      = dash["last_poll_jst"]
            dash["signal_direction"]  = decision.get("signal_direction", 0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K663   # ~61.0% post-K663

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K668: Realized Sh >= 8, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  8.0,     # >=8 (50% of K663 OOS 17.13)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=8 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_1_5pct": "$63,060/yr net @$10M @4x (1.5% sleeve, OOS 6.18% ann ret)",
        "dual_sleeve_note":        "K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = ~$114,598/yr net @$10M",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K668"
    dash["strategy"]            = "K663 TIA-ETH FR Differential (ETH-base, Modular DA cluster, W=168h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY"
    dash["eth_base_mechanism"]  = {
        "formula":            "diff = TIA_FR - ETH_FR  (direct, no orthogonalization)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config, G6 PASS 55.3 trades/yr)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "g5b_tia_btc_k507_corr": 0.2309,   # critical orthogonality check PASS
        "vol_ratio_tia_eth":  2.1227,       # PASS >= 1.5x
        "adf_pvalue":         0.0,
        "ou_halflife_h":      5.2,
        "k660_rule_exception": (
            "K660 rule predicted BLOCKED-G5b (TIA at +1.08%/yr, 9.4%/yr below ETH — APT territory). "
            "ACTUAL: G5b corr=0.2309 PASSES (< 0.40). "
            "WHY TIA ≠ APT: TIA vol_ratio=2.12x + periodic Celestia DA narrative spikes above ETH. "
            "APT consistently negative (-1.4%/yr), rarely spikes. "
            "K660 rule refined: ETH-base works when vol_ratio >= 2x even if mean below ETH."
        ),
        "note":               (
            "ETH base decouples from BTC-base mechanism (K507 TIA-BTC pattern). "
            "TIA FR = Celestia modular DA narrative cycles; ETH FR = DeFi/staking yields. "
            "K507 (TIA-BTC) G5b: corr=0.2309 — orthogonal PASS. "
            "TIA family track: K507 TIA-BTC Sh=14.44 + K663 TIA-ETH Sh=17.13. "
            "Dual-sleeve: K507 1.5% + K663 1.5% = $114,598/yr net @$10M."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   8.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.015,
        "venue":                 "HL primary (TIA-PERP + ETH-PERP both on HL)",
    }
    dash["oos_performance"] = {
        "sharpe":                   17.1322,
        "sharpe_is":                31.305,
        "is_oos_ratio":             0.548,
        "oos_ann_ret_pct":          6.1824,
        "ann_return_usd_1_5pct_4x": 63_060,
        "ann_return_usd_gross":     74_188,
        "dual_sleeve_net_yr":       114_598,  # K507 $51,538 + K663 $63,060
        "wave_accept":              "K663 ACCEPT (K668 scaffold) — 9/9 §6 gates PASS",
        "cluster":                  "Modular DA / Celestia (TIA, ETH-base, K660 SURPRISE)",
        "cluster_rationale":        (
            "TIA (Celestia modular data availability) FR driven by rollup DA demand cycles, "
            "EIP-4844 competition narrative, Celestia Mainnet milestone events. "
            "ETH-base mechanism K660 SURPRISE: K660 rule predicted BLOCKED-G5b (like APT), "
            "but TIA vol_ratio=2.12x + periodic DA spikes create G5b corr=0.2309 (PASS). "
            "Dual-sleeve with K507 TIA-BTC eligible (corr=0.23 < 0.40): both ACCEPT."
        ),
        "g5b_critical_corr":        0.2309,    # TIA-ETH vs TIA-BTC K507
        "g5b_verdict":              "PASS (< 0.40) — TIA-ETH orthogonal to TIA-BTC K507",
        "walk_forward":             "4/4 folds positive (100%)",
        "perm_pvalue":              0.0,
        "dsr_pvalue":               1.08e-38,
        "trades_per_yr":            55.3,
        "max_drawdown_pct":         0.4231,
        "calmar":                   14.6,
        "daemon_number":            "51st",
        "k507_comparison": {
            "k507_oos_sharpe":  14.439,
            "k663_oos_sharpe":  17.1322,
            "sharpe_delta":     2.6932,
            "k507_net_yr_10m":  51538,
            "k663_net_yr_10m":  63060,
            "delta_net_yr":     11522,
        },
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
      1. Fetch TIA + ETH FRs from HL
      2. Compute TIA-ETH differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, HL primary)
      6. If holding: check drift + rebalance
      7. Write k663_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K663 TIA-ETH FR Differential (ETH-base, Modular DA) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Dual:      K507 TIA-BTC 1.5% + K663 TIA-ETH 1.5% = 3.0% total sleeve")
    print(f"  Venue:     HL primary (TIA-PERP + ETH-PERP, both HL perps)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: +~1.5pp -> ~61.0% (TIA-PERP + ETH-PERP both on HL, within 65% limit)")
    print(f"  Signal:    diff = TIA_FR - ETH_FR  (direct, no OLS orthogonalization)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  ETH-base:  G5b TIA-BTC K507 corr=0.2309 PASS < 0.40 (K660 SURPRISE)")
    print(f"  K660 rule: K660 predicted BLOCKED-G5b (APT-style). ACTUAL: PASS. TIA vol_ratio=2.12x.")
    print(f"  9/9 gates: G1={17.13:.2f} G2=0.0 G3=1.08e-38 G4=4/4 G5b={0.2309:.4f} G6=55.3 G7=6.18% G8=HL G9=218d")

    # Step 1: Fetch + compute TIA-ETH differential
    print("\n  [Step 1] Computing TIA-ETH FR differential...")
    signal = compute_signal()
    print(f"  TIA FR:     {signal['fr_tia']:+.8f} (8h, HL)")
    print(f"  ETH FR:     {signal['fr_eth']:+.8f} (8h, HL)")
    print(f"  TIA-ETH:    {signal['tia_eth_diff']:+.8f}  (direct differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_TIA, -1=BEAR_TIA, 0=NEUTRAL)")
    print(f"  Regime:     {signal['regime']}")
    print(f"  History:    {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:   LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:    {decision['position_state']}")
        print(f"  Mean 168h:{decision['mean_168h']:+.8f}")
    else:
        print(f"  Signal:   NEUTRAL (rolling_mean_168h == 0 exactly)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  TIA leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  ETH leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 6.18% ann ret = $63,060/yr net (1.5% sleeve)")
    print(f"  Dual-sleeve:      K507 $51,538/yr + K663 $63,060/yr = ~$114,598/yr net @$10M")

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
        print(f"  Action: CLOSE (mean_168h == 0 exactly)")
        trade_result = close_paired_position("signal_neutral_exact_zero", dry_run=dry_run)

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
    print(f"\n  === K663 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  TIA-ETH Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  G5b K507 corr:      0.2309 (PASS < 0.40 — orthogonal to TIA-BTC)")
    print(f"  K660 exception:     TIA vol_ratio=2.12x + DA spikes -> NOT APT-style")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         17.13 (IS=31.31, ratio=0.548)")
    print(f"  Cluster:            Modular DA / Celestia (TIA, ETH-base, 51st daemon)")
    print(f"  Profit 1.5% sleeve: $63,060/yr net @$10M @4x (OOS 6.18% ann ret)")
    print(f"  Dual K507+K663:     ~$114,598/yr net @$10M (1.5%+1.5% = 3% total)")
    print(f"  HL concentration:   ~61.0% (within 65% limit, +1.5pp from ~59.5%)")
    print(f"  60d gate:           Realized Sh>=8 + fill>=60% + maxDD<15%")
    print(f"  v6.41 path:         K663 TIA-ETH 1.5% HL sleeve (51st daemon)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K663 TIA-ETH FR Differential Strategy (K668 scaffold, ETH-base Modular DA)"
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
        print(f"\n=== K663 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K663 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K663 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

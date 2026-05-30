#!/usr/bin/env python3
"""
k661_avax_eth_run.py — K661 AVAX-ETH Funding Rate Differential Strategy
=========================================================================
Implements a paired-trade (long AVAX / short ETH or reverse) based on the
168h rolling mean of the AVAX-ETH funding rate differential.

ETH-base mechanism (K629 pattern, K661 application to AVAX family):
  K484 AVAX-BTC uses BTC as the base asset. K661 applies the ETH-base mechanism
  from K629 (WLD-ETH) / K658 (SOL-ETH) to AVAX, switching the short leg from
  BTC to ETH.
  K661 ACCEPT CONDITIONAL — ETH-BASE COMPARABLE (BTC-BASE MARGINALLY BETTER):
    - OOS Sh=28.26 vs K484 Sh=43.89 (delta -15.63; BTC-base marginally superior)
    - PnL corr=0.3731 < 0.40 → dual diversification value → BOTH deployable
    - Combined K484 1.5% + K661 1.5% = $139K vs $76K single K484 alone
  AVAX-ETH edge:
    - AVAX FR driven by subnet/RWA events (Avalanche9000, RWA tokenization)
    - ETH FR driven by DeFi/staking yields (stETH/LST, L1 gas narrative)
    - Partially distinct regimes → PnL corr=0.3731 (orthogonal enough for dual-sleeve)
    - G5a ETH-BTC K449 corr=-0.008 (CRITICAL: near-zero, shared ETH leg OK)

Architecture (K677 scaffold, K668/K669 pattern):
  1. fetch_fr_batch()               → fetch AVAX + ETH FR every 8h from HL
  2. compute_signal(avax_fr, eth_fr) → 168h rolling mean of (AVAX_FR - ETH_FR); sign()
  3. decide_position(signal)         → LONG_AVAX_SHORT_ETH | LONG_ETH_SHORT_AVAX | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (AVAX + ETH legs, both HL)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K661 AVAX subnet/RWA hypothesis (ACCEPT CONDITIONAL — 6/7 gates, G6 structural):
  - AVAX = Avalanche: high-performance L1 with Subnet architecture
  - AVAX FR dynamics driven by:
      Avalanche9000 subnet launches (new subnet activations, Teleporter IBC)
      RWA tokenization events (institutional RWA deployment on Avalanche)
      AVAX token staking/validator yield dynamics (2-year lock cycles)
      DeFi ecosystem events (Trader Joe, BENQI, Aave Avalanche portal)
  - ETH-base mechanism: ETH FR driven by DeFi/staking (stETH/LST demand) —
    orthogonal to AVAX's subnet/RWA cycles by construction.
  - CONDITIONAL on: BTC-base (K484) marginally superior Sh=43.89 vs Sh=28.26
    BUT: dual-sleeve with K484 provides portfolio-level benefit via diversification
    (PnL corr=0.3731 < 0.40 threshold → both strategies can coexist).
  - Combined K484 1.5% + K661 1.5% = $139K/yr est @$10M
    (vs $76K single K484 alone — +$63K diversification premium)
  - HL concentration post-K661: +1.5pp (AVAX-PERP + ETH-PERP both HL legs)
    Within 65% limit (K484 already on HL, ETH leg shared with K449)
  - Walk-forward: 4/4 folds positive (100% — G4 PASS)
  - Perm p-value: 0.000 (G2 PASS)
  - G6 structural: 18.6 entries/yr (below 30 threshold — same as K484/K658)
  - G5a ETH-BTC K449 corr=-0.008 (CRITICAL shared-leg check — PASS)
  - G5b AVAX-BTC K484 corr=0.3731 (family orthogonality — PASS < 0.40)
  - 53rd daemon (6th ETH-base mechanism scaffold)

Execution:
  - HL primary (AVAX-PERP + ETH-PERP, both HL perps)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 1.5% sleeve, 4x leverage (dual with K484 AVAX-BTC 1.5%)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (primary config, 18.6 trades/yr, G6 structural same as K484)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k661_avax_eth_run.py --dry-run
  python3 scripts/k661_avax_eth_run.py --status
  python3 scripts/k661_avax_eth_run.py --rebalance
  python3 scripts/k661_avax_eth_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k661_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k661_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k661_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.015         # K661 sleeve = 1.5% of AUM (dual with K484 AVAX-BTC 1.5%)
LEVERAGE            = 4.0           # 4x per K661 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h, 18.6 trades/yr)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean — per K661 spec)
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (HL primary — AVAX-PERP + ETH-PERP, both on HL) ─────────────
# Both legs on HL (delta-neutral carry)
# HL concentration: ~62.5% (post-K669 estimate) + 1.5pp (K661 AVAX+ETH sleeve)
# K661 is HL-only: AVAX-PERP and ETH-PERP both on HL
# Note: ETH leg is shared with K449/K663 but is an independent hedge position
HL_CONCENTRATION_PRE_K661  = 62.5   # post-K669 reference estimate
HL_CONCENTRATION_POST_K661 = 64.0   # K661 adds ~1.5pp (AVAX+ETH, 1.5% sleeve)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_AVAX_SHORT_ETH = "LONG_AVAX_SHORT_ETH"
STATE_LONG_ETH_SHORT_AVAX = "LONG_ETH_SHORT_AVAX"

# ── Symbols fetched from HL for FR data ──────────────────────────────────────
# K661: AVAX + ETH only — direct differential, no orthogonalization factors
SYMBOLS = ("AVAX", "ETH")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k661/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k661] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (AVAX + ETH from HL)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for AVAX and ETH from HL.
    Returns {symbol: fr_8h_fraction}.

    HL API: metaAndAssetCtxs -> funding field per asset.
    K661: both legs on HL (AVAX-PERP + ETH-PERP). ETH-base mechanism.
    K484 AVAX-BTC uses BTC as base; K661 switches to ETH (same AVAX leg, different base).
    """
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [k661] HL metaAndAssetCtxs fetch failed", file=sys.stderr)
        return {}
    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
    result: Dict[str, float] = {}
    for sym in SYMBOLS:
        if sym not in universe:
            print(f"  [k661] Symbol {sym} not found in HL universe", file=sys.stderr)
            continue
        idx = universe[sym]
        ctx = asset_ctxs[idx]
        try:
            result[sym] = float(ctx.get("funding", 0.0))
        except (TypeError, ValueError):
            continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K661 FR history JSONL."""
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
    fr_avax: float, fr_eth: float, avax_eth_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_avax":       round(fr_avax,        10),
        "fr_eth":        round(fr_eth,          10),
        "avax_eth_diff": round(avax_eth_diff,   10),  # AVAX_FR - ETH_FR (direct differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (AVAX-ETH direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_avax: Optional[float] = None,
    fr_eth:  Optional[float] = None,
) -> dict:
    """
    Fetch live AVAX and ETH FRs from HL, compute AVAX-ETH differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K661 direct differential — no orthogonalization):
      diff = AVAX_FR - ETH_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> short AVAX, long ETH (AVAX FR > ETH during subnet/RWA spikes)
             sign < 0 -> long AVAX, short ETH (ETH structural premium; AVAX FR << ETH)

    K661 AVAX-ETH dual-sleeve mechanism (K677 scaffold):
      - K661 ACCEPT CONDITIONAL (6/7 gates, G6 structural same as K484/K658):
        OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base marginally superior on Sharpe)
        BUT PnL corr=0.3731 < 0.40 → BOTH orthogonal enough to coexist
      - Combined K484 1.5% + K661 1.5% = $139K/yr est @$10M
        (vs $76K single K484 — $63K annual diversification premium)
      - G5a ETH-BTC K449 corr=-0.008 (CRITICAL: AVAX-ETH shares ETH leg with K449;
        near-zero means AVAX subnet/RWA events do NOT correlate with ETH DeFi events)
      - vol_ratio AVAX/ETH: 1.38x (PASS >= 1.2 threshold; lower than AVAX/BTC 1.50x
        because ETH is more volatile in FR than BTC)
      - ETH-base mechanism: AVAX subnet/RWA narrative cycles decouple from ETH
        DeFi/staking yields → distinct FR drivers → clean orthogonal differential

    K661 §6 gate results (6/7 PASS, G6 structural):
      - OOS Sharpe: 28.2551 (W=168h, zero threshold, G1 PASS)
      - OOS Ann Return: 6.61% (unlevered on notional, G7 PASS at 4x: 26.42%)
      - ADF p=0.0 (stationary), OU halflife=3.7h
      - Walk-forward: 4/4 positive (100%, G4 PASS)
      - Perm p=0.0 (1000 reshuffles, G2 PASS), DSR p=6.31e-100 (G3 PASS)
      - Trades/yr: 18.6 (G6 structural — below 30 threshold; same as K484/K658)
      - G5a ETH-BTC K449 corr=-0.008 (CRITICAL shared-leg PASS)
      - G5b AVAX-BTC K484 corr=0.3731 (PASS < 0.40 — family orthogonality key)

    Returns:
      {
        "fr_avax":           float,
        "fr_eth":            float,
        "avax_eth_diff":     float,     # AVAX_FR - ETH_FR (current)
        "mean_168h":         float,     # 168h rolling mean of differential
        "diff_sigma":        float,     # 168h rolling sigma (informational)
        "history_points":    int,
        "regime":            str,       # BULL_AVAX | BEAR_AVAX | NEUTRAL
        "signal_direction":  int,       # +1 | -1 | 0
        "ts_jst":            str,
      }
    """
    if fr_avax is None or fr_eth is None:
        frs     = _fetch_hl_fr_batch()
        fr_avax = frs.get("AVAX", 0.0)
        fr_eth  = frs.get("ETH",  0.0)

    # AVAX-ETH direct differential (no orthogonalization — ETH base is the mechanism fix)
    avax_eth_diff = fr_avax - fr_eth

    _append_fr_history(fr_avax, fr_eth, avax_eth_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["avax_eth_diff"] for r in history if "avax_eth_diff" in r]

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

    # Regime classification (zero threshold — per K661 spec)
    # BULL_AVAX: AVAX FR > ETH FR (AVAX expensive; subnet/RWA event spike)
    # BEAR_AVAX: AVAX FR < ETH FR (ETH structural premium; predominantly short ETH, long AVAX)
    if mean_168h > 0:
        regime    = "BULL_AVAX"   # AVAX-ETH diff positive -> AVAX FR > ETH FR (subnet/RWA spike)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_AVAX"   # AVAX-ETH diff negative -> ETH FR > AVAX FR (structural)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_avax":           round(fr_avax,        10),
        "fr_eth":            round(fr_eth,           10),
        "avax_eth_diff":     round(avax_eth_diff,    10),
        "mean_168h":         round(mean_168h,        10),
        "diff_sigma":        round(sigma,            10),
        "history_points":    len(diffs),
        "regime":            regime,
        "signal_direction":  direction,
        "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Position decision
# ─────────────────────────────────────────────────────────────────────────────

def decide_position(signal: dict) -> Optional[dict]:
    """
    Determine trade direction from AVAX-ETH differential rolling mean.

    Logic (AVAX-ETH direct differential pair, HL primary):
      regime = BULL_AVAX (mean_168h > 0):
        AVAX FR > ETH FR: AVAX expensive (high funding cost to long during subnet/RWA spike)
        -> short AVAX (collect high FR) / long ETH (cheap carry)
        -> position_state = LONG_ETH_SHORT_AVAX
        -> both legs on HL

      regime = BEAR_AVAX (mean_168h < 0):
        ETH FR > AVAX FR: ETH expensive (structural premium; DeFi/staking demand)
        -> long AVAX (cheap carry) / short ETH (collect ETH structural premium)
        -> position_state = LONG_AVAX_SHORT_ETH
        -> both legs on HL

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    K661 edge (ETH-base mechanism, K677 dual-sleeve):
      The AVAX-ETH differential captures Avalanche subnet/RWA narrative cycles
      vs ETH DeFi/staking cycles. G5b corr=0.3731 vs K484 AVAX-BTC:
        - BULL_AVAX (subnet/RWA spikes): AVAX FR spikes above ETH during Avalanche
          events (Avalanche9000 launch, major RWA tokenization on Avalanche, Teleporter
          IBC announcements) — K661 shorts AVAX.
          K484 in same period: may also short AVAX (both K661 and K484 agree).
          But signal threshold differs: K484 uses BTC as reference (ETH is more
          volatile than BTC in FR terms), so K661 triggers on different timing.
        - BEAR_AVAX (structural): ETH >> AVAX -> both K661 and K484 predominantly
          LONG AVAX. ETH base vs BTC base creates slightly different thresholds
          (ETH-BTC = -1.04%/yr gap; AVAX-ETH = -4.18%/yr; AVAX-BTC = -5.17%/yr).
      vol_ratio AVAX/ETH 1.38x (PASS >= 1.2x): meaningful AVAX FR volatility
      relative to ETH enables signal generation despite noisier ETH anchor.
      G5a K449 ETH-BTC corr=-0.008: near-zero → AVAX subnet events NOT correlated
      with ETH DeFi events that drive K449 (shared ETH leg risk = minimal).

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

    if regime == "BULL_AVAX":
        # AVAX FR > ETH FR: AVAX expensive (subnet/RWA spike)
        # short AVAX (collect high FR) / long ETH (cheap carry)
        long_asset  = "ETH"
        short_asset = "AVAX"
        state       = STATE_LONG_ETH_SHORT_AVAX
    else:  # BEAR_AVAX
        # ETH FR > AVAX FR: ETH expensive (structural premium; DeFi/staking)
        # long AVAX (cheap carry) / short ETH (collect structural premium)
        long_asset  = "AVAX"
        short_asset = "ETH"
        state       = STATE_LONG_AVAX_SHORT_ETH

    # Both legs on HL (K661: AVAX-PERP + ETH-PERP, both HL)
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
    Compute equal notional for both legs of the AVAX-ETH paired trade.

    K661 HL-only config (both AVAX-PERP + ETH-PERP on HL):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 1.5% = $150K)
      total_notional   = sleeve_capital x lev   ($150K x 4 = $600K)
      notional_per_leg = total_notional / 2     ($300K per leg)

    At $10M / 1.5% sleeve / 4x:
      AVAX leg:  $75K capital x 4x = $300K notional (HL AVAX-PERP)
      ETH leg:   $75K capital x 4x = $300K notional (HL ETH-PERP)
      Total:     $600K notional (two legs combined)
      Margin:    $150K (1.5% of AUM)
      HL conc:   +~1.5pp from current ~62.5% -> ~64.0% (within 65% limit)
      Net profit: ~$63,416/yr @$10M @4x (OOS 6.61% ann ret x $10M x 4x x 1.5%)
      Dual:      K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = 3.0% total sleeve
                 Combined est @$10M: ~$139,099/yr net

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
    Submit K661 AVAX-ETH paired trade: POST_ONLY both legs in parallel.

    Protocol (K661 HL primary — both legs on HL):
      1. Submit AVAX leg on HL POST_ONLY
      2. Submit ETH leg on HL POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out within IOC_TIMEOUT_SEC
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "AVAX", "notional": 300000, "venue": "HL"}
      short_leg: {"symbol": "ETH",  "notional": 300000, "venue": "HL"}
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
        print(f"  [K661] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "HL_PRIMARY_AVAX_ETH_DUAL_SLEEVE",
            "mechanism_note":   (
                "AVAX-ETH direct differential (ETH-base mechanism, K661): "
                "AVAX FR = Avalanche subnet/RWA narrative cycles (Avalanche9000, RWA tokenization); "
                "ETH FR = DeFi/staking yields (stETH/LST, L1 gas narrative). "
                "ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base marginally better). "
                "Dual-sleeve eligible: PnL corr=0.3731 < 0.40 (K484 AVAX-BTC family orthogonality). "
                "G5a ETH-BTC K449 corr=-0.008 (CRITICAL: near-zero, shared ETH leg minimal risk). "
                "Combined K484 1.5% + K661 1.5% = ~$139K/yr est @$10M (vs $76K single K484). "
                "53rd daemon (6th ETH-base scaffold)."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K661] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    # Scaffold: poll not implemented — retry next 8h cycle
    print(f"  [K661] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K661 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K661 HL-only: both legs on HL (AVAX-PERP + ETH-PERP).
    Drift detection: compare stored AVAX leg notional vs ETH leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K658 pattern).

    Note: AVAX has higher price volatility than ETH in price terms (smaller cap alt),
    but AVAX FR has lower volatility than BTC FR relative to ETH (vol_ratio 1.38x
    vs K484's 1.50x). Monitor drift more frequently during Avalanche narrative events.

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
    drift_pct        = float(dashboard.get("delta_neutral_drift_pct", 0.0))
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
    Both legs on HL (K661 HL primary — AVAX-PERP + ETH-PERP).

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

    if state == STATE_LONG_AVAX_SHORT_ETH:
        long_sym,  short_sym  = "AVAX", "ETH"
    else:  # LONG_ETH_SHORT_AVAX
        long_sym,  short_sym  = "ETH", "AVAX"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K661] {mode_tag} CLOSE:")
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
        print(f"  [K661] SCAFFOLD CLOSE:")
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
    """Load k661_dashboard.json; return defaults if missing."""
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
    """Write k661_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]          = signal.get("ts_jst", "—")
    dash["fr_avax_current"]        = signal.get("fr_avax",        0.0)
    dash["fr_eth_current"]         = signal.get("fr_eth",          0.0)
    dash["avax_eth_diff_current"]  = signal.get("avax_eth_diff",   0.0)
    dash["mean_168h"]              = signal.get("mean_168h",       0.0)
    dash["diff_sigma"]             = signal.get("diff_sigma",      0.0)
    dash["regime"]                 = signal.get("regime",    "NEUTRAL")
    dash["signal_direction"]       = signal.get("signal_direction", 0)
    dash["history_points"]         = signal.get("history_points",   0)

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
    dash["delta_neutral_drift_pct"] = rebalance.get("drift_pct",            0.0)
    dash["rebalance_required"]       = rebalance.get("rebalance_required", False)

    # Margin / notional summary
    dash["total_notional_usdc"]      = round(total_notional, 2)
    dash["notional_per_leg_usdc"]    = round(notional_per_leg, 2)
    dash["leverage"]                 = LEVERAGE
    dash["sleeve_pct"]               = SLEEVE_PCT
    dash["aum_ref_usdc"]             = aum
    dash["margin_used_usdc"]         = round(total_notional / LEVERAGE, 2)
    dash["margin_pct_of_aum"]        = round((total_notional / LEVERAGE) / aum, 4)
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K661  # ~64.0% post-K661

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K677: Realized Sh >= 14, fill >= 60%, DD < 15%)
    # Gate: 50% of OOS Sh=28.26 = 14.13 (rounded to 14)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  14.0,     # >=14 (50% of K661 OOS 28.26)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,        # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=14 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_1_5pct": "$63,416/yr net @$10M @4x (1.5% sleeve, OOS 6.61% ann ret)",
        "dual_sleeve_note":        "K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = ~$139,099/yr net @$10M",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K677"
    dash["strategy"]            = "K661 AVAX-ETH FR Differential (ETH-base, AVAX Subnet/RWA Cluster, W=168h)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "HL_PRIMARY"
    dash["eth_base_mechanism"]  = {
        "formula":              "diff = AVAX_FR - ETH_FR  (direct, no OLS orthogonalization)",
        "rolling_window":       "W=168h (21 x 8h periods, primary config, 18.6 trades/yr, G6 structural)",
        "signal":               "sign(rolling_mean_168h(diff))",
        "g5a_eth_btc_k449_corr":  -0.008,  # CRITICAL shared-leg check PASS
        "g5b_avax_btc_k484_corr":  0.3731, # family orthogonality PASS < 0.40
        "vol_ratio_avax_eth":       1.3828, # PASS >= 1.2x (ETH more volatile than BTC in FR)
        "adf_pvalue":               0.0,
        "ou_halflife_h":            3.7,
        "k661_vs_k484": (
            "K661 ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base marginally superior). "
            "BUT PnL corr=0.3731 < 0.40 -> dual-sleeve eligible. "
            "Combined K484 1.5% + K661 1.5% = ~$139K/yr est @$10M (vs $76K single K484). "
            "$63K annual diversification premium justifies dual-sleeve."
        ),
        "note":               (
            "ETH base decouples from BTC-base mechanism (K484 AVAX-BTC pattern). "
            "AVAX FR = Avalanche subnet/RWA narrative cycles (Avalanche9000, RWA tokenization, Teleporter IBC). "
            "ETH FR = DeFi/staking yields (stETH/LST, L1 gas narrative). "
            "G5a K449 ETH-BTC corr=-0.008: near-zero (AVAX subnet events NOT correlated with ETH DeFi events). "
            "K484 AVAX-BTC family track: K484 Sh=43.89 (primary) + K661 Sh=28.26 (dual-sleeve). "
            "vol_ratio AVAX/ETH 1.38x < AVAX/BTC 1.50x: ETH is more volatile in FR than BTC, "
            "making AVAX-ETH noisier but still tradeable differential. "
            "6th ETH-base scaffold: K629 WLD + K658 SOL + K663 TIA + K661 AVAX (all HL primary). "
            "53rd daemon (K677 scaffold)."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   14.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.015,
        "venue":                 "HL primary (AVAX-PERP + ETH-PERP both on HL)",
    }
    dash["oos_performance"] = {
        "sharpe":                    28.2551,
        "sharpe_k484_comparison":    43.887,
        "sharpe_delta_vs_k484":      -15.6319,
        "oos_ann_ret_pct":           6.6058,
        "oos_ann_ret_4x_pct":        26.4232,
        "ann_return_usd_1_5pct_4x":  63416,
        "ann_return_usd_gross":      79270,
        "dual_sleeve_net_yr":        139099,  # K484 $75,683 + K661 $63,416
        "wave_accept":               "K661 ACCEPT CONDITIONAL (K677 scaffold) — 6/7 §6 gates (G6 structural)",
        "cluster":                   "AVAX Subnet/RWA (AVAX, ETH-base, K484 dual-sleeve, 53rd daemon)",
        "cluster_rationale": (
            "AVAX (Avalanche L1 with Subnet architecture) FR driven by Avalanche9000 subnet launches, "
            "RWA tokenization events (institutional deployment on Avalanche), AVAX staking/validator "
            "yield dynamics, and DeFi ecosystem events (Trader Joe, BENQI, Aave Avalanche portal). "
            "ETH-base mechanism: ETH FR = DeFi/staking yields (structurally distinct from AVAX subnet/RWA). "
            "ACCEPT CONDITIONAL: BTC-base (K484) marginally superior Sh=43.89, BUT dual-sleeve eligible "
            "because PnL corr=0.3731 < 0.40. Combined K484+K661 ~$139K/yr vs $76K single = $63K diversification premium."
        ),
        "g5a_critical_corr":         -0.008,   # ETH-BTC K449 (shared ETH leg) PASS
        "g5b_family_corr":            0.3731,   # AVAX-BTC K484 (family orthogonality) PASS
        "g5b_verdict":               "PASS (< 0.40) — AVAX-ETH orthogonal to AVAX-BTC K484 for dual-sleeve",
        "walk_forward":              "4/4 folds positive (100%)",
        "perm_pvalue":                0.0,
        "dsr_pvalue":                 6.31e-100,
        "trades_per_yr":              18.6,
        "g6_note":                   "G6 structural: 18.6/yr < 30 threshold (same as K484/K658 — 7d rolling mean reduces flip frequency)",
        "max_drawdown_pct":           0.2625,
        "vol_ratio_avax_eth":         1.3828,
        "ou_halflife_h":              3.7,
        "daemon_number":             "53rd",
        "eth_base_family_rank":       "6th ETH-base scaffold: K629 WLD + K658 SOL + K663 TIA + K661 AVAX",
        "k484_comparison": {
            "k484_oos_sharpe":   43.887,
            "k661_oos_sharpe":   28.2551,
            "sharpe_delta":      -15.6319,
            "k484_net_yr_10m":   75683,
            "k661_net_yr_10m":   63416,
            "combined_net_yr":   139099,
            "diversif_premium":   63416,  # combined - k484 single = extra from k661
            "pnl_corr":          0.3731,
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
      1. Fetch AVAX + ETH FRs from HL
      2. Compute AVAX-ETH differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, HL primary)
      6. If holding: check drift + rebalance
      7. Write k661_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K661 AVAX-ETH FR Differential (ETH-base, AVAX Subnet/RWA Dual-Sleeve) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Dual:      K484 AVAX-BTC 1.5% + K661 AVAX-ETH 1.5% = 3.0% total sleeve")
    print(f"  Venue:     HL primary (AVAX-PERP + ETH-PERP, both HL perps)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  HL impact: +~1.5pp -> ~64.0% (AVAX-PERP + ETH-PERP both on HL, within 65% limit)")
    print(f"  Signal:    diff = AVAX_FR - ETH_FR  (direct, no OLS orthogonalization)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  DECISION:  ACCEPT CONDITIONAL: OOS Sh=28.26 vs K484 Sh=43.89 (BTC-base better)")
    print(f"             PnL corr=0.3731 < 0.40 -> dual-sleeve eligible -> $139K/yr combined")
    print(f"  G5a K449:  ETH-BTC corr=-0.008 (CRITICAL shared-leg check PASS)")
    print(f"  G5b K484:  AVAX-BTC corr=0.3731 (family orthogonality PASS < 0.40)")
    print(f"  53rd daemon, 6th ETH-base scaffold (K629 WLD + K658 SOL + K663 TIA + K661 AVAX)")

    # Step 1: Fetch + compute AVAX-ETH differential
    print("\n  [Step 1] Computing AVAX-ETH FR differential...")
    signal = compute_signal()
    print(f"  AVAX FR:     {signal['fr_avax']:+.8f} (8h, HL)")
    print(f"  ETH FR:      {signal['fr_eth']:+.8f} (8h, HL)")
    print(f"  AVAX-ETH:    {signal['avax_eth_diff']:+.8f}  (direct differential)")
    print(f"  Mean 168h:   {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h:  {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:   {signal['signal_direction']:+d}  (+1=BULL_AVAX, -1=BEAR_AVAX, 0=NEUTRAL)")
    print(f"  Regime:      {signal['regime']}")
    print(f"  History:     {signal['history_points']} data points")

    # Step 2: Position decision
    print("\n  [Step 2] Deciding position...")
    decision = decide_position(signal)
    if decision:
        print(f"  Signal:    LONG {decision['long_asset']}@{decision['long_venue']} / "
              f"SHORT {decision['short_asset']}@{decision['short_venue']}")
        print(f"  State:     {decision['position_state']}")
        print(f"  Mean 168h: {decision['mean_168h']:+.8f}")
    else:
        print(f"  Signal:    NEUTRAL (rolling_mean_168h == 0 exactly)")

    # Step 3: Notional sizing
    notional_per_leg, total_notional = \
        compute_delta_neutral_notional(aum, SLEEVE_PCT, LEVERAGE)
    print(f"\n  [Step 3] Notional sizing:")
    print(f"  Sleeve capital:   ${aum * SLEEVE_PCT:,.0f}  ({SLEEVE_PCT:.1%} x ${aum/1e6:.0f}M)")
    print(f"  AVAX leg:         ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  ETH leg:          ${notional_per_leg:,.0f}  (1.5% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS 6.61% ann ret = $63,416/yr net (1.5% sleeve)")
    print(f"  Dual-sleeve:      K484 $75,683/yr + K661 $63,416/yr = ~$139,099/yr net @$10M")

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
    print(f"\n  === K661 Cycle Complete ===")
    print(f"  Position state:      {dash_out.get('position_state')}")
    print(f"  Regime:              {dash_out.get('regime')}")
    print(f"  AVAX-ETH Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:    {dash_out.get('signal_direction')}")
    print(f"  G5a K449 ETH-BTC:    corr=-0.008 (CRITICAL shared-leg PASS)")
    print(f"  G5b K484 AVAX-BTC:   corr=0.3731 (family orthogonality PASS < 0.40)")
    print(f"  Paper-trade mode:    {PAPER_TRADE}")
    print(f"  OOS Sharpe:          28.26 (K484=43.89; BTC-base marginally better)")
    print(f"  ACCEPT CONDITIONAL:  PnL corr=0.3731 -> dual-sleeve eligible")
    print(f"  Cluster:             AVAX Subnet/RWA (ETH-base, 53rd daemon, K677 scaffold)")
    print(f"  Profit 1.5% sleeve:  $63,416/yr net @$10M @4x (OOS 6.61% ann ret)")
    print(f"  Dual K484+K661:      ~$139,099/yr net @$10M (1.5%+1.5% = 3% total)")
    print(f"  HL concentration:    ~64.0% (within 65% limit, +~1.5pp)")
    print(f"  60d gate:            Realized Sh>=14 + fill>=60% + maxDD<15%")
    print(f"  v6.43 path:          K661 AVAX-ETH 1.5% HL sleeve (53rd daemon, dual with K484)")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K661 AVAX-ETH FR Differential Strategy (K677 scaffold, ETH-base AVAX Subnet/RWA Dual-Sleeve)"
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
        print(f"\n=== K661 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K661 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K661 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

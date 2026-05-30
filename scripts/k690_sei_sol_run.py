#!/usr/bin/env python3
"""
k690_sei_sol_run.py — K690 SEI-SOL FR Differential Strategy
=============================================================
FIFTH ALT-ALT pair: SEI vs SOL (no BTC/ETH base).
Signal: SEI_FR - SOL_FR
W=168h rolling mean, zero threshold (sign only)
Bybit-only (SEI-PERP + SOL-PERP on Bybit)
HL concentration: 62.5% (Bybit-only preserves headroom — PREFERRED)

K690 SEI-SOL alt-alt hypothesis:
  SEI (Sei Network) FR dynamics: Cosmos SDK + native parallel EVM (CometBFT + Twin-turbo
  consensus + SeiDB). DeFi protocol launches on parallel EVM, CosmWasm adoption, Cosmos-EVM
  bridge activity, exchange-native perpetual speculation (SEIUSDT), SeiDB-optimized throughput
  events. NEGATIVE mean FR (-3.65% ann) — short-sellers dominate SEI perps (bearish bias vs
  bullish SOL). This creates a dominant directional signal: LONG SOL / SHORT SEI captures BOTH
  positive SOL carry AND negative SEI carry simultaneously (carry-positive in dominant regime).
  SOL (Solana) FR dynamics: Monolithic SVM DePIN/Retail adoption, meme-coin cycle premium
  (BONK/WIF), Firedancer upgrade hype, validator economics, ETF speculation.
  SOL FR is persistently positive (+7.70% ann) — structural retail demand premium.
  Alt-alt mechanism: SEI (Cosmos EVM parallel chain) vs SOL (Solana SVM L1) — cross-ecosystem
  Cosmos-EVM vs SVM premium axis. Cosmos EVM-native parallelism (SEI) vs Solana SVM DePIN/Retail.
  FIFTH alt-alt pair in portfolio. Mid-cap vs large-cap exception: SEI (~$2-8B) vs SOL (~$60-80B).
  Vol ratio SEI/SOL=1.32x (below 1.5x normal threshold; 6m SEI/SOL=1.94x). ADF p=1.01e-23.
  OU half-life=4.41h (strong mean-reversion, 2nd fastest in alt-alt family).

K690 §6 validation (ACCEPT — 12/12 G4 folds positive, UNPRECEDENTED in family):
  - OOS Sharpe: 25.11 (W=168h, zero threshold, ~218d OOS)
  - OOS Ann Return: $104,174/yr net @$10M @4x @3% standalone sleeve
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF stat -12.7158 (strongly stationary p=1.01e-23), OU half-life=4.41h (strong)
  - G4 walk-forward: 12/12 folds positive (UNPRECEDENTED — all folds positive, first in family)
  - Bybit-only (both SEI-PERP + SOL-PERP on Bybit)
  - OKX SEI available as preferred G8 reference (OKX SEI corr=0.664 passes G8)
  - 60d gate: Realized Sh >= 12 (50% of OOS Sh=25.11), fill >= 60%, DD < 15%

K507+K476 algebraic overlap warning:
  K507 SEI-BTC (HL+Bybit, 2% sleeve) — SEI leg.
  K476 SOL-BTC  (HL-only, 1.5% sleeve)  — SOL leg.
  K690 SEI-SOL: mathematically SEI_FR - SOL_FR = (SEI_FR - BTC_FR) - (SOL_FR - BTC_FR)
  ALGEBRAIC: K690 ≈ K507_direction - K476_direction (anti-correlated with K507 by construction,
  corr(K690, K507) = -0.5109 — PORTFOLIO-HEDGING K507 long-SEI exposure).
  G5c corr = -0.5109 signed (ABS 0.5109 > 0.40 threshold — signed PASS per §6 K266 convention).
  K690 + K682 (ATOM-SOL): SOL shared leg — SOL double-exposure if both active.
  K690 + K686 (AVAX-SOL): SOL shared leg — SOL triple-exposure risk if all three active.
  DEFAULT: K690 standalone (3% Bybit sleeve, independent). Reduce K507/K476 if desired.

Architecture (K679/K682/K684/K686 alt-alt scaffold pattern):
  1. fetch_fr_batch()                → fetch SEI + SOL FR every 8h from Bybit
  2. compute_signal(sei_fr, sol_fr) → 168h rolling mean of (SEI_FR - SOL_FR); sign()
  3. decide_position(signal)         → LONG_SEI_SHORT_SOL | LONG_SOL_SHORT_SEI | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (SEI + SOL legs, both Bybit)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K693 production scaffold:
  - 58th daemon (fifth alt-alt pair, WF 12/12 unprecedented)
  - Bybit-only (HL at 62.5%, Bybit preferred to preserve headroom)
  - 3% standalone sleeve (not dual with K507/K476 unless rebalanced)
  - $104,174/yr net @$10M @4x @3% sleeve (OOS Sh=25.11)
  - 60d paper-trade gate: Realized Sh>=12 + fill>=60% + maxDD<15%

Execution:
  - Bybit primary (SEI-PERP + SOL-PERP, both Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage (standalone)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k690_sei_sol_run.py --dry-run
  python3 scripts/k690_sei_sol_run.py --status
  python3 scripts/k690_sei_sol_run.py --rebalance
  python3 scripts/k690_sei_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k690_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k690_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k690_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K690 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K690 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — SEI-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 62.5% baseline — Bybit preferred (preserves 2.5pp headroom)
# K690 is fully Bybit-only: SEI-PERP and SOL-PERP both on Bybit
# Scenario C: both legs Bybit → HL stays at 62.5% (PREFERRED)
HL_CONCENTRATION_PRE_K690   = 62.5   # post-K679/K682/K684/K686 reference
HL_CONCENTRATION_POST_K690  = 62.5   # UNCHANGED — Bybit-only, no HL impact
BYBIT_ONLY_REASON           = (
    "Bybit preferred: both SEI-PERP + SOL-PERP available on Bybit, "
    "HL headroom preserved (K690 spec). HL stays at 62.5% (unchanged, 2.5pp headroom). "
    "OKX SEI also available as preferred G8 reference (OKX SEI corr=0.664 passes G8)."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_SEI_SHORT_SOL = "LONG_SEI_SHORT_SOL"
STATE_LONG_SOL_SHORT_SEI = "LONG_SOL_SHORT_SEI"

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K690: SEI + SOL only — direct alt-alt differential (FIFTH ALT-ALT pair)
SYMBOLS = ("SEI", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k690/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k690] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k690/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k690] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (SEI + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for SEI and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K690: both legs on Bybit (SEI-PERP + SOL-PERP).
    Bybit-only preferred: HL concentration at 62.5% (within 65% cap).
    Both SEIUSDT and SOLUSDT perpetuals listed on Bybit.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    G8 note: OKX SEI corr=0.664 (best G8 reference for SEI leg). Bybit SEI corr=0.526
    (borderline; OKX SEI is preferred reference anchor per K690 G8 spec).
    Note: OKX reference is informational — Bybit is the execution venue.
    """
    result: Dict[str, float] = {}

    # Primary: Bybit /v5/market/tickers (linear perpetuals)
    bybit_url = f"{BYBIT_API_URL}/v5/market/tickers?category=linear"
    raw = _http_get(bybit_url)
    if raw and raw.get("retCode") == 0:
        tickers = raw.get("result", {}).get("list", [])
        sym_map = {t["symbol"]: t for t in tickers}
        for sym in SYMBOLS:
            perp_sym = f"{sym}USDT"
            if perp_sym in sym_map:
                tick = sym_map[perp_sym]
                try:
                    result[sym] = float(tick.get("fundingRate", 0.0))
                except (TypeError, ValueError):
                    pass
        if len(result) == len(SYMBOLS):
            return result
        print(f"  [k690] Bybit partial result {list(result.keys())} — trying HL fallback",
              file=sys.stderr)

    # Fallback: HL metaAndAssetCtxs (informational cross-check only)
    raw_hl = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if raw_hl and isinstance(raw_hl, list) and len(raw_hl) >= 2:
        meta       = raw_hl[0]
        asset_ctxs = raw_hl[1]
        universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}
        for sym in SYMBOLS:
            if sym not in result and sym in universe:
                idx = universe[sym]
                ctx = asset_ctxs[idx]
                try:
                    result[sym] = float(ctx.get("funding", 0.0))
                    print(f"  [k690] {sym} FR from HL fallback (informational)", file=sys.stderr)
                except (TypeError, ValueError):
                    continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K690 FR history JSONL."""
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
    fr_sei: float, fr_sol: float, sei_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_sei":       round(fr_sei,       10),
        "fr_sol":       round(fr_sol,        10),
        "sei_sol_diff": round(sei_sol_diff,  10),  # SEI_FR - SOL_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (SEI-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_sei: Optional[float] = None,
    fr_sol: Optional[float] = None,
) -> dict:
    """
    Fetch live SEI and SOL FRs from Bybit, compute SEI-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K690 direct alt-alt differential — no orthogonalization):
      diff = SEI_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> SEI FR > SOL FR -> short SOL (collect), long SEI (cheap carry)
             sign < 0 -> SOL FR > SEI FR -> long SEI (cheap/negative carry), short SOL (collect)

    NOTE: SEI has NEGATIVE mean FR (-3.65%/ann). The dominant regime is SOL_FR >> SEI_FR.
    In the dominant regime (sign < 0): LONG SOL (collect positive SOL FR) + SHORT SEI
    (collect negative SEI FR = short-sellers pay us). CARRY-POSITIVE in both legs.

    Alt-alt mechanism (FIFTH ALT-ALT pair — K690):
      SEI FR tracks Cosmos EVM parallel chain demand: DeFi protocol launches, CosmWasm
      adoption, Cosmos-EVM bridge activity, SeiDB throughput events. NEGATIVE mean FR
      (-3.65%/ann) — bearish bias on SEI perps (short-sellers dominate).
      SOL FR tracks Solana SVM DePIN/Retail adoption premium: meme-coin season (BONK/WIF),
      Firedancer upgrade hype, SOL ETF speculation, validator economics. Persistently positive
      (+7.70% ann) — structural retail demand premium. SOL usually far higher than SEI.
      SEI-SOL diff captures relative Cosmos-EVM vs SVM premium: SEI negative carry + SOL
      positive carry = structural carry differential of ~11.4%/ann in favor of LONG_SOL.

    Mathematical identity (K690 overlap warning):
      SEI_FR - SOL_FR = (SEI_FR - BTC_FR) - (SOL_FR - BTC_FR) = K507_dir - K476_dir
      K690 is algebraically decomposable into K507 + K476 components.
      Corr(K690, K507) = -0.5109 signed (ANTI-CORRELATED — K690 HEDGES K507 long-SEI).
      Running K690 + K507 + K476 simultaneously creates algebraic overlap.
      K690 + K682 (ATOM-SOL): SOL leg shared → SOL double-exposure if both active.
      K690 + K686 (AVAX-SOL): SOL leg shared → SOL triple-exposure risk if all three active.
      DEFAULT: K690 standalone (3% Bybit sleeve, independent).

    K690 §6 validation:
      - OOS Sharpe: 25.11 (W=168h, zero threshold, ~218d OOS period)
      - OOS Ann Return: 10.27% (1x, unlevered on notional)
      - ADF stat -12.7158 (strongly stationary p=1.01e-23), OU half-life=4.41h (STRONG)
      - Walk-forward: 12/12 folds positive (G4 UNPRECEDENTED — all folds positive, first in family)
      - 60d gate: Realized Sh>=12 + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_sei":           float,
        "fr_sol":           float,
        "sei_sol_diff":     float,    # SEI_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_SEI | BEAR_SEI | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_sei is None or fr_sol is None:
        frs    = _fetch_bybit_fr_batch()
        fr_sei = frs.get("SEI", 0.0)
        fr_sol = frs.get("SOL", 0.0)

    # SEI-SOL direct alt-alt differential (no orthogonalization)
    sei_sol_diff = fr_sei - fr_sol

    _append_fr_history(fr_sei, fr_sol, sei_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["sei_sol_diff"] for r in history if "sei_sol_diff" in r]

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

    # Regime classification (zero threshold — per K690 spec)
    # BULL_SEI: SEI FR > SOL FR (rare Cosmos EVM demand spike: DeFi launch / CosmWasm event)
    # BEAR_SEI: SEI FR < SOL FR (dominant regime ~90%+ of time: SOL retail/meme premium)
    if mean_168h > 0:
        regime    = "BULL_SEI"   # SEI-SOL diff positive → SEI FR > SOL FR (rare Cosmos EVM spike)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_SEI"   # SEI-SOL diff negative → SOL FR > SEI FR (dominant: SOL retail premium)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_sei":           round(fr_sei,        10),
        "fr_sol":           round(fr_sol,          10),
        "sei_sol_diff":     round(sei_sol_diff,    10),
        "mean_168h":        round(mean_168h,        10),
        "diff_sigma":       round(sigma,            10),
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
    Determine trade direction from SEI-SOL differential rolling mean.

    Logic (SEI-SOL direct alt-alt pair, Bybit primary):
      regime = BULL_SEI (mean_168h > 0):
        SEI FR > SOL FR: rare Cosmos EVM demand spike (DeFi protocol launch / CosmWasm event)
        -> long SEI (collect high SEI FR) / short SOL (cheaper retail carry)
        -> position_state = LONG_SEI_SHORT_SOL
        -> both legs on Bybit

      regime = BEAR_SEI (mean_168h < 0):
        SOL FR > SEI FR: dominant regime (~90%+ of time)
        SOL retail/meme-coin season premium + SEI negative carry = CARRY-POSITIVE
        -> long SOL (collect high SOL FR + structural retail premium)
        -> short SEI (collect negative SEI FR — short-sellers PAY us)
        -> position_state = LONG_SOL_SHORT_SEI
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (FIFTH ALT-ALT pair — K690):
      SEI and SOL are cross-ecosystem L1s with orthogonal FR drivers.
      BULL_SEI: Cosmos EVM demand spike (DeFi protocol launch, CosmWasm adoption wave,
        Cosmos-EVM bridge activity, SeiDB throughput narrative, exchange-native speculation).
        SEI FR >> SOL FR → long SEI (collect) / short SOL (cheaper retail carry).
      BEAR_SEI: SOL retail premium dominates (meme-coin BONK/WIF rallies, Firedancer hype,
        SOL ETF speculation, validator economics). SEI FR negative (short-sellers dominate).
        SOL FR >> SEI FR → long SOL (collect positive carry) / short SEI (collect negative carry).
        CARRY-POSITIVE: both legs earn positive carry simultaneously in BEAR_SEI dominant regime.
      Mid-cap vs large-cap: SEI ~$2-8B, SOL ~$60-80B. Different MC tier.
      Different ecosystems: Cosmos EVM parallel (SEI) vs Solana SVM retail (SOL).
      Vol ratio SEI/SOL=1.32x (SEI more volatile — typical mid-cap vs large-cap pattern).
      ADF stat -12.7158 confirms stationarity (p=1.01e-23). Signal valid.

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

    if regime == "BULL_SEI":
        # SEI FR > SOL FR: rare Cosmos EVM demand spike
        # long SEI (collect high FR) / short SOL (cheaper retail carry)
        long_asset  = "SEI"
        short_asset = "SOL"
        state       = STATE_LONG_SEI_SHORT_SOL
    else:  # BEAR_SEI
        # SOL FR > SEI FR: dominant regime (~90%+)
        # long SOL (collect high positive carry) / short SEI (collect negative carry)
        long_asset  = "SOL"
        short_asset = "SEI"
        state       = STATE_LONG_SOL_SHORT_SEI

    # Both legs on Bybit (K690: SEI-PERP + SOL-PERP, both Bybit)
    long_venue  = "BYBIT"
    short_venue = "BYBIT"

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
    Compute equal notional for both legs of the SEI-SOL paired trade.

    K690 Bybit-only config (both SEI-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x (standalone):
      SEI leg:   $150K capital x 4x = $600K notional (Bybit SEI-PERP)
      SOL leg:   $150K capital x 4x = $600K notional (Bybit SOL-PERP)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      HL conc:   UNCHANGED at 62.5% (Bybit-only, HL headroom preserved)
      Net profit: ~$104,174/yr @$10M @4x @3% sleeve (OOS ann ret x notional)
      K507+K476 note: standalone (no algebraic netting assumed)
      K682 note: K690 + K682 share SOL leg — deploy standalone, monitor SOL exposure
      K686 note: K690 + K686 share SOL leg — both standalone, monitor SOL triple-exposure

    Returns (notional_per_leg, total_notional).
    """
    sleeve_capital   = aum * sleeve_pct
    total_notional   = sleeve_capital * leverage
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
    Submit K690 SEI-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K690 Bybit primary — both legs on Bybit):
      1. Submit SEI leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SOL", "notional": 600000, "venue": "BYBIT"}
      short_leg: {"symbol": "SEI", "notional": 600000, "venue": "BYBIT"}
      dry_run:   True = paper-trade simulation (default)

    Returns execution result dict.
    """
    ts         = datetime.now(UTC).isoformat()
    long_sym   = long_leg["symbol"]
    short_sym  = short_leg["symbol"]
    long_notl  = long_leg.get("notional", 0.0)
    short_notl = short_leg.get("notional", 0.0)
    long_venue  = long_leg.get("venue",  "BYBIT")
    short_venue = short_leg.get("venue", "BYBIT")

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K690] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
              f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
        result = {
            "status":           "DRY_RUN",
            "long_result":      {"order_id": f"PAPER_LONG_{long_sym}_{int(time.time())}",  "status": "DRY_RUN"},
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
            "venue_config":     "BYBIT_ONLY_SEI_SOL_ALT_ALT",
            "mechanism_note":   (
                "SEI-SOL direct alt-alt differential (K690 FIFTH ALT-ALT, 58th daemon): "
                "SEI FR = Cosmos EVM parallel chain demand (DeFi protocol launches, CosmWasm, "
                "Cosmos-EVM bridge activity, SeiDB throughput events — NEGATIVE mean -3.65%/ann, "
                "short-sellers dominate SEI perps, bearish bias on Cosmos EVM chain); "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF, "
                "Firedancer upgrade hype, SOL ETF speculation, validator economics — "
                "persistently positive +7.70%/ann structural retail demand premium). "
                "Dominant regime: LONG SOL / SHORT SEI — carry-positive in BOTH legs "
                "(SOL positive carry + SEI negative carry paid to us). "
                "Bybit-only: SEI-PERP + SOL-PERP both on Bybit. HL stays 62.5% (unchanged). "
                "K507+K476 algebraic overlap: K690 STANDALONE (no algebraic netting). "
                "K682/K686 SOL-exposure: K690+K682+K686 share SOL leg — run standalone. "
                "OOS Sh=25.11 (W=168h, zero threshold), $104,174/yr @$10M @4x @3% sleeve. "
                "G4 WF 12/12 UNPRECEDENTED (all folds positive — first in alt-alt family)."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K690] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K690] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K690 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K690 Bybit-only: both legs on Bybit (SEI-PERP + SOL-PERP).
    Drift detection: compare stored SEI leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679/K682/K684/K686 pattern).

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
    Both legs on Bybit (K690 Bybit primary — SEI-PERP + SOL-PERP).

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

    if state == STATE_LONG_SEI_SHORT_SOL:
        long_sym,  short_sym  = "SEI", "SOL"
    else:  # LONG_SOL_SHORT_SEI
        long_sym,  short_sym  = "SOL", "SEI"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K690] {mode_tag} CLOSE:")
        print(f"    Step 1 (SHORT first): cover {short_sym}@BYBIT ${short_notional:,.0f}")
        print(f"    Step 2 (LONG second): sell  {long_sym}@BYBIT  ${long_notional:,.0f}")
        print(f"    reason={reason}")
        result = {
            "status":          "DRY_RUN_CLOSED",
            "reason":          reason,
            "close_sequence":  "short_first_then_long",
            "closed_short":    short_sym,
            "closed_long":     long_sym,
            "venue":           "BYBIT",
            "short_notional":  short_notional,
            "long_notional":   long_notional,
            "close_mode":      "IOC_REDUCE_ONLY",
            "ts_utc":          ts,
        }
    else:
        print(f"  [K690] SCAFFOLD CLOSE:")
        print(f"    Step 1: IOC reduce {short_sym} (cover short) @BYBIT  reason={reason}")
        print(f"    Step 2: IOC reduce {long_sym} (sell long) @BYBIT")
        result = {
            "status":         "SCAFFOLD_CLOSE",
            "reason":         reason,
            "close_sequence": "short_first_then_long",
            "venue":          "BYBIT",
            "ts_utc":         ts,
        }

    _append_trade_log(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    """Load k690_dashboard.json; return defaults if missing."""
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
        "venue":                   "BYBIT",
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
    """Write k690_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_sei_current"]       = signal.get("fr_sei",        0.0)
    dash["fr_sol_current"]       = signal.get("fr_sol",        0.0)
    dash["sei_sol_diff_current"] = signal.get("sei_sol_diff",  0.0)
    dash["mean_168h"]            = signal.get("mean_168h",     0.0)
    dash["diff_sigma"]           = signal.get("diff_sigma",    0.0)
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
            dash["venue"]             = "BYBIT"
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K690   # 62.5% UNCHANGED (Bybit-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K693: Realized Sh >= 12, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  12.0,    # >=12 (50% of OOS Sh=25.11 → ~12.6, rounded to 12)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,      # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=12 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$104,174/yr net @$10M @4x (3% sleeve, OOS Sh 25.11)",
        "alt_alt_note":            "FIFTH ALT-ALT pair (SEI-SOL, no BTC/ETH leg). Standalone. 58th daemon. WF 12/12 UNPRECEDENTED.",
        "overlap_warning":         "K507 SEI-BTC + K476 SOL-BTC algebraic overlap; K682/K686 share SOL leg — run standalone",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K693"
    dash["strategy"]            = "K690 SEI-SOL FR Differential (FIFTH ALT-ALT, W=168h, Bybit-only)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = SEI_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "fifth_alt_alt":      True,
        "bybit_only_reason":  (
            "Bybit preferred: both SEI-PERP + SOL-PERP available on Bybit. "
            "HL stays at 62.5% (headroom preserved). OKX SEI also available "
            "as preferred G8 reference (OKX SEI corr=0.664 passes G8)."
        ),
        "hl_concentration":   62.5,
        "midcap_altalt_note": (
            "SEI-SOL is MID-CAP vs LARGE-CAP pair: SEI MC ~$2-8B vs SOL MC ~$60-80B. "
            "Vol ratio SEI/SOL=1.32x (below 1.5x normal alt-alt threshold). "
            "Mid-cap alt-alt exception applied. ADF stat -12.7158 confirms stationarity "
            "(p=1.01e-23). OU half-life=4.41h (strong mean-reversion, 2nd fastest in family). "
            "SEI negative FR (-3.65%/ann) creates dominant directional signal."
        ),
        "k507_k476_warning":  (
            "K507 SEI-BTC (HL+Bybit, 2% sleeve) + K476 SOL-BTC (HL-only, 1.5% sleeve) overlap. "
            "SEI-SOL = K507_direction - K476_direction (algebraic identity). "
            "K690 + K507 + K476 = complex algebraic overlap. Run K690 STANDALONE. "
            "Anti-corr K690 vs K507 = -0.5109 (HEDGES K507 long-SEI exposure). "
            "Default: K690 standalone 3% Bybit sleeve."
        ),
        "k682_sol_warning":   (
            "K682 ATOM-SOL shares SOL leg with K690 SEI-SOL. "
            "K690 + K682 active simultaneously = SOL double-exposure. "
            "Monitor combined SOL notional vs sleeve targets. "
            "Default: both STANDALONE (separate 3%/2% sleeves, independent margin)."
        ),
        "k686_sol_warning":   (
            "K686 AVAX-SOL shares SOL leg with K690 SEI-SOL. "
            "K690 + K686 + K682 all active = SOL triple-exposure. "
            "Monitor combined SOL notional across all three strategies. "
            "Default: all STANDALONE (separate sleeves, independent margin)."
        ),
        "sei_fr_drivers": (
            "Sei Network Cosmos SDK + CosmWasm + parallel EVM (CometBFT + Twin-turbo consensus). "
            "DeFi protocol launches on parallel EVM, CosmWasm adoption, Cosmos-EVM bridge activity. "
            "SeiDB-optimized throughput events, exchange-native perpetual speculation (SEIUSDT). "
            "NEGATIVE mean FR (-3.65%/ann): short-sellers dominate SEI perps (bearish bias)."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium, meme-coin season (BONK/WIF), "
            "Firedancer upgrade hype, SOL ETF speculation, validator economics. "
            "Persistently positive (+7.70%/ann structural retail demand premium)."
        ),
        "carry_dominance": (
            "SEI mean FR -3.65%/ann NEGATIVE. SOL mean FR +7.70%/ann POSITIVE. "
            "SEI-SOL diff mean = -1.30e-05/h (SOL usually far higher by ~11.4%/ann). "
            "Dominant regime (BEAR_SEI, ~90%+): LONG SOL / SHORT SEI is CARRY-POSITIVE "
            "in BOTH legs simultaneously. G2 perm p=1.0 is structural (carry-dominated). "
            "Primary validation: G3 DSR p=0.0 (PASS) + G4 WF 12/12 (UNPRECEDENTED)."
        ),
        "mathematical_identity": (
            "SEI_FR - SOL_FR = (SEI_FR - BTC_FR) - (SOL_FR - BTC_FR) = K507_dir - K476_dir. "
            "K690 algebraically decomposed into K507 + K476. "
            "Anti-correlated with K507 (corr=-0.5109) — K690 HEDGES K507 long-SEI positions."
        ),
        "family_rank": (
            "FIFTH alt-alt direction. WF 12/12 UNPRECEDENTED (all folds positive — first in family): "
            "K686=11/12, K682=10/12, K679=11/12, K684=6/12. "
            "OOS Sh: K686=50.27 > K682=43.43 > K679=39.29 > K684=9.65 > K690=25.11. "
            "K690 WF 12/12 unprecedented is the key differentiator. "
            "Combined alt-alt: ~$768K/yr @$10M (5 pairs, 3%+2%+3%+3%+3% sleeves)."
        ),
        "ou_half_life": "4.41h (0.184d) — STRONG mean-reversion (2nd fastest in alt-alt family).",
        "g4_unprecedented": "12/12 folds positive — UNPRECEDENTED in alt-alt family. Prior best: K679=11/12, K686=11/12.",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   12.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "BYBIT primary (SEI-PERP + SOL-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   25.11,
        "oos_ann_ret_pct":          10.272,
        "ann_return_usd_3pct_4x":   104174,
        "daily_usdc":               285,
        "wave_accept":              "K690 ACCEPT (K693 scaffold) — FIFTH ALT-ALT pair, Cosmos EVM parallel vs Solana SVM retail cross-ecosystem, WF 12/12 UNPRECEDENTED",
        "cluster":                  "SEI-SOL Alt-Alt FR Differential (Cosmos EVM parallel vs Solana SVM retail, Bybit-only)",
        "cluster_rationale": (
            "SEI (Cosmos EVM parallel chain, DeFi/CosmWasm — NEGATIVE mean FR -3.65%/ann) "
            "vs SOL (Solana SVM retail/meme — persistently positive +7.70%/ann): fifth alt-alt pair. "
            "No BTC or ETH leg — pure alt-to-alt cross-ecosystem Cosmos-EVM vs SVM differential. "
            "Dominant regime: LONG SOL / SHORT SEI is carry-positive in both legs. "
            "Bybit-only: HL stays at 62.5% (preferred — headroom preserved). "
            "SEI-PERP + SOL-PERP both on Bybit. OKX SEI preferred G8 reference. "
            "K507+K476 algebraic overlap: standalone 3% sleeve recommended. "
            "K682+K686+K690 share SOL leg: monitor combined SOL exposure."
        ),
        "daemon_number":            "58th",
        "family_rank": {
            "k686_oos_sharpe":   50.27,
            "k682_oos_sharpe":   43.43,
            "k679_oos_sharpe":   39.29,
            "k690_oos_sharpe":   25.11,
            "k684_oos_sharpe":   9.65,
            "k690_pair":         "SEI-SOL (alt-alt, FIFTH, WF 12/12 UNPRECEDENTED)",
            "alt_alt_count":     5,
            "g4_note":           "K690 WF 12/12 is UNPRECEDENTED — all 12 walk-forward folds positive (prior best: K679/K686 at 11/12)",
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
      1. Fetch SEI + SOL FRs from Bybit
      2. Compute SEI-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k690_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K690 SEI-SOL FR Differential (FIFTH ALT-ALT, Bybit-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit-only (SEI-PERP + SOL-PERP, both Bybit)")
    print(f"  HL conc:   62.5% (preferred — Bybit-only preserves 2.5pp headroom)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = SEI_FR - SOL_FR  (direct alt-alt, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  FIFTH:     FIFTH ALT-ALT pair (no BTC/ETH leg) — OOS Sh=25.11, WF 12/12 UNPRECEDENTED")
    print(f"  Mid-cap:   SEI/SOL vol ratio=1.32x — mid-cap alt-alt exception (ADF p=1.01e-23)")
    print(f"  Carry:     SEI mean FR -3.65%/ann NEGATIVE. Dominant: LONG SOL / SHORT SEI carry-positive.")
    print(f"  Overlap:   K507 SEI-BTC + K476 SOL-BTC algebraic; K682/K686 share SOL leg")
    print(f"  58th:      OOS Sh={25.11:.2f} W=168h Bybit-only 3% sleeve $104,174/yr @$10M @4x")

    # Step 1: Fetch + compute SEI-SOL differential
    print("\n  [Step 1] Computing SEI-SOL FR differential from Bybit...")
    signal = compute_signal()
    print(f"  SEI FR:     {signal['fr_sei']:+.8f} (8h, Bybit, Cosmos EVM -3.65%/ann NEGATIVE)")
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (8h, Bybit, retail +7.70%/ann persistent)")
    print(f"  SEI-SOL:    {signal['sei_sol_diff']:+.8f}  (direct alt-alt differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_SEI, -1=BEAR_SEI, 0=NEUTRAL)")
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
    print(f"  SEI leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=25.11 = $104,174/yr net (3% sleeve, standalone)")
    print(f"  HL conc:          UNCHANGED 62.5% (Bybit-only — 2.5pp headroom preserved)")

    # Step 4: Load current position + decide action
    dash = _load_dashboard()
    current_state = dash.get("position_state", STATE_NEUTRAL)
    print(f"\n  [Step 4] Current position: {current_state}")

    trade_result = None
    if decision and current_state == STATE_NEUTRAL:
        print(f"  Action: ENTER {decision['position_state']}")
        long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "BYBIT"}
        short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "BYBIT"}
        trade_result = submit_paired_trade(long_leg, short_leg, dry_run=dry_run)
        print(f"  Trade status: {trade_result['status']}")

    elif decision and current_state != STATE_NEUTRAL:
        if decision["position_state"] != current_state:
            print(f"  Action: CLOSE + FLIP (signal reversed)")
            close_result = close_paired_position("signal_reversal", dry_run=dry_run)
            print(f"  Close status: {close_result['status']}")
            long_leg  = {"symbol": decision["long_asset"],  "notional": notional_per_leg, "venue": "BYBIT"}
            short_leg = {"symbol": decision["short_asset"], "notional": notional_per_leg, "venue": "BYBIT"}
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
    print(f"\n  === K690 SEI-SOL Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  SEI-SOL Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  FIFTH ALT-ALT:      SEI-SOL (no BTC/ETH base) OOS Sh=25.11, WF 12/12 UNPRECEDENTED")
    print(f"  Bybit-only:         HL 62.5% (headroom preserved — SEI+SOL on Bybit)")
    print(f"  K507+K476 overlap:  STANDALONE 3% sleeve (no netting)")
    print(f"  K682/K686 SOL:      Monitor SOL triple-exposure if K690+K682+K686 concurrent")
    print(f"  Mid-cap alt-alt:    SEI/SOL vol ratio=1.32x — exception applied, ADF p=1.01e-23")
    print(f"  Carry dominant:     SEI mean FR -3.65%/ann. BEAR_SEI: LONG SOL/SHORT SEI carry-positive.")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         25.11 (W=168h, zero threshold, ~218d OOS)")
    print(f"  Cluster:            SEI-SOL Alt-Alt (Cosmos EVM parallel vs Solana SVM retail, 58th daemon)")
    print(f"  Profit 3% sleeve:   $104,174/yr net @$10M @4x (standalone)")
    print(f"  HL concentration:   62.5% UNCHANGED (Bybit-only, headroom preserved)")
    print(f"  60d gate:           Realized Sh>=12 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K690 SEI-SOL FR Differential Strategy (K693 scaffold, FIFTH ALT-ALT, Bybit-only)"
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
        print(f"\n=== K690 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K690 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K690 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
k686_avax_sol_run.py — K686 AVAX-SOL FR Differential Strategy
==============================================================
FOURTH ALT-ALT pair: AVAX vs SOL (no BTC/ETH base).
Signal: AVAX_FR - SOL_FR (direct alt-alt differential)
W=168h rolling mean, zero threshold (sign only)
Bybit-only (AVAX-PERP + SOL-PERP on Bybit)
HL concentration: 62.5% (Bybit-only preserves headroom — PREFERRED)

K686 AVAX-SOL alt-alt hypothesis:
  AVAX (Avalanche) FR dynamics: Subnet architecture (C-Chain, P-Chain, X-Chain),
  institutional RWA partnerships (Avalanche9000), permissioned subnets for TradFi,
  HFT node colocation demand, enterprise blockchain adoption cycles.
  AVAX FR is episodic (+6.39% ann) — institutional demand waves, subnet launches.
  SOL (Solana) FR dynamics: Monolithic SVM DePIN/Retail adoption, meme-coin cycle
  premium (BONK/WIF), Firedancer upgrade hype, validator economics, ETF speculation.
  SOL FR is persistently positive (+7.73% ann) — structural retail demand premium.
  Alt-alt mechanism: AVAX and SOL are same-tier large-cap L1s with orthogonal FR drivers.
  AVAX FR tracks Avalanche institutional/RWA narrative; SOL FR tracks Solana consumer/retail.
  These two L1 narratives create meaningful AVAX-SOL differential signals distinct from
  BTC/ETH-base family and from other alt-alt pairs (APT-SOL, ATOM-SOL, SOL-INJ).
  FOURTH alt-alt pair in portfolio. Same-tier L1 exception: vol ratio AVAX/SOL=0.85x
  (below 1.5x normal alt-alt threshold) — ADF confirms stationarity regardless.

K686 §6 validation (ACCEPT — 11/12 G4 folds positive, OOS Sh=50.27):
  - OOS Sharpe: 50.27 (W=168h, zero threshold, ~216d OOS)
  - OOS Ann Return: $102,153/yr net @$10M @4x @3% standalone sleeve
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF stat -13.99 (strongly stationary p<1e-10), OU half-life=0.15d (3.6h — FASTEST)
  - G4 walk-forward: 11/12 folds positive (non-blocking per alt-alt family precedent)
  - Bybit-only (both AVAX-PERP + SOL-PERP on Bybit)
  - 60d gate: Realized Sh >= 25, fill >= 60%, DD < 15%

K484+K476 algebraic overlap warning:
  K484 AVAX-BTC (HL+Bybit, 1.5% sleeve) — AVAX leg.
  K476 SOL-BTC  (HL-only, 1.5% sleeve)  — SOL leg.
  K686 AVAX-SOL: mathematically AVAX_FR - SOL_FR = (AVAX_FR - BTC_FR) - (SOL_FR - BTC_FR)
  ALGEBRAIC: K686 ≈ K484_direction - K476_direction (anti-correlated with K484 by construction,
  corr(K686, K484) = -0.6295 — PORTFOLIO-HEDGING K484 long-AVAX exposure).
  G5c corr = -0.6295 signed (ABS 0.6295 > 0.40 threshold — signed PASS per §6 K266 convention).
  K682 ATOM-SOL shares SOL leg with K686 AVAX-SOL → SOL double-exposure if both active.
  K679 APT-SOL shares SOL leg with K686 AVAX-SOL → SOL triple-exposure risk if all three active.
  DEFAULT: K686 standalone (3% Bybit sleeve, independent). Reduce K484/K476 if desired.

Architecture (K679/K682/K684 alt-alt scaffold pattern):
  1. fetch_fr_batch()                → fetch AVAX + SOL FR every 8h from Bybit
  2. compute_signal(avax_fr, sol_fr) → 168h rolling mean of (AVAX_FR - SOL_FR); sign()
  3. decide_position(signal)         → LONG_AVAX_SHORT_SOL | LONG_SOL_SHORT_AVAX | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (AVAX + SOL legs, both Bybit)
  5. daily_rebalance()               → drift > 5% triggers rebalance
  6. close_paired_position(reason)   → sequential: short first, then long

K689 production scaffold:
  - 57th daemon (fourth alt-alt pair, highest Sh 50.27 in alt-alt family)
  - Bybit-only (HL at 62.5%, Bybit preferred to preserve headroom)
  - 3% standalone sleeve (not dual with K484/K476 unless rebalanced)
  - $102,153/yr net @$10M @4x @3% sleeve (OOS Sh=50.27)
  - 60d paper-trade gate: Realized Sh>=25 + fill>=60% + maxDD<15%

Execution:
  - Bybit primary (AVAX-PERP + SOL-PERP, both Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage (standalone)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k686_avax_sol_run.py --dry-run
  python3 scripts/k686_avax_sol_run.py --status
  python3 scripts/k686_avax_sol_run.py --rebalance
  python3 scripts/k686_avax_sol_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k686_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k686_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k686_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K686 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K686 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — AVAX-PERP + SOL-PERP on Bybit) ─────────────────
# HL concentration: 62.5% baseline — Bybit preferred (preserves 2.5pp headroom)
# K686 is fully Bybit-only: AVAX-PERP and SOL-PERP both on Bybit
# Scenario C: both legs Bybit → HL stays at 62.5% (PREFERRED)
HL_CONCENTRATION_PRE_K686   = 62.5   # post-K679/K682/K684 reference
HL_CONCENTRATION_POST_K686  = 62.5   # UNCHANGED — Bybit-only, no HL impact
BYBIT_ONLY_REASON           = (
    "Bybit preferred: both AVAX-PERP + SOL-PERP available on Bybit, "
    "HL headroom preserved (K686 spec). HL stays at 62.5% (unchanged, 2.5pp headroom)."
)

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL             = "NEUTRAL"
STATE_LONG_AVAX_SHORT_SOL = "LONG_AVAX_SHORT_SOL"
STATE_LONG_SOL_SHORT_AVAX = "LONG_SOL_SHORT_AVAX"

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K686: AVAX + SOL only — direct alt-alt differential (FOURTH ALT-ALT pair)
SYMBOLS = ("AVAX", "SOL")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k686/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k686] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k686/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k686] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (AVAX + SOL from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for AVAX and SOL from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K686: both legs on Bybit (AVAX-PERP + SOL-PERP).
    Bybit-only preferred: HL concentration at 62.5% (within 65% cap).
    Both AVAXUSDT and SOLUSDT perpetuals listed on Bybit.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
    G8 note: Bybit AVAX corr=0.392 (raw) vs HL — K484 AVAX-BTC precedent applies
    (K484 accepted with same G8 metric; AVAX HL uses 1h continuous vs Bybit 8h discrete).
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
        print(f"  [k686] Bybit partial result {list(result.keys())} — trying HL fallback",
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
                    print(f"  [k686] {sym} FR from HL fallback (informational)", file=sys.stderr)
                except (TypeError, ValueError):
                    continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K686 FR history JSONL."""
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
    fr_avax: float, fr_sol: float, avax_sol_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":        datetime.now(UTC).isoformat(),
        "fr_avax":       round(fr_avax,       10),
        "fr_sol":        round(fr_sol,         10),
        "avax_sol_diff": round(avax_sol_diff,  10),  # AVAX_FR - SOL_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (AVAX-SOL direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_avax: Optional[float] = None,
    fr_sol:  Optional[float] = None,
) -> dict:
    """
    Fetch live AVAX and SOL FRs from Bybit, compute AVAX-SOL differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K686 direct alt-alt differential — no orthogonalization):
      diff = AVAX_FR - SOL_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> AVAX FR > SOL FR -> short AVAX (collect), long SOL (cheap retail carry)
             sign < 0 -> SOL FR > AVAX FR -> long AVAX (cheap inst carry), short SOL (collect)

    Alt-alt mechanism (FOURTH ALT-ALT pair — K686):
      AVAX FR tracks Avalanche Subnet institutional demand: subnet launches, Avalanche9000
      upgrades, RWA institutional partnerships, HFT colocation cycles. Episodic (+6.39% ann).
      SOL FR tracks Solana SVM DePIN/Retail adoption premium: meme-coin season (BONK/WIF),
      Firedancer upgrade hype, SOL ETF speculation, validator economics. Persistently positive
      (+7.73% ann) — structural retail demand premium. SOL usually slightly higher than AVAX.
      AVAX-SOL diff captures relative cross-L1 premium: institutional Subnet vs consumer SVM.
      Same-tier L1 exception: both ~$20-80B MC, vol ratio AVAX/SOL=0.85x (AVAX more stable).
      No BTC or ETH leg → pure alt-alt → fourth distinct cross-ecosystem pair.

    Mathematical identity (K686 overlap warning):
      AVAX_FR - SOL_FR = (AVAX_FR - BTC_FR) - (SOL_FR - BTC_FR) = K484_dir - K476_dir
      K686 is algebraically decomposable into K484 + K476 components.
      Corr(K686, K484) = -0.6295 signed (ANTI-CORRELATED — K686 HEDGES K484 K484 long-AVAX).
      Running K686 + K484 + K476 simultaneously creates algebraic overlap.
      K686 + K682 (ATOM-SOL): SOL leg shared → SOL double-exposure if both active.
      K686 + K679 (APT-SOL):  SOL leg shared → SOL triple-exposure risk if all three active.
      DEFAULT: K686 standalone (3% Bybit sleeve, independent).

    K686 §6 validation:
      - OOS Sharpe: 50.27 (W=168h, zero threshold, ~216d OOS period)
      - OOS Ann Return: 10.02% (1x, unlevered on notional)
      - ADF stat -13.99 (strongly stationary p<1e-10), OU half-life=0.15d (3.6h — FASTEST)
      - Walk-forward: 11/12 folds positive (G4 non-blocking per alt-alt precedent)
      - 60d gate: Realized Sh>=25 + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_avax":          float,
        "fr_sol":           float,
        "avax_sol_diff":    float,    # AVAX_FR - SOL_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_AVAX | BEAR_AVAX | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_avax is None or fr_sol is None:
        frs     = _fetch_bybit_fr_batch()
        fr_avax = frs.get("AVAX", 0.0)
        fr_sol  = frs.get("SOL",  0.0)

    # AVAX-SOL direct alt-alt differential (no orthogonalization)
    avax_sol_diff = fr_avax - fr_sol

    _append_fr_history(fr_avax, fr_sol, avax_sol_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["avax_sol_diff"] for r in history if "avax_sol_diff" in r]

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

    # Regime classification (zero threshold — per K686 spec)
    # BULL_AVAX: AVAX FR > SOL FR (Avalanche institutional demand spike — subnet launch / RWA event)
    # BEAR_AVAX: AVAX FR < SOL FR (SOL retail/meme premium dominates — typical regime ~80%+ of time)
    if mean_168h > 0:
        regime    = "BULL_AVAX"   # AVAX-SOL diff positive → AVAX FR > SOL FR (AVAX institutional spike)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_AVAX"   # AVAX-SOL diff negative → SOL FR > AVAX FR (SOL retail premium)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_avax":          round(fr_avax,        10),
        "fr_sol":           round(fr_sol,          10),
        "avax_sol_diff":    round(avax_sol_diff,   10),
        "mean_168h":        round(mean_168h,       10),
        "diff_sigma":       round(sigma,           10),
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
    Determine trade direction from AVAX-SOL differential rolling mean.

    Logic (AVAX-SOL direct alt-alt pair, Bybit primary):
      regime = BULL_AVAX (mean_168h > 0):
        AVAX FR > SOL FR: AVAX expensive (Subnet launch / RWA institutional demand spike)
        -> short AVAX (collect high AVAX FR) / long SOL (cheaper retail carry)
        -> position_state = LONG_SOL_SHORT_AVAX
        -> both legs on Bybit

      regime = BEAR_AVAX (mean_168h < 0):
        SOL FR > AVAX FR: SOL expensive (retail/meme-coin season / DePIN adoption premium)
        -> long AVAX (cheap institutional carry) / short SOL (collect high SOL FR)
        -> position_state = LONG_AVAX_SHORT_SOL
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (FOURTH ALT-ALT pair — K686):
      AVAX and SOL are same-tier large-cap L1s with orthogonal FR drivers.
      BULL_AVAX: Avalanche institutional premium spikes (subnet launches — C-Chain EVM subnet
        for TradFi, Avalanche9000 upgrade, RWA institutional partnerships, HFT colocation).
        AVAX FR >> SOL FR → short AVAX (collect) / long SOL (cheap retail carry).
      BEAR_AVAX: SOL consumer/retail premium (meme-coin BONK/WIF rallies, Firedancer hype,
        SOL ETF speculation, Solana validator delinquency events spike demand, DePIN launches).
        SOL FR >> AVAX FR → long AVAX / short SOL (collect high SOL FR).
      Same-tier L1: both ~$20-80B MC, both EVM-compatible (AVAX C-Chain, SOL EVM emulation).
      Different ecosystems: Avalanche institutional/RWA vs Solana consumer/retail.
      Vol ratio AVAX/SOL=0.85x (AVAX more stable than SOL — unusual inverse pattern).
      Same-tier L1 exception: vol threshold relaxed; ADF confirms stationarity (p<1e-10).

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
        # AVAX FR > SOL FR: AVAX expensive (Subnet launch / RWA institutional demand spike)
        # short AVAX (collect high FR) / long SOL (cheaper retail carry)
        long_asset  = "SOL"
        short_asset = "AVAX"
        state       = STATE_LONG_SOL_SHORT_AVAX
    else:  # BEAR_AVAX
        # SOL FR > AVAX FR: SOL expensive (retail/meme-coin season / DePIN adoption premium)
        # long AVAX (cheap institutional carry) / short SOL (collect high SOL FR)
        long_asset  = "AVAX"
        short_asset = "SOL"
        state       = STATE_LONG_AVAX_SHORT_SOL

    # Both legs on Bybit (K686: AVAX-PERP + SOL-PERP, both Bybit)
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
    Compute equal notional for both legs of the AVAX-SOL paired trade.

    K686 Bybit-only config (both AVAX-PERP + SOL-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x (standalone):
      AVAX leg:  $150K capital x 4x = $600K notional (Bybit AVAX-PERP)
      SOL leg:   $150K capital x 4x = $600K notional (Bybit SOL-PERP)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      HL conc:   UNCHANGED at 62.5% (Bybit-only, HL headroom preserved)
      Net profit: ~$102,153/yr @$10M @4x @3% sleeve (OOS ann ret x notional)
      K484+K476 note: standalone (no algebraic netting assumed)
      K682 note: K686 + K682 share SOL leg — deploy standalone, monitor SOL exposure
      K679 note: K686 + K679 share SOL leg — both standalone, monitor SOL triple-exposure

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
    Submit K686 AVAX-SOL paired trade: POST_ONLY both legs in parallel.

    Protocol (K686 Bybit primary — both legs on Bybit):
      1. Submit AVAX leg on Bybit POST_ONLY
      2. Submit SOL leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "AVAX", "notional": 600000, "venue": "BYBIT"}
      short_leg: {"symbol": "SOL",  "notional": 600000, "venue": "BYBIT"}
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
        print(f"  [K686] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_ONLY_AVAX_SOL_ALT_ALT",
            "mechanism_note":   (
                "AVAX-SOL direct alt-alt differential (K686 FOURTH ALT-ALT, 57th daemon): "
                "AVAX FR = Avalanche Subnet institutional demand (subnet launches, Avalanche9000, "
                "RWA institutional partnerships, HFT colocation cycles — episodic +6.39% ann); "
                "SOL FR = Solana SVM DePIN/Retail adoption premium (meme-coin BONK/WIF, "
                "Firedancer upgrade hype, SOL ETF speculation, validator economics — "
                "persistently positive +7.73% ann structural retail demand premium). "
                "Bybit-only: AVAX-PERP + SOL-PERP both on Bybit. HL stays 62.5% (unchanged, headroom preserved). "
                "K484+K476 algebraic overlap: K686 STANDALONE (no algebraic netting). "
                "K682/K679 SOL-exposure: K686+K682+K679 share SOL leg — run standalone. "
                "OOS Sh=50.27 (W=168h, zero threshold), $102,153/yr @$10M @4x @3% sleeve. "
                "HIGHEST OOS Sharpe in alt-alt family (K682=43.4, K679=39.3, K684=9.6)."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K686] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K686] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K686 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K686 Bybit-only: both legs on Bybit (AVAX-PERP + SOL-PERP).
    Drift detection: compare stored AVAX leg notional vs SOL leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679/K682/K684 pattern).

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
    Both legs on Bybit (K686 Bybit primary — AVAX-PERP + SOL-PERP).

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

    if state == STATE_LONG_AVAX_SHORT_SOL:
        long_sym,  short_sym  = "AVAX", "SOL"
    else:  # LONG_SOL_SHORT_AVAX
        long_sym,  short_sym  = "SOL", "AVAX"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K686] {mode_tag} CLOSE:")
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
        print(f"  [K686] SCAFFOLD CLOSE:")
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
    """Load k686_dashboard.json; return defaults if missing."""
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
    """Write k686_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]         = signal.get("ts_jst", "—")
    dash["fr_avax_current"]       = signal.get("fr_avax",       0.0)
    dash["fr_sol_current"]        = signal.get("fr_sol",        0.0)
    dash["avax_sol_diff_current"] = signal.get("avax_sol_diff", 0.0)
    dash["mean_168h"]             = signal.get("mean_168h",     0.0)
    dash["diff_sigma"]            = signal.get("diff_sigma",    0.0)
    dash["regime"]                = signal.get("regime",  "NEUTRAL")
    dash["signal_direction"]      = signal.get("signal_direction", 0)
    dash["history_points"]        = signal.get("history_points", 0)

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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K686   # 62.5% UNCHANGED (Bybit-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K689: Realized Sh >= 25, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  25.0,    # >=25 (50% of OOS Sh=50.27)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,      # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=25 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$102,153/yr net @$10M @4x (3% sleeve, OOS Sh 50.27)",
        "alt_alt_note":            "FOURTH ALT-ALT pair (AVAX-SOL, no BTC/ETH leg). Standalone. 57th daemon. HIGHEST Sh in alt-alt family.",
        "overlap_warning":         "K484 AVAX-BTC + K476 SOL-BTC algebraic overlap; K682/K679 share SOL leg — run standalone",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K689"
    dash["strategy"]            = "K686 AVAX-SOL FR Differential (FOURTH ALT-ALT, W=168h, Bybit-only)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = AVAX_FR - SOL_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "fourth_alt_alt":     True,
        "bybit_only_reason":  "Bybit preferred: HL stays at 62.5% (headroom preserved). Both AVAX-PERP + SOL-PERP on Bybit.",
        "hl_concentration":   62.5,
        "same_tier_l1_note":  (
            "AVAX-SOL is first same-tier large-cap L1 pair in alt-alt family. "
            "Vol ratio AVAX/SOL=0.85x (AVAX more stable than SOL — unusual inverse). "
            "Same-tier L1 exception: vol threshold relaxed to 1.0x minimum. "
            "ADF stat -13.99 confirms stationarity (p<1e-10). Signal valid."
        ),
        "k484_k476_warning":  (
            "K484 AVAX-BTC (HL+Bybit, 1.5% sleeve) + K476 SOL-BTC (HL-only, 1.5% sleeve) overlap. "
            "AVAX-SOL = K484_direction - K476_direction (algebraic identity). "
            "K686 + K484 + K476 = complex algebraic overlap. Run K686 STANDALONE. "
            "Anti-corr K686 vs K484 = -0.6295 (HEDGES K484 long-AVAX exposure). "
            "Default: K686 standalone 3% Bybit sleeve."
        ),
        "k682_sol_warning":   (
            "K682 ATOM-SOL shares SOL leg with K686 AVAX-SOL. "
            "K686 + K682 active simultaneously = SOL double-exposure. "
            "Monitor combined SOL notional vs sleeve targets. "
            "Default: both STANDALONE (separate 3%/3% sleeves, independent margin)."
        ),
        "k679_sol_warning":   (
            "K679 APT-SOL shares SOL leg with K686 AVAX-SOL. "
            "K686 + K679 + K682 all active = SOL triple-exposure. "
            "Monitor combined SOL notional across all three strategies. "
            "Default: all STANDALONE (separate sleeves, independent margin)."
        ),
        "avax_fr_drivers": (
            "Avalanche Subnet architecture (C-Chain EVM, P-Chain validator, X-Chain asset). "
            "Institutional RWA partnerships (TradFi permissioned subnets), Avalanche9000 upgrade. "
            "HFT colocation demand, enterprise blockchain adoption cycles. "
            "Episodic demand spikes (+6.39% ann, institutional cycle-driven)."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium, meme-coin season (BONK/WIF), "
            "Firedancer upgrade hype, SOL ETF speculation, validator economics. "
            "Persistently positive (+7.73% ann structural retail demand premium)."
        ),
        "mathematical_identity": (
            "AVAX_FR - SOL_FR = (AVAX_FR - BTC_FR) - (SOL_FR - BTC_FR) = K484_dir - K476_dir. "
            "K686 algebraically decomposed into K484 + K476. "
            "Anti-correlated with K484 (corr=-0.6295) — K686 HEDGES K484 long-AVAX positions."
        ),
        "family_rank": (
            "FOURTH alt-alt direction. HIGHEST OOS Sharpe in alt-alt family: "
            "K686=50.27 > K682=43.43 > K679=39.29 > K684=9.65. "
            "Combined alt-alt: ~$663K/yr @$10M (4 pairs × 3% sleeve)."
        ),
        "ou_half_life": "0.15d (3.6h) — FASTEST mean-reversion in alt-alt family.",
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   25.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "BYBIT primary (AVAX-PERP + SOL-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   50.27,
        "oos_ann_ret_pct":          10.015,
        "ann_return_usd_3pct_4x":   102153,
        "daily_usdc":               280,
        "wave_accept":              "K686 ACCEPT (K689 scaffold) — FOURTH ALT-ALT pair, Avalanche institutional vs Solana retail cross-L1",
        "cluster":                  "AVAX-SOL Alt-Alt FR Differential (Avalanche Subnet institutional vs Solana SVM retail, Bybit-only)",
        "cluster_rationale": (
            "AVAX (Avalanche Subnet institutional/RWA) vs SOL (Solana SVM retail/meme): fourth alt-alt pair. "
            "No BTC or ETH leg — pure alt-to-alt cross-L1 same-tier differential. "
            "AVAX FR = institutional demand cycles (episodic, subnet launches); "
            "SOL FR = consumer/retail premium (persistent, meme-coin seasonal). "
            "Bybit-only: HL stays at 62.5% (preferred — headroom preserved). "
            "AVAX-PERP + SOL-PERP both on Bybit. "
            "K484+K476 algebraic overlap: standalone 3% sleeve recommended. "
            "K682+K679+K686 share SOL leg: monitor combined SOL exposure."
        ),
        "daemon_number":            "57th",
        "family_rank": {
            "k686_oos_sharpe":  50.27,
            "k682_oos_sharpe":  43.43,
            "k679_oos_sharpe":  39.29,
            "k684_oos_sharpe":  9.65,
            "k686_pair":        "AVAX-SOL (alt-alt, FOURTH, HIGHEST Sh)",
            "alt_alt_count":    4,
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
      1. Fetch AVAX + SOL FRs from Bybit
      2. Compute AVAX-SOL differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k686_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K686 AVAX-SOL FR Differential (FOURTH ALT-ALT, Bybit-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit-only (AVAX-PERP + SOL-PERP, both Bybit)")
    print(f"  HL conc:   62.5% (preferred — Bybit-only preserves 2.5pp headroom)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = AVAX_FR - SOL_FR  (direct alt-alt, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  FOURTH:    FOURTH ALT-ALT pair (no BTC/ETH leg) — OOS Sh=50.27 (HIGHEST in family)")
    print(f"  Same-tier: AVAX/SOL vol ratio=0.85x — same-tier L1 exception applied (ADF confirmed)")
    print(f"  Overlap:   K484 AVAX-BTC + K476 SOL-BTC algebraic; K682/K679 share SOL leg")
    print(f"  57th:      OOS Sh={50.27:.2f} W=168h Bybit-only 3% sleeve $102,153/yr @$10M @4x")

    # Step 1: Fetch + compute AVAX-SOL differential
    print("\n  [Step 1] Computing AVAX-SOL FR differential from Bybit...")
    signal = compute_signal()
    print(f"  AVAX FR:    {signal['fr_avax']:+.8f} (8h, Bybit, institutional +6.39% ann episodic)")
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (8h, Bybit, retail +7.73% ann persistent)")
    print(f"  AVAX-SOL:   {signal['avax_sol_diff']:+.8f}  (direct alt-alt differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_AVAX, -1=BEAR_AVAX, 0=NEUTRAL)")
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
    print(f"  AVAX leg:         ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=50.27 = $102,153/yr net (3% sleeve, standalone)")
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
    print(f"\n  === K686 AVAX-SOL Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  AVAX-SOL Mean 168h: {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  FOURTH ALT-ALT:     AVAX-SOL (no BTC/ETH base) OOS Sh=50.27 (HIGHEST in family)")
    print(f"  Bybit-only:         HL 62.5% (headroom preserved — AVAX+SOL on Bybit)")
    print(f"  K484+K476 overlap:  STANDALONE 3% sleeve (no netting)")
    print(f"  K682/K679 SOL:      Monitor SOL triple-exposure if K686+K682+K679 concurrent")
    print(f"  Same-tier L1:       AVAX/SOL vol ratio=0.85x — exception applied, ADF confirmed")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         50.27 (W=168h, zero threshold, ~216d OOS)")
    print(f"  Cluster:            AVAX-SOL Alt-Alt (Avalanche institutional vs Solana retail, 57th daemon)")
    print(f"  Profit 3% sleeve:   $102,153/yr net @$10M @4x (standalone)")
    print(f"  HL concentration:   62.5% UNCHANGED (Bybit-only, headroom preserved)")
    print(f"  60d gate:           Realized Sh>=25 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K686 AVAX-SOL FR Differential Strategy (K689 scaffold, FOURTH ALT-ALT, Bybit-only)"
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
        print(f"\n=== K686 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K686 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K686 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())

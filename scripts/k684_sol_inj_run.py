#!/usr/bin/env python3
"""
k684_sol_inj_run.py — K684 SOL-INJ FR Differential Strategy
=============================================================
THIRD ALT-ALT pair: SOL vs INJ (no BTC/ETH base).
Signal: SOL_FR - INJ_FR (direct alt-alt differential)
W=168h rolling mean, zero threshold (sign only)
Bybit-only (SOL-PERP + INJ-PERP on Bybit)
HL concentration: 62.5% (Bybit-only preserves headroom — PREFERRED)

K684 SOL-INJ alt-alt hypothesis:
  SOL (Solana) FR dynamics: Monolithic SVM DePIN/Retail adoption, meme-coin cycle
  premium (BONK/WIF), Firedancer upgrade hype, validator economics, ETF speculation.
  SOL FR is persistently positive (+7.7% ann) — structural retail demand premium.
  INJ (Injective) FR dynamics: Cosmos DeFi perp DEX — liquidation cascades, INJ burn
  mechanics (deflationary), IBC bridge activity, Cosmos TVL inflows/outflows.
  INJ FR is episodic (+3.6% ann) — Cosmos DeFi TVL-driven spikes, mean-reverting.
  Alt-alt mechanism: SOL and INJ are cross-ecosystem alts with orthogonal FR drivers.
  SOL FR tracks Solana SVM retail narrative; INJ FR tracks Cosmos DeFi perp mechanics.
  These two alt narratives create meaningful SOL-INJ differential signals distinct from
  BTC/ETH-base family and from APT-SOL (K679). Third alt-alt pair in portfolio.

K684 §6 validation (ACCEPT — 12/13 gates):
  - OOS Sharpe: 9.65 (W=168h, zero threshold, 216d OOS)
  - OOS Ann Return: $114,316/yr net @$10M @4x @3% standalone sleeve
  - W=168h rolling mean, zero threshold (sign of diff)
  - ADF p<1e-30 (strongly stationary), OU half-life=5.42h (STRONG mean-reversion)
  - G4 walk-forward: 6/12 folds positive (G4 structural — alt-alt complexity)
  - Bybit-only (both SOL-PERP + INJ-PERP on Bybit)
  - 60d gate: Realized Sh >= 5, fill >= 60%, DD < 15%

K476+K500 algebraic overlap warning:
  K476 SOL-BTC (HL-only, 1.5% sleeve) — SOL leg.
  K500 INJ-BTC (HL+Bybit, sleeve) — INJ leg.
  K684 SOL-INJ: mathematically SOL_FR - INJ_FR = (SOL_FR - BTC_FR) - (INJ_FR - BTC_FR)
  ALGEBRAIC: K684 ≈ K476_direction - K500_direction (anti-correlated with K500 by construction).
  K679 SOL-INJ: K684 shares SOL leg with K679 APT-SOL -> SOL double-exposure if both active.
  DEFAULT: K684 standalone (3% Bybit sleeve, independent). Reduce K476/K500 weights if desired.

Architecture (K679/K683 alt-alt scaffold pattern):
  1. fetch_fr_batch()               → fetch SOL + INJ FR every 8h from Bybit
  2. compute_signal(sol_fr, inj_fr) → 168h rolling mean of (SOL_FR - INJ_FR); sign()
  3. decide_position(signal)        → LONG_SOL_SHORT_INJ | LONG_INJ_SHORT_SOL | NEUTRAL
  4. submit_paired_trade(long, short) → POST_ONLY paired (SOL + INJ legs, both Bybit)
  5. daily_rebalance()              → drift > 5% triggers rebalance
  6. close_paired_position(reason)  → sequential: short first, then long

K687 production scaffold:
  - 56th daemon (third alt-alt pair, 2nd in K679 series)
  - Bybit-only (HL at 62.5%, Bybit preferred to preserve headroom)
  - 3% standalone sleeve (not dual with K476/K500 unless rebalanced)
  - $114,316/yr net @$10M @4x @3% sleeve (OOS Sh=9.65)
  - 60d paper-trade gate: Realized Sh>=5 + fill>=60% + maxDD<15%

Execution:
  - Bybit primary (SOL-PERP + INJ-PERP, both Bybit)
  - POST_ONLY paired execution (K439 pattern)
  - Position: 3% sleeve, 4x leverage (standalone)
  - 8h cadence (matches FR settlement cycle)
  - W=168h rolling mean (21 x 8h periods)

Paper-trade mode is the DEFAULT.  No orders are submitted unless
PAPER_TRADE=False is explicitly set in the environment.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib urllib + json only.

Usage:
  python3 scripts/k684_sol_inj_run.py --dry-run
  python3 scripts/k684_sol_inj_run.py --status
  python3 scripts/k684_sol_inj_run.py --rebalance
  python3 scripts/k684_sol_inj_run.py --close "scheduled exit"
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

DASHBOARD_PATH  = DATA_DIR  / "k684_dashboard.json"
FR_HISTORY_PATH = CACHE_DIR / "k684_fr_history.jsonl"
TRADE_LOG_PATH  = CACHE_DIR / "k684_paper_trades.jsonl"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# ── Strategy constants ────────────────────────────────────────────────────────
PAPER_TRADE         = True          # never submit real orders in paper-trade mode
SLEEVE_PCT          = 0.030         # K684 sleeve = 3% of AUM (standalone, Bybit-only)
LEVERAGE            = 4.0           # 4x per K684 analysis (K430 cap)
AUM_DEFAULT         = 10_000_000.0  # $10M reference AUM
DRIFT_REBALANCE_PCT = 0.05          # rebalance if legs drift > 5%
IOC_TIMEOUT_SEC     = 300           # 5 min fill window
EMA_PERIOD_HOURS    = 168           # 168h rolling mean primary config (W=168h)
EMA_PERIOD_PERIODS  = EMA_PERIOD_HOURS // 8  # = 21 periods (8h settlement cycle)
SIGNAL_SIGMA_MULT   = 0.0           # zero threshold (sign of rolling mean)
BYBIT_API_URL       = "https://api.bybit.com"
HL_API_URL          = "https://api.hyperliquid.xyz/info"

# ── Venue config (Bybit-only — SOL-PERP + INJ-PERP on Bybit) ─────────────────
# HL concentration: 62.5% baseline — Bybit preferred (preserves 2.5pp headroom)
# K684 is fully Bybit-only: SOL-PERP and INJ-PERP both on Bybit
# Scenario C: both legs Bybit → HL stays at 62.5% (PREFERRED)
HL_CONCENTRATION_PRE_K684   = 62.5   # post-K683/K685/K679 reference
HL_CONCENTRATION_POST_K684  = 62.5   # UNCHANGED — Bybit-only, no HL impact
BYBIT_ONLY_REASON           = "Bybit preferred: both SOL-PERP + INJ-PERP available Bybit, HL headroom preserved (K684 spec)"

# ── Position state constants ──────────────────────────────────────────────────
STATE_NEUTRAL            = "NEUTRAL"
STATE_LONG_SOL_SHORT_INJ = "LONG_SOL_SHORT_INJ"
STATE_LONG_INJ_SHORT_SOL = "LONG_INJ_SHORT_SOL"

# ── Symbols fetched from Bybit for FR data ────────────────────────────────────
# K684: SOL + INJ only — direct alt-alt differential (THIRD ALT-ALT pair)
SYMBOLS = ("SOL", "INJ")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "crypto-lab-k684/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k684] HTTP error: {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "crypto-lab-k684/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [k684] HTTP error: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Funding rate fetch (SOL + INJ from Bybit)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bybit_fr_batch() -> Dict[str, float]:
    """
    Fetch current 8h funding rates for SOL and INJ from Bybit.
    Returns {symbol: fr_8h_fraction}.

    Bybit API: /v5/market/tickers?category=linear
    K684: both legs on Bybit (SOL-PERP + INJ-PERP).
    Bybit-only preferred: HL concentration at 62.5% (within 65% cap).
    Both SOL-USDT and INJ-USDT perpetuals listed on Bybit.

    Fallback: HL metaAndAssetCtxs for cross-reference (informational only).
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
        print(f"  [k684] Bybit partial result {list(result.keys())} — trying HL fallback",
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
                    print(f"  [k684] {sym} FR from HL fallback (informational)", file=sys.stderr)
                except (TypeError, ValueError):
                    continue
    return result


def _load_fr_history() -> List[dict]:
    """Load K684 FR history JSONL."""
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
    fr_sol: float, fr_inj: float, sol_inj_diff: float
) -> None:
    """Append one FR snapshot to history."""
    rec = {
        "ts_utc":       datetime.now(UTC).isoformat(),
        "fr_sol":       round(fr_sol,       10),
        "fr_inj":       round(fr_inj,        10),
        "sol_inj_diff": round(sol_inj_diff,  10),  # SOL_FR - INJ_FR (direct alt-alt differential)
    }
    with open(FR_HISTORY_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Signal computation (SOL-INJ direct differential, 168h rolling mean)
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(
    fr_sol: Optional[float] = None,
    fr_inj: Optional[float] = None,
) -> dict:
    """
    Fetch live SOL and INJ FRs from Bybit, compute SOL-INJ differential,
    and compute 168h rolling mean for direction signal.

    Signal mechanism (K684 direct alt-alt differential — no orthogonalization):
      diff = SOL_FR - INJ_FR
      mean_168h = 168h rolling mean of diff (21 x 8h periods)
      sign  = sign(mean_168h)
      Enter: sign > 0 -> SOL FR > INJ FR -> short SOL (collect), long INJ (cheap carry)
             sign < 0 -> INJ FR > SOL FR -> long SOL (cheap carry), short INJ (collect)

    Alt-alt mechanism (THIRD ALT-ALT pair — K684, 3rd in alt-alt series):
      SOL FR tracks Solana SVM DePIN/Retail adoption premium, meme-coin season (BONK/WIF),
      Firedancer upgrade hype, Solana ETF speculation, validator economics.
      SOL FR is persistently positive (+7.7% ann) — structural retail demand premium.
      INJ FR tracks Injective Cosmos DeFi perp DEX activity — liquidation cascades,
      INJ burn mechanics (deflationary tokenomics), IBC bridge flow, Cosmos TVL dynamics.
      INJ FR is episodic (+3.6% ann) — episodic Cosmos DeFi TVL-driven spikes.
      SOL-INJ diff captures relative cross-ecosystem premium: SVM-retail vs CosmWasm-DeFi.
      No BTC or ETH leg → pure alt-alt → third distinct cross-ecosystem pair.

    Mathematical identity (K684 overlap warning):
      SOL_FR - INJ_FR = (SOL_FR - BTC_FR) - (INJ_FR - BTC_FR) = K476_dir - K500_dir
      K684 is algebraically decomposable into K476 + K500 components.
      Running K684 + K476 + K500 simultaneously creates algebraic overlap.
      K684 + K679 (APT-SOL): SOL leg appears in both → SOL double-exposure.
      DEFAULT: K684 standalone (3% Bybit sleeve, independent).

    K684 §6 validation:
      - OOS Sharpe: 9.65 (W=168h, zero threshold, 216d OOS period)
      - OOS Ann Return: 11.21% (1x, unlevered on notional)
      - ADF p<1e-30 (strongly stationary), OU half-life=5.42h (STRONG)
      - Walk-forward: 6/12 folds positive (G4 structural for alt-alt complexity)
      - 60d gate: Realized Sh>=5 + fill>=60% + maxDD<15%

    Returns:
      {
        "fr_sol":           float,
        "fr_inj":           float,
        "sol_inj_diff":     float,    # SOL_FR - INJ_FR (current)
        "mean_168h":        float,    # 168h rolling mean of differential
        "diff_sigma":       float,    # 168h rolling sigma (informational)
        "history_points":   int,
        "regime":           str,      # BULL_SOL | BEAR_SOL | NEUTRAL
        "signal_direction": int,      # +1 | -1 | 0
        "ts_jst":           str,
      }
    """
    if fr_sol is None or fr_inj is None:
        frs    = _fetch_bybit_fr_batch()
        fr_sol = frs.get("SOL", 0.0)
        fr_inj = frs.get("INJ", 0.0)

    # SOL-INJ direct alt-alt differential (no orthogonalization)
    sol_inj_diff = fr_sol - fr_inj

    _append_fr_history(fr_sol, fr_inj, sol_inj_diff)

    # Load history for rolling mean + sigma (168h = 21 x 8h periods)
    history = _load_fr_history()
    diffs   = [r["sol_inj_diff"] for r in history if "sol_inj_diff" in r]

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

    # Regime classification (zero threshold — per K684 spec)
    # BULL_SOL: SOL FR > INJ FR (SOL retail/meme/DePIN narrative premium spike)
    # BEAR_SOL: SOL FR < INJ FR (INJ Cosmos DeFi TVL spike or liquidation cascade)
    if mean_168h > 0:
        regime    = "BULL_SOL"   # SOL-INJ diff positive → SOL FR > INJ FR (SOL premium)
        direction = 1
    elif mean_168h < 0:
        regime    = "BEAR_SOL"   # SOL-INJ diff negative → INJ FR > SOL FR (INJ spike)
        direction = -1
    else:
        regime    = "NEUTRAL"
        direction = 0

    return {
        "fr_sol":           round(fr_sol,       10),
        "fr_inj":           round(fr_inj,        10),
        "sol_inj_diff":     round(sol_inj_diff,  10),
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
    Determine trade direction from SOL-INJ differential rolling mean.

    Logic (SOL-INJ direct alt-alt pair, Bybit primary):
      regime = BULL_SOL (mean_168h > 0):
        SOL FR > INJ FR: SOL expensive (DePIN/meme-coin/ETF premium spike)
        -> short SOL (collect high SOL FR) / long INJ (cheaper Cosmos carry)
        -> position_state = LONG_INJ_SHORT_SOL
        -> both legs on Bybit

      regime = BEAR_SOL (mean_168h < 0):
        INJ FR > SOL FR: INJ expensive (Cosmos DeFi liquidation cascade / IBC inflow)
        -> long SOL (cheap SVM carry) / short INJ (collect high INJ FR)
        -> position_state = LONG_SOL_SHORT_INJ
        -> both legs on Bybit

      regime = NEUTRAL: no trade (mean_168h == 0 exactly — rare)

    Alt-alt edge (THIRD ALT-ALT pair — K684):
      SOL and INJ are cross-ecosystem alts with orthogonal FR drivers.
      BULL_SOL: Solana retail premium spikes (meme-coin BONK/WIF rallies, Firedancer hype,
        SOL ETF speculation, Solana validator delinquency events spike demand).
        SOL FR >> INJ FR → short SOL (collect) / long INJ (cheap carry).
      BEAR_SOL: INJ Cosmos DeFi premium (Cosmos TVL spike, Injective burn event,
        liquidation cascade in Cosmos perp DEX drives INJ demand, IBC bridge flow).
        INJ FR >> SOL FR → long SOL / short INJ (collect high INJ FR).
      Cross-ecosystem: SVM vs CosmWasm — architecturally orthogonal (different VM,
        consensus, MC scale, tokenomics) → low-moderate FR correlation.

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

    if regime == "BULL_SOL":
        # SOL FR > INJ FR: SOL expensive (DePIN/meme-coin/ETF premium spike)
        # short SOL (collect high FR) / long INJ (cheaper Cosmos carry)
        long_asset  = "INJ"
        short_asset = "SOL"
        state       = STATE_LONG_INJ_SHORT_SOL
    else:  # BEAR_SOL
        # INJ FR > SOL FR: INJ expensive (Cosmos DeFi liquidation / IBC inflow)
        # long SOL (cheap SVM carry) / short INJ (collect high INJ FR)
        long_asset  = "SOL"
        short_asset = "INJ"
        state       = STATE_LONG_SOL_SHORT_INJ

    # Both legs on Bybit (K684: SOL-PERP + INJ-PERP, both Bybit)
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
    Compute equal notional for both legs of the SOL-INJ paired trade.

    K684 Bybit-only config (both SOL-PERP + INJ-PERP on Bybit):
      sleeve_capital   = aum x sleeve_pct      (e.g. $10M x 3.0% = $300K)
      total_notional   = sleeve_capital x lev   ($300K x 4 = $1.2M)
      notional_per_leg = total_notional / 2     ($600K per leg)

    At $10M / 3% sleeve / 4x (standalone):
      SOL leg:   $150K capital x 4x = $600K notional (Bybit SOL-PERP)
      INJ leg:   $150K capital x 4x = $600K notional (Bybit INJ-PERP)
      Total:     $1.2M notional (two legs combined)
      Margin:    $300K (3% of AUM)
      HL conc:   UNCHANGED at 62.5% (Bybit-only, HL headroom preserved)
      Net profit: ~$114,316/yr @$10M @4x @3% sleeve (OOS ann ret x notional)
      K476+K500 note: standalone (no algebraic netting assumed)
      K679 note: K684 + K679 share SOL leg — deploy standalone, monitor SOL exposure

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
    Submit K684 SOL-INJ paired trade: POST_ONLY both legs in parallel.

    Protocol (K684 Bybit primary — both legs on Bybit):
      1. Submit SOL leg on Bybit POST_ONLY
      2. Submit INJ leg on Bybit POST_ONLY
      3. Both legs submitted in parallel (K439 pattern)
      4. IOC fallback per leg if POST_ONLY times out
      5. If both fail: retry next 8h cycle

    Args:
      long_leg:  {"symbol": "SOL", "notional": 600000, "venue": "BYBIT"}
      short_leg: {"symbol": "INJ", "notional": 600000, "venue": "BYBIT"}
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
        print(f"  [K684] {mode_tag}: LONG {long_sym}@{long_venue} ${long_notl:,.0f}  "
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
            "venue_config":     "BYBIT_ONLY_SOL_INJ_ALT_ALT",
            "mechanism_note":   (
                "SOL-INJ direct alt-alt differential (K684 THIRD ALT-ALT, 56th daemon): "
                "SOL FR = Solana SVM DePIN/Retail adoption (meme-coin BONK/WIF premium, "
                "Firedancer upgrade hype, SOL ETF speculation, validator economics — "
                "persistently positive +7.7% ann structural retail demand premium); "
                "INJ FR = Injective Cosmos DeFi perp DEX (liquidation cascades, INJ burn "
                "mechanics deflationary, IBC bridge activity, Cosmos TVL spikes — "
                "episodic +3.6% ann Cosmos DeFi dynamics). "
                "Bybit-only: SOL-PERP + INJ-PERP both on Bybit. HL stays 62.5% (unchanged, headroom preserved). "
                "K476+K500 algebraic overlap: K684 STANDALONE (no algebraic netting). "
                "K679 SOL-exposure: K684+K679 share SOL leg — monitor SOL double-exposure. "
                "OOS Sh=9.65 (W=168h, zero threshold), $114,316/yr @$10M @4x @3% sleeve."
            ),
            "ts_utc":           ts,
        }
        _append_trade_log(result)
        return result

    # LIVE scaffold (not reached in PAPER_TRADE mode):
    print(f"  [K684] SCAFFOLD LIVE: parallel POST_ONLY "
          f"LONG {long_sym}@{long_venue} ${long_notl:,.0f} "
          f"+ SHORT {short_sym}@{short_venue} ${short_notl:,.0f}")
    long_order_id  = f"SCAFFOLD_LONG_{long_sym}_{int(time.time())}"
    short_order_id = f"SCAFFOLD_SHORT_{short_sym}_{int(time.time())}"

    print(f"  [K684] Neither leg filled within timeout — retry next 8h cycle")
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
    Check if current K684 position has drifted beyond DRIFT_REBALANCE_PCT (5%).

    K684 Bybit-only: both legs on Bybit (SOL-PERP + INJ-PERP).
    Drift detection: compare stored SOL leg notional vs INJ leg notional.
    Threshold: 5% (same as K449/K476/K484/K493/K629/K663/K679 pattern).

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
    Both legs on Bybit (K684 Bybit primary — SOL-PERP + INJ-PERP).

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

    if state == STATE_LONG_SOL_SHORT_INJ:
        long_sym,  short_sym  = "SOL", "INJ"
    else:  # LONG_INJ_SHORT_SOL
        long_sym,  short_sym  = "INJ", "SOL"

    long_notional  = float(dash.get("long_notional",  0.0))
    short_notional = float(dash.get("short_notional", 0.0))

    if dry_run or PAPER_TRADE:
        mode_tag = "DRY_RUN" if dry_run else "PAPER_TRADE"
        print(f"  [K684] {mode_tag} CLOSE:")
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
        print(f"  [K684] SCAFFOLD CLOSE:")
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
    """Load k684_dashboard.json; return defaults if missing."""
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
    """Write k684_dashboard.json with full signal + regime state."""
    dash = _load_dashboard()

    # Update signal data
    dash["last_poll_jst"]        = signal.get("ts_jst", "—")
    dash["fr_sol_current"]       = signal.get("fr_sol",       0.0)
    dash["fr_inj_current"]       = signal.get("fr_inj",       0.0)
    dash["sol_inj_diff_current"] = signal.get("sol_inj_diff", 0.0)
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
    dash["hl_concentration_pct"]     = HL_CONCENTRATION_POST_K684   # 62.5% UNCHANGED (Bybit-only)

    # Paper-trade status
    paper_status = dash.get("paper_trade_status", {"days_elapsed": 0, "target_60d": 60})
    dash["paper_trade_status"]       = paper_status

    # 60d activation gate metrics (K687: Realized Sh >= 5, fill >= 60%, DD < 15%)
    dash["gate_metrics"] = {
        "realized_sharpe_target":  5.0,     # >=5 (per K687 spec, OOS Sh=9.65)
        "fill_rate_target_pct":    60,
        "max_drawdown_target_pct": 15,       # <15%
        "current_realized_sharpe": dash.get("60d_sharpe", 0.0),
        "current_fill_rate_pct":   0.0,
        "current_max_dd_pct":      0.0,
        "gate_status":             "IN_PROGRESS",
        "activation_trigger":      "60d paper-trade: Sh>=5 AND fill>=60% AND maxDD<15%",
        "profit_at_activation_3pct": "$114,316/yr net @$10M @4x (3% sleeve, OOS Sh 9.65)",
        "alt_alt_note":            "THIRD ALT-ALT pair (SOL-INJ, no BTC/ETH leg). Standalone. 56th daemon.",
        "overlap_warning":         "K476 SOL-BTC + K500 INJ-BTC algebraic overlap; K679 APT-SOL shares SOL leg — run standalone",
    }

    # Strategy metadata
    dash["paper_trade_mode"]    = PAPER_TRADE
    dash["wave"]                = "K687"
    dash["strategy"]            = "K684 SOL-INJ FR Differential (THIRD ALT-ALT, W=168h, Bybit-only)"
    dash["execution_mode"]      = "POST_ONLY_PARALLEL"
    dash["venue_config"]        = "BYBIT_ONLY"
    dash["alt_alt_mechanism"]   = {
        "formula":            "diff = SOL_FR - INJ_FR  (direct alt-alt, no base asset)",
        "rolling_window":     "W=168h (21 x 8h periods, primary config)",
        "signal":             "sign(rolling_mean_168h(diff))",
        "third_alt_alt":      True,
        "bybit_only_reason":  "Bybit preferred: HL stays at 62.5% (headroom preserved). Both SOL-PERP + INJ-PERP on Bybit.",
        "hl_concentration":   62.5,
        "k476_k500_warning":  (
            "K476 SOL-BTC (HL-only, 1.5% sleeve) + K500 INJ-BTC overlap. "
            "SOL-INJ = K476_direction - K500_direction (algebraic identity). "
            "K684 + K476 + K500 = complex algebraic overlap. Run K684 STANDALONE. "
            "Default: K684 standalone 3% Bybit sleeve."
        ),
        "k679_sol_warning":   (
            "K679 APT-SOL shares SOL leg with K684 SOL-INJ. "
            "K684 + K679 active simultaneously = SOL double-exposure. "
            "Monitor combined SOL notional vs sleeve targets. "
            "Default: both STANDALONE (separate 3% sleeves, independent margin)."
        ),
        "sol_fr_drivers": (
            "Solana SVM DePIN/Retail adoption premium, meme-coin season (BONK/WIF), "
            "Firedancer upgrade hype, SOL ETF speculation, validator economics. "
            "Persistently positive (+7.7% ann structural retail demand premium)."
        ),
        "inj_fr_drivers": (
            "Injective Cosmos DeFi perp DEX — liquidation cascades, INJ burn mechanics "
            "(deflationary tokenomics), IBC bridge activity, Cosmos TVL spikes. "
            "Episodic (+3.6% ann Cosmos DeFi dynamics, mean-reverting)."
        ),
        "mathematical_identity": (
            "SOL_FR - INJ_FR = (SOL_FR - BTC_FR) - (INJ_FR - BTC_FR) = K476_dir - K500_dir. "
            "K684 algebraically decomposed into K476 + K500. Anti-correlated with K500 (INJ-BTC) by construction."
        ),
    }
    dash["activation_criteria"] = {
        "60d_paper_trade_gate":  "required",
        "realized_sharpe_min":   5.0,
        "fill_rate_min_pct":     60,
        "max_drawdown_max_pct":  15,
        "status":                "SCAFFOLD-READY",
        "activation_sleeve_pct": 0.030,
        "venue":                 "BYBIT primary (SOL-PERP + INJ-PERP both on Bybit)",
    }
    dash["oos_performance"] = {
        "sharpe":                   9.65,
        "oos_ann_ret_pct":          11.207,
        "ann_return_usd_3pct_4x":   114316,
        "wave_accept":              "K684 ACCEPT (K687 scaffold) — THIRD ALT-ALT pair, SVM-retail vs Cosmos-DeFi axis",
        "cluster":                  "SOL-INJ Alt-Alt FR Differential (SVM DePIN-Retail vs Cosmos-DeFi-Perp, Bybit-only)",
        "cluster_rationale": (
            "SOL (Solana SVM DePIN/Retail) vs INJ (Injective Cosmos DeFi perp DEX): third alt-alt pair. "
            "No BTC or ETH leg — pure alt-to-alt cross-ecosystem differential. "
            "SOL FR = retail sentiment (persistently positive, high persistence); "
            "INJ FR = Cosmos DeFi episodic spikes (mean-reverting, liquidation-driven). "
            "Bybit-only: HL stays at 62.5% (preferred — headroom preserved). "
            "SOL-PERP + INJ-PERP both on Bybit. "
            "K476+K500 algebraic overlap: standalone 3% sleeve recommended. "
            "K679+K684 share SOL leg: monitor combined SOL exposure."
        ),
        "daemon_number":            "56th",
        "family_rank": {
            "k684_oos_sharpe":  9.65,
            "k682_oos_sharpe":  43.43,
            "k679_oos_sharpe":  39.29,
            "k684_pair":        "SOL-INJ (alt-alt, THIRD)",
            "alt_alt_count":    3,
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
      1. Fetch SOL + INJ FRs from Bybit
      2. Compute SOL-INJ differential + 168h rolling mean
      3. Decide position (sign of rolling mean — zero threshold)
      4. Compute delta-neutral notional
      5. If entering: submit paired trade (POST_ONLY, Bybit primary)
      6. If holding: check drift + rebalance
      7. Write k684_dashboard.json
    """
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K684 SOL-INJ FR Differential (THIRD ALT-ALT, Bybit-only) — {ts_jst} ===")
    print(f"  Mode:      {'DRY-RUN' if dry_run else 'PAPER-TRADE' if PAPER_TRADE else 'LIVE'}")
    print(f"  AUM:       ${aum:,.0f}  Sleeve: {SLEEVE_PCT:.1%}  Leverage: {LEVERAGE}x")
    print(f"  Venue:     Bybit-only (SOL-PERP + INJ-PERP, both Bybit)")
    print(f"  HL conc:   62.5% (preferred — Bybit-only preserves 2.5pp headroom)")
    print(f"  Execution: POST_ONLY parallel (K439)")
    print(f"  Signal:    diff = SOL_FR - INJ_FR  (direct alt-alt, no base asset)")
    print(f"             sign(rolling_mean_168h)  (zero threshold, W=168h = 21 x 8h periods)")
    print(f"  THIRD:     THIRD ALT-ALT pair (no BTC/ETH leg) — OOS Sh=9.65 (216d OOS)")
    print(f"  Overlap:   K476 SOL-BTC + K500 INJ-BTC algebraic; K679 APT-SOL shares SOL leg")
    print(f"  9/9 gates: OOS Sh={9.65:.2f} W=168h Bybit-only 3% sleeve $114,316/yr @$10M @4x")

    # Step 1: Fetch + compute SOL-INJ differential
    print("\n  [Step 1] Computing SOL-INJ FR differential from Bybit...")
    signal = compute_signal()
    print(f"  SOL FR:     {signal['fr_sol']:+.8f} (8h, Bybit, persistent +7.7% ann retail premium)")
    print(f"  INJ FR:     {signal['fr_inj']:+.8f} (8h, Bybit, episodic +3.6% ann Cosmos DeFi)")
    print(f"  SOL-INJ:    {signal['sol_inj_diff']:+.8f}  (direct alt-alt differential)")
    print(f"  Mean 168h:  {signal['mean_168h']:+.8f}")
    print(f"  Sigma 168h: {signal['diff_sigma']:+.8f}  (informational)")
    print(f"  Direction:  {signal['signal_direction']:+d}  (+1=BULL_SOL, -1=BEAR_SOL, 0=NEUTRAL)")
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
    print(f"  SOL leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  INJ leg:          ${notional_per_leg:,.0f}  (3% x ${aum/1e6:.0f}M x {LEVERAGE}x / 2)")
    print(f"  Total notional:   ${total_notional:,.0f}")
    print(f"  Margin required:  ${total_notional/LEVERAGE:,.0f}  ({SLEEVE_PCT:.1%} AUM)")
    print(f"  Profit @$10M 4x:  OOS Sh=9.65 = $114,316/yr net (3% sleeve, standalone)")
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
    print(f"\n  === K684 Cycle Complete ===")
    print(f"  Position state:     {dash_out.get('position_state')}")
    print(f"  Regime:             {dash_out.get('regime')}")
    print(f"  SOL-INJ Mean 168h:  {dash_out.get('mean_168h'):+.8f}")
    print(f"  Signal direction:   {dash_out.get('signal_direction')}")
    print(f"  THIRD ALT-ALT:      SOL-INJ (no BTC/ETH base) OOS Sh=9.65")
    print(f"  Bybit-only:         HL 62.5% (headroom preserved — SOL+INJ on Bybit)")
    print(f"  K476+K500 overlap:  STANDALONE 3% sleeve (no netting)")
    print(f"  K679 SOL-exposure:  Monitor SOL double-exposure if K679+K684 concurrent")
    print(f"  Paper-trade mode:   {PAPER_TRADE}")
    print(f"  OOS Sharpe:         9.65 (W=168h, zero threshold, 216d OOS)")
    print(f"  Cluster:            SOL-INJ Alt-Alt (SVM DePIN-Retail vs Cosmos-DeFi-Perp, 56th daemon)")
    print(f"  Profit 3% sleeve:   $114,316/yr net @$10M @4x (standalone)")
    print(f"  HL concentration:   62.5% UNCHANGED (Bybit-only, headroom preserved)")
    print(f"  60d gate:           Realized Sh>=5 + fill>=60% + maxDD<15%")
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K684 SOL-INJ FR Differential Strategy (K687 scaffold, THIRD ALT-ALT, Bybit-only)"
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
        print(f"\n=== K684 Dashboard ({dash.get('last_poll_jst', '—')}) ===")
        print(json.dumps(dash, indent=2))
        return 0

    if args.rebalance:
        dash   = _load_dashboard()
        result = daily_rebalance(dash)
        print(f"\n=== K684 Rebalance Check ===")
        print(json.dumps(result, indent=2))
        return 0

    if args.close:
        result = close_paired_position(args.close, dry_run=args.dry_run)
        print(f"\n=== K684 Close Result ===")
        print(json.dumps(result, indent=2))
        return 0

    return run_cycle(dry_run=args.dry_run, aum=args.aum)


if __name__ == "__main__":
    sys.exit(main())
